# bot/handlers/settings.py

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.states import BotState
from bot.menu import Menu
from database.manager import db

from services.config_service import config

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the settings menu with a professional overview."""
    user_id = update.effective_user.id
    if str(user_id) != str(config.admin_id):
        return ConversationHandler.END

    settings_data = {
        'GROQ_API_KEY': db.get_setting('GROQ_API_KEY'),
        'TWITTER_USERNAME': db.get_setting('TWITTER_USERNAME'),
        'TWITTER_PASSWORD': db.get_setting('TWITTER_PASSWORD')
    }
    
    query = update.callback_query
    if query:
        await query.answer()
        msg = (
            "⚙️ **System Configuration**\n\n"
            "Manage your core credentials here. These stay securely in your database.\n\n"
            "🧠 **AI Service:** LLaMA3 redesigns your content.\n"
            "🐦 **Twitter Service:** Used for fetching & publishing."
        )
        await query.edit_message_text(
            msg,
            reply_markup=Menu.settings_menu(settings_data),
            parse_mode="Markdown"
        )
    return BotState.SETTINGS_MENU

async def ask_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provides detailed prompts for each setting."""
    query = update.callback_query
    await query.answer()
    
    key_map = {
        "settings_set_groq": (
            BotState.SET_GROQ_KEY, 
            "🔑 **Groq API Key**\n\nRequired for AI content redesign.\nFind it at `console.groq.com.\n\n**Please enter your key:**"
        ),
        "settings_set_tw_user": (
            BotState.SET_TW_USER, 
            "👤 **Twitter Account**\n\nProvide the username for login.\n💡 Example: `cryptoking_news`"
        ),
        "settings_set_tw_pass": (
            BotState.SET_TW_PASS, 
            "🔒 **Twitter Password**\n\nYour password is required for automation.\n🔑 **Enter it now:**"
        )
    }
    
    next_state, prompt = key_map.get(query.data)
    await query.edit_message_text(prompt, parse_mode="Markdown")
    return next_state

async def set_groq_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    if not val.startswith("gsk_") and len(val) < 20:
        await update.message.reply_text("⚠️ That doesn't look like a valid Groq API Key. Please try again or type /cancel:")
        return BotState.SET_GROQ_KEY
        
    db.set_setting("GROQ_API_KEY", val)
    await update.message.reply_text("✅ Groq API Key updated successfully!", reply_markup=Menu.main_menu())
    return ConversationHandler.END

async def set_tw_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip().replace("@", "")
    db.set_setting("TWITTER_USERNAME", val)
    await update.message.reply_text(f"✅ Twitter Username set to @{val}!", reply_markup=Menu.main_menu())
    return ConversationHandler.END

async def set_tw_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.set_setting("TWITTER_PASSWORD", update.message.text.strip())
    await update.message.reply_text("✅ Twitter Password encrypted and saved!", reply_markup=Menu.main_menu())
    return ConversationHandler.END
