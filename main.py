# main.py

import asyncio
import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes
)

from bot.states import BotState
from bot.menu import Menu
from bot.handlers import (
    view_tasks, manage_task, add_task_start, receive_task_name,
    receive_source_platform, receive_source_id, receive_dest_platform, 
    receive_dest_id, commit_task, show_settings, ask_setting, 
    set_groq_key, set_tw_user, set_tw_pass,
    toggle_task_status, delete_task, show_help, cancel_creation
)
from database.manager import db
from core.engine import ProcessingEngine
from services.config_service import config
from services.logger import logger

# --- Command Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for the bot with rich detailing."""
    admin_id = config.admin_id or "1654334233"
    user = update.effective_user
    
    if str(user.id) != str(admin_id):
        logger.warning(f"Unauthorized access attempt by {user.full_name} ({user.id})")
        return
        
    welcome_text = (
        f"👋 **Welcome back, {user.first_name}!**\n\n"
        "Your **Professional Automation Suite** is active and ready.\n\n"
        "🚀 **System Overview:**\n"
        "• **Engine Status:** 🟢 Online & Monitoring\n"
        "• **AI Model:** LLaMA3 (via Groq)\n"
        "• **Interval:** 60s Check Cycle\n\n"
        "Use the menu below to manage your tasks, configure API keys, or view the detailed help guide."
    )
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=Menu.main_menu(),
        parse_mode="Markdown"
    )
    return BotState.START

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles back-to-menu navigation."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "🚀 **Main Menu**\n\nChoose an action:",
            reply_markup=Menu.main_menu(),
            parse_mode="Markdown"
        )
    return BotState.START

async def capture_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Global handler to capture messages for dynamic sources (Telegram)."""
    if update.channel_post:
        msg = update.channel_post
        chat_id = msg.chat_id
        content = msg.text or msg.caption or ""
        item_id = str(msg.message_id)
        
        # Extract media
        media_urls = []
        if msg.photo:
            photo = msg.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            media_urls.append(file.file_path)
        elif msg.video:
            file = await context.bot.get_file(msg.video.file_id)
            media_urls.append(file.file_path)
            
        db.add_source_item(str(chat_id), "telegram", content, item_id, media_urls)
        logger.debug(f"[Capture] Stored message {item_id} from {chat_id}")

# --- Main Setup ---
def main():
    token = config.telegram_token
    if not token:
        logger.error("[Main] TELEGRAM_BOT_TOKEN not found! Exiting.")
        return

    # 1. Setup Application
    application = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start_command),
            CommandHandler("help", show_help),
            CallbackQueryHandler(add_task_start, pattern="^tasks_add$"),
            CallbackQueryHandler(view_tasks, pattern="^tasks_view$"),
            CallbackQueryHandler(show_settings, pattern="^settings_view$")
        ],
        states={
            BotState.START: [
                CallbackQueryHandler(view_tasks, pattern="^tasks_view$"),
                CallbackQueryHandler(add_task_start, pattern="^tasks_add$"),
                CallbackQueryHandler(show_settings, pattern="^settings_view$"),
                CallbackQueryHandler(show_help, pattern="^help_view$"),
                CallbackQueryHandler(manage_task, pattern="^tasks_manage_"),
                CallbackQueryHandler(lambda u, c: toggle_task_status(u, c, False), pattern="^tasks_pause_"),
                CallbackQueryHandler(lambda u, c: toggle_task_status(u, c, True), pattern="^tasks_resume_"),
                CallbackQueryHandler(delete_task, pattern="^tasks_delete_"),
            ],
            # Task Creation Flow
            BotState.TASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_task_name)],
            BotState.SELECT_SOURCE_PLATFORM: [CallbackQueryHandler(receive_source_platform, pattern="^source_")],
            BotState.ENTER_SOURCE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_source_id)],
            BotState.SELECT_DEST_PLATFORM: [CallbackQueryHandler(receive_dest_platform, pattern="^dest_")],
            BotState.ENTER_DEST_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_dest_id)],
            BotState.CONFIRM_TASK: [CallbackQueryHandler(commit_task, pattern="^task_create_")],
            
            # Settings Flow
            BotState.SETTINGS_MENU: [
                CallbackQueryHandler(ask_setting, pattern="^settings_set_"),
                CallbackQueryHandler(main_menu_callback, pattern="^menu_main$")
            ],
            BotState.SET_GROQ_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_groq_key)],
            BotState.SET_TW_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_tw_user)],
            BotState.SET_TW_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_tw_pass)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_creation),
            CommandHandler("start", start_command),
            CallbackQueryHandler(main_menu_callback, pattern="^menu_main$")
        ],
        allow_reentry=True,
        per_message=True
    )

    application.add_handler(conv_handler)
    
    # Global Message Capture for Sources
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL, capture_message))
    
    # Global handlers for navigation safety
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^menu_main$"))
    application.add_handler(CallbackQueryHandler(show_help, pattern="^help_view$"))

    # 3. Initialize Background Engine
    engine = ProcessingEngine(token)
    
    async def engine_supervisor():
        """Keeps the engine running even if it crashes."""
        while True:
            try:
                logger.info("[Main] Starting Engine Supervisor...")
                await engine.start(interval=60)
            except Exception as e:
                logger.error(f"[Main] Engine crashed: {e}. Restarting in 10s...")
                await asyncio.sleep(10)

    # 4. Run Everything
    logger.info("[Main] Launching bot and supervisor...")
    
    loop = asyncio.get_event_loop()
    loop.create_task(engine_supervisor())
    
    application.run_polling()

if __name__ == "__main__":
    main()
