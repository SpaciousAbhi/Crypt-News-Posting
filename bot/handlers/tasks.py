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

async def toggle_task_status(update: Update, context: ContextTypes.DEFAULT_TYPE, status: bool):
    """Pauses or resumes a task with feedback."""
    query = update.callback_query
    await query.answer()
    
    task_id = int(query.data.split("_")[2])
    db.execute("UPDATE tasks SET is_active = %s WHERE id = %s", (status, task_id))
    
    action = "RESUMED ▶️" if status else "PAUSED ⏸"
    await query.edit_message_text(f"✨ **Task Status Updated!**\n\nThe task has been {action} and the engine has been notified.", reply_markup=Menu.main_menu(), parse_mode="Markdown")
    return ConversationHandler.END

async def delete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deletes a task permanently."""
    query = update.callback_query
    await query.answer()
    
    task_id = int(query.data.split("_")[2])
    db.delete_task(task_id)
    
    await query.edit_message_text("🗑️ **Task Deleted.**\n\nTask and all associated history have been removed from the database.", reply_markup=Menu.main_menu(), parse_mode="Markdown")
    return ConversationHandler.END

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows a professional, detailed help guide."""
    help_text = (
        "📖 **Professional Automation Guide**\n\n"
        "This system uses AI (LLaMA3) to redesign content from sources and publish it to your channels.\n\n"
        "⚡ **Getting Started:**\n"
        "1️⃣ **Configure Settings:** Enter your Groq API Key and Twitter login in the 'Settings' menu.\n"
        "2️⃣ **Create a Task:** Give it a name, choose a source (e.g., a Twitter handle), and a target (e.g., your Telegram channel).\n"
        "3️⃣ **Let it Run:** Every 60 seconds, the engine checks for new posts, redesigns them for a premium look, and publishes them.\n\n"
        "💡 **Pro Tip:** For Telegram targets, always use the ID starting with `-100...` for maximum reliability."
    )
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(help_text, reply_markup=Menu.main_menu(), parse_mode="Markdown")
    else:
        await update.message.reply_text(help_text, reply_markup=Menu.main_menu(), parse_mode="Markdown")
    return ConversationHandler.END

async def add_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the 'Add Task' conversation with clear guidance."""
    query = update.callback_query
    await query.answer()
    
    msg = (
        "🏗️ **New Task Creation**\n\n"
        "Let's build your automation! Follow the steps below.\n\n"
        "**Step 1:** Enter a unique **Name** for this task (e.g. `Crypto Alert` or `Elon Tweets`):"
    )
    await query.edit_message_text(msg, parse_mode="Markdown")
    return BotState.TASK_NAME

async def receive_task_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the name and explains the 'Source' stage."""
    context.user_data['new_task_name'] = update.message.text
    
    msg = (
        f"✅ Name Set: `{update.message.text}`\n\n"
        "**Step 2: Source Platform**\n"
        "Where should we monitor for new content? Select a platform below:"
    )
    await update.message.reply_text(
        msg,
        reply_markup=Menu.platform_selection("source"),
        parse_mode="Markdown"
    )
    return BotState.SELECT_SOURCE_PLATFORM

async def receive_source_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores source platform and provides input examples."""
    query = update.callback_query
    await query.answer()
    
    platform = query.data.split("_")[1]
    context.user_data['new_source_platform'] = platform
    
    if platform == "twitter_rss":
        prompt = (
            "🐦 **Twitter Source Details**\n\n"
            "Please provide the **Twitter Username** you want to mirror.\n"
            "💡 Example: `elonmusk` or `@elonmusk`"
        )
    else:
        prompt = (
            "✈️ **Telegram Source Details**\n\n"
            "Please provide the **Channel ID** (e.g. `-100...`) or **@username**."
        )
        
    await query.edit_message_text(prompt, parse_mode="Markdown")
    return BotState.ENTER_SOURCE_ID

async def receive_source_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives and validates source ID, then asks for destination."""
    source_id = update.message.text.strip().replace("@", "")
    platform = context.user_data.get('new_source_platform')
    
    if platform == "twitter_rss" and not re.match(r"^[\w]{1,15}$", source_id):
        await update.message.reply_text("❌ **Invalid Twitter username.**\nPlease try again (e.g. `binance`):")
        return BotState.ENTER_SOURCE_ID
        
    context.user_data['new_source_id'] = source_id
    
    msg = (
        f"🎯 Source Tracked: `@{source_id}`\n\n"
        "**Step 3: Destination Platform**\n"
        "Where should the AI-redesigned content be published?"
    )
    await update.message.reply_text(
        msg,
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
    
    if platform == "twitter":
        prompt = "🐦 Enter the **Twitter Account** (handle) to publish to:"
    else:
        prompt = (
            "✈️ **Telegram Target Details**\n\n"
            "Provide the **Channel ID** where you want to post.\n"
            "💡 Tip: Use your channel's ID (starts with `-100...`)."
        )
    await query.edit_message_text(f"**Step 4:** {prompt}", parse_mode="Markdown")
    return BotState.ENTER_DEST_ID

async def receive_dest_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives dest ID and shows a professional summary."""
    dest_id = update.message.text.strip()
    platform = context.user_data.get('new_dest_platform')
    
    # Warning for common Telegram ID mistakes
    if platform == "telegram" and not (dest_id.startswith("-100") or dest_id.startswith("@")):
        await update.message.reply_text("⚠️ **Note:** Telegram channel IDs usually start with `-100...`. Double-check your ID.")
        
    context.user_data['new_dest_id'] = dest_id
    
    summary = (
        "📦 **Final Task Review**\n\n"
        f"📋 **Name:** `{context.user_data['new_task_name']}`\n"
        f"📥 **Source:** `{context.user_data['new_source_platform']} ({context.user_data['new_source_id']})`\n"
        f"📤 **Target:** `{context.user_data['new_dest_platform']} ({context.user_data['new_dest_id']})`\n\n"
        "**Ready to launch?** The AI engine will monitor and redesign posts for you."
    )
    
    await update.message.reply_text(
        summary,
        reply_markup=Menu.confirmation_keyboard("task_create"),
        parse_mode="Markdown"
    )
    return BotState.CONFIRM_TASK

async def cancel_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels the conversation with a clear message."""
    query = update.callback_query
    if query: await query.answer()
    
    text = "❌ **Task Creation Aborted**\n\nNo changes were made to your system. Returning to the dashboard..."
    if query:
        await query.edit_message_text(text, reply_markup=Menu.main_menu(), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=Menu.main_menu(), parse_mode="Markdown")
    return ConversationHandler.END

async def commit_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the task with a celebratory success message."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "task_create_confirm":
        # Final Save
        task_name = context.user_data['new_task_name']
        task_id = db.create_task(task_name, update.effective_user.id)
        db.add_source(task_id, context.user_data['new_source_platform'], context.user_data['new_source_id'])
        db.add_destination(task_id, context.user_data['new_dest_platform'], context.user_data['new_dest_id'])
        
        success_msg = (
            f"🎉 **Success! Task Created.**\n\n"
            f"Your new task `{task_name}` is now live! The background engine has been synchronized and will begin monitoring for updates shortly."
        )
        await query.edit_message_text(success_msg, parse_mode="Markdown", reply_markup=Menu.main_menu())
    else:
        await query.edit_message_text("❌ **Task Aborted.**\n\nNo changes were saved.", reply_markup=Menu.main_menu(), parse_mode="Markdown")
        
    return ConversationHandler.END
