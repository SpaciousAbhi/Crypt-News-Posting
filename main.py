# main.py

import os
import sqlite3
from typing import Optional
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
from config import TASKS, save_tasks_to_yaml
from ai_utils import modify_message
from menu import main_menu_keyboard, remove_task_keyboard
from conversation import (
    NAME,
    SOURCE_PLATFORM,
    SOURCES,
    TARGET_PLATFORM,
    TARGETS,
    AI_OPTIONS,
    HEADER,
    FOOTER,
    WATERMARK_FROM,
    WATERMARK_TO,
    CONFIRMATION,
    add_task_start,
    received_task_name,
    received_source_platform,
    received_sources,
    received_target_platform,
    received_targets,
    toggle_ai_option,
    done_ai_options,
    received_header,
    received_footer,
    received_watermark_from,
    received_watermark_to,
    confirm_task,
    cancel_task,
)
from edit_conversation import (
    SELECT_TASK,
    EDIT_MENU,
    EDIT_NAME,
    EDIT_SOURCES,
    EDIT_TARGETS,
    EDIT_AI_OPTIONS,
    CONFIRM_EDIT,
    edit_task_start,
    select_task_to_edit,
    edit_name,
    received_new_name,
    edit_sources,
    received_edit_source_platform,
    received_new_sources,
    edit_targets,
    received_edit_target_platform,
    received_new_targets,
    edit_ai_options,
    done_editing,
)
from notifications import send_admin_notification

# Load configuration from .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

from database import db

# --- Cache Helper Functions ---
def is_message_processed(message_id: str) -> bool:
    """Checks if a message_id has already been processed."""
    result = db.fetchone("SELECT message_id FROM processed WHERE message_id=%s", (str(message_id),))
    return result is not None


def mark_message_as_processed(message_id: str):
    """Marks a message_id as processed."""
    db.execute("INSERT INTO processed (message_id) VALUES (%s)", (str(message_id),))


