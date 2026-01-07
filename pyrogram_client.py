# pyrogram_client.py

import os
from pyrogram import Client

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("PYROGRAM_SESSION_STRING")

if SESSION_STRING:
    app = Client(
        "user_account",
        session_string=SESSION_STRING,
        api_id=API_ID,
        api_hash=API_HASH,
    )
else:
    app = None
