# NCU Campus QA Bot - Server

## 架構說明 (Architecture)

本專案使用 **Ollama** 與 **Gemini API** 實作 RAG (Retrieval-Augmented Generation) 系統：

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│  LINE User  │ ───> │  LINE Bot    │ ───> │   RAG Server    │
│             │      │  (Flask)     │      │  (FastAPI)      │
└─────────────┘      └──────────────┘      └─────────────────┘
                            │                        │
                            │                        ▼
                            │               ┌─────────────────┐
                            │               │  Ollama         │
                            │               │  - Embedding    │
                            │               │  Gemini API     │
                            │               │  - Flash Model  │
                            │               └─────────────────┘
                            │                        │
                            │                        ▼
                            │               ┌─────────────────┐
                            └──────────────>│  Vector DB      │
                                            │  (ChromaDB)     │
                                            └─────────────────┘
```

## 專案結構

```
server/
├── rag_server/           # RAG 伺服器
│   ├── chroma_db-qwen3/  # 已經建立好的向量庫
│   ├── .env.example      # 環境變數的範例 
│   ├── constants.py      # 放路徑/模型名稱等通用常數
│   ├── requirements.txt  # 必要套件
│   ├── DBHandler.py      # 向量資料庫處理
│   └── server.py         # rag server
├── linebot/            # LINE Bot 伺服器
│   ├── app.py          # Flask webhook server
│   └── .env            # 環境變數設定
└── open_webui/         # (舊) Open WebUI 測試用
```

### 核心元件

1. **RAG Server** (`rag_server/`)
    - 使用LangChain 整合RAG相關功能:
        - 使用 Ollama `qwen3-embedding:0.6b` 做文本嵌入
        - ChromaDB 儲存向量資料庫
    - 使用FastAPI 建立rag server，LLM根據DBHandler檢索到的資料做回覆
        - 使用 Gemini `gemini-2.5-flash` 生成回答

2. **LINE Bot** (`linebot/`)
    - Flask web server 接收 LINE webhook
    - 轉發用戶訊息至 RAG Server
    - 回傳 AI 生成的答案至 LINE

## 快速開始 (Quick Start)

### 前置需求
- Python 3.11+
- Ollama (下載: https://ollama.com/)
- Gemini API Key (從 https://aistudio.google.com/app/apikey 取得)
- ngrok (下載: https://ngrok.com/download/windows)
- LINE Developer Account (從 https://developers.line.biz/ 設定)

### 1. Ollama
獲取embedding模型(本專案使用`qwen3-embedding:0.6b`)
```bash
ollama pull qwen3-embedding:0.6b
```

### 2. 設定 RAG Server

```bash
cd rag_server
pip install -r requirements.txt

# 設定環境變數
cp .env.example .env
# 編輯 .env 填入 GEMINI_API_KEY

# 建立向量資料庫
python DBHandler.py
#將chroma_db-qwen3命名為chroma_db作為RAG使用的向量庫可跳過此步驟

# 啟動 RAG Server
uvicorn server:app --host 127.0.0.1 --port 8000
```

### 3. 設定 LINE Bot

```bash
cd linebot
pip install -r requirements.txt

# 設定環境變數
cp .env.example .env
# 編輯 .env 填入 LINE credentials 和 RAG_SERVER_URL

# 啟動 LINE Bot
python app.py
```

### 4. 設定 LINE Webhook

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


## API 端點

### RAG Server (Port 8000)
- `GET /health` - 健康檢查
- `POST /v1/chat/completions` - RAG 查詢
- `GET /debug/files` - 查看已索引文件

### LINE Bot (Port 5000)
- `POST /callback` - LINE webhook endpoint


## 可改進的地方

* **資料處理方式**
  * 不同格式的處理 (表格、PDF、網頁等)
  * 日期問題：需給出最新資訊，考慮給 LLM 今日日期

* **模型優化**
  * 調整 Gemini 模型參數 (temperature, top_k)
  * 嘗試不同的 embedding 模型
  * 修改系統提示詞提升回答品質

* **檢索改進**
  * 可加入 reranking 機制
  * 調整 chunk size 和 overlap
  * 提供csv/pdf檔案下載連結