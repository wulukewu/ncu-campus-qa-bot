## 注意事項
### 環境
環境盡量分開，避免套件衝突
環境建立(window,vscode，在terminal打指令):
```
python -m venv .venv #建環境
.venv/Scripts/Activate.ps1 #切環境
```
### 向量庫 (chroma_db)
如果向量庫需做更動，盡量把先前的向量庫刪掉，避免檢索出錯誤資料或資料重複

## 做RAG LLM相關的
### open_webui
用open-webui做rag測試，自己環境建好可以直接用自己的

### rag_server
```
news                 #公告資料
contants.py          #放路徑/模型名稱等通用常數
DBHandler.py         #處理向量庫的
requirements.txt     #必要套件
server.py            #rag server
```
> 目前只針對news/csie_news.csv做向量庫

## 可改進的地方
* 資料的處理方式
    * 需要包含哪些內容(標題/內文)
    * 不同格式的處理(news公告/表格)
    * 日期問題，須給出最新資訊，看要不要給LLM今日日期
* 使用不同的LLM模型
* 修改系統提示詞
* 有時有給檢索到的資訊，回答時卻沒使用