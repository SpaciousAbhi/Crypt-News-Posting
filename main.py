import os
import time
import sqlite3
import requests
import snscrape.modules.twitter as sntwitter

from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Bot
from rapidfuzz import fuzz

# Load configuration from .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID      = os.getenv('TELEGRAM_CHANNEL_ID')
GROQ_KEY        = os.getenv('GROQ_API_KEY')
POLL_INTERVAL   = int(os.getenv('POLL_INTERVAL', 300))
TWITTER_ACCOUNTS = os.getenv('TWITTER_ACCOUNTS', '').split(',')

# Initialize Telegram bot
bot = Bot(token=TELEGRAM_TOKEN)

# Initialize SQLite cache (thread‐safe)
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

DUPLICATE_THRESHOLD = 85

# Groq LLaMA3 summarization
def llama3_summary(text: str) -> str:
    prompt = (
        "Rewrite this tweet as a concise, engaging crypto-news summary "
        "with relevant emojis to highlight sentiment and key points:\n\n"
        + text
    )
    url = 'https://api.groq.com/openai/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {GROQ_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': 'llama3-70b-8192',
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.3,
        'max_tokens': 200
    }
    res = requests.post(url, headers=headers, json=payload)
    res.raise_for_status()
    return res.json()['choices'][0]['message']['content'].strip()

# Cache helpers
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

# Telegram poster
def post_to_channel(msg: str):
    bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode='HTML')

# Main polling loop
last_checked = {
    acct: datetime.utcnow() - timedelta(seconds=POLL_INTERVAL)
    for acct in TWITTER_ACCOUNTS
}

print(f"Bot started. Polling every {POLL_INTERVAL}s for: {TWITTER_ACCOUNTS}")

while True:
    try:
        for acct in TWITTER_ACCOUNTS:
            since = last_checked[acct]
            query = f"from:{acct} since:{since.date()}"
            for tweet in sntwitter.TwitterSearchScraper(query).get_items():
                if tweet.date <= since:
                    continue
                tid = str(tweet.id)
                if is_processed(tid):
                    continue
                # Generate summary with emojis
                summary = llama3_summary(tweet.content)
                if is_duplicate(summary):
                    continue
                post_to_channel(summary)
                mark_processed(tid, summary)
            last_checked[acct] = datetime.utcnow()
    except Exception as e:
        print(f"[Error] {e}")
    time.sleep(POLL_INTERVAL)
