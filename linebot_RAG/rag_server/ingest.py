import os
from pathlib import Path
from langchain_ollama import OllamaEmbeddings
from langchain_community.document_loaders import PyPDFLoader, TextLoader, DirectoryLoader, CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from chromadb import PersistentClient 

DOCS_DIR = r"./docs"
DB_DIR = r"C:\linebot_RAG\rag_server\chroma_db"
EMBED_BASE_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "mxbai-embed-large"

def build_docs():
    loaders = [
        DirectoryLoader(DOCS_DIR, glob="**/*.pdf", loader_cls=PyPDFLoader),
        DirectoryLoader(DOCS_DIR, glob="**/*.txt", loader_cls=TextLoader),
        DirectoryLoader(DOCS_DIR, glob="**/*.md", loader_cls=TextLoader),
        DirectoryLoader(
            DOCS_DIR, 
            glob="**/*.csv", 
            loader_cls=CSVLoader, 
            loader_kwargs={"encoding": "utf8"} 
        ),
    ]
    docs = []
    for loader in loaders:
        try:
            docs.extend(loader.load())
        except Exception as e:
            print(f"[Loader Error] Failed to load documents: {e}") 
    return docs

if __name__ == "__main__":
    Path(DB_DIR).mkdir(parents=True, exist_ok=True)
    docs = build_docs()
    print(f"Loaded docs: {len(docs)}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200,
        separators=["\n\n", "\n", "。", "，", " ", ""],
    )
    splits = splitter.split_documents(docs)
    print(f"Split into chunks: {len(splits)}")

    emb = OllamaEmbeddings(model=EMBED_MODEL, base_url=EMBED_BASE_URL)
    _ = emb.embed_query("ping")
    print("Embedding warmup OK")

    client = PersistentClient(path=DB_DIR)

    vs = Chroma.from_documents(
        documents=splits,
        embedding=emb,
        client=client, 
        collection_name="local_docs",
    )
    print("Chroma DB built at", DB_DIR)