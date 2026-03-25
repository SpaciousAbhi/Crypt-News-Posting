# database/manager.py

import os
import sqlite3
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv("DATABASE_URL", "bot_data.db")
        self.is_postgres = self.db_url.startswith("postgres://") or self.db_url.startswith("postgresql://")
        
        # Handle Heroku's postgres:// vs postgresql://
        if self.is_postgres and self.db_url.startswith("postgres://"):
            self.db_url = self.db_url.replace("postgres://", "postgresql://", 1)
            
        self._init_db()

    def _get_connection(self):
        if self.is_postgres:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(self.db_url)
            return conn, conn.cursor(cursor_factory=RealDictCursor)
        else:
            conn = sqlite3.connect(self.db_url)
            conn.row_factory = sqlite3.Row
            return conn, conn.cursor()

    def _init_db(self):
        conn, cursor = self._get_connection()
        
        # SQL for both SQLite and Postgres (mostly compatible)
        queries = [
            # Global Settings
            """CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            
            # Tasks
            """CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                user_id BIGINT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                config TEXT, -- Task-specific JSON config
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""" if self.is_postgres else 
            """CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                config TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            
            # Sources
            """CREATE TABLE IF NOT EXISTS sources (
                id SERIAL PRIMARY KEY,
                task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
                platform TEXT NOT NULL,
                identifier TEXT NOT NULL,
                config TEXT, -- Store JSON here
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""" if self.is_postgres else 
            """CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
                platform TEXT NOT NULL,
                identifier TEXT NOT NULL,
                config TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            
            # Destinations
            """CREATE TABLE IF NOT EXISTS destinations (
                id SERIAL PRIMARY KEY,
                task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
                platform TEXT NOT NULL,
                identifier TEXT NOT NULL,
                config TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""" if self.is_postgres else 
            """CREATE TABLE IF NOT EXISTS destinations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
                platform TEXT NOT NULL,
                identifier TEXT NOT NULL,
                config TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            
            # Processed State tracking
            """CREATE TABLE IF NOT EXISTS processed_items (
                task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
                source_id INTEGER REFERENCES sources(id) ON DELETE CASCADE,
                item_id TEXT NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (task_id, source_id, item_id)
            )""" if self.is_postgres else 
            """CREATE TABLE IF NOT EXISTS processed_items (
                task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
                source_id INTEGER REFERENCES sources(id) ON DELETE CASCADE,
                item_id TEXT NOT NULL,
                processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (task_id, source_id, item_id)
            )""",
            
            # Dynamic Source Items (Capture)
            """CREATE TABLE IF NOT EXISTS source_items (
                id SERIAL PRIMARY KEY,
                identifier TEXT NOT NULL,
                platform TEXT NOT NULL,
                content TEXT,
                media_json TEXT, -- JSON string of media URLs
                item_id TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""" if self.is_postgres else 
            """CREATE TABLE IF NOT EXISTS source_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                identifier TEXT NOT NULL,
                platform TEXT NOT NULL,
                content TEXT,
                media_json TEXT,
                item_id TEXT UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
        ]
        
        try:
            for query in queries:
                cursor.execute(query)
            
            # Migration: Add config column to tasks if missing
            try:
                if self.is_postgres:
                    cursor.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS config TEXT")
                else:
                    cursor.execute("ALTER TABLE tasks ADD COLUMN config TEXT")
            except:
                pass # Already exists or other error handled gracefully
                
            conn.commit()
        finally:
            conn.close()

    def execute(self, query: str, params: tuple = ()):
        conn, cursor = self._get_connection()
        try:
            # Handle placeholder difference
            if not self.is_postgres:
                query = query.replace("%s", "?")
            
            cursor.execute(query, params)
            conn.commit()
            return cursor
        finally:
            conn.close()

    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        conn, cursor = self._get_connection()
        try:
            if not self.is_postgres:
                query = query.replace("%s", "?")
                
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        results = self.fetch_all(query, params)
        return results[0] if results else None

    # --- Settings CRUD ---
    def set_setting(self, key: str, value: str):
        if self.is_postgres:
            query = """INSERT INTO settings (key, value) VALUES (%s, %s) 
                       ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP"""
        else:
            query = "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (%s, %s, CURRENT_TIMESTAMP)"
        self.execute(query, (key, value))

    def get_setting(self, key: str) -> Optional[str]:
        row = self.fetch_one("SELECT value FROM settings WHERE key = %s", (key,))
        return row['value'] if row else None

    # --- Task Management ---
    def create_task(self, name: str, user_id: int, config: Dict[str, Any] = {}) -> int:
        conn, cursor = self._get_connection()
        try:
            placeholder = "%s" if self.is_postgres else "?"
            query = f"INSERT INTO tasks (name, user_id, config) VALUES ({placeholder}, {placeholder}, {placeholder})"
            if self.is_postgres:
                query += " RETURNING id"
                cursor.execute(query, (name, user_id, json.dumps(config)))
                task_id = cursor.fetchone()['id']
            else:
                cursor.execute(query, (name, user_id, json.dumps(config)))
                task_id = cursor.lastrowid
            conn.commit()
            return task_id
        finally:
            conn.close()

    def update_task(self, task_id: int, updates: Dict[str, Any]):
        """Updates task fields (name, config, is_active)."""
        if not updates:
            return
            
        fields = []
        params = []
        for k, v in updates.items():
            if k == 'config':
                v = json.dumps(v)
            fields.append(f"{k} = %s")
            params.append(v)
        
        params.append(task_id)
        query = f"UPDATE tasks SET {', '.join(fields)} WHERE id = %s"
        self.execute(query, tuple(params))

    def get_tasks(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        if user_id:
            query = "SELECT * FROM tasks WHERE user_id = %s ORDER BY created_at DESC"
            return self.fetch_all(query, (user_id,))
        return self.fetch_all("SELECT * FROM tasks ORDER BY created_at DESC")

    def delete_task(self, task_id: int):
        self.execute("DELETE FROM tasks WHERE id = %s", (task_id,))

    # --- Source & Destination CRUD ---
    def add_source(self, task_id: int, platform: str, identifier: str, config: Dict[str, Any] = {}):
        self.execute(
            "INSERT INTO sources (task_id, platform, identifier, config) VALUES (%s, %s, %s, %s)",
            (task_id, platform, identifier, json.dumps(config))
        )

    def add_destination(self, task_id: int, platform: str, identifier: str, config: Dict[str, Any] = {}):
        self.execute(
            "INSERT INTO destinations (task_id, platform, identifier, config) VALUES (%s, %s, %s, %s)",
            (task_id, platform, identifier, json.dumps(config))
        )

    def get_task_details(self, task_id: int) -> Dict[str, Any]:
        task = self.fetch_one("SELECT * FROM tasks WHERE id = %s", (task_id,))
        if not task:
            return None
        
        # Resilient access to avoid KeyError during migration
        cfg_str = task.get('config')
        task['config'] = json.loads(cfg_str) if cfg_str else {}
        
        task['sources'] = self.fetch_all("SELECT * FROM sources WHERE task_id = %s", (task_id,))
        task['destinations'] = self.fetch_all("SELECT * FROM destinations WHERE task_id = %s", (task_id,))
        
        # Deserialize JSON configs
        for s in task['sources']:
            s['config'] = json.loads(s['config']) if s['config'] else {}
        for d in task['destinations']:
            d['config'] = json.loads(d['config']) if d['config'] else {}
            
        return task

    # --- Processed State ---
    def is_item_processed(self, task_id: int, source_id: int, item_id: str) -> bool:
        row = self.fetch_one(
            "SELECT 1 FROM processed_items WHERE task_id = %s AND source_id = %s AND item_id = %s",
            (task_id, source_id, item_id)
        )
        return row is not None

    def mark_item_processed(self, task_id: int, source_id: int, item_id: str):
        try:
            self.execute(
                "INSERT INTO processed_items (task_id, source_id, item_id) VALUES (%s, %s, %s)",
                (task_id, source_id, item_id)
            )
        except:
            pass # Already exists

    # --- Source Item Capture ---
    def add_source_item(self, identifier: str, platform: str, content: str, item_id: str, media_urls: List[str] = []):
        try:
            self.execute(
                "INSERT INTO source_items (identifier, platform, content, item_id, media_json) VALUES (%s, %s, %s, %s, %s)",
                (identifier, platform, content, item_id, json.dumps(media_urls))
            )
        except Exception as e:
            # logger.error(f"[DB] Failed to add source item: {e}")
            pass # Duplicate item_id

    def get_unread_source_items(self, identifier: str, platform: str, limit: int = 5) -> List[Dict[str, Any]]:
        query = "SELECT * FROM source_items WHERE identifier = %s AND platform = %s ORDER BY created_at DESC LIMIT %s"
        return self.fetch_all(query, (identifier, platform, limit))

# Global Instance
db = DatabaseManager()
