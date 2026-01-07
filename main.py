# main.py

import sqlite3
import os
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
from database import init_db, SessionLocal, Task
from cache import TASKS, load_tasks
from ai_utils import modify_message
from menu import main_menu_keyboard, remove_task_keyboard
import conversation as conv
import edit_conversation as edit_conv
from notifications import send_admin_notification

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")


# --- Database Initialization for Caching ---
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


# --- Content Filtering ---
def should_forward_message(message_text: str, task_filters: dict) -> bool:
    """Checks if a message should be forwarded based on keywords."""
    include_keywords = task_filters.get("include_keywords", [])
    exclude_keywords = task_filters.get("exclude_keywords", [])

    # If there are include keywords, the message must contain at least one of them
    if include_keywords and not any(
        keyword.lower() in message_text.lower() for keyword in include_keywords
    ):
        return False

    # If there are exclude keywords, the message must not contain any of them
    if exclude_keywords and any(
        keyword.lower() in message_text.lower() for keyword in exclude_keywords
    ):
        return False

    return True


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
        return await conv.add_task_start(update, context)
    elif data == "remove_task":
        await remove_task(query)
        return ConversationHandler.END
    elif data.startswith("delete_task_"):
        await delete_task(query)
        return ConversationHandler.END
    elif data == "edit_task":
        return await edit_conv.edit_task_start(update, context)
    elif data.startswith("select_task_"):
        return await edit_conv.select_task_to_edit(update, context)
    elif data == "edit_name":
        return await edit_conv.edit_name(update, context)
    elif data == "edit_sources":
        return await edit_conv.edit_sources(update, context)
    elif data == "edit_targets":
        return await edit_conv.edit_targets(update, context)
    elif data == "edit_ai_options":
        return await edit_conv.edit_ai_options(update, context)
    elif data == "done_editing":
        return await edit_conv.done_editing(update, context)
    elif data == "help":
        await help_menu(query)
        return ConversationHandler.END
    elif data.startswith("toggle_"):
        return await conv.toggle_ai_option(update, context)
    elif data == "done_ai_options":
        return await conv.done_ai_options(update, context)
    elif data == "confirm_task":
        return await conv.confirm_task(update, context)
    elif data == "cancel_task":
        return await conv.cancel_task(update, context)
    else:
        await query.edit_message_text(
            text=f"Unknown option: {data}",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END


async def view_tasks(query):
    """Displays a detailed view of the current tasks."""
    if not TASKS:
        await query.edit_message_text(
            text="No tasks are currently configured.",
            reply_markup=main_menu_keyboard(),
        )
        return

    status_message = "📊 **Current Tasks**\n\n"
    for i, task in enumerate(TASKS, 1):
        status_message += f"🔹 **Task {i}: {task.name}**\n"

        # Sources and Targets
        sources = ", ".join(map(str, task.sources))
        status_message += f"   - **Sources:** `{sources}`\n"
        targets = ", ".join(map(str, task.targets))
        status_message += f"   - **Targets:** `{targets}`\n"

        # AI Options
        if task.ai_options:
            status_message += "   - **AI Options:**\n"
            if task.ai_options.get("reword"):
                status_message += "     - Reword: `Yes`\n"
            else:
                status_message += "     - Reword: `No`\n"

            if task.ai_options.get("summarize"):
                summary_length = task.ai_options.get("summary_length", "Default")
                status_message += (
                    f"     - Summarize: `Yes (Length: {summary_length})`\n"
                )
            else:
                status_message += "     - Summarize: `No`\n"

            if task.ai_options.get("header"):
                status_message += f"     - Header: `{task.ai_options['header']}`\n"
            if task.ai_options.get("footer"):
                status_message += f"     - Footer: `{task.ai_options['footer']}`\n"
            watermark = task.ai_options.get("watermark", {})
            if watermark and watermark.get("replace_from") and watermark.get("replace_to"):
                status_message += (
                    f"     - Watermark: `{watermark['replace_from']}` -> `{watermark['replace_to']}`\n"
                )

        # Filters
        if task.filters:
            status_message += "   - **Filters:**\n"
            include = ", ".join(task.filters.get("include_keywords", []))
            if include:
                status_message += f"     - Include Keywords: `{include}`\n"
            exclude = ", ".join(task.filters.get("exclude_keywords", []))
            if exclude:
                status_message += f"     - Exclude Keywords: `{exclude}`\n"

        status_message += "\n"

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
        text="Select a task to remove:", reply_markup=remove_task_keyboard(TASKS)
    )


