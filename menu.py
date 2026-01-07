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
        [InlineKeyboardButton("❓ Help", callback_data="help")],
    ]
    return InlineKeyboardMarkup(keyboard)

def ai_options_keyboard(options):
    """Returns the AI options keyboard with toggle buttons."""
    keyboard = [
        [
            InlineKeyboardButton(
                f"Reword: {'✅' if options['reword'] else '❌'}",
                callback_data="toggle_reword",
            )
        ],
        [
            InlineKeyboardButton(
                f"Summarize: {'✅' if options['summarize'] else '❌'}",
                callback_data="toggle_summarize",
            )
        ],
        [InlineKeyboardButton("Done", callback_data="done_ai_options")],
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
