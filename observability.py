# observability.py

import os
import httpx


async def send_admin_notification(
    message: str, bot_token: str = None, admin_chat_id: str = None
):
    """
    Sends a notification to the admin chat.
    Uses a separate, simple bot instance to avoid conflicts with the main application.
    """
    bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
    admin_chat_id = admin_chat_id or os.getenv("ADMIN_CHAT_ID")

    if not bot_token or not admin_chat_id:
        print(
            "ERROR: Admin notification not sent. TELEGRAM_BOT_TOKEN and ADMIN_CHAT_ID must be set."
        )
        return

    try:
        # We use httpx for a simple, fire-and-forget async request.
        # Using a full Bot instance here can sometimes cause event loop conflicts.
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        params = {"chat_id": admin_chat_id, "text": message, "parse_mode": "Markdown"}
        async with httpx.AsyncClient() as client:
            await client.get(url, params=params)
        print("Admin notification sent.")
    except Exception as e:
        print(f"ERROR: Failed to send admin notification: {e}")
