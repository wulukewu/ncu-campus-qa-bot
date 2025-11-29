# rag_server
實作RAG功能
* DBHandler.py: 儲存向量資料庫以及檢索向量資料庫
* server.py: 使用FastAPI建立rag server，LLM根據DBHandler檢索到的資料做回覆

```
chroma_db-qwen3/     #已經建立好的向量庫
.env.example         #環境變數的範例 
constants.py         #放路徑/模型名稱等通用常數
DBHandler.py         #處理向量庫的
requirements.txt     #必要套件
server.py            #rag server
```

## 設定
### 1. Ollama
取得embedding模型
```bash
ollama pull qwen3-embedding:0.6b
```

### 2. 安裝必要套件
```bash
pip install -r requirements.txt       
```

### 3. 設定環境變數
複製 `.env.example` 為 `.env` 並設定你的 Gemini API Key:
```bash
cp .env.example .env
```

編輯 `.env` 檔案:
```
GEMINI_API_KEY=your_gemini_api_key_here
MODE=rag
```
取得 Gemini API Key: https://aistudio.google.com/app/apikey

### 4. 建向量庫
```bash
python DBHandler.py
```
將chroma_db-qwen3命名為chroma_db作為RAG使用的向量庫可跳過此步驟

### 5. 啟動 RAG Server
```bash
uvicorn server:app --host 127.0.0.1 --port 8000
```
> terminal會記錄檢索到的資料

## API 端點

- `GET /health` - 檢查伺服器狀態
- `GET /v1/models` - 列出可用模型
- `POST /v1/chat/completions` - RAG 查詢端點
- `GET /debug/files` - 查看已索引的文件

## 使用的模型

- **Embedding**: `qwen3-embedding:0.6b` (使用Ollama在本地端跑)
- **LLM**: `gemini-2.5-flash` (Gemini Flash)

> embedding 模型參考: https://docs.google.com/spreadsheets/d/1zad1tMFp7OmNjUvm_a-Ni22av2uBmqYclVRgJQGUtl0/edit?usp=drive_linkhttps://docs.google.com/spreadsheets/d/1zad1tMFp7OmNjUvm_a-Ni22av2uBmqYclVRgJQGUtl0/edit?usp=drive_link