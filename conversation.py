# conversation.py

from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)
from menu import main_menu_keyboard, ai_options_keyboard, confirmation_keyboard
from config import TASKS, save_tasks_to_yaml

# States for the conversation
NAME, SOURCES, TARGETS, AI_OPTIONS, CONFIRMATION = range(5)

async def add_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the conversation to add a new task."""
    context.user_data["ai_options"] = {
        "reword": False,
        "summarize": False,
        "header": None,
        "footer": None,
        "watermark": None,
    }
    await update.callback_query.edit_message_text(
        "Let's add a new task. First, what is the name of the task?"
    )
    return NAME

async def received_task_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the task name and asks for the source channels."""
    context.user_data["task_name"] = update.message.text
    await update.message.reply_text(
        "Great. Now, please provide the source channel IDs, separated by commas."
    )
    return SOURCES

async def received_sources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the source channels and asks for the target channels."""
    try:
        context.user_data["sources"] = [
            int(x.strip()) for x in update.message.text.split(",")
        ]
        await update.message.reply_text(
            "Got it. Now, please provide the target channel IDs, separated by commas."
        )
        return TARGETS
    except ValueError:
        await update.message.reply_text(
            "Invalid input. Please provide a comma-separated list of numeric channel IDs."
        )
        return SOURCES

async def received_targets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the target channels and asks for the AI options."""
    try:
        context.user_data["targets"] = [
            int(x.strip()) for x in update.message.text.split(",")
        ]
        await update.message.reply_text(
            "Please select the AI options for this task.",
            reply_markup=ai_options_keyboard(context.user_data["ai_options"]),
        )
        return AI_OPTIONS
    except ValueError:
        await update.message.reply_text(
            "Invalid input. Please provide a comma-separated list of numeric channel IDs."
        )
        return TARGETS

async def toggle_ai_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggles an AI option."""
    query = update.callback_query
    option = query.data.split("_")[1]
    context.user_data["ai_options"][option] = not context.user_data["ai_options"][
        option
    ]
    await query.edit_message_reply_markup(
        reply_markup=ai_options_keyboard(context.user_data["ai_options"])
    )
    return AI_OPTIONS

async def done_ai_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finishes the AI options selection and asks for confirmation."""
    ai_options = context.user_data["ai_options"]
    confirmation_message = (
        "Please confirm the new task:\n\n"
        f"**Name:** {context.user_data['task_name']}\n"
        f"**Sources:** {context.user_data['sources']}\n"
        f"**Targets:** {context.user_data['targets']}\n"
        f"**Reword:** {'✅' if ai_options['reword'] else '❌'}\n"
        f"**Summarize:** {'✅' if ai_options['summarize'] else '❌'}\n"
        f"**Header:** {ai_options['header'] or 'Not set'}\n"
        f"**Footer:** {ai_options['footer'] or 'Not set'}\n"
        f"**Watermark:** {ai_options['watermark'] or 'Not set'}\n"
    )
    await update.callback_query.edit_message_text(
        confirmation_message,
        reply_markup=confirmation_keyboard(),
        parse_mode="Markdown",
    )
    return CONFIRMATION

async def confirm_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the task."""
    new_task = {
        "name": context.user_data["task_name"],
        "sources": context.user_data["sources"],
        "targets": context.user_data["targets"],
        "ai_options": context.user_data["ai_options"],
    }
    TASKS.append(new_task)
    save_tasks_to_yaml()
    await update.callback_query.edit_message_text(
        "Task saved successfully!", reply_markup=main_menu_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels the task creation."""
    await update.callback_query.edit_message_text(
        "Task creation canceled.", reply_markup=main_menu_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END
