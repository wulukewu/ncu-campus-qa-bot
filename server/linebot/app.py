from flask import Flask, request, abort
import requests, pandas as pd, os, io
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError
import re, logging
from PyPDF2 import PdfReader
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# === 基本設定 ===
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LLAMA_API_URL = os.getenv("LLAMA_API_URL")

GITHUB_BASE = (
    "https://raw.githubusercontent.com/wulukewu/ncu-campus-qa-bot/main/crawler/docs/"
)

config = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
api_client = ApiClient(config)
messaging_api = MessagingApi(api_client)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

logging.basicConfig(level=logging.INFO)

knowledge_base = []  # 儲存所有文件文字


# =====================================================
# 讀取 GitHub 上的 csv / txt / pdf
# =====================================================
def load_github_files():
    folders = [
        "adm_news/csv/",
        "oga_news/csv/",
        "csie_news/csv/",
        "adm_regulations/pdf/",
        "adm_course-qa/pdf/",
        "oga_common-qa/csv/",
    ]
    for folder in folders:
        # 嘗試列出常見檔名
        for ext in ["csv", "txt", "pdf"]:
            for name in ["data", "info", "qa", "content"]:
                url = f"{GITHUB_BASE}{folder}{name}.{ext}"
                try:
                    res = requests.get(url)
                    if res.status_code == 200:
                        text = extract_text(res.content, ext)
                        knowledge_base.append((folder, text))
                        print(f"✅ Loaded: {url}")
                        break
                except Exception as e:
                    print(f"❌ Error reading {url}: {e}")


def extract_text(file_bytes, ext):
    if ext == "csv":
        df = pd.read_csv(io.BytesIO(file_bytes))
        return df.to_string(index=False)
    elif ext == "txt":
        return file_bytes.decode("utf-8", errors="ignore")
    elif ext == "pdf":
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    return ""


# =====================================================
# 從知識庫搜尋最相關的片段
# =====================================================
def search_knowledge(question):
    question_lower = question.lower()
    best_match = None
    best_score = 0

    for folder, text in knowledge_base:
        # 簡單文字比對
        score = sum(word in text.lower() for word in question_lower.split())
        if score > best_score:
            best_score = score
            best_match = (folder, text[:2000])  # 限制長度避免太大
    return best_match


# =====================================================
# 丟給 Llama 產生回答
# =====================================================
def ask_llama(question, context):
    payload = {
        "model": "llama-3.2-1b-instruct",
        "messages": [
            {
                "role": "system",
                "content": "你是中央大學智慧客服，根據提供的資料回答問題",
            },
            {"role": "user", "content": f"資料內容：{context}\n\n問題：{question}"},
        ],
        "temperature": 0.7,
        "max_tokens": 500,
    }
    res = requests.post(LLAMA_API_URL, json=payload)
    if res.status_code == 200:
        return res.json()["choices"][0]["message"]["content"]
    return f"模型錯誤：{res.status_code}"


# =====================================================
# LINE webhook
# =====================================================
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    question = event.message.text.strip()
    match = search_knowledge(question)
    if match:
        folder, context = match
        answer = ask_llama(question, context)
    else:
        answer = "抱歉，我目前找不到相關資料。"

    reply = ReplyMessageRequest(
        reply_token=event.reply_token, messages=[TextMessage(text=answer)]
    )
    messaging_api.reply_message(reply)


if __name__ == "__main__":
    print("📚 正在從 GitHub 載入資料...")
    load_github_files()
    print(f"✅ 知識庫載入完成，共 {len(knowledge_base)} 份文件。")
    app.run(port=5000)
