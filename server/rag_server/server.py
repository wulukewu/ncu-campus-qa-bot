from __future__ import annotations
import os, time, argparse, traceback
from typing import List, Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage

from DBHandler import DBHandler

try:
    from langchain_community.vectorstores import Chroma
except ImportError:
    Chroma = None

from constants import *

app = FastAPI(title="Unified RAG/LLM Server")

parser = argparse.ArgumentParser()
parser.add_argument("--mode", choices=["rag", "llm"], default=os.getenv("MODE", "rag"))
args, _ = parser.parse_known_args()
MODE = args.mode

_state = {"emb": None, "vs": None, "err": None, "mode": MODE}

SYSTEM_PROMPT = (
    "你是中央大學資訊查詢的助理。\n\n"
    "**重要規則：你必須嚴格基於以下提供的資訊來回答問題。**\n"
    "- 如果提供的資訊中有答案，請直接引用並回答\n"
    "- 如果提供的資訊不足以回答問題，請明確說明「根據現有資料無法回答此問題」\n"
    "- 不要使用提供資訊以外的知識來回答\n\n"
    "提供的資訊：\n{context}\n\n"
    "請使用繁體中文回答，並在回答後註明資料來源。"
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
    if Chroma is None:
        raise RuntimeError("Chroma not available; please install langchain_community")

    try:
        emb = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
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
        "llm_model": LLM_MODEL,
        "embed_model": EMBED_MODEL,
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
    return {"object": "list", "data": [{"id": "ncu-rag-ollama", "object": "model"}]}

@app.post("/v1/chat/completions")
def chat(req: ChatCompletionRequest):
    try:
        last_user = ""
        for m in req.messages:
            if m.role == "user":
                last_user = m.content

        llm = ChatOllama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, temperature=req.temperature or 0.1)

        if MODE == "rag":
            ensure_rag_ready()
            context = dbHandler.retrieve_context(_state['vs'], last_user, req.top_k or TOP_K)
            sys_prompt = SYSTEM_PROMPT.format(context=context)
            #ans = llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=last_user)]).content
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
