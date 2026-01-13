# clients.py

import os
from pyrogram import Client

# Conditionally initialize the Pyrogram client
# This allows the bot to run in "bot-only" mode if the user account credentials are not provided.

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("PYROGRAM_SESSION_STRING")

pyrogram_app = None
if API_ID and API_HASH and SESSION_STRING:
    pyrogram_app = Client(
        "user_account",
        api_id=int(API_ID),
        api_hash=API_HASH,
        session_string=SESSION_STRING,
    )
    print("Pyrogram client initialized.")
else:
    print("Pyrogram client not configured. Running in bot-only mode.")

# The python-telegram-bot Application object is created in main.py as it's the primary orchestrator.
