# conversation.py

from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)
from menu import main_menu_keyboard, ai_options_keyboard, confirmation_keyboard
from database import SessionLocal, Task
from cache import load_tasks

# States for the conversation
(
    NAME,
    SOURCES,
    TARGETS,
    AI_OPTIONS,
    HEADER,
    FOOTER,
    WATERMARK_FROM,
    WATERMARK_TO,
    CONFIRMATION,
) = range(9)


async def add_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the conversation to add a new task."""
    context.user_data["ai_options"] = {
        "reword": False,
        "summarize": False,
        "header": None,
        "footer": None,
        "watermark": {"replace_from": None, "replace_to": None},
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
    """Finishes the AI options selection and asks for the header."""
    await update.callback_query.edit_message_text(
        "Please enter the header text, or send 'skip' for no header."
    )
    return HEADER


async def received_header(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the header and asks for the footer."""
    if update.message.text.lower() != "skip":
        context.user_data["ai_options"]["header"] = update.message.text
    await update.message.reply_text(
        "Please enter the footer text, or send 'skip' for no footer."
    )
    return FOOTER


async def received_footer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the footer and asks for the watermark."""
    if update.message.text.lower() != "skip":
        context.user_data["ai_options"]["footer"] = update.message.text
    await update.message.reply_text(
        "Please enter the watermark text to be replaced, or send 'skip'."
    )
    return WATERMARK_FROM


async def received_watermark_from(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Receives the watermark 'from' text and asks for the 'to' text."""
    if update.message.text.lower() != "skip":
        context.user_data["ai_options"]["watermark"][
            "replace_from"
        ] = update.message.text
        await update.message.reply_text(
            "Please enter the new watermark text."
        )
        return WATERMARK_TO
    else:
        # Skip the watermark and go to confirmation
        return await show_confirmation(update, context)


async def received_watermark_to(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Receives the watermark 'to' text and shows the confirmation."""
    context.user_data["ai_options"]["watermark"][
        "replace_to"
    ] = update.message.text
    return await show_confirmation(update, context)


async def show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the final confirmation message."""
    ai_options = context.user_data["ai_options"]
    watermark = ai_options["watermark"]
    watermark_text = (
        f"'{watermark['replace_from']}' -> '{watermark['replace_to']}'"
        if watermark["replace_from"] and watermark["replace_to"]
        else "Not set"
    )

    confirmation_message = (
        "Please confirm the new task:\n\n"
        f"**Name:** {context.user_data['task_name']}\n"
        f"**Sources:** {context.user_data['sources']}\n"
        f"**Targets:** {context.user_data['targets']}\n"
        f"**Reword:** {'✅' if ai_options['reword'] else '❌'}\n"
        f"**Summarize:** {'✅' if ai_options['summarize'] else '❌'}\n"
        f"**Header:** {ai_options['header'] or 'Not set'}\n"
        f"**Footer:** {ai_options['footer'] or 'Not set'}\n"
        f"**Watermark:** {watermark_text}\n"
    )

    # Check if this function was called from a query or a message
    if update.callback_query:
        await update.callback_query.edit_message_text(
            confirmation_message,
            reply_markup=confirmation_keyboard(),
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            confirmation_message,
            reply_markup=confirmation_keyboard(),
            parse_mode="Markdown",
        )
    return CONFIRMATION


async def confirm_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the task to the database."""
    db = SessionLocal()
    new_task = Task(
        name=context.user_data["task_name"],
        sources=context.user_data["sources"],
        targets=context.user_data["targets"],
        ai_options=context.user_data["ai_options"],
        filters={},  # Initialize with empty filters
    )
    db.add(new_task)
    db.commit()
    db.close()
    load_tasks()  # Refresh the cache

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
