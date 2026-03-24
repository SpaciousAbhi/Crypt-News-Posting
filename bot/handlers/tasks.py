# bot/handlers/tasks.py

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.states import BotState
from bot.menu import Menu
from database.manager import db
from services.logger import logger

async def view_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the list of tasks."""
    user_id = update.effective_user.id
    tasks = db.get_tasks(user_id)
    
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "📊 **Your Tasks**\n\nManage your automation tasks below.",
            reply_markup=Menu.task_list(tasks),
            parse_mode="Markdown"
        )
    return ConversationHandler.END

async def manage_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows options for a specific task."""
    query = update.callback_query
    await query.answer()
    
    task_id = int(query.data.split("_")[2])
    task = db.get_task_details(task_id)
    
    if not task:
        await query.edit_message_text("❌ Task not found.", reply_markup=Menu.main_menu())
        return ConversationHandler.END

    status_str = "✅ Active" if task['is_active'] else "⏸ Paused"
    detail_text = (
        f"🛠 **Managing Task:** {task['name']}\n"
        f"Status: {status_str}\n\n"
        f"📥 **Sources:** {len(task['sources'])}\n"
        f"📤 **Destinations:** {len(task['destinations'])}\n"
    )
    
    await query.edit_message_text(
        detail_text,
        reply_markup=Menu.task_manage(task),
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def add_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the 'Add Task' conversation."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("📝 **New Task**\n\nPlease enter a name for this task:")
    return BotState.TASK_NAME

async def receive_task_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the task name and asks for the source platform."""
    context.user_data['new_task_name'] = update.message.text
    
    await update.message.reply_text(
        "🌐 **Source Platform**\n\nWhere should we get updates from?",
        reply_markup=Menu.platform_selection("source"),
        parse_mode="Markdown"
    )
    return BotState.SELECT_SOURCE_PLATFORM

async def toggle_task_status(update: Update, context: ContextTypes.DEFAULT_TYPE, status: bool):
    """Pauses or resumes a task."""
    query = update.callback_query
    await query.answer()
    
    task_id = int(query.data.split("_")[2])
    db.execute("UPDATE tasks SET is_active = %s WHERE id = %s", (status, task_id))
    
    action = "resumed" if status else "paused"
    await query.edit_message_text(f"✅ Task {action} successfully!", reply_markup=Menu.main_menu())
    return ConversationHandler.END

async def delete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deletes a task."""
    query = update.callback_query
    await query.answer()
    
    task_id = int(query.data.split("_")[2])
    db.delete_task(task_id)
    
    await query.edit_message_text("🗑 Task deleted permanently.", reply_markup=Menu.main_menu())
    return ConversationHandler.END

async def receive_source_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores source platform and asks for identifier."""
    query = update.callback_query
    await query.answer()
    
    platform = query.data.split("_")[1]
    context.user_data['new_source_platform'] = platform
    
    prompt = "🐦 Twitter username (e.g. `elonmusk`):" if platform == "twitter_rss" else "✈️ Telegram Channel ID (e.g. `-100...`):"
    await query.edit_message_text(f"Please provide the {prompt}", parse_mode="Markdown")
    return BotState.ENTER_SOURCE_ID

async def receive_source_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the source ID and asks for destination platform."""
    context.user_data['new_source_id'] = update.message.text
    
    await update.message.reply_text(
        "🚀 **Destination Platform**\n\nWhere should the content be published?",
        reply_markup=Menu.platform_selection("dest"),
        parse_mode="Markdown"
    )
    return BotState.SELECT_DEST_PLATFORM

async def receive_dest_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores destination platform and asks for identifier."""
    query = update.callback_query
    await query.answer()
    
    platform = query.data.split("_")[1]
    context.user_data['new_dest_platform'] = platform
    
    prompt = "🐦 Twitter username (reposting):" if platform == "twitter" else "✈️ Telegram Channel/Group ID:"
    await query.edit_message_text(f"Please provide the {prompt}")
    return BotState.ENTER_DEST_ID

async def receive_dest_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the dest ID and asks for confirmation."""
    context.user_data['new_dest_id'] = update.message.text
    
    summary = (
        f"📝 **Task Summary**\n\n"
        f"**Name:** {context.user_data['new_task_name']}\n"
        f"**Source:** {context.user_data['new_source_platform']} ({context.user_data['new_source_id']})\n"
        f"**Destination:** {context.user_data['new_dest_platform']} ({context.user_data['new_dest_id']})\n"
    )
    
    await update.message.reply_text(
        summary,
        reply_markup=Menu.confirmation_keyboard("task_create"),
        parse_mode="Markdown"
    )
    return BotState.CONFIRM_TASK

async def commit_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the task to the database."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "task_create_confirm":
        # Final Save
        task_id = db.create_task(context.user_data['new_task_name'], update.effective_user.id)
        db.add_source(task_id, context.user_data['new_source_platform'], context.user_data['new_source_id'])
        db.add_destination(task_id, context.user_data['new_dest_platform'], context.user_data['new_dest_id'])
        
        await query.edit_message_text("✅ **Task Created Successfully!**\n\nThe background engine will start monitoring your source soon.", parse_mode="Markdown", reply_markup=Menu.main_menu())
    else:
        await query.edit_message_text("❌ Task creation cancelled.", reply_markup=Menu.main_menu())
        
    return ConversationHandler.END
