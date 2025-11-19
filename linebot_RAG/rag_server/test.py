# 假設您在 .venv 環境中運行
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings

DB_DIR = r"./chroma_db"
EMBED_MODEL = "mxbai-embed-large"
EMBED_BASE_URL = "http://127.0.0.1:11434"

# 1. 載入嵌入模型
emb = OllamaEmbeddings(model=EMBED_MODEL, base_url=EMBED_BASE_URL)

# 2. 載入 ChromaDB
vs = Chroma(
    persist_directory=DB_DIR,
    embedding_function=emb,
    collection_name="local_docs" # 確保這裡也是 local_docs
)

# 3. 執行檢索測試
query = "告訴我最近有關 course 的信息"
# k=3 表示檢索三個最相關的文檔片段
results = vs.similarity_search(query, k=3)

print("--- 檢索結果 ---")
for doc in results:
    print(f"來源: {doc.metadata.get('source', 'N/A')}")
    print(f"內容: {doc.page_content[:200]}...") # 打印前200個字符
    print("-" * 20)