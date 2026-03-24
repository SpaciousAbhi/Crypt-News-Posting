# notifications.py

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def send_admin_notification(message: str):
    """Synchronously sends a notification message to the admin."""
    token = "7798265687:AAG61EtPE_SQfIwIKv8qjD1fZaes15VEBW4"
    admin_id = "1654334233"

    if not admin_id or not token:
        print(
            "[Info] Admin notification not sent "
            "(ADMIN_CHAT_ID or TELEGRAM_BOT_TOKEN not set)"
        )
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": admin_id,
        "text": f"🚨 **Bot Error**\n\n{message}",
        "parse_mode": "Markdown",
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[Critical Error] Could not send error notification to admin: {e}")
