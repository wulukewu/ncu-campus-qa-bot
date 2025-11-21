from flask import Flask, request, abort
import requests
import os
import logging
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
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# === 基本設定 ===
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
RAG_SERVER_URL = os.getenv("RAG_SERVER_URL", "http://127.0.0.1:8000/v1/chat/completions")

config = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
api_client = ApiClient(config)
messaging_api = MessagingApi(api_client)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

logging.basicConfig(level=logging.INFO)


# =====================================================
# 呼叫 RAG Server
# =====================================================
def ask_rag_server(question):
    """Call the RAG server with Gemini API to get answers"""
    try:
        payload = {
            "model": "ncu-rag-gemini",
            "messages": [
                {"role": "user", "content": question}
            ],
            "temperature": 0.1
        }

        logging.info(f"Calling RAG server: {RAG_SERVER_URL}")
        res = requests.post(RAG_SERVER_URL, json=payload, timeout=30)
        
        if res.status_code == 200:
            response_data = res.json()
            answer = response_data["choices"][0]["message"]["content"]
            return answer
        else:
            logging.error(f"RAG server error: HTTP {res.status_code}")
            return f"抱歉，系統暫時無法回應。請稍後再試。(錯誤碼: {res.status_code})"
    except requests.exceptions.Timeout:
        logging.error("RAG server timeout")
        return "抱歉，系統回應時間過長。請稍後再試。"
    except Exception as e:
        logging.error(f"Error calling RAG server: {e}")
        return "抱歉，系統發生錯誤。請稍後再試。"


# =====================================================
# LINE webhook
# =====================================================
@app.route("/")
def home():
    """Simple health check endpoint"""
    return {
        "status": "running",
        "service": "NCU LINE Bot",
        "rag_server": RAG_SERVER_URL,
        "endpoints": {
            "webhook": "/callback",
            "health": "/"
        }
    }


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
    """Handle incoming messages from LINE"""
    question = event.message.text.strip()
    logging.info(f"Received question: {question}")
    
    # Call RAG server to get answer
    answer = ask_rag_server(question)
    
    # Reply to user
    reply = ReplyMessageRequest(
        reply_token=event.reply_token,
        messages=[TextMessage(text=answer)],
    )
    messaging_api.reply_message(reply)


# =====================================================
# 啟動伺服器
# =====================================================
if __name__ == "__main__":
    import os
    
    print("🤖 NCU LINE Bot with Gemini RAG Server")
    print(f"📡 RAG Server URL: {RAG_SERVER_URL}")
    print(f"🌐 Server will be accessible at: http://0.0.0.0:5000")
    
    # Get debug mode from environment
    debug_mode = os.getenv('FLASK_DEBUG', '0') == '1'
    
    if debug_mode:
        print("⚠️  Running in DEBUG mode with hot reload")
    
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)