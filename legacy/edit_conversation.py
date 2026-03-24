# edit_conversation.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)
from menu import main_menu_keyboard, ai_options_keyboard
from config import TASKS, save_tasks_to_yaml

# States for the conversation
SELECT_TASK, EDIT_MENU, EDIT_NAME, EDIT_SOURCES, EDIT_TARGETS, EDIT_AI_OPTIONS, CONFIRM_EDIT = range(20, 27)

async def edit_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the conversation to edit a new task."""
    from menu import edit_task_keyboard

    if not TASKS:
        await update.callback_query.edit_message_text(
            text="No tasks to edit.", reply_markup=main_menu_keyboard()
        )
        return ConversationHandler.END
    await update.callback_query.edit_message_text(
        "Select a task to edit:", reply_markup=edit_task_keyboard()
    )
    return SELECT_TASK

async def select_task_to_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Selects the task to edit."""
    from menu import edit_options_keyboard
    task_index = int(update.callback_query.data.split("_")[2])
    context.user_data["task_index"] = task_index
    context.user_data["task"] = TASKS[task_index].copy()

    await update.callback_query.edit_message_text(
        f"Editing task: **{context.user_data['task']['name']}**\n\n"
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
    context.user_data["task"]["name"] = update.message.text
    await update.message.reply_text(
        f"Name updated to: **{context.user_data['task']['name']}**\n\n"
        "What else would you like to edit?",
        reply_markup=edit_options_keyboard(),
        parse_mode="Markdown",
    )
    return EDIT_MENU

async def edit_sources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts editing sources by asking for platform."""
    from menu import platform_selection_keyboard
    await update.callback_query.edit_message_text(
        "Select the **new source** platform:",
        reply_markup=platform_selection_keyboard("edit_source_"),
        parse_mode="Markdown"
    )
    return EDIT_SOURCES

async def received_edit_source_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores the platform and asks for the identifier."""
    query = update.callback_query
    await query.answer()
    platform = query.data.split("_")[2]
    context.user_data["edit_source_platform"] = platform
    prompt = "Twitter username:" if platform == "twitter" else "Telegram Channel ID:"
    await query.edit_message_text(f"Please provide the {prompt}")
    return EDIT_SOURCES

async def received_new_sources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the new source identifier."""
    from menu import edit_options_keyboard
    platform = context.user_data.get("edit_source_platform", "twitter")
    text = update.message.text.strip()
    
    context.user_data["task"]["sources"] = [{"platform": platform, "identifier": text if platform == "twitter" else int(text)}]
    
    await update.message.reply_text(
        "Sources updated! What else would you like to edit?",
        reply_markup=edit_options_keyboard(),
        parse_mode="Markdown",
    )
    return EDIT_MENU

async def edit_targets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts editing targets by asking for platform."""
    from menu import platform_selection_keyboard
    await update.callback_query.edit_message_text(
        "Select the **new destination** platform:",
        reply_markup=platform_selection_keyboard("edit_target_"),
        parse_mode="Markdown"
    )
    return EDIT_TARGETS

async def received_edit_target_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores the platform and asks for the identifier."""
    query = update.callback_query
    await query.answer()
    platform = query.data.split("_")[2]
    context.user_data["edit_target_platform"] = platform
    prompt = "Twitter username:" if platform == "twitter" else "Telegram Channel ID:"
    await query.edit_message_text(f"Please provide the {prompt}")
    return EDIT_TARGETS

async def received_new_targets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the new target identifier."""
    from menu import edit_options_keyboard
    platform = context.user_data.get("edit_target_platform", "twitter")
    text = update.message.text.strip()
    
    context.user_data["task"]["targets"] = [{"platform": platform, "identifier": text if platform == "twitter" else int(text)}]
    
    await update.message.reply_text(
        "Targets updated! What else would you like to edit?",
        reply_markup=edit_options_keyboard(),
        parse_mode="Markdown",
    )
    return EDIT_MENU

async def edit_ai_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the AI options editing."""
    await update.callback_query.edit_message_text(
        "Please select the AI options for this task.",
        reply_markup=ai_options_keyboard(context.user_data["task"]["ai_options"]),
    )
    return EDIT_AI_OPTIONS

async def done_editing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the changes."""
    task_index = context.user_data["task_index"]
    TASKS[task_index] = context.user_data["task"]
    save_tasks_to_yaml()
    await update.callback_query.edit_message_text(
        "Task updated successfully!",
        reply_markup=main_menu_keyboard(),
    )
    context.user_data.clear()
    return ConversationHandler.END