# --- Background Monitoring Job ---
async def twitter_monitor_job(context: ContextTypes.DEFAULT_TYPE):
    """Job that polls Twitter sources for all active tasks."""
    print("[Job] Checking for new tweets...")
    from monitors import RSSMonitor, TwitterMonitor
    from publishers import TelegramPublisher, TwitterPublisher
    
    rss_monitor = RSSMonitor()
    # Initialize twikit only if needed to save resources/prevent bans
    tw_monitor = None
    tw_publisher = None
    
    tw_user = os.getenv("TWITTER_USERNAME")
    tw_pass = os.getenv("TWITTER_PASSWORD")

    telegram_pub = TelegramPublisher(context.bot)

    for task in TASKS:
        if task.get("paused"):
            continue
            
        task_name = task.get("name", "Unnamed")
        sources = task.get("sources", [])
        ai_options = task.get("ai_options", {})
        
        for source in sources:
            source_id = source.get("identifier")
            source_platform = source.get("platform", "twitter")
            
            if source_platform != "twitter":
                continue # Only handling Twitter for now
                
            # Fetch latest tweets
            # Try RSS first
            tweets = rss_monitor.fetch_latest_tweets(source_id)
            
            if not tweets and tw_user and tw_pass:
                # Fallback to Twikit
                if not tw_monitor:
                    tw_monitor = TwitterMonitor(tw_user, tw_pass)
                tweets = await tw_monitor.fetch_latest_tweets(source_id)
            
            if not tweets:
                continue
                
            last_id = db.get_last_processed_id(task_name, source_id)
            
            # Sort tweets by ID (newest first usually, but we want to process oldest to newest)
            tweets.sort(key=lambda x: x.id)
            
            for tweet in tweets:
                if last_id and tweet.id <= last_id:
                    continue
                
                print(f"[Job] Found new tweet from {source_id}: {tweet.id}")
                
                # Redesign content
                modified_text = modify_message(tweet.text, ai_options, GROQ_KEY)
                
                # Publish to destinations
                targets = task.get("targets", [])
                for target in targets:
                    target_platform = target.get("platform")
                    target_id = target.get("identifier")
                    
                    if target_platform == "telegram":
                        await telegram_pub.publish(target_id, modified_text, tweet.media_urls)
                    elif target_platform == "twitter":
                        if not tw_publisher and tw_user and tw_pass:
                            tw_publisher = TwitterPublisher(tw_user, tw_pass)
                        if tw_publisher:
                            await tw_publisher.publish(modified_text, tweet.media_urls)
                
                # Update last processed ID
                last_id = tweet.id
                db.set_last_processed_id(task_name, source_id, last_id)

    return True


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
        return await add_task_start(update, context)
    elif data == "remove_task":
        await remove_task(query)
        return ConversationHandler.END
    elif data.startswith("delete_task_"):
        await delete_task(query)
        return ConversationHandler.END
    elif data == "edit_task":
        return await edit_task_start(update, context)
    elif data.startswith("select_task_"):
        return await select_task_to_edit(update, context)
    elif data == "edit_name":
        return await edit_name(update, context)
    elif data == "edit_sources":
        return await edit_sources(update, context)
    elif data == "edit_targets":
        return await edit_targets(update, context)
    elif data == "edit_ai_options":
        return await edit_ai_options(update, context)
    elif data == "done_editing":
        return await done_editing(update, context)
    elif data == "toggle_redesign":
        return await toggle_ai_option(update, context)
    elif data.startswith("pause_task_"):
        index = int(data.split("_")[2])
        TASKS[index]["paused"] = True
        save_tasks_to_yaml()
        await query.edit_message_text(f"⏸ Task '{TASKS[index]['name']}' paused.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END
    elif data.startswith("resume_task_"):
        index = int(data.split("_")[2])
        TASKS[index]["paused"] = False
        save_tasks_to_yaml()
        await query.edit_message_text(f"▶️ Task '{TASKS[index]['name']}' resumed.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END
    elif data.startswith("manage_task_"):
        index = int(data.split("_")[2])
        task = TASKS[index]
        from menu import task_control_keyboard
        
        sources = [f"{s['platform']}:`{s['identifier']}`" for s in task.get("sources", [])]
        targets = [f"{t['platform']}:`{t['identifier']}`" for t in task.get("targets", [])]
        
        detail_text = (
            f"🛠 **Managing Task:** {task['name']}\n\n"
            f"📥 **Sources:** {', '.join(sources)}\n"
            f"📤 **Targets:** {', '.join(targets)}\n"
            f"🤖 **Redesign:** {'✅' if task.get('ai_options', {}).get('redesign') else '❌'}\n"
        )
        await query.edit_message_text(
            text=detail_text,
            reply_markup=task_control_keyboard(index, task.get("paused")),
            parse_mode="Markdown"
        )
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


    status_message = "📊 **Current Tasks**\n\nClick a task below to manage it:"
    keyboard = []
    for i, task in enumerate(TASKS):
        task_name = task.get("name", "Unnamed Task")
        paused = "⏸" if task.get("paused") else "▶️"
        keyboard.append([InlineKeyboardButton(f"{paused} {task_name}", callback_data=f"manage_task_{i}")])
    
    keyboard.append([InlineKeyboardButton("➕ Add New Task", callback_data="add_task")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="start")])

    await query.edit_message_text(
        text=status_message,
        reply_markup=InlineKeyboardMarkup(keyboard),
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
        sources = task.get("sources", [])
        # Check if any source matches this Telegram channel
        is_source = False
        for s in sources:
            if s.get("platform") == "telegram" and s.get("identifier") == chat_id:
                is_source = True
                break
        
        if is_source:
            # Check if the message should be forwarded
            if not should_forward_message(message_text, task.get("filters", {})):
                continue

            ai_options = task.get("ai_options", {})
            modified_content = modify_message(
                message_text, ai_options, GROQ_KEY
            )

            from publishers import TelegramPublisher, TwitterPublisher
            telegram_pub = TelegramPublisher(context.bot)
            tw_user = os.getenv("TWITTER_USERNAME")
            tw_pass = os.getenv("TWITTER_PASSWORD")
            tw_publisher = None

            targets = task.get("targets", [])
            for target in targets:
                target_platform = target.get("platform", "telegram") # default for legacy
                target_id = target.get("identifier")

                if target_platform == "telegram":
                    await telegram_pub.publish(target_id, modified_content, [])
                elif target_platform == "twitter":
                    if not tw_publisher and tw_user and tw_pass:
                        tw_publisher = TwitterPublisher(tw_user, tw_pass)
                    if tw_publisher:
                        await tw_publisher.publish(modified_content, [])

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
    send_admin_notification(error_message)


# --- Main Application Setup ---
def main():
    """Starts the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Register the global error handler
    application.add_error_handler(error_handler)

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_callback_handler)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_task_name)],
            SOURCE_PLATFORM: [
                CallbackQueryHandler(received_source_platform, pattern="^source_platform_")
            ],
            SOURCES: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_sources)],
            TARGET_PLATFORM: [
                CallbackQueryHandler(received_target_platform, pattern="^target_platform_")
            ],
            TARGETS: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_targets)],
            AI_OPTIONS: [
                CallbackQueryHandler(toggle_ai_option, pattern="^toggle_"),
                CallbackQueryHandler(done_ai_options, pattern="^done_ai_options$"),
            ],
            HEADER: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_header)],
            FOOTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_footer)],
            WATERMARK_FROM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_watermark_from)
            ],
            WATERMARK_TO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_watermark_to)
            ],
            CONFIRMATION: [
                CallbackQueryHandler(confirm_task, pattern="^confirm_task$"),
                CallbackQueryHandler(cancel_task, pattern="^cancel_task$"),
            ],
            SELECT_TASK: [
                CallbackQueryHandler(select_task_to_edit, pattern="^select_task_")
            ],
            EDIT_MENU: [
                CallbackQueryHandler(edit_name, pattern="^edit_name$"),
                CallbackQueryHandler(edit_sources, pattern="^edit_sources$"),
                CallbackQueryHandler(edit_targets, pattern="^edit_targets$"),
                CallbackQueryHandler(edit_ai_options, pattern="^edit_ai_options$"),
                CallbackQueryHandler(done_editing, pattern="^done_editing$"),
            ],
            EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_new_name)],
            EDIT_SOURCES: [
                CallbackQueryHandler(received_edit_source_platform, pattern="^edit_source_platform_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_new_sources)
            ],
            EDIT_TARGETS: [
                CallbackQueryHandler(received_edit_target_platform, pattern="^edit_target_platform_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_new_targets)
            ],
            EDIT_AI_OPTIONS: [
                CallbackQueryHandler(toggle_ai_option, pattern="^toggle_"),
                CallbackQueryHandler(done_editing, pattern="^done_editing$"),
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

    # Register the background monitoring job
    application.job_queue.run_repeating(twitter_monitor_job, interval=60, first=10)

    print("Bot started. Listening for channel posts and Twitter updates...")
    for task in TASKS:
        task_name = task.get("name", "Unnamed Task")
        sources = [s.get("identifier") for s in task.get("sources", [])]
        print(f" - Task '{task_name}' running for sources: {sources}")

    application.run_polling()


if __name__ == "__main__":
    main()
