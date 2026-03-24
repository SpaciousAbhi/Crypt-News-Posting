# bot/menu.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict, Any

class Menu:
    @staticmethod
    def main_menu():
        keyboard = [
            [InlineKeyboardButton("📊 Tasks", callback_data="tasks_view")],
            [InlineKeyboardButton("➕ New Task", callback_data="tasks_add")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings_view")],
            [InlineKeyboardButton("❓ Help", callback_data="help_view")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def settings_menu(config: Dict[str, Any]):
        def status(val): return "✅" if val else "❌"
        
        keyboard = [
            [InlineKeyboardButton("🔑 Groq Key", callback_data="settings_set_groq"),
             InlineKeyboardButton(status(config.get('GROQ_API_KEY')), callback_data="settings_view")],
            [InlineKeyboardButton("👤 Twitter User", callback_data="settings_set_tw_user"),
             InlineKeyboardButton(status(config.get('TWITTER_USERNAME')), callback_data="settings_view")],
            [InlineKeyboardButton("🔒 Twitter Pass", callback_data="settings_set_tw_pass"),
             InlineKeyboardButton(status(config.get('TWITTER_PASSWORD')), callback_data="settings_view")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_main")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def task_list(tasks: List[Dict[str, Any]]):
        keyboard = []
        for task in tasks:
            status = "▶️" if task['is_active'] else "⏸"
            keyboard.append([InlineKeyboardButton(f"{status} {task['name']}", callback_data=f"tasks_manage_{task['id']}")])
        
        keyboard.append([InlineKeyboardButton("➕ New Task", callback_data="tasks_add")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu_main")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def task_manage(task: Dict[str, Any]):
        status_text = "⏸ Pause" if task['is_active'] else "▶️ Resume"
        status_cmd = "pause" if task['is_active'] else "resume"
        
        keyboard = [
            [InlineKeyboardButton(status_text, callback_data=f"tasks_{status_cmd}_{task['id']}")],
            [InlineKeyboardButton("✏️ Edit", callback_data=f"tasks_edit_{task['id']}")],
            [InlineKeyboardButton("🗑 Delete", callback_data=f"tasks_delete_{task['id']}")],
            [InlineKeyboardButton("🔙 Back", callback_data="tasks_view")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def platform_selection(prefix: str):
        keyboard = [
            [InlineKeyboardButton("🐦 Twitter (RSS)", callback_data=f"{prefix}_twitter_rss")],
            [InlineKeyboardButton("✈️ Telegram", callback_data=f"{prefix}_telegram")],
            [InlineKeyboardButton("❌ Cancel", callback_data="menu_main")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def confirmation_keyboard(prefix: str):
        keyboard = [
            [InlineKeyboardButton("✅ Confirm", callback_data=f"{prefix}_confirm"),
             InlineKeyboardButton("❌ Cancel", callback_data=f"{prefix}_cancel")]
        ]
        return InlineKeyboardMarkup(keyboard)
