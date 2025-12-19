import os
import sys
from typing import List, Tuple
from pathlib import Path
from linebot.v3.messaging import PushMessageRequest, TextMessage
from linebot.v3.messaging.exceptions import ApiException

# Try to import from linebot app module (aliased as linebot_server_app)
try:
    # Check if crawler_worker already loaded it
    import linebot_server_app
    from linebot_server_app import messaging_api, LINE_PUSH_ENABLED
except ImportError:
    # If running standalone, we need to load it manually using importlib
    # because of the name collision with rag_server/app.py
    import importlib.util
    
    current_dir = Path(__file__).resolve().parent
    server_dir = current_dir.parent
    linebot_dir = server_dir / "linebot"
    
    try:
        spec = importlib.util.spec_from_file_location("linebot_server_app", str(linebot_dir / "app.py"))
        linebot_server_app = importlib.util.module_from_spec(spec)
        sys.modules["linebot_server_app"] = linebot_server_app
        spec.loader.exec_module(linebot_server_app)
        
        from linebot_server_app import messaging_api
        
        # Check for LINE_PUSH_ENABLED or load from env
        if hasattr(linebot_server_app, 'LINE_PUSH_ENABLED'):
             LINE_PUSH_ENABLED = linebot_server_app.LINE_PUSH_ENABLED
        else:
             LINE_PUSH_ENABLED = os.getenv("LINE_PUSH_ENABLED", "1") == "1"
             
    except Exception as e:
        print(f"Warning: Could not import messaging_api from linebot/app.py: {e}")
        messaging_api = None
        LINE_PUSH_ENABLED = False

def send_push_message(line_user_id: str, message: str) -> bool:
    """透過 LINE Messaging API 向單一使用者發送訊息"""
    if messaging_api is None:
        print("❌ Messaging API not initialized.")
        return False

    try:
        push_message_request = PushMessageRequest(
            to=line_user_id,
            messages=[TextMessage(text=message)]
        )
        messaging_api.push_message(push_message_request)
        
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
    if not LINE_PUSH_ENABLED:
        print(f"⚠️ PUSH DISABLED: Would have sent new announcement '{title}' to {len(subscribers)} users.")
        return

    message_body = (
        f"\n🎉 國立中央大學【{category}】有新公告！\n"
        f"標題: {title}\n"
        f"連結: {url}"
    )
    
    print(f"Sending push for topic '{category}' to {len(subscribers)} subscribers.")
    
    for _, line_user_id, _ in subscribers:
        send_push_message(line_user_id, message_body)
