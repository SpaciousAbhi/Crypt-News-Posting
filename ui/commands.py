# ui/commands.py

import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)

from ui.text import WELCOME_MESSAGE, HELP_MESSAGE
from ui.buttons import main_menu_keyboard
from database import SessionLocal, User, Task
from core import restricted


async def view_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays a list of the user's tasks."""
    telegram_id = update.effective_user.id
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == telegram_id).first()

    if not user:
        await update.callback_query.edit_message_text(
            "You are not registered. Please use /start first."
        )
        db.close()
        return

    tasks = db.query(Task).filter(Task.user_id == user.user_id).all()
    db.close()

    if not tasks:
        message = "You have no tasks configured."
    else:
        message = "**Your Forwarding Tasks**\n\n"
        for task in tasks:
            status = "✅ Enabled" if task.enabled else "❌ Disabled"
            message += f"- **({status})** {task.name}\n"
            message += (
                f"  `ID: {task.task_id}`\n\n"  # Using task_id as the unique identifier
            )

    await update.callback_query.edit_message_text(
        message,
        reply_markup=main_menu_keyboard(),  # This should be a task-specific keyboard later
        parse_mode="Markdown",
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command and registers the user."""
    telegram_id = update.message.from_user.id
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == telegram_id).first()

    if not user:
        role = "owner" if str(telegram_id) == os.getenv("OWNER_TELEGRAM_ID") else "user"
        new_user = User(telegram_id=telegram_id, role=role)
        db.add(new_user)
        db.commit()
        print(f"New user registered: {telegram_id}, Role: {role}")

    db.close()

    await update.message.reply_text(
        WELCOME_MESSAGE,
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /help command."""
    await update.message.reply_text(
        HELP_MESSAGE,
        parse_mode="Markdown",
    )


async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Wrapper for view_tasks to be used as a command."""

    # Simulate a callback query to reuse the view_tasks function
    class MockCallbackQuery:
        async def answer(self):
            pass

        async def edit_message_text(self, *args, **kwargs):
            await update.message.reply_text(*args, **kwargs)

    update.callback_query = MockCallbackQuery()
    await view_tasks(update, context)


@restricted("admin")
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the current status of the bot."""
    # In a real implementation, we would fetch these stats from a database or cache.
    active_tasks = 0
    messages_forwarded_24h = 0
    errors_24h = 0

    status_message = f"""
**Bot Status**

- **Status:** `OPERATIONAL`
- **Active Tasks:** {active_tasks}
- **Messages Forwarded (24h):** {messages_forwarded_24h}
- **Errors (24h):** {errors_24h}
- **Pyrogram Client:** `{'CONNECTED' if context.bot_data.get('pyrogram_app') else 'DISCONNECTED'}`

All systems are running normally.
    """
    await update.message.reply_text(status_message, parse_mode="Markdown")


@restricted("user")
async def task_delete_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Asks for confirmation to delete a task."""
    task_id = context.args[0] if context.args else None
    if not task_id:
        await update.message.reply_text("Usage: /task_delete <task_id>")
        return

    keyboard = [
        [
            InlineKeyboardButton(
                "⚠️ Yes, Delete Task", callback_data=f"confirm_delete_{task_id}"
            )
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_delete")],
    ]
    await update.message.reply_text(
        f"Are you sure you want to permanently delete task `{task_id}`?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def handle_delete_confirmation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles the confirmation callback for deleting a task."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("confirm_delete_"):
        task_id = int(data.split("_")[2])
        telegram_id = query.from_user.id

        db = SessionLocal()
        # Ensure the user owns the task before deleting
        task = (
            db.query(Task)
            .join(User)
            .filter(Task.task_id == task_id, User.telegram_id == telegram_id)
            .first()
        )

        if task:
            db.delete(task)
            db.commit()
            await query.edit_message_text(f"✅ Task `{task_id}` has been deleted.")
        else:
            await query.edit_message_text(
                "Error: Task not found or you do not have permission to delete it."
            )
        db.close()

    elif data == "cancel_delete":
        await query.edit_message_text("Deletion cancelled.")


async def button_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles button presses from inline keyboards that are not part of a conversation."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "view_tasks":
        await view_tasks(update, context)
    elif data.startswith("confirm_delete_") or data == "cancel_delete":
        await handle_delete_confirmation(update, context)
    else:
        # This can be expanded with other non-conversation callbacks
        await query.edit_message_text(
            text=f"This option is not implemented yet: {data}"
        )
        await query.message.reply_text(
            text="Main Menu", reply_markup=main_menu_keyboard()
        )


def register_commands(app: Application) -> None:
    """Registers all the command handlers with the application."""
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("tasks", tasks_command))
    app.add_handler(CommandHandler("task_delete", task_delete_command))
    app.add_handler(CommandHandler("status", status_command))

    # Register the generic button handler
    app.add_handler(CallbackQueryHandler(button_callback_handler))
