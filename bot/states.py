# bot/states.py

from enum import Enum, auto

class BotState(Enum):
    # Task Creation
    START = auto()
    TASK_NAME = auto()
    SELECT_SOURCE_PLATFORM = auto()
    ENTER_SOURCE_ID = auto()
    SELECT_DEST_PLATFORM = auto()
    ENTER_DEST_ID = auto()
    CONFIRM_TASK = auto()
    
    # Task Editing
    EDIT_TASK_SELECT = auto()
    EDIT_TASK_MENU = auto()
    
    # Settings Management
    SETTINGS_MENU = auto()
    SET_GROQ_KEY = auto()
    SET_TW_USER = auto()
    SET_TW_PASS = auto()
    SET_ADMIN_ID = auto()
