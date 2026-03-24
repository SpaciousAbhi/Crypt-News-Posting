# menu.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import TASKS

def main_menu_keyboard():
    """Returns the main menu keyboard."""
    keyboard = [
        [InlineKeyboardButton("📊 View Tasks", callback_data="view_tasks")],
        [InlineKeyboardButton("➕ Add New Task", callback_data="add_task")],
        [InlineKeyboardButton("➖ Remove Task", callback_data="remove_task")],
        [InlineKeyboardButton("✏️ Edit Task", callback_data="edit_task")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("❓ Help", callback_data="help")],
    ]
    return InlineKeyboardMarkup(keyboard)


def settings_keyboard():
    """Returns the settings menu keyboard."""
    keyboard = [
        [InlineKeyboardButton("🔑 Set Groq API Key", callback_data="set_groq_key")],
        [InlineKeyboardButton("👤 Set Twitter Username", callback_data="set_tw_user")],
        [InlineKeyboardButton("🔒 Set Twitter Password", callback_data="set_tw_pass")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="start")],
    ]
    return InlineKeyboardMarkup(keyboard)

def ai_options_keyboard(options):
    """Returns the AI options keyboard with toggle buttons."""
    keyboard = [
        [
            InlineKeyboardButton(
                f"Redesign (AI): {'✅' if options.get('redesign') else '❌'}",
                callback_data="toggle_redesign",
            )
        ],
        [
            InlineKeyboardButton(
                f"Reword: {'✅' if options.get('reword') else '❌'}",
                callback_data="toggle_reword",
            )
        ],
        [
            InlineKeyboardButton(
                f"Summarize: {'✅' if options.get('summarize') else '❌'}",
                callback_data="toggle_summarize",
            )
        ],
        [InlineKeyboardButton("Done", callback_data="done_ai_options")],
    ]
    return InlineKeyboardMarkup(keyboard)

def platform_selection_keyboard(prefix=""):
    """Returns a keyboard for platform selection."""
    keyboard = [
        [
            InlineKeyboardButton("🐦 Twitter (X)", callback_data=f"{prefix}platform_twitter"),
            InlineKeyboardButton("✈️ Telegram", callback_data=f"{prefix}platform_telegram"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def task_control_keyboard(index, is_paused):
    """Returns options for a specific task."""
    status_btn = "▶️ Resume" if is_paused else "⏸ Pause"
    status_cmd = "resume" if is_paused else "pause"
    keyboard = [
        [InlineKeyboardButton(status_btn, callback_data=f"{status_cmd}_task_{index}")],
        [InlineKeyboardButton("✏️ Edit", callback_data=f"select_task_{index}")],
        [InlineKeyboardButton("❌ Remove", callback_data=f"delete_task_{index}")],
        [InlineKeyboardButton("🔙 Back", callback_data="view_tasks")],
    ]
    return InlineKeyboardMarkup(keyboard)

def remove_task_keyboard():
    """Returns a keyboard with a button for each task to remove."""
    keyboard = []
    for i, task in enumerate(TASKS):
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"❌ {task['name']}", callback_data=f"delete_task_{i}"
                )
            ]
        )
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="start")])
    return InlineKeyboardMarkup(keyboard)

def edit_task_keyboard():
    """Returns a keyboard with a button for each task to edit."""
    keyboard = []
    for i, task in enumerate(TASKS):
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"✏️ {task['name']}", callback_data=f"select_task_{i}"
                )
            ]
        )
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="start")])
    return InlineKeyboardMarkup(keyboard)

def edit_options_keyboard():
    """Returns a keyboard with options to edit a task."""
    keyboard = [
        [InlineKeyboardButton("✏️ Name", callback_data="edit_name")],
        [InlineKeyboardButton("📥 Sources", callback_data="edit_sources")],
        [InlineKeyboardButton("📤 Targets", callback_data="edit_targets")],
        [InlineKeyboardButton("🤖 AI Options", callback_data="edit_ai_options")],
        [InlineKeyboardButton("✅ Done Editing", callback_data="done_editing")],
    ]
    return InlineKeyboardMarkup(keyboard)

def confirmation_keyboard():
    """Returns a confirmation keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data="confirm_task"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_task"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
