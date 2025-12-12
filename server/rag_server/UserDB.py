import sqlite3
from typing import List, Tuple, Optional

DB_PATH = "subscriptions.db"

class UserDB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False) 
        self.cursor = self.conn.cursor()
        self._create_table()

    def _create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id TEXT PRIMARY KEY,
                line_user_id TEXT NOT NULL, 
                topic TEXT NOT NULL,
                enabled INTEGER DEFAULT 1
            )
        """)
        self.conn.commit()

    def subscribe(self, user_id: str, line_user_id: str, topic: str):
        """新增或更新訂閱"""
        self.cursor.execute("""
            INSERT OR REPLACE INTO subscriptions (user_id, line_user_id, topic, enabled) 
            VALUES (?, ?, ?, 1)
        """, (user_id, line_user_id, topic))
        self.conn.commit()

    def get_subscribers(self, topic: Optional[str] = None) -> List[Tuple[str, str, str]]:
        """
        返回 (user_id, line_user_id, topic) 列表。
        """
        if topic:
            self.cursor.execute(
                "SELECT user_id, line_user_id, topic FROM subscriptions WHERE topic = ? AND enabled = 1", (topic,)
            )
        else:
            self.cursor.execute("SELECT user_id, line_user_id, topic FROM subscriptions WHERE enabled = 1")
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()
