# database/manager.py

import os
import sqlite3
import json
import psycopg2
from psycopg2 import pool
from typing import List, Dict, Any, Optional
from datetime import datetime
from services.logger import logger

class DatabaseManager:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self.is_postgres = self.db_url and self.db_url.startswith("postgres")
        self._pool = None
        self._sqlite_conn = None
        
        if self.is_postgres:
            self._init_pool()
        else:
            self._init_sqlite()
            
        self._init_db()

    @property
    def placeholder(self):
        return "%s" if self.is_postgres else "?"

    def _prepare_query(self, query: str) -> str:
        """Converts generic ? placeholders to platform-specific ones."""
        if self.is_postgres:
            return query.replace("?", "%s")
        return query

    def _init_pool(self):
        try:
            # Handle heroku postgres:// vs postgresql://
            url = self.db_url.replace("postgres://", "postgresql://") if self.db_url else None
            self._pool = psycopg2.pool.SimpleConnectionPool(
                1, 20, dsn=url, sslmode='require'
            )
            logger.info("[DB] PostgreSQL connection pool initialized.")
        except Exception as e:
            logger.error(f"[DB] PostgreSQL pool initialization failed: {e}")

    def _init_sqlite(self):
        db_path = "bot_database.db"
        try:
            self._sqlite_conn = sqlite3.connect(db_path, check_same_thread=False)
            self._sqlite_conn.execute("PRAGMA journal_mode=WAL")
            self._sqlite_conn.execute("PRAGMA synchronous=NORMAL")
            logger.info("[DB] SQLite persistent connection initialized (WAL mode).")
        except Exception as e:
            logger.error(f"[DB] SQLite initialization failed: {e}")

    def _get_connection(self):
        if self.is_postgres:
            if not self._pool: self._init_pool()
            conn = self._pool.getconn()
            from psycopg2.extras import RealDictCursor
            return conn, conn.cursor(cursor_factory=RealDictCursor)
        else:
            return self._sqlite_conn, self._sqlite_conn.cursor()

    def _release_connection(self, conn):
        if self.is_postgres and self._pool:
            self._pool.putconn(conn)

    def _init_db(self):
        conn, cursor = self._get_connection()
        try:
            queries = [
                '''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''',
                '''CREATE TABLE IF NOT EXISTS mirror_health (
                    url TEXT PRIMARY KEY,
                    fail_count INTEGER DEFAULT 0,
                    last_fail DOUBLE PRECISION DEFAULT 0,
                    last_success DOUBLE PRECISION DEFAULT 0,
                    is_active INTEGER DEFAULT 1
                )''',
                '''CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    name TEXT,
                    user_id INTEGER,
                    status TEXT DEFAULT 'active',
                    options TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''',
                '''CREATE TABLE IF NOT EXISTS sources (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER,
                    platform TEXT,
                    identifier TEXT,
                    last_check_id TEXT,
                    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
                )''',
                '''CREATE TABLE IF NOT EXISTS destinations (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER,
                    platform TEXT,
                    identifier TEXT,
                    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
                )''',
                '''CREATE TABLE IF NOT EXISTS processed_items (
                    item_id TEXT PRIMARY KEY,
                    source_id INTEGER,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )'''
            ]
            
            # Revert SERIAL/DOUBLE for SQLite
            if not self.is_postgres:
                queries = [q.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT") for q in queries]
                queries = [q.replace("DOUBLE PRECISION", "REAL") for q in queries]
            
            for q in queries:
                cursor.execute(q)
            conn.commit()
            logger.info("[DB] Core tables verified.")
        except Exception as e:
            logger.error(f"[DB] Schema initialization error: {e}")
            conn.rollback()
        finally:
            self._release_connection(conn)

    def execute(self, query: str, params: tuple = ()):
        query = self._prepare_query(query)
        conn, cursor = self._get_connection()
        try:
            cursor.execute(query, params)
            conn.commit()
        except Exception as e:
            logger.error(f"[DB] Execute error: {e}")
            conn.rollback()
        finally:
            self._release_connection(conn)

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        query = self._prepare_query(query)
        conn, cursor = self._get_connection()
        try:
            cursor.execute(query, params)
            res = cursor.fetchone()
            if self.is_postgres: return res
            return dict(res) if res else None
        finally:
            self._release_connection(conn)

    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict]:
        query = self._prepare_query(query)
        conn, cursor = self._get_connection()
        try:
            cursor.execute(query, params)
            res = cursor.fetchall()
            if self.is_postgres: return res
            return [dict(row) for row in res]
        finally:
            self._release_connection(conn)

    # --- Mirror Management ---
    def update_mirror_status(self, url: str, success: bool):
        ts = datetime.now().timestamp()
        if success:
            sql = f"""INSERT INTO mirror_health (url, last_success, is_active) VALUES ({self.placeholder}, {self.placeholder}, 1) 
                      ON CONFLICT(url) DO UPDATE SET fail_count=0, last_success=EXCLUDED.last_success, is_active=1"""
            self.execute(sql, (url, ts))
        else:
            sql = f"""INSERT INTO mirror_health (url, last_fail, fail_count) VALUES ({self.placeholder}, {self.placeholder}, 1) 
                      ON CONFLICT(url) DO UPDATE SET fail_count=mirror_health.fail_count+1, last_fail=EXCLUDED.last_fail, is_active=CASE WHEN mirror_health.fail_count > 5 THEN 0 ELSE 1 END"""
            self.execute(sql, (url, ts))

    def get_active_mirrors(self) -> List[str]:
        res = self.fetch_all("SELECT url FROM mirror_health WHERE is_active=1 ORDER BY last_success DESC, fail_count ASC")
        return [r['url'] for r in res]

    def register_mirror(self, url: str):
        if self.is_postgres:
            self.execute("INSERT INTO mirror_health (url) VALUES (%s) ON CONFLICT DO NOTHING", (url,))
        else:
            self.execute("INSERT OR IGNORE INTO mirror_health (url) VALUES (?)", (url,))

    # --- Task Management ---
    def create_task(self, name: str, user_id: int, options: dict) -> int:
        query = f"INSERT INTO tasks (name, user_id, options) VALUES ({self.placeholder}, {self.placeholder}, {self.placeholder})"
        if self.is_postgres:
            query += " RETURNING id"
            conn, cursor = self._get_connection()
            cursor.execute(query, (name, user_id, json.dumps(options)))
            res = cursor.fetchone()
            conn.commit()
            self._release_connection(conn)
            return res['id']
        else:
            self.execute(query, (name, user_id, json.dumps(options)))
            res = self.fetch_one("SELECT last_insert_rowid() as id")
            return res['id']

    def add_source(self, task_id: int, platform: str, identifier: str):
        self.execute("INSERT INTO sources (task_id, platform, identifier) VALUES (?, ?, ?)", (task_id, platform, identifier))

    def add_destination(self, task_id: int, platform: str, identifier: str):
        self.execute("INSERT INTO destinations (task_id, platform, identifier) VALUES (?, ?, ?)", (task_id, platform, identifier))

    def get_tasks(self, user_id: int) -> List[Dict]:
        return self.fetch_all("SELECT * FROM tasks WHERE user_id=?", (user_id,))

    def get_task_details(self, task_id: int) -> Optional[Dict]:
        task = self.fetch_one("SELECT * FROM tasks WHERE id=?", (task_id,))
        if task:
            task['sources'] = self.fetch_all("SELECT * FROM sources WHERE task_id=?", (task_id,))
            task['destinations'] = self.fetch_all("SELECT * FROM destinations WHERE task_id=?", (task_id,))
            task['options'] = json.loads(task['options'])
        return task

    def update_source_last_id(self, source_id: int, last_id: str):
        self.execute("UPDATE sources SET last_check_id=? WHERE id=?", (last_id, source_id))

    def is_item_processed(self, item_id: str) -> bool:
        res = self.fetch_one("SELECT 1 FROM processed_items WHERE item_id=?", (item_id,))
        return res is not None

    def mark_item_processed(self, item_id: str, source_id: int):
        if self.is_postgres:
            self.execute("INSERT INTO processed_items (item_id, source_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (item_id, source_id))
        else:
            self.execute("INSERT OR IGNORE INTO processed_items (item_id, source_id) VALUES (?, ?)", (item_id, source_id))

    def set_setting(self, key: str, value: str):
        if self.is_postgres:
            self.execute("INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (key, value))
        else:
            self.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))

    def get_setting(self, key: str) -> Optional[str]:
        res = self.fetch_one("SELECT value FROM settings WHERE key=?", (key,))
        return res['value'] if res else None

    def delete_task(self, task_id: int):
        self.execute("DELETE FROM tasks WHERE id=?", (task_id,))

# Global Instance
db = DatabaseManager()
