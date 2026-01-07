# edit_conversation.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)
from menu import main_menu_keyboard, ai_options_keyboard
from database import SessionLocal, Task
from main import load_tasks

# States for the conversation
SELECT_TASK, EDIT_MENU, EDIT_NAME, EDIT_SOURCES, EDIT_TARGETS, EDIT_AI_OPTIONS, CONFIRM_EDIT = range(7)

async def edit_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the conversation to edit a task."""
    from menu import edit_task_keyboard
    db = SessionLocal()
    tasks = db.query(Task).all()
    db.close()

    if not tasks:
        await update.callback_query.edit_message_text(
            text="No tasks to edit.", reply_markup=main_menu_keyboard()
        )
        return ConversationHandler.END
    await update.callback_query.edit_message_text(
        "Select a task to edit:", reply_markup=edit_task_keyboard(tasks)
    )
    return SELECT_TASK


async def select_task_to_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Selects the task to edit."""
    from menu import edit_options_keyboard
    task_id = int(update.callback_query.data.split("_")[2])
    context.user_data["task_id"] = task_id

    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    db.close()

    if not task:
        await update.callback_query.edit_message_text(
            "Task not found.", reply_markup=main_menu_keyboard()
        )
        return ConversationHandler.END

    # Store a dictionary representation for editing
    context.user_data["task_edit"] = {
        "name": task.name,
        "sources": task.sources,
        "targets": task.targets,
        "ai_options": task.ai_options,
        "filters": task.filters,
    }

    await update.callback_query.edit_message_text(
        f"Editing task: **{task.name}**\n\n"
        "What would you like to edit?",
        reply_markup=edit_options_keyboard(),
        parse_mode="Markdown",
    )
    return EDIT_MENU

async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Asks for the new name."""
    await update.callback_query.edit_message_text("Please enter the new name for the task.")
    return EDIT_NAME

async def received_new_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the new name."""
    from menu import edit_options_keyboard
    context.user_data["task_edit"]["name"] = update.message.text
    await update.message.reply_text(
        f"Name updated to: **{context.user_data['task_edit']['name']}**\n\n"
        "What else would you like to edit?",
        reply_markup=edit_options_keyboard(),
        parse_mode="Markdown",
    )
    return EDIT_MENU

async def edit_sources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Asks for the new sources."""
    await update.callback_query.edit_message_text("Please enter the new source channel IDs, separated by commas.")
    return EDIT_SOURCES

async def received_new_sources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the new sources."""
    from menu import edit_options_keyboard
    try:
        context.user_data["task_edit"]["sources"] = [
            int(x.strip()) for x in update.message.text.split(",")
        ]
        await update.message.reply_text(
            f"Sources updated to: **{context.user_data['task_edit']['sources']}**\n\n"
            "What else would you like to edit?",
            reply_markup=edit_options_keyboard(),
            parse_mode="Markdown",
        )
        return EDIT_MENU
    except ValueError:
        await update.message.reply_text(
            "Invalid input. Please provide a comma-separated list of numeric channel IDs."
        )
        return EDIT_SOURCES

async def edit_targets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Asks for the new targets."""
    await update.callback_query.edit_message_text("Please enter the new target channel IDs, separated by commas.")
    return EDIT_TARGETS

async def received_new_targets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the new targets."""
    from menu import edit_options_keyboard
    try:
        context.user_data["task_edit"]["targets"] = [
            int(x.strip()) for x in update.message.text.split(",")
        ]
        await update.message.reply_text(
            f"Targets updated to: **{context.user_data['task_edit']['targets']}**\n\n"
            "What else would you like to edit?",
            reply_markup=edit_options_keyboard(),
            parse_mode="Markdown",
        )
        return EDIT_MENU
    except ValueError:
        await update.message.reply_text(
            "Invalid input. Please provide a comma-separated list of numeric channel IDs."
        )
        return EDIT_TARGETS


async def edit_ai_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the AI options editing."""
    await update.callback_query.edit_message_text(
        "Please select the AI options for this task.",
        reply_markup=ai_options_keyboard(context.user_data["task_edit"]["ai_options"]),
    )
    return EDIT_AI_OPTIONS


async def done_editing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the changes to the database."""
    task_id = context.user_data["task_id"]
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()

    if task:
        task.name = context.user_data["task_edit"]["name"]
        task.sources = context.user_data["task_edit"]["sources"]
        task.targets = context.user_data["task_edit"]["targets"]
        task.ai_options = context.user_data["task_edit"]["ai_options"]
        db.commit()
        load_tasks()  # Refresh the cache
        await update.callback_query.edit_message_text(
            "Task updated successfully!",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await update.callback_query.edit_message_text(
            "Error: Task not found.",
            reply_markup=main_menu_keyboard(),
        )

    db.close()
    context.user_data.clear()
    return ConversationHandler.END
