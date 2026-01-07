# main.py

import os
import sqlite3
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Import custom modules
from config import TASKS
from ai_utils import modify_message

# Load configuration from .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")

# --- Database Initialization ---
conn = sqlite3.connect("cache.db", check_same_thread=False)
cur = conn.cursor()
cur.execute(
    """CREATE TABLE IF NOT EXISTS processed (
           message_id TEXT PRIMARY KEY,
           timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
       )"""
)
conn.commit()


# --- Cache Helper Functions ---
def is_message_processed(message_id: int) -> bool:
    """Checks if a message_id has already been processed."""
    cur.execute("SELECT 1 FROM processed WHERE message_id=?", (str(message_id),))
    return cur.fetchone() is not None


def mark_message_as_processed(message_id: int):
    """Marks a message_id as processed."""
    cur.execute(
        "INSERT INTO processed (message_id) VALUES (?)", (str(message_id),)
    )
    conn.commit()


# --- Telegram Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message when the /start command is issued."""
    welcome_text = (
        "👋 **Welcome to the Advanced Forwarding Bot!**\n\n"
        "I monitor channels and forward their messages to your targets, "
        "enhanced with AI modifications.\n\n"
        "**Available Commands:**\n"
        "`/start`  - Shows this welcome message.\n"
        "`/status` - Displays the status of all tasks.\n"
        "`/help`   - Provides help and info about the bot."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the status of all configured forwarding tasks."""
    if not TASKS:
        await update.message.reply_text("No tasks are currently configured.")
        return

    status_message = (
        "📊 **Bot Status**\n\nI am running the following tasks:\n\n"
    )
    for i, task in enumerate(TASKS, 1):
        task_name = task.get("name", "Unnamed Task")
        status_message += f"🔹 **Task {i}: {task_name}**\n"

        sources = ", ".join(map(str, task.get("sources", [])))
        status_message += f"   - **Sources:** `{sources}`\n"

        targets = ", ".join(map(str, task.get("targets", [])))
        status_message += f"   - **Targets:** `{targets}`\n\n"

    await update.message.reply_text(status_message, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provides help information."""
    help_text = (
        "ℹ️ **How I Work**\n\n"
        "This bot uses a `config.yaml` file to define 'tasks.' "
        "Each task specifies source and target channel IDs, and AI options "
        "for modifying messages (e.g., summarize, reword).\n\n"
        "To change my behavior, modify `config.yaml` and restart."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


# --- Core Message Handling Logic ---
async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles new posts from any channel the bot is in."""
    channel_post = update.channel_post
    if not channel_post or not channel_post.text:
        return

    message_id = channel_post.message_id
    chat_id = channel_post.chat_id
    message_text = channel_post.text

    # Prevent processing the same message multiple times
    if is_message_processed(message_id):
        return

    for task in TASKS:
        source_ids = task.get("sources", [])
        if chat_id in source_ids:
            targets = task.get("targets", [])
            ai_options = task.get("ai_options", {})

            # Modify the message using AI
            modified_content = modify_message(
                message_text, ai_options, GROQ_KEY
            )

            # Forward the modified message to all target channels
            for target_id in targets:
                try:
                    await context.bot.send_message(
                        chat_id=target_id, text=modified_content
                    )
                except Exception as e:
                    print(
                        f"[Error] Failed to send to target {target_id}: {e}"
                    )

            # Mark the message as processed after forwarding
            mark_message_as_processed(message_id)


# --- Main Application Setup ---
def main():
    """Starts the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("help", help_command))

    # Register the message handler for channel posts
    application.add_handler(
        MessageHandler(
            filters.UpdateType.CHANNEL_POST & filters.TEXT,
            handle_channel_post,
        )
    )

    print("Bot started. Listening for channel posts...")
    for task in TASKS:
        task_name = task.get("name", "Unnamed Task")
        sources = task.get("sources", [])
        print(f" - Task '{task_name}' running for sources: {sources}")

    # Start the Bot
    application.run_polling()


if __name__ == "__main__":
    main()
