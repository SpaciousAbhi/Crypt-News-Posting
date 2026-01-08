# main.py

import asyncio
import os
import signal
from dotenv import load_dotenv

from telegram.ext import Application, MessageHandler, filters, ContextTypes
from pyrogram import filters as pyrogram_filters
from pyrogram.handlers import MessageHandler as pyrogram_MessageHandler

from database import init_db
from core import process_message
from ui.commands import register_commands
from ui.conversations import get_create_task_conv_handler
from observability import send_admin_notification
from clients import pyrogram_app

# from observability import setup_logging # Will be uncommented later


async def run_bot():
    """Initializes and runs the bot."""
    # setup_logging() # Will be uncommented later

    # Initialize the database
    init_db()

    # Create the PTB application
    ptb_app = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    # --- Global Error Handler ---
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
        """Catches all unhandled exceptions and sends a notification."""
        error_message = (
            f"🔴 **Unhandled Exception**\n\n"
            f"**Update:** `{update}`\n\n"
            f"**Error:** `{context.error}`"
        )
        print(f"CRITICAL: {error_message}")
        await send_admin_notification(error_message)

    ptb_app.add_error_handler(error_handler)

    # Register command handlers
    register_commands(ptb_app)

    # Register the conversation handler for creating tasks
    conv_handler = get_create_task_conv_handler()
    ptb_app.add_handler(conv_handler)

    # Register message handlers for forwarding
    ptb_app.add_handler(
        MessageHandler(filters.ChatType.CHANNEL & ~filters.COMMAND, process_message)
    )
    ptb_app.add_handler(
        MessageHandler(filters.ChatType.GROUP & ~filters.COMMAND, process_message)
    )

    # --- Graceful Shutdown ---
    loop = asyncio.get_running_loop()
    stop = asyncio.Future()
    loop.add_signal_handler(signal.SIGINT, stop.set_result, None)
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)

    # Register Pyrogram handler if available
    if pyrogram_app:
        pyrogram_app.add_handler(
            pyrogram_MessageHandler(
                process_message,
                filters=pyrogram_filters.private
                | pyrogram_filters.group
                | pyrogram_filters.channel,
            )
        )

    # --- Non-blocking Startup ---
    await ptb_app.initialize()
    if pyrogram_app:
        await pyrogram_app.start()

    await ptb_app.start()
    await ptb_app.updater.start_polling()

    print("Bot started. Listening for messages...")

    # Wait for a shutdown signal
    await stop

    # --- Shutdown Sequence ---
    print("Shutting down bot...")
    await ptb_app.updater.stop()
    await ptb_app.stop()
    if pyrogram_app:
        await pyrogram_app.stop()
    await ptb_app.shutdown()
    print("Bot shut down gracefully.")


if __name__ == "__main__":
    load_dotenv()
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")