async def delete_task(query):
    """Deletes the selected task."""
    task_id = int(query.data.split("_")[2])
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    if task:
        task_name = task.name
        db.delete(task)
        db.commit()
        load_tasks()  # Refresh the cache
        await query.edit_message_text(
            text=f"Task '{task_name}' has been removed.",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await query.edit_message_text(
            text="Task not found.",
            reply_markup=main_menu_keyboard(),
        )
    db.close()


async def help_menu(query):
    """Displays the help menu."""
    help_text = (
        "ℹ️ **How I Work**\n\n"
        "This bot uses a database to define 'tasks.' "
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
        if chat_id in task.sources:
            # Check if the message should be forwarded
            if not should_forward_message(message_text, task.filters or {}):
                continue

            modified_content = modify_message(
                message_text, task.ai_options or {}, GROQ_API_KEY
            )

            for target_id in task.targets:
                try:
                    await context.bot.send_message(
                        chat_id=target_id, text=modified_content
                    )
                except Exception as e:
                    error_message = (
                        f"Failed to send a message to target `{target_id}`.\n"
                        f"**Reason:** `{e}`\n\n"
                        "Please ensure the bot is an administrator in the channel."
                    )
                    print(f"[Error] {error_message}")
                    send_admin_notification(
                        TELEGRAM_BOT_TOKEN, ADMIN_CHAT_ID, error_message
                    )

            mark_message_as_processed(message_id)


# --- Error Handler ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handles all unhandled exceptions and sends a notification."""
    error_message = (
        "An unhandled exception occurred.\n\n"
        f"**Update:** `{update}`\n"
        f"**Error:** `{context.error}`"
    )
    print(f"[Critical Error] {error_message}")
    send_admin_notification(TELEGRAM_BOT_TOKEN, ADMIN_CHAT_ID, error_message)


# --- Main Application Setup ---
def main():
    """Starts the bot."""
    # Initialize the database and load tasks into the cache
    init_db()
    load_tasks()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register the global error handler
    application.add_error_handler(error_handler)

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_callback_handler)],
        states={
            conv.NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, conv.received_task_name)],
            conv.SOURCES: [MessageHandler(filters.TEXT & ~filters.COMMAND, conv.received_sources)],
            conv.TARGETS: [MessageHandler(filters.TEXT & ~filters.COMMAND, conv.received_targets)],
            conv.AI_OPTIONS: [
                CallbackQueryHandler(conv.toggle_ai_option, pattern="^toggle_"),
                CallbackQueryHandler(conv.done_ai_options, pattern="^done_ai_options$"),
            ],
            conv.HEADER: [MessageHandler(filters.TEXT & ~filters.COMMAND, conv.received_header)],
            conv.FOOTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, conv.received_footer)],
            conv.WATERMARK_FROM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, conv.received_watermark_from)
            ],
            conv.WATERMARK_TO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, conv.received_watermark_to)
            ],
            conv.CONFIRMATION: [
                CallbackQueryHandler(conv.confirm_task, pattern="^confirm_task$"),
                CallbackQueryHandler(conv.cancel_task, pattern="^cancel_task$"),
            ],
            edit_conv.SELECT_TASK: [
                CallbackQueryHandler(edit_conv.select_task_to_edit, pattern="^select_task_")
            ],
            edit_conv.EDIT_MENU: [
                CallbackQueryHandler(edit_conv.edit_name, pattern="^edit_name$"),
                CallbackQueryHandler(edit_conv.edit_sources, pattern="^edit_sources$"),
                CallbackQueryHandler(edit_conv.edit_targets, pattern="^edit_targets$"),
                CallbackQueryHandler(edit_conv.edit_ai_options, pattern="^edit_ai_options$"),
                CallbackQueryHandler(edit_conv.done_editing, pattern="^done_editing$"),
            ],
            edit_conv.EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_conv.received_new_name)],
            edit_conv.EDIT_SOURCES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_conv.received_new_sources)
            ],
            edit_conv.EDIT_TARGETS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_conv.received_new_targets)
            ],
            edit_conv.EDIT_AI_OPTIONS: [
                CallbackQueryHandler(conv.toggle_ai_option, pattern="^toggle_"),
                CallbackQueryHandler(edit_conv.done_editing, pattern="^done_editing$"),
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
        print(f" - Task '{task.name}' running for sources: {task.sources}")

    application.run_polling()


if __name__ == "__main__":
    main()
