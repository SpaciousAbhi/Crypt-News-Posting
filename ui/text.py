# ui/text.py

# This file centralizes all static UX copy.

WELCOME_MESSAGE = """
👋 **Welcome to the Advanced AI Forwarding Bot!**

I can monitor Telegram chats, apply powerful AI transformations to messages, and forward them to your channels or groups.

Please choose an option from the menu below to get started.
"""

HELP_MESSAGE = """
ℹ️ **Help & Documentation**

**How I Work**
This bot forwards messages from source chats to target chats, with optional AI modifications. A "Task" is a single forwarding rule that links sources, targets, and AI rules.

**Accessing Private Chats**
For me to see messages in private chats, you must add me:
- **Private Channels:** Add me as an **Administrator** with "Read Messages" (for sources) or "Post Messages" (for targets) permissions.
- **Private Groups:** Simply add me as a **Member**.

**Finding Chat IDs**
To get the ID of a private channel or group, forward a message from it to a bot like `@JsonDumpBot`. The `forward_from_chat` -> `id` field is the chat ID you need.

Use the main menu to manage your tasks. If you need further assistance, please contact the bot owner.
"""
