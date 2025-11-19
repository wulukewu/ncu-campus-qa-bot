from __future__ import annotations
import os, time, argparse, traceback
from typing import List, Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage

from langchain_chroma import Chroma
from chromadb import PersistentClient
import traceback

vs = None 
emb = None 

app = FastAPI(title="Unified RAG/LLM Server")

parser = argparse.ArgumentParser()
parser.add_argument("--mode", choices=["rag", "llm"], default=os.getenv("MODE", "rag"))
args, _ = parser.parse_known_args()
MODE = args.mode

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2")
EMBED_MODEL = os.getenv("EMBED_MODEL", "mxbai-embed-large")
DB_DIR = os.getenv("DB_DIR", r"C:\linebot_RAG\rag_server\chroma_db") 
TOP_K = int(os.getenv("TOP_K", "5"))


SYSTEM_PROMPT = (
    "你是一位專門回答中央大學(NCU)相關問題的知識型助理。請**嚴格根據**我提供的 `{context}` 內容來回答使用者的問題。\n"
    "**請仔細整合 Context 中的資訊，並根據問題的性質分類並條列出來。** 例如：如果問通用資訊，請分類為 學術公告、活動快訊、行政資訊等。如果問單一資訊，請只回答該資訊。\n"
    "如果 Context 中沒有足夠的資訊回答問題，你必須明確地說「根據提供的資料，我無法回答這個問題。」**不要編造答案。**\n\n"
    "Context:\n{context}\n"
)

_state = {"emb": None, "vs": None, "err": None, "mode": MODE}

class Message(BaseModel):
    model_config = ConfigDict(extra="allow")
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.2
    top_k: Optional[int] = None
    stream: Optional[bool] = False

def ensure_rag_ready():
    global vs, emb

    if vs is not None:
        return

    print("--- RAG Initialization ---")
    
    try:
        emb = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
        
        client = PersistentClient(path=DB_DIR)
        
        vs = Chroma(
            client=client,
            embedding_function=emb,
            collection_name="local_docs"
        )
        
        doc_count = vs._collection.count()
        if doc_count == 0:
            print("[WARNING] ChromaDB collection 'local_docs' is empty. Please run ingest.py.")
        
        _state["vs"] = vs
        _state["emb"] = emb
        
        print(f"RAG ready. DB path: {DB_DIR}. Total chunks: {doc_count}")

    except Exception as e:
        print(f"[RAG Init Error] Failed to initialize Chroma: {e}")
        traceback.print_exc()
        _state["err"] = str(e)
        raise RuntimeError("Failed to initialize ChromaDB. Check the DB_DIR path and chroma.sqlite3 file.")

@app.get("/health")
def health():
    return {
        "ok": True,
        "mode": MODE,
        "llm_model": LLM_MODEL,
        "embed_model": EMBED_MODEL,
        "db_path": DB_DIR,
        "ready": (_state["vs"] is not None) if MODE == "rag" else True,
        "init_error": _state["err"],
    }


@app.get("/api/version")
def api_version():
    """
    Open WebUI 需要這個接口來確認 Ollama 的版本。
    """
    return {"version": "0.1.48"}

@app.get("/api/tags")
def api_tags():
    """
    Open WebUI 需要這個接口來取得模型列表。
    """
    return {
        "models": [
            {
                "name": "rag-ollama",
                "model": "rag-ollama",
                "version": "1.0.0",
                "modified_at": "2023-01-01T00:00:00Z",
                "size": 0,
                "digest": "sha256:000000",
                "details": {
                    "format": "gguf",
                    "family": "llama",
                    "families": ["llama"],
                    "parameter_size": "7B",
                    "quantization_level": "Q4_0"
                }
            }
        ]
    }

@app.get("/v1/models")
def models():
    """
    OpenAI 兼容格式的模型列表接口。
    """
    return {"object": "list", "data": [{"id": "rag-ollama", "object": "model"}]}


@app.get("/debug/files")
def debug_files():
    """
    用於檢查 RAG 向量資料庫狀態和已索引檔案的統計資訊。
    """
    ensure_rag_ready()
    
    if _state["vs"] is None:
        return JSONResponse(content={"error": "RAG not initialized. Check server logs."}, status_code=500)

    try:
        metas = _state["vs"]._collection.get(include=["metadatas"])
        
        files = {}
        for meta in metas.get("metadatas", []):
            source = meta.get("source", "Unknown")
            files[source] = files.get(source, 0) + 1

        return JSONResponse(content={
            "status": "RAG Ready",
            "db_path": DB_DIR,
            "collection_count": _state["vs"]._collection.count(),
            "files_indexed": files
        })
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(content={"error": f"Failed to retrieve collection metadata: {e}"}, status_code=500)


def retrieve_context(query: str, k: int) -> str:
    try:
        ensure_rag_ready()
        
        if _state["vs"] is None:
             print("[retrieve] RAG not ready.")
             return "No context found."
             
        docs = _state["vs"].similarity_search(query, k=k)
        return "\n\n".join(
            f"[DOC {i+1}] {d.metadata.get('source','')}\n{d.page_content}"
            for i, d in enumerate(docs)
        )
    except Exception as e:
        print("[retrieve] error:", e)
        traceback.print_exc()
        return ""

@app.post("/v1/chat/completions")
def chat(req: ChatCompletionRequest):
    try:
        last_user = ""
        for m in req.messages:
            if m.role == "user":
                last_user = m.content

        llm = ChatOllama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, temperature=req.temperature or 0.2)

        if MODE == "rag":
            context = retrieve_context(last_user, req.top_k or TOP_K)
            print("--- RETRIEVED CONTEXT ---")
            print(context)
            print("-------------------------")
            
            sys_prompt = SYSTEM_PROMPT.format(context=context)
            ans = llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=last_user)]).content
        else:
            ans = llm.invoke(last_user).content

        return JSONResponse(content={
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": req.model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": ans}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        })
    except Exception as e:
        print("[/v1/chat/completions] error:", e)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e), "trace": traceback.format_exc()})