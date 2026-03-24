# bot/handlers/settings.py

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.states import BotState
from bot.menu import Menu
from database.manager import db

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the settings menu."""
    config = {
        'GROQ_API_KEY': db.get_setting('GROQ_API_KEY'),
        'TWITTER_USERNAME': db.get_setting('TWITTER_USERNAME'),
        'TWITTER_PASSWORD': db.get_setting('TWITTER_PASSWORD')
    }
    
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "⚙️ **Global Settings**\n\nManage your API keys and Twitter credentials below.",
            reply_markup=Menu.settings_menu(config),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "⚙️ **Global Settings**\n\nManage your API keys and Twitter credentials below.",
            reply_markup=Menu.settings_menu(config),
            parse_mode="Markdown"
        )
    return BotState.SETTINGS_MENU

async def ask_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    key_map = {
        "settings_set_groq": (BotState.SET_GROQ_KEY, "🔑 Please enter your **Groq API Key**:"),
        "settings_set_tw_user": (BotState.SET_TW_USER, "👤 Please enter your **Twitter Username**:"),
        "settings_set_tw_pass": (BotState.SET_TW_PASS, "🔒 Please enter your **Twitter Password**:")
    }
    
    next_state, prompt = key_map.get(query.data)
    await query.edit_message_text(prompt, parse_mode="Markdown")
    return next_state

async def save_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the input value to the corresponding setting."""
    if str(update.effective_chat.id) != str(db.get_setting("ADMIN_CHAT_ID") or "1654334233"):
        return ConversationHandler.END

    user_input = update.message.text
    # We use context.user_data to track what we're saving if needed, 
    # but the ConversationHandler state is enough.
    
    # This function will be called by different states in the ConversationHandler
    # We'll handle the logic in the main controller for cleaner dispatch,
    # or implement specific handlers here.
    
    # Generic save based on context
    setting_key = context.user_data.get('setting_to_save')
    if setting_key:
        db.set_setting(setting_key, user_input)
        await update.message.reply_text(f"✅ Setting `{setting_key}` updated successfully!", reply_markup=Menu.main_menu())
        
    return ConversationHandler.END

async def set_groq_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.set_setting("GROQ_API_KEY", update.message.text)
    await update.message.reply_text("✅ Groq API Key updated!", reply_markup=Menu.main_menu())
    return ConversationHandler.END

async def set_tw_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.set_setting("TWITTER_USERNAME", update.message.text)
    await update.message.reply_text("✅ Twitter Username updated!", reply_markup=Menu.main_menu())
    return ConversationHandler.END

async def set_tw_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.set_setting("TWITTER_PASSWORD", update.message.text)
    await update.message.reply_text("✅ Twitter Password updated!", reply_markup=Menu.main_menu())
    return ConversationHandler.END
