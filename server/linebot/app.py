from flask import Flask, request, abort
import requests, pandas as pd, os, io, re, logging
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
from PyPDF2 import PdfReader
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# === 基本設定 ===
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LLAMA_API_URL = os.getenv("LLAMA_API_URL")

LOCAL_DOCS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../crawler/docs"))

config = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
api_client = ApiClient(config)
messaging_api = MessagingApi(api_client)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

logging.basicConfig(level=logging.INFO)

knowledge_base = []  # 所有文件的純文字內容


def load_local_files():
    folders = [
        "adm_course-form",
        "adm_course-qa/pdf",
        "adm_courses/pdf",
        "adm_freshman/pdf",
        "adm_news/csv",
        "adm_registration-form/pdf",
        "adm_registration-qa/pdf",
        "adm_regulations/pdf",
        "adm_statistics",
        "adm_tution/pdf",
        "csie_news/csv",
        "oga_common-qa/csv",
        "oga_news/csv",
    ]

    for folder in folders:
        folder_path = os.path.join(LOCAL_DOCS_PATH, folder)
        print(f"📂 Checking folder: {folder_path}")

        if not os.path.isdir(folder_path):
            print(f"❌ Folder not found: {folder_path}")
            continue

        for root, _, files in os.walk(folder_path):
            for name in files:
                if not any(name.endswith(ext) for ext in [".csv", ".txt", ".pdf"]):
                    continue

                file_path = os.path.join(root, name)
                print(f"📄 Reading {name}")

                with open(file_path, "rb") as f:
                    file_bytes = f.read()
                
                ext = name.split(".")[-1]
                text = extract_text(file_bytes, ext)

                knowledge_base.append((folder, text))

    print(f"✅ 知識庫載入完成，共 {len(knowledge_base)} 份文件。")


def extract_text(file_bytes, ext):
    if ext == "csv":
        try:
            df = pd.read_csv(io.BytesIO(file_bytes))
            return df.to_string(index=False)
        except pd.errors.EmptyDataError:
            print(f"⚠️  Skipping empty csv file.")
            return ""
    elif ext == "txt":
        return file_bytes.decode("utf-8", errors="ignore")
    elif ext == "pdf":
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        except Exception as e:
            print(f"⚠️  Skipping problematic pdf file: {e}")
            return ""
    return ""


# =====================================================
# 搜尋知識庫
# =====================================================
def search_knowledge(question):
    question_lower = question.lower()
    best_match = None
    best_score = 0

    for folder, text in knowledge_base:
        score = sum(word in text.lower() for word in question_lower.split())
        if score > best_score:
            best_score = score
            best_match = (folder, text[:2000])

    return best_match


# =====================================================
# 呼叫 LLaMA 作答
# =====================================================
def ask_llama(question, context):
    payload = {
        "model": "llama-3.2-1b-instruct",
        "messages": [
            {
                "role": "system",
                "content": "你是中央大學智慧客服，根據提供的資料回答問題。",
            },
            {"role": "user", "content": f"資料：\n{context}\n\n問題：{question}"},
        ],
        "temperature": 0.7,
        "max_tokens": 500,
    }

    res = requests.post(LLAMA_API_URL, json=payload)
    if res.status_code == 200:
        return res.json()["choices"][0]["message"]["content"]

    return f"模型錯誤：HTTP {res.status_code}"


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
        reply_token=event.reply_token,
        messages=[TextMessage(text=answer)],
    )
    messaging_api.reply_message(reply)


# =====================================================
# 啟動伺服器
# =====================================================
if __name__ == "__main__":
    print("📚 從本地端載入資料中...")
    load_local_files()
    app.run(port=5000)