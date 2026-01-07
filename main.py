# main.py

import os
import time
import sqlite3
import snscrape.modules.twitter as sntwitter

from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Bot
from rapidfuzz import fuzz

# Import custom modules
from config import TASKS
from ai_utils import modify_message

# Load configuration from .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GROQ_KEY        = os.getenv('GROQ_API_KEY')
POLL_INTERVAL   = int(os.getenv('POLL_INTERVAL', 300))
DUPLICATE_THRESHOLD = 85

# Initialize Telegram bot
bot = Bot(token=TELEGRAM_TOKEN)

# Initialize SQLite cache
conn = sqlite3.connect('cache.db', check_same_thread=False)
cur  = conn.cursor()
cur.execute(
    """CREATE TABLE IF NOT EXISTS processed (
           tweet_id TEXT PRIMARY KEY,
           summary  TEXT,
           timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
       )"""
)
conn.commit()

# --- Cache Helper Functions ---

def is_processed(tid: str) -> bool:
    cur.execute('SELECT 1 FROM processed WHERE tweet_id=?', (tid,))
    return cur.fetchone() is not None

def mark_processed(tid: str, summary: str):
    cur.execute(
        'INSERT INTO processed (tweet_id, summary) VALUES (?, ?)',
        (tid, summary)
    )
    conn.commit()

def is_duplicate(summary: str) -> bool:
    cur.execute('SELECT summary FROM processed ORDER BY timestamp DESC LIMIT 100')
    for (old,) in cur.fetchall():
        if fuzz.token_set_ratio(summary, old) >= DUPLICATE_THRESHOLD:
            return True
    return False

# --- Telegram Helper Function ---

def post_to_targets(msg: str, targets: list):
    for channel_id in targets:
        try:
            bot.send_message(chat_id=channel_id, text=msg, parse_mode='HTML')
        except Exception as e:
            print(f"[Error] Failed to send to {channel_id}: {e}")

# --- Main Polling Loop ---

# Initialize last checked timestamps for all sources across all tasks
last_checked = {}
for task in TASKS:
    for source in task['sources']:
        if source not in last_checked:
            last_checked[source] = datetime.utcnow() - timedelta(seconds=POLL_INTERVAL)

print(f"Bot started. Polling every {POLL_INTERVAL}s...")
for task in TASKS:
    print(f" - Task '{task['name']}' running for sources: {task['sources']}")

while True:
    try:
        for task in TASKS:
            sources = task['sources']
            targets = task['targets']
            ai_options = task['ai_options']

            for source_acct in sources:
                since = last_checked[source_acct]
                query = f"from:{source_acct.lstrip('@')} since:{since.date()}"

                # Scrape tweets
                for tweet in sntwitter.TwitterSearchScraper(query).get_items():
                    if tweet.date <= since:
                        continue

                    tid = str(tweet.id)
                    if is_processed(tid):
                        continue

                    # Modify message using AI
                    modified_content = modify_message(tweet.content, ai_options, GROQ_KEY)

                    if is_duplicate(modified_content):
                        continue

                    # Post to all target channels for the task
                    post_to_targets(modified_content, targets)

                    # Mark as processed
                    mark_processed(tid, modified_content)

                # Update last checked time for this source
                last_checked[source_acct] = datetime.utcnow()

    except Exception as e:
        print(f"[Error] An unexpected error occurred: {e}")

    time.sleep(POLL_INTERVAL)
