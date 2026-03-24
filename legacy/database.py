# database.py

import os
import sqlite3
import json
from typing import Optional, List, Dict

# Check for Heroku/External PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")

class Database:
    """A database wrapper that supports both SQLite and PostgreSQL."""

    def __init__(self):
        self.is_postgres = DATABASE_URL is not None
        self._init_db()

    def _get_connection(self):
        if self.is_postgres:
            import psycopg2
            # Heroku requires sslmode=require for external connections
            return psycopg2.connect(DATABASE_URL, sslmode='prefer')
        else:
            return sqlite3.connect("cache.db", check_same_thread=False)

    def _init_db(self):
        conn = self._get_connection()
        cur = conn.cursor()
        
        # Processed messages table
        if self.is_postgres:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS processed (
                    message_id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS last_processed (
                    task_id TEXT,
                    source_id TEXT,
                    last_id TEXT,
                    PRIMARY KEY (task_id, source_id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bot_config (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS processed (
                    message_id TEXT PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS last_processed (
                    task_id TEXT,
                    source_id TEXT,
                    last_id TEXT,
                    PRIMARY KEY (task_id, source_id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bot_config (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
        conn.commit()
        conn.close()

    def execute(self, query: str, params: tuple = ()):
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            # PostgreSQL uses %s, SQLite uses ?
            if not self.is_postgres:
                query = query.replace("%s", "?")
            cur.execute(query, params)
            conn.commit()
        except Exception as e:
            print(f"[Database Error] {e}")
            conn.rollback()
        finally:
            conn.close()

    def fetchone(self, query: str, params: tuple = ()):
        conn = self._get_connection()
        cur = conn.cursor()
        if not self.is_postgres:
            query = query.replace("%s", "?")
        cur.execute(query, params)
        result = cur.fetchone()
        conn.close()
        return result

    def fetchall(self, query: str, params: tuple = ()):
        conn = self._get_connection()
        cur = conn.cursor()
        if not self.is_postgres:
            query = query.replace("%s", "?")
        cur.execute(query, params)
        results = cur.fetchall()
        conn.close()
        return results

    # --- Task & Config Helpers ---
    def save_tasks(self, tasks_list: List[Dict]):
        tasks_json = json.dumps(tasks_list)
        if self.is_postgres:
            self.execute(
                "INSERT INTO bot_config (key, value) VALUES (%s, %s) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                ("tasks", tasks_json)
            )
        else:
            self.execute(
                "INSERT OR REPLACE INTO bot_config (key, value) VALUES (?, ?)",
                ("tasks", tasks_json)
            )

    def load_tasks(self) -> Optional[List[Dict]]:
        result = self.fetchone("SELECT value FROM bot_config WHERE key = %s", ("tasks",))
        if result:
            return json.loads(result[0])
        return None

    def get_last_processed_id(self, task_id: str, source_id: str) -> Optional[str]:
        result = self.fetchone(
            "SELECT last_id FROM last_processed WHERE task_id=%s AND source_id=%s",
            (task_id, source_id)
        )
        return result[0] if result else None

    def set_last_processed_id(self, task_id: str, source_id: str, last_id: str):
        if self.is_postgres:
            self.execute(
                "INSERT INTO last_processed (task_id, source_id, last_id) VALUES (%s, %s, %s) "
                "ON CONFLICT (task_id, source_id) DO UPDATE SET last_id = EXCLUDED.last_id",
                (task_id, source_id, str(last_id))
            )
        else:
            self.execute(
                "INSERT OR REPLACE INTO last_processed (task_id, source_id, last_id) VALUES (?, ?, ?)",
                (task_id, source_id, str(last_id))
            )

    def set_config(self, key: str, value: str):
        if self.is_postgres:
            self.execute(
                "INSERT INTO bot_config (key, value) VALUES (%s, %s) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                (key, value)
            )
        else:
            self.execute(
                "INSERT OR REPLACE INTO bot_config (key, value) VALUES (?, ?)",
                (key, value)
            )

    def get_config(self, key: str) -> Optional[str]:
        result = self.fetchone("SELECT value FROM bot_config WHERE key = %s", (key,))
        return result[0] if result else None

# Global instance
db = Database()
