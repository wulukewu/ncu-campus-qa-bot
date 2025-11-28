import os
import traceback
import pandas as pd
import shutil
from pathlib import Path
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_ollama import OllamaEmbeddings

from langchain_core.documents import Document
from pypdf import PdfReader

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from constants import *


# 用於儲存向量資料庫以及檢索向量資料庫
class DBHandler:
    def __init__(self):
        Path(DB_DIR).mkdir(parents=True, exist_ok=True)
        self.docs_dir = Path(DOCS_DIR)
        self.emb=self.getEmbeddings()

    def getEmbeddings(self):
        # 優先從環境變數讀取 OLLAMA_BASE_URL
        base_url = os.getenv("OLLAMA_BASE_URL")
        if not base_url:
            # 如果未設置環境變數，則根據是否在 Docker 中來決定預設值
            if os.path.exists('/.dockerenv'):
                base_url = "http://host.docker.internal:11434"
            else:
                base_url = "http://localhost:11434"
        
        return OllamaEmbeddings(
            model=OLLAMA_EMBED_MODEL,
            base_url=base_url
        )

    def _log_error(self, message):
        print(f"❌ Error: {message}")

    def _log_info(self, message):
        print(f"ℹ️  {message}")

    def _load_pdf(self, file_path: Path) -> list[Document]:
        try:
            self._log_info(f"Processing PDF: {file_path.name}")
            reader = PdfReader(file_path)
            full_text = "".join(page.extract_text() for page in reader.pages if page.extract_text())

            if not full_text:
                self._log_info(f"No text extracted from PDF: {file_path.name}")
                return []

            metadata = {
                'id': file_path.stem,
                'title': file_path.stem,
                'source': str(file_path.resolve()),
                'category': file_path.parent.name,
                'date': ""  # PDFs don't have a reliable date field
            }
            doc = Document(page_content=full_text, metadata=metadata)
            return [doc]
        except Exception as e:
            self._log_error(f"Failed to process PDF {file_path.name}: {e}")
            return []

    def _load_csv(self, file_path: Path) -> list[Document]:
        try:
            self._log_info(f"Processing CSV: {file_path.name}")

            # Special handling for news.csv, which has a clear structure
            if 'news.csv' in file_path.name:
                try:
                    df = pd.read_csv(file_path, encoding="utf-8")
                    # Check for expected columns
                    expected_cols = ['list_title', 'detail_text', 'url', 'category', 'list_date']
                    if not all(col in df.columns for col in expected_cols):
                         raise ValueError(f"Missing one of the expected columns in {file_path.name}")

                    docs = []
                    for i, row in df.iterrows():
                        content = f"[標題] {row['list_title']}\n[內容] {row['detail_text']}"
                        metadata = {
                            'id': f"{file_path.stem}_{i+1}",
                            'title': str(row['list_title']),
                            'source': str(row['url']),
                            'category': str(row['category']),
                            'date': str(row['list_date'])
                        }
                        doc = Document(page_content=content, metadata=metadata)
                        docs.append(doc)
                    return docs
                except Exception as e:
                    self._log_error(f"Could not process structured CSV {file_path.name}: {e}. Falling back to generic processing.")
            
            # Generic processing for all other CSVs
            df = pd.read_csv(file_path, header=None, encoding="utf-8", on_bad_lines='skip')
            if df.empty:
                self._log_info(f"CSV file is empty or could not be read: {file_path.name}")
                return []
            
            # Concatenate all rows into a single document
            full_content = "\n".join([",".join(row.astype(str)) for _, row in df.iterrows()])
            
            if not full_content.strip():
                self._log_info(f"No content in CSV: {file_path.name}")
                return []

            metadata = {
                'id': file_path.stem,
                'title': file_path.stem,
                'source': str(file_path.resolve()),
                'category': file_path.parent.name,
                'date': ""
            }
            return [Document(page_content=full_content, metadata=metadata)]

        except pd.errors.EmptyDataError:
            self._log_info(f"Skipping empty or malformed CSV: {file_path.name}")
            return []
        except Exception as e:
            self._log_error(f"Failed to process CSV {file_path.name}: {e}")
            return []

    def build_all_docs(self):
        """Scans the DOCS_DIR, processes all PDF and CSV files, and yields Documents one by one."""
        if not self.docs_dir.exists():
            self._log_error(f"Documents directory not found at: {self.docs_dir.resolve()}")
            return

        self._log_info(f"Scanning for documents in: {self.docs_dir.resolve()}")
        
        files = list(self.docs_dir.rglob("*.pdf")) + list(self.docs_dir.rglob("*.csv"))
        
        if not files:
            self._log_info("No PDF or CSV files found in the document directory.")
            return
            
        self._log_info(f"Found {len(files)} files to process.")

        for file_path in files:
            if file_path.suffix == ".pdf":
                yield from self._load_pdf(file_path)
            elif file_path.suffix == ".csv":
                yield from self._load_csv(file_path)

    # 建向量庫
    def buildDB(self, collection_name, doc_split=False, batch_size=50):
        docs_generator = self.build_all_docs()

        try:
            first_doc = [next(docs_generator)]
        except StopIteration:
            self._log_error("No documents found to build database. Aborting.")
            return
        
        import time

        _ = self.emb.embed_query("ping")
        print("Embedding warmup OK")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000, chunk_overlap=200,
            separators=["\n\n", "\n", "。", "，", " ", ""],
        )
        
        # Split the first document
        if doc_split:
            first_doc = splitter.split_documents(first_doc)

        print(f"Creating vector store with the first document...")
        
        # Create vector store with the first doc
        vs = Chroma.from_documents(
            documents=first_doc,
            embedding=self.emb,
            persist_directory=DB_DIR,
            collection_name=collection_name,
        )

        # Process the rest of the documents in batches
        batch = []
        for doc in docs_generator:
            batch.append(doc)
            if len(batch) >= batch_size:
                if doc_split:
                    split_batch = splitter.split_documents(batch)
                    print(f"Processing batch of {len(batch)} docs (split into {len(split_batch)} chunks)...")
                    vs.add_documents(split_batch)
                else:
                    print(f"Processing batch of {len(batch)} docs...")
                    vs.add_documents(batch)
                batch = []
        
        # Add any remaining documents in the last batch
        if batch:
            if doc_split:
                split_batch = splitter.split_documents(batch)
                print(f"Processing final batch of {len(batch)} docs (split into {len(split_batch)} chunks)...")
                vs.add_documents(split_batch)
            else:
                print(f"Processing final batch of {len(batch)} docs...")
                vs.add_documents(batch)

        print(f"\n✅ Successfully processed documents.")
        print(f"Chroma DB built at: {Path(DB_DIR).resolve()}")


    # 從vecter_store檢所前k個最相似的docs
    def retrieve_context(self, vecter_store, query: str, k: int) -> str:
        try:
            if vecter_store is None:
                self._log_error("Vector store is not available.")
                return ""
            docs = vecter_store.similarity_search(query, k=k)
            return "\n\n".join(
                #f"[DOC {i+1}]"
                #f"[id] {d.metadata.get('id','無')}\n"
                f"[標題] {d.metadata.get('title','無')}\n"
                f"[來源] {d.metadata.get('source','無')}\n"
                f"[日期] {d.metadata.get('date','無')}\n"
                f"[內容]\n{d.page_content}"
                for i, d in enumerate(docs)
            )
        except Exception as e:
            self._log_error(f"Retrieve error: {e}")
            traceback.print_exc()
            return ""


# 用來建向量庫的
if __name__ == "__main__":
    dbHandler = DBHandler()

    print(f"\n{'='*80}")
    print(f"Starting database build from all documents...")
    
    dbHandler.buildDB(
        collection_name=COLLECTION_NAME,
        doc_split=True,
        batch_size=100  # Larger batch size can be more efficient if memory allows
    )
    
    print("\n" + "="*80)
    print("✅ Database build process finished.")
    print("="*80)

    # 3. Test retrieval (optional)
    print("\nTesting retrieval function...")
    try:
        emb = dbHandler.getEmbeddings()
        vs = Chroma(persist_directory=DB_DIR, embedding_function=emb, collection_name=COLLECTION_NAME)
        
        query = input("請輸入文字查詢相似文章 (or type QUIT):\n> ")
        while query.upper() != "QUIT":
            if query:
                context = dbHandler.retrieve_context(vs, query, 5)
                print("\n--- Retrieved Context ---\n")
                print(context)
                print("\n--- End of Context ---\n")
            query = input("> ")
    except Exception as e:
        print(f"An error occurred during test retrieval: {e}")
    