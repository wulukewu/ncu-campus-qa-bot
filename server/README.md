# NCU Campus QA Bot - Server

## 架構說明 (Architecture)

本專案使用 **Gemini API** 實作 RAG (Retrieval-Augmented Generation) 系統：

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│  LINE User  │ ───> │  LINE Bot    │ ───> │   RAG Server    │
│             │      │  (Flask)     │      │  (FastAPI)      │
└─────────────┘      └──────────────┘      └─────────────────┘
                            │                        │
                            │                        ▼
                            │               ┌─────────────────┐
                            │               │  Gemini API     │
                            │               │  - Embedding    │
                            │               │  - Flash Model  │
                            │               └─────────────────┘
                            │                        │
                            │                        ▼
                            │               ┌─────────────────┐
                            └──────────────>│  Vector DB      │
                                           │  (ChromaDB)     │
                                           └─────────────────┘
```

### 核心元件

1. **RAG Server** (`rag_server/`)
   - 使用 Gemini `text-embedding-004` 做文本嵌入
   - 使用 Gemini `gemini-2.0-flash-exp` 生成回答
   - ChromaDB 儲存向量資料庫
   - 目前資料來源：news/csie_news.csv

2. **LINE Bot** (`linebot/`)
   - Flask web server 接收 LINE webhook
   - 轉發用戶訊息至 RAG Server
   - 回傳 AI 生成的答案至 LINE

## 快速開始 (Quick Start)

### 前置需求
- Python 3.11+
- Gemini API Key (從 https://aistudio.google.com/app/apikey 取得)
- LINE Developer Account (從 https://developers.line.biz/ 設定)

### 1. 設定 RAG Server

```bash
cd rag_server
pip install -r requirements.txt

# 設定環境變數
cp .env.example .env
# 編輯 .env 填入 GEMINI_API_KEY

# 建立向量資料庫
python DBHandler.py

# 啟動 RAG Server
uvicorn server:app --host 127.0.0.1 --port 8000
```

### 2. 設定 LINE Bot

```bash
cd linebot
pip install -r requirements.txt

# 設定環境變數
cp .env.example .env
# 編輯 .env 填入 LINE credentials 和 RAG_SERVER_URL

# 啟動 LINE Bot
python app.py
```

### 3. 設定 LINE Webhook

使用 ngrok 在本地測試：
```bash
ngrok http 5000
```

在 LINE Developers Console 設定 webhook URL:
```
https://your-ngrok-url.ngrok.io/callback
```

## 環境注意事項

### 虛擬環境
環境盡量分開，避免套件衝突

建立虛擬環境 (Windows, VSCode):
```bash
python -m venv venv
venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate    # Linux/Mac
```

### 向量庫 (ChromaDB)
如果向量庫需做更動，盡量把先前的向量庫刪掉，避免檢索出錯誤資料或資料重複

```bash
rm -rf rag_server/chroma_db
```

## 專案結構

```
server/
├── rag_server/          # RAG 伺服器
│   ├── server.py        # FastAPI server
│   ├── DBHandler.py     # 向量資料庫處理
│   ├── constants.py     # 設定常數
│   ├── news/            # 公告資料
│   └── chroma_db/       # 向量資料庫
├── linebot/             # LINE Bot 伺服器
│   ├── app.py          # Flask webhook server
│   └── .env            # 環境變數設定
└── open_webui/         # (舊) Open WebUI 測試用
```

## 可改進的地方

* **資料處理方式**
  * 包含更多資料來源 (目前僅有 CSIE news)
  * 不同格式的處理 (表格、PDF、網頁等)
  * 日期問題：需給出最新資訊，考慮給 LLM 今日日期

* **模型優化**
  * 調整 Gemini 模型參數 (temperature, top_k)
  * 嘗試不同的 embedding 模型
  * 修改系統提示詞提升回答品質

* **檢索改進**
  * 有時檢索到資訊但 LLM 沒使用
  * 可加入 reranking 機制
  * 調整 chunk size 和 overlap

## API 端點

### RAG Server (Port 8000)
- `GET /health` - 健康檢查
- `POST /v1/chat/completions` - RAG 查詢
- `GET /debug/files` - 查看已索引文件

### LINE Bot (Port 5000)
- `POST /callback` - LINE webhook endpoint