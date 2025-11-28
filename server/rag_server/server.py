from __future__ import annotations
import os, time, argparse, traceback
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama.embeddings import OllamaEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage

from DBHandler import DBHandler

from langchain_chroma import Chroma

from constants import *

app = FastAPI(title="NCU RAG Server with Gemini")

parser = argparse.ArgumentParser()
parser.add_argument("--mode", choices=["rag", "llm"], default=os.getenv("MODE", "rag"))
args, _ = parser.parse_known_args()
MODE = args.mode

_state = {"emb": None, "vs": None, "err": None, "mode": MODE}

SYSTEM_PROMPT = (
    "你是國立中央大學的校園資訊助理。請根據以下提供的資料來回答問題。\n\n"
    "回答規則：\n"
    "1. **盡力回答**：根據提供的「參考資料」，盡可能完整回答使用者的問題。\n"
    "2. **誠實為上**：如果資料中沒有相關資訊，請誠實地回答「根據我目前所知的資料，無法回答您的問題。」\n"
    "3. **引用來源**：在回答的結尾，請務必附上資料來源，格式為「資料來源：[來源檔案名稱]」。如果有多個來源，請都列出來。\n"
    "4. **保持簡潔**：回答力求簡潔、直接，並使用繁體中文。\n\n"
    "---參考資料---\n"
    "{context}\n"
    "---"
)

#用於儲存向量資料庫以及檢索向量資料庫
dbHandler = DBHandler()

class Message(BaseModel):
    model_config = ConfigDict(extra="allow")
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.1
    top_k: Optional[int] = None
    stream: Optional[bool] = False

def ensure_rag_ready(collection_name=COLLECTION_NAME):
    if _state["vs"] is not None:
        return

    try:
        emb = OllamaEmbeddings(model=OLLAMA_EMBED_MODEL, base_url=OLLAMA_BASE_URL)
        _ = emb.embed_query("ping")
        vs = Chroma(persist_directory=DB_DIR, embedding_function=emb, collection_name=collection_name)
        _state["emb"] = emb
        _state["vs"] = vs
        _state["err"] = None
    except Exception as e:
        _state["err"] = f"init failed: {e}"
        raise

@app.get("/health")
def health():
    return {
        "ok": True,
        "mode": MODE,
        "llm_model": GEMINI_FLASH_MODEL,
        "embed_model": OLLAMA_EMBED_MODEL,
        "db_path": DB_DIR,
        "ready": (_state["vs"] is not None) if MODE == "rag" else True,
        "init_error": _state["err"],
    }

@app.get("/debug/files")
def debug_files():
    ensure_rag_ready()
    metas = _state["vs"]._collection.get(include=["metadatas"])
    sources = sorted(set(m.get("source") for m in metas["metadatas"] if m.get("source")))
    return {"count": len(sources), "sources": sources}

@app.get("/v1/models")
def models():
    return {"object": "list", "data": [{"id": "ncu-rag-gemini", "object": "model"}]}

@app.post("/v1/chat/completions")
def chat(req: ChatCompletionRequest):
    try:
        last_user = ""
        for m in req.messages:
            if m.role == "user":
                last_user = m.content

        llm = ChatGoogleGenerativeAI(
            model=GEMINI_FLASH_MODEL,
            google_api_key=GEMINI_API_KEY,
            temperature=req.temperature or 0.1
        )

        if MODE == "rag":
            ensure_rag_ready()
            context = dbHandler.retrieve_context(_state['vs'], last_user, req.top_k or TOP_K)
            sys_prompt = SYSTEM_PROMPT.format(context=context)
            ans = llm.invoke([HumanMessage(content=sys_prompt+last_user)]).content
        else:
            ans = llm.invoke(last_user).content

        print('='*80)
        print("USER:"+last_user)
        if MODE == "rag":
            print("與問題相關之資訊:")
            print(context)
        print('-'*80)
        print("ASSISTANT:")
        print(ans)
        print('='*80)

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
