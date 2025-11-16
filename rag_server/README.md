# rag_server
用於儲存向量資料庫以及檢索向量資料庫
```
news                 #公告資料
contants.py          #放路徑/模型名稱等通用常數
DBHandler.py         #處理向量庫的
requirements.txt     #必要套件
server.py            #rag server
```
> 目前只針對news/csie_news.csv做向量庫

 ### 安裝必要套件
```
pip install -r requirements.txt       
```

### 從ollama取模型
```
ollama pull mxbai-embed-large
ollama pull llama3.2:3b
```
更多可pull的模型: https://ollama.com/library


### 建向量庫
```
python DBHandler.py
```

請忽略:
```
Failed to send telemetry event ClientStartEvent: capture() takes 1 positional argument but 3 were given
Failed to send telemetry event ClientCreateCollectionEvent: capture() takes 1 positional argument but 3 were given
```
可以把main裡面註解去掉測試檢索功能

### 啟動rag server
```
uvicorn server:app --host 127.0.0.1 --port 8000
```
> terminal會記錄檢索到的資料