# bot/menu.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict, Any

class Menu:
    @staticmethod
    def main_menu():
        keyboard = [
            [InlineKeyboardButton("📊 View All Tasks", callback_data="tasks_view")],
            [InlineKeyboardButton("➕ Create New Task", callback_data="tasks_add")],
            [InlineKeyboardButton("⚙️ System Settings", callback_data="settings_view")],
            [InlineKeyboardButton("📖 Help & Guide", callback_data="help_view")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def settings_menu(config: Dict[str, Any]):
        def status(val): return "✅ Set" if val else "❌ Not Set"
        
        keyboard = [
            [InlineKeyboardButton("🧠 Groq API Key", callback_data="settings_set_groq"),
             InlineKeyboardButton(status(config.get('GROQ_API_KEY')), callback_data="settings_view")],
            [InlineKeyboardButton("👤 Twitter Username", callback_data="settings_set_tw_user"),
             InlineKeyboardButton(status(config.get('TWITTER_USERNAME')), callback_data="settings_view")],
            [InlineKeyboardButton("🔒 Twitter Password", callback_data="settings_set_tw_pass"),
             InlineKeyboardButton(status(config.get('TWITTER_PASSWORD')), callback_data="settings_view")],
            [InlineKeyboardButton("🔙 Return to Menu", callback_data="menu_main")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def task_list(tasks: List[Dict[str, Any]]):
        keyboard = []
        for task in tasks:
            status = "🟢" if task['is_active'] else "🟡"
            keyboard.append([InlineKeyboardButton(f"{status} {task['name']}", callback_data=f"tasks_manage_{task['id']}")])
        
        keyboard.append([InlineKeyboardButton("➕ Add Another Task", callback_data="tasks_add")])
        keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_main")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def task_manage(task: Dict[str, Any]):
        status_text = "⏸️ Pause Automation" if task['is_active'] else "▶️ Resume Automation"
        status_cmd = "pause" if task['is_active'] else "resume"
        
        keyboard = [
            [InlineKeyboardButton(status_text, callback_data=f"tasks_{status_cmd}_{task['id']}")],
            [InlineKeyboardButton("🗑️ Delete Permanently", callback_data=f"tasks_delete_{task['id']}")],
            [InlineKeyboardButton("🔙 Back to Task List", callback_data="tasks_view")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def platform_selection(prefix: str):
        keyboard = [
            [InlineKeyboardButton("🐦 Twitter (via RSS Mirror)", callback_data=f"{prefix}_twitter_rss")],
            [InlineKeyboardButton("🐦 Twitter (Direct Login)", callback_data=f"{prefix}_twitter")],
            [InlineKeyboardButton("✈️ Telegram Channel", callback_data=f"{prefix}_telegram")],
            [InlineKeyboardButton("❌ Abort & Cancel", callback_data="menu_main")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def confirmation_keyboard(prefix: str):
        keyboard = [
            [InlineKeyboardButton("🚀 Launch Task", callback_data=f"{prefix}_confirm"),
             InlineKeyboardButton("❌ Cancel", callback_data=f"{prefix}_cancel")]
        ]
        return InlineKeyboardMarkup(keyboard)
