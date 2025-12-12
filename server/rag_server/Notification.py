import os
from dotenv import load_dotenv
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, TextMessage
from linebot.v3.messaging.exceptions import ApiException
from typing import List, Tuple
load_dotenv()
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_PUSH_ENABLED = os.getenv("LINE_PUSH_ENABLED", "1") == "1"
if not CHANNEL_ACCESS_TOKEN:
    raise ValueError("LINE_CHANNEL_ACCESS_TOKEN environment variable is not set.")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

def push_new_announcement(subscribers: List[Tuple[str, str, str]], title: str, url: str, category: str):
    if not LINE_PUSH_ENABLED:
        print(f"⚠️ PUSH DISABLED: Would have sent new announcement '{title}' to {len(subscribers)} users.")
        return
    
def send_push_message(line_user_id: str, message: str) -> bool:
    """透過 LINE Messaging API 向單一使用者發送訊息"""
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            
            push_message_request = PushMessageRequest(
                to=line_user_id,
                messages=[TextMessage(text=message)]
            )
            line_bot_api.push_message(push_message_request)
            
            print(f"✅ Message sent successfully to user {line_user_id[-4:]}")
            return True
    except ApiException as e:
        print(f"❌ LINE Messaging API failed for user {line_user_id[-4:]}: {e.status} - {e.body}")
        return False
    except Exception as e:
        print(f"❌ LINE Messaging API request failed: {e}")
        return False

def push_new_announcement(subscribers: List[Tuple[str, str, str]], title: str, url: str, category: str):
    """向所有訂閱者推播新公告 (line_user_id 在 subscribers 的第二個元素)"""
    message_body = (
        f"\n🎉 國立中央大學【{category}】有新公告！\n"
        f"標題: {title}\n"
        f"連結: {url}"
    )
    
    print(f"Sending push for topic '{category}' to {len(subscribers)} subscribers.")
    
    for _, line_user_id, _ in subscribers:
        send_push_message(line_user_id, message_body)
