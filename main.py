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
    CallbackQueryHandler,
    ConversationHandler,
)

# Import custom modules
from config import TASKS, save_tasks_to_yaml, load_tasks_from_yaml
from ai_utils import modify_message
from menu import main_menu_keyboard, remove_task_keyboard
from conversation import (
    NAME,
    SOURCES,
    TARGETS,
    AI_OPTIONS,
    CONFIRMATION,
    add_task_start,
    received_task_name,
    received_sources,
    received_targets,
    toggle_ai_option,
    done_ai_options,
    confirm_task,
    cancel_task,
)

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
    """Sends a welcome message with the main menu."""
    welcome_text = "👋 **Welcome to the Advanced Forwarding Bot!**\n\n"
    "Please choose an option from the menu below:"

    # Check if the message is from a callback query
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=welcome_text,
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            text=welcome_text,
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown",
        )
    return ConversationHandler.END


# --- Callback Query Handler ---
async def button_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Handles button presses from inline keyboards."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "start":
        return await start(update, context)
    elif data == "view_tasks":
        await view_tasks(query)
        return ConversationHandler.END
    elif data == "add_task":
        return await add_task_start(update, context)
    elif data == "remove_task":
        await remove_task(query)
        return ConversationHandler.END
    elif data.startswith("delete_task_"):
        await delete_task(query)
        return ConversationHandler.END
    elif data == "help":
        await help_menu(query)
        return ConversationHandler.END
    elif data.startswith("toggle_"):
        return await toggle_ai_option(update, context)
    elif data == "done_ai_options":
        return await done_ai_options(update, context)
    elif data == "confirm_task":
        return await confirm_task(update, context)
    elif data == "cancel_task":
        return await cancel_task(update, context)
    else:
        await query.edit_message_text(
            text=f"Unknown option: {data}",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END


async def view_tasks(query):
    """Displays the current tasks."""
    if not TASKS:
        await query.edit_message_text(
            text="No tasks are currently configured.",
            reply_markup=main_menu_keyboard(),
        )
        return

    status_message = "📊 **Current Tasks**\n\n"
    for i, task in enumerate(TASKS, 1):
        task_name = task.get("name", "Unnamed Task")
        status_message += f"🔹 **Task {i}: {task_name}**\n"
        sources = ", ".join(map(str, task.get("sources", [])))
        status_message += f"   - **Sources:** `{sources}`\n"
        targets = ", ".join(map(str, task.get("targets", [])))
        status_message += f"   - **Targets:** `{targets}`\n\n"

    await query.edit_message_text(
        text=status_message,
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )


async def remove_task(query):
    """Displays a list of tasks to remove."""
    if not TASKS:
        await query.edit_message_text(
            text="No tasks to remove.", reply_markup=main_menu_keyboard()
        )
        return
    await query.edit_message_text(
        text="Select a task to remove:", reply_markup=remove_task_keyboard()
    )


async def delete_task(query):
    """Deletes the selected task."""
    task_index = int(query.data.split("_")[2])
    task_name = TASKS[task_index]["name"]
    del TASKS[task_index]
    save_tasks_to_yaml()
    load_tasks_from_yaml()
    await query.edit_message_text(
        text=f"Task '{task_name}' has been removed.",
        reply_markup=main_menu_keyboard(),
    )


async def help_menu(query):
    """Displays the help menu."""
    help_text = (
        "ℹ️ **How I Work**\n\n"
        "This bot uses a `config.yaml` file to define 'tasks.' "
        "Each task specifies source and target channel IDs, and AI options "
        "for modifying messages.\n\n"
        "Use the menu to manage your tasks."
    )
    await query.edit_message_text(
        text=help_text,
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )


# --- Core Message Handling Logic ---
async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles new posts from any channel the bot is in."""
    channel_post = update.channel_post
    if not channel_post or not channel_post.text:
        return

    message_id = channel_post.message_id
    chat_id = channel_post.chat_id
    message_text = channel_post.text

    if is_message_processed(message_id):
        return

    for task in TASKS:
        source_ids = task.get("sources", [])
        if chat_id in source_ids:
            targets = task.get("targets", [])
            ai_options = task.get("ai_options", {})
            modified_content = modify_message(
                message_text, ai_options, GROQ_KEY
            )

            for target_id in targets:
                try:
                    await context.bot.send_message(
                        chat_id=target_id, text=modified_content
                    )
                except Exception as e:
                    print(f"[Error] Failed to send to target {target_id}: {e}")

            mark_message_as_processed(message_id)


# --- Main Application Setup ---
def main():
    """Starts the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_callback_handler)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_task_name)],
            SOURCES: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_sources)],
            TARGETS: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_targets)],
            AI_OPTIONS: [
                CallbackQueryHandler(toggle_ai_option, pattern="^toggle_"),
                CallbackQueryHandler(done_ai_options, pattern="^done_ai_options$"),
            ],
            CONFIRMATION: [
                CallbackQueryHandler(confirm_task, pattern="^confirm_task$"),
                CallbackQueryHandler(cancel_task, pattern="^cancel_task$"),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
        per_message=False,
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
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

    application.run_polling()


if __name__ == "__main__":
    main()
