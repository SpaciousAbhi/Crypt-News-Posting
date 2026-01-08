# core.py

from functools import wraps
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes

from pyrogram import Client
from pyrogram.types import Message as PyrogramMessage
from database import SessionLocal, User, Task, Source, ProcessedMessage
from observability import send_admin_notification
from ai_engine import transform_message


def restricted(role: str):
    """
    A decorator that restricts access to a command handler to a specific role.
    """

    def decorator(func):
        @wraps(func)
        async def wrapped(
            update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
        ):
            telegram_id = update.effective_user.id
            db = SessionLocal()
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            db.close()

            if not user:
                # Assuming the message is from a command. If it's a callback query, this needs adjustment.
                if update.message:
                    await update.message.reply_text(
                        "You are not registered. Please use /start first."
                    )
                elif update.callback_query:
                    await update.callback_query.answer(
                        "You are not registered. Please use /start first.",
                        show_alert=True,
                    )
                return

            # Role hierarchy: owner > admin > user
            if role == "owner" and user.role != "owner":
                reply = "This command is restricted to the bot owner."
                if update.message:
                    await update.message.reply_text(reply)
                elif update.callback_query:
                    await update.callback_query.answer(reply, show_alert=True)
                return
            if role == "admin" and user.role not in ["owner", "admin"]:
                reply = "This command is restricted to admins."
                if update.message:
                    await update.message.reply_text(reply)
                elif update.callback_query:
                    await update.callback_query.answer(reply, show_alert=True)
                return

            return await func(update, context, *args, **kwargs)

        return wrapped

    return decorator


async def process_message(
    client_or_update: Update | Client,
    message_or_context: ContextTypes.DEFAULT_TYPE | PyrogramMessage,
):
    """
    The core function that handles incoming messages and forwards them based on tasks.
    This function is now client-agnostic.
    """
    if isinstance(client_or_update, Update):
        # From python-telegram-bot
        message = client_or_update.effective_message
        context = message_or_context
        bot = context.bot
    else:
        # From Pyrogram
        message = message_or_context
        bot = client_or_update  # The client is the bot in Pyrogram's case

    if not message:
        return

    source_chat_id = message.chat.id
    source_message_id = message.id
    message_key = f"{source_chat_id}:{source_message_id}"

    db = SessionLocal()

    # 1. Message Deduplication Check
    if (
        db.query(ProcessedMessage)
        .filter(ProcessedMessage.message_key == message_key)
        .first()
    ):
        print(f"Duplicate message detected: {message_key}. Skipping.")
        db.close()
        return

    # 2. Mark message as processed IMMEDIATELY to handle race conditions
    new_processed_message = ProcessedMessage(
        message_key=message_key,
        source_chat_id=source_chat_id,
        source_message_id=source_message_id,
        expires_at=datetime.utcnow() + timedelta(days=3),  # Add a TTL
    )
    db.add(new_processed_message)
    db.commit()

    # 3. Find matching tasks
    # This query joins Task and Source tables to find tasks where the source chat_id matches.
    tasks_to_process = (
        db.query(Task)
        .join(Source)
        .filter(Source.chat_id == source_chat_id, Task.enabled)
        .all()
    )

    if not tasks_to_process:
        print(f"No active tasks found for source chat {source_chat_id}.")
        db.close()
        return

    print(f"Found {len(tasks_to_process)} task(s) for message {message_key}.")

    # 4. Process each matched task
    for task in tasks_to_process:
        print(f"Processing task: {task.name} ({task.task_id})")

        original_text = message.text or message.caption
        source_chat_name = message.chat.title or f"Chat {source_chat_id}"

        # Determine if we should apply transformations and do it once per task
        apply_ai = original_text and task.ai_rules
        modified_text = None

        if apply_ai:
            modified_text = await transform_message(
                original_text, task.ai_rules, source_chat_name
            )
            if modified_text is None:
                print(f"Aborting task {task.name} for this message due to AI failure.")
                continue  # Skip to the next task

        for target in task.targets:
            try:
                if apply_ai:
                    # Send the pre-transformed text with media if applicable
                    if message.photo:
                        await bot.send_photo(
                            chat_id=target.chat_id,
                            photo=message.photo.file_id,
                            caption=modified_text,
                        )
                    elif message.video:
                        await bot.send_video(
                            chat_id=target.chat_id,
                            video=message.video.file_id,
                            caption=modified_text,
                        )
                    elif message.document:
                        await bot.send_document(
                            chat_id=target.chat_id,
                            document=message.document.file_id,
                            caption=modified_text,
                        )
                    else:  # Text-only message
                        await bot.send_message(
                            chat_id=target.chat_id, text=modified_text
                        )

                    print(
                        f"Successfully sent transformed message to target {target.chat_id}"
                    )

                else:
                    # If there is no text or no rules, just forward the original message
                    await bot.forward_message(
                        chat_id=target.chat_id,
                        from_chat_id=source_chat_id,
                        message_id=source_message_id,
                    )
                    print(
                        f"Successfully forwarded original message to target {target.chat_id}"
                    )

            except Exception as e:
                error_message = f"🔴 **Task Failure**\n\n**Task:** `{task.name}`\n**Target:** `{target.chat_id}`\n**Error:** Failed to forward or send message.\n**Reason:** `{e}`"
                print(error_message)
                await send_admin_notification(error_message)

    db.close()
