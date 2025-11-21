# rag_server
用於儲存向量資料庫以及檢索向量資料庫 (使用 Gemini API)

```
news                 #公告資料
constants.py         #放路徑/模型名稱等通用常數
DBHandler.py         #處理向量庫的
requirements.txt     #必要套件
server.py            #rag server
```
> 目前只針對news/csie_news.csv做向量庫

## 設定

### 1. 安裝必要套件
```bash
pip install -r requirements.txt       
```

### 2. 設定環境變數
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

### 3. 建向量庫
```bash
python DBHandler.py
```

可以把 main 裡面註解去掉測試檢索功能

### 4. 啟動 RAG Server
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

- **Embedding**: `text-embedding-004` (Gemini)
- **LLM**: `gemini-2.5-flash` (Gemini Flash)