import os
import sys
import time
import shutil
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List 
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

# Add linebot directory to sys.path to allow importing app.py directly
# We cannot verify "import linebot" because linebot is also a pip package name
# We cannot "import app" because rag_server has its own app.py
current_dir = Path(__file__).resolve().parent
server_dir = current_dir.parent
linebot_dir = server_dir / "linebot"

# Load linebot .env
linebot_env_path = linebot_dir / ".env"
if linebot_env_path.exists():
    print(f"Loading environment from {linebot_env_path}")
    load_dotenv(linebot_env_path)

# Use importlib to load linebot/app.py as a distinct module to avoid name collision
try:
    import importlib.util
    import sys
    
    spec = importlib.util.spec_from_file_location("linebot_server_app", str(linebot_dir / "app.py"))
    line_bot_app = importlib.util.module_from_spec(spec)
    sys.modules["linebot_server_app"] = line_bot_app
    spec.loader.exec_module(line_bot_app)
    
    print("✅ Successfully loaded linebot/app.py as linebot_server_app")
except Exception as e:
    print(f"Warning: Could not import linebot app: {e}")
    line_bot_app = None

from DBHandler import DBHandler
from UserDB import UserDB
from Notification import push_new_announcement

import app as crawler_app
from langchain_core.documents import Document 

CRAWL_CSV_PATH = Path("docs/news.csv")
BACKUP_CSV_PATH = Path("docs/news_backup.csv")
TARGET_TOPIC = "資電院公告" 
CRAWL_CATEGORIES = ["系辦公告", "演講公告"] 

db_handler = DBHandler()
user_db = UserDB()

def compare_and_process_new_docs(old_csv_path: Path, new_csv_path: Path, is_initial_run: bool = False):
    
    if not new_csv_path.exists():
        print("❌ New CSV file not found. Skipping update.")
        return

    try:
        new_df = pd.read_csv(new_csv_path, encoding="utf-8").fillna('')
        old_urls = set()
        if old_csv_path.exists():
            old_df = pd.read_csv(old_csv_path, encoding="utf-8").fillna('')
            old_urls = set(old_df['url'].tolist())
    except Exception as e:
        print(f"❌ Error loading/parsing CSVs: {e}")
        return

    new_announcements = new_df[~new_df['url'].isin(old_urls)]
    
    if new_announcements.empty:
        print("ℹ️ No new announcements found.")
        return

    print(f"✨ Found {len(new_announcements)} new announcements!")

    new_docs: List[Document] = []
    
    for _, row in new_announcements.iterrows():
        content = f"[標題] {row['list_title']}\n[內容] {row['detail_text']}"
        metadata = {
            'id': f"crawler_{row['url']}",
            'title': str(row['list_title']),
            'source': str(row['url']),
            'category': str(row['category']),
            'date': str(row['list_date'])
        }
        new_docs.append(Document(page_content=content, metadata=metadata))

    db_handler.add_documents(new_docs, doc_split=True)
    print("✅ RAG Vector DB updated with new documents.")

    if is_initial_run:
        print("⚠️ Initial run complete. Push notification skipped to prevent cold-start flood.")
        return

    subscribers = user_db.get_subscribers(TARGET_TOPIC)
    if subscribers:
        for _, row in new_announcements.iterrows():
            push_new_announcement(
                subscribers, 
                row['list_title'], 
                row['url'], 
                row['category']
            )
    else:
        print("ℹ️ No subscribers found for push notification.")

def scheduled_task(is_initial_run: bool = False):
    """定期執行的排程任務"""
    
    if is_initial_run:
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting INITIAL RAG DB build task...")
    else:
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting SCHEDULED RAG update and notification task...")
        
        if CRAWL_CSV_PATH.exists():
            shutil.copy(CRAWL_CSV_PATH, BACKUP_CSV_PATH)
            print(f"Backed up old CSV to {BACKUP_CSV_PATH}")

    try:
        crawler_app.crawl(
            CRAWL_CATEGORIES,
            output_csv=str(CRAWL_CSV_PATH),
            delay=0.5
        )
        print("Crawler finished successfully.")
    except SystemExit:
        pass
    except Exception as e:
        print(f"❌ Crawler failed with error: {e}")
        return

    compare_and_process_new_docs(BACKUP_CSV_PATH, CRAWL_CSV_PATH, is_initial_run=is_initial_run)
    
    print("Task finished.")

if __name__ == "__main__":
    print("Starting Worker Scheduler...")
    
    if not BACKUP_CSV_PATH.exists():
        print("⚠️ First run detected. Running full crawl to establish baseline...")
        
        scheduled_task(is_initial_run=True)
        
        if CRAWL_CSV_PATH.exists():
            shutil.copy(CRAWL_CSV_PATH, BACKUP_CSV_PATH)
            print("✅ Baseline established. All existing data is now considered 'old'.")
        else:
            print("❌ Initial crawl failed, cannot establish baseline. Please check the crawler.")
            exit()
    
    scheduler = BlockingScheduler()

    scheduler.add_job(
        scheduled_task, 
        'date', 
        run_date=datetime.now(), 
        id='initial_run_job', 
        kwargs={'is_initial_run': False}
    )

    scheduler.add_job(
        scheduled_task, 
        'interval', 
        hours=4, 
        id='rag_update_job', 
        kwargs={'is_initial_run': False}
    )

    try:
        print("🔄 Scheduler started. Press Ctrl+C to exit.")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\nWorker stopped by user.")
        pass