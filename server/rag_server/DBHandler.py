import traceback
from langchain_text_splitters import RecursiveCharacterTextSplitter
import pandas as pd
from pathlib import Path
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document

try:
    from langchain_community.vectorstores import Chroma
except ImportError:
    Chroma = None
    
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
    def buildDB(self, collection_name, docs, doc_split=False):
        emb = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
        _ = emb.embed_query("ping")
        print("Embedding warmup OK")

        if doc_split:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, chunk_overlap=100,
                separators=["\n\n", "\n", "。", "，", " ", ""],
            )
            docs = splitter.split_documents(docs)
            
            print(f"Split into chunks: {len(doc_split)}")

        vs = Chroma.from_documents(
            documents=docs,
            embedding=emb,
            persist_directory=DB_DIR,
            collection_name=collection_name,
        )
        vs.persist()
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
    #全部3000多筆太多可以試試分批存
    dbHandler.buildDB(collection_name=COLLECTION_NAME, docs=docs[:500]) #暫時用前n筆公告測試
    print("儲存完成")
    
    #請忽略:
    #Failed to send telemetry event ClientStartEvent: capture() takes 1 positional argument but 3 were given
    #Failed to send telemetry event ClientCreateCollectionEvent: capture() takes 1 positional argument but 3 were given

    
    #測試檢索功能用的
    emb = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
    _ = emb.embed_query("ping")
    vs = Chroma(persist_directory=DB_DIR, embedding_function=emb, collection_name=COLLECTION_NAME)
    query = input("請輸入文字查詢相似文章:\n")
    while query!="QUIT":
        context = dbHandler.retrieve_context(vs, query, 10)
        print(context)
        query = input()
    