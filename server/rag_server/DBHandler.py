import traceback
from langchain_text_splitters import RecursiveCharacterTextSplitter
import pandas as pd
from pathlib import Path
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from langchain_chroma import Chroma
    
from constants import *

#用於儲存向量資料庫以及檢索向量資料庫
class DBHandler:
    def __init__(self):
        Path(DB_DIR).mkdir(parents=True, exist_ok=True)

    #將每筆公告(news)各整理成一份doc，回傳整理後的docs
    #department_name: 學校哪個部門的資訊
    #目前是針對資工系公告做的，其他格式不同
    def buildNewsDocs(self, department_name="csie"):
        docs = []
        title_col_name = 'list_title'
        content_col_name = 'detail_text'
        
        path = "news/" + department_name + "_news.csv"
        df = pd.read_csv(path, encoding="utf-8")

        n_docs = len(df)
        #將資料分成一筆筆公告的doc
        for i in range(n_docs):
            #每筆公告
            content = f"[標題] {df[title_col_name].iloc[i]}\n"
            content += f"[內容] {df[content_col_name].iloc[i]}"
            
            metadata = {
                'id':       str(i+1),
                'title':    str(df['list_title'].iloc[i]),
                'source':   str(df['url'].iloc[i]),
                'category': str(df['category'].iloc[i]),
                'date':     str(df['list_date'].iloc[i])
            }

            doc = Document(
                page_content=content,
                metadata=metadata
            )

            docs.append(doc)
        print(f"Loaded docs: {len(docs)}")
        return docs

    #建向量庫
    def buildDB(self, collection_name, docs, doc_split=False, batch_size=50):
        import time
        from langchain_google_genai._common import GoogleGenerativeAIError
        
        emb = GoogleGenerativeAIEmbeddings(
            model=GEMINI_EMBED_MODEL,
            google_api_key=GEMINI_API_KEY
        )
        _ = emb.embed_query("ping")
        print("Embedding warmup OK")

        if doc_split:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, chunk_overlap=100,
                separators=["\n\n", "\n", "。", "，", " ", ""],
            )
            docs = splitter.split_documents(docs)
            print(f"Split into chunks: {len(docs)}")

        # Process in batches with retry logic
        print(f"\nProcessing {len(docs)} documents in batches of {batch_size}...")
        
        # Create vector store with first batch
        first_batch = docs[:batch_size]
        remaining_docs = docs[batch_size:]
        
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                print(f"Creating vector store with first {len(first_batch)} documents (attempt {attempt + 1}/{max_retries})...")
                vs = Chroma.from_documents(
                    documents=first_batch,
                    embedding=emb,
                    persist_directory=DB_DIR,
                    collection_name=collection_name,
                )
                break
            except GoogleGenerativeAIError as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  Error: {str(e)[:100]}...")
                    print(f"   Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise
        
        # Add remaining documents in batches
        if remaining_docs:
            total_batches = (len(remaining_docs) + batch_size - 1) // batch_size
            for i in range(0, len(remaining_docs), batch_size):
                batch = remaining_docs[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                
                for attempt in range(max_retries):
                    try:
                        print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} docs, attempt {attempt + 1}/{max_retries})...")
                        vs.add_documents(batch)
                        time.sleep(1)  # Rate limiting
                        break
                    except GoogleGenerativeAIError as e:
                        if attempt < max_retries - 1:
                            print(f"⚠️  Error: {str(e)[:100]}...")
                            print(f"   Retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                            retry_delay = min(retry_delay * 1.5, 60)  # Exponential backoff, max 60s
                        else:
                            print(f"❌ Failed to process batch {batch_num} after {max_retries} attempts")
                            print(f"   Continuing with next batch...")
                            continue
        
        # Persist is automatic in newer langchain-chroma, but we can explicitly save
        print(f"\n✅ Successfully processed {len(docs)} documents")
        print("Chroma DB built at", DB_DIR)

    #從vecter_store檢所前k個最相似的docs
    def retrieve_context(self, vecter_store, query: str, k: int) -> str:
        try:
            docs = vecter_store.similarity_search(query, k=k)
            return "\n\n".join(
                f"[DOC {i+1}]"
                f"[id] {d.metadata.get('id','無')}\n"
                f"[標題] {d.metadata.get('title','無')}\n"
                f"[來源] {d.metadata.get('source','無')}\n"
                f"[日期] {d.metadata.get('date','無')}\n"
                f"[內容]\n{d.page_content}"
                for i, d in enumerate(docs)
            )
        except Exception as e:
            print("[retrieve] error:", e)
            traceback.print_exc()
            return ""

#用來建向量庫的
if __name__ == "__main__":
    dbHandler = DBHandler()
    
    docs= dbHandler.buildNewsDocs()
    print(docs[1])
    
    # Process in smaller batches to avoid API rate limits
    # Use batch_size=25 for more reliable processing
    print(f"\n{'='*80}")
    print(f"Starting database build...")
    print(f"Total documents loaded: {len(docs)}")
    print(f"Will process: {min(500, len(docs))} documents")
    print(f"{'='*80}\n")
    
    dbHandler.buildDB(
        collection_name=COLLECTION_NAME,
        docs=docs[:500],  # Process first 500 for testing
        batch_size=25      # Smaller batches = more reliable
    )
    
    print("\n" + "="*80)
    print("✅ 儲存完成")
    print("="*80)
    
    #請忽略:
    #Failed to send telemetry event ClientStartEvent: capture() takes 1 positional argument but 3 were given
    #Failed to send telemetry event ClientCreateCollectionEvent: capture() takes 1 positional argument but 3 were given

    
    #測試檢索功能用的
    emb = GoogleGenerativeAIEmbeddings(
        model=GEMINI_EMBED_MODEL,
        google_api_key=GEMINI_API_KEY
    )
    _ = emb.embed_query("ping")
    vs = Chroma(persist_directory=DB_DIR, embedding_function=emb, collection_name=COLLECTION_NAME)
    query = input("請輸入文字查詢相似文章:\n")
    while query!="QUIT":
        context = dbHandler.retrieve_context(vs, query, 10)
        print(context)
        query = input()
    