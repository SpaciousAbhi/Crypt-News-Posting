# ui/buttons.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard():
    """Returns the main menu keyboard."""
    keyboard = [
        [InlineKeyboardButton("📊 View Tasks", callback_data="view_tasks")],
        [InlineKeyboardButton("➕ Create New Task", callback_data="create_task")],
        [InlineKeyboardButton("❓ Help & Documentation", callback_data="help")],
    ]
    return InlineKeyboardMarkup(keyboard)


def task_menu_keyboard():
    """Returns the keyboard for the main task configuration menu."""
    keyboard = [
        [InlineKeyboardButton("➕ Manage Sources", callback_data="mng_sources")],
        [InlineKeyboardButton("🎯 Manage Targets", callback_data="mng_targets")],
        [InlineKeyboardButton("🤖 Manage AI Rules", callback_data="mng_ai_rules")],
        [InlineKeyboardButton("✏️ Rename Task", callback_data="rename_task")],
        [
            InlineKeyboardButton("✅ Save & Enable", callback_data="save_enable"),
            InlineKeyboardButton("💾 Save Disabled", callback_data="save_disable"),
        ],
        [InlineKeyboardButton("❌ Cancel Creation", callback_data="cancel_creation")],
    ]
    return InlineKeyboardMarkup(keyboard)
