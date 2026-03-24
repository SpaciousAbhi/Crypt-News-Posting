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
    """Entry point for the bot."""
    # Ensure only admin can use the bot
    admin_id = config.admin_id or "1654334233"
    if str(update.effective_user.id) != str(admin_id):
        return
        
    await update.message.reply_text(
        "🚀 **Advanced Automation Bot**\n\nWelcome to your production-grade automation engine.",
        reply_markup=Menu.main_menu(),
        parse_mode="Markdown"
    )
    return BotState.START

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles back-to-menu navigation."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🚀 **Main Menu**\n\nChoose an action:",
        reply_markup=Menu.main_menu(),
        parse_mode="Markdown"
    )
    return BotState.START

# --- Main Setup ---
def main():
    token = config.telegram_token
    if not token:
        logger.error("[Main] TELEGRAM_BOT_TOKEN not found! Exiting.")
        return

    # 1. Setup Application
    application = Application.builder().token(token).build()

    # 2. Define Main ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start_command),
            CommandHandler("help", show_help)
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
        allow_reentry=True
    )

    application.add_handler(conv_handler)
    
    # Global handlers for navigation safety
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^menu_main$"))
    application.add_handler(CallbackQueryHandler(show_help, pattern="^help_view$"))

    # 3. Initialize Background Engine
    engine = ProcessingEngine(token)
    
    # We use a helper to start the engine in the background
    async def start_engine():
        await engine.start(interval=60)

    # 4. Run Everything
    logger.info("[Main] Launching bot and background engine...")
    
    # For Heroku and local async stability:
    loop = asyncio.get_event_loop()
    loop.create_task(start_engine())
    
    application.run_polling(
        read_timeout=30,
        write_timeout=30,
        connect_timeout=30,
        pool_timeout=30
    )

if __name__ == "__main__":
    main()
