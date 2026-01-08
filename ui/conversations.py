# ui/conversations.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    CommandHandler,
)

from database import SessionLocal, User, Task, Source, Target, AIRule
from ui.buttons import task_menu_keyboard, main_menu_keyboard

# Conversation states
(
    NAME,
    MENU,
    SOURCES_MENU,
    AWAITING_SOURCE,
    TARGETS_MENU,
    AWAITING_TARGET,
    AI_RULES_MENU,
    AWAITING_AI_RULE_TYPE,
    AWAITING_AI_RULE_CONFIG,
    RENAME,
) = range(10)


# --- Helper Functions ---


async def _get_task_summary(task_id: int, db: SessionLocal) -> str:
    """Gets a summary of the task's current configuration."""
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        return "Error: Task not found."

    sources = db.query(Source).filter(Source.task_id == task_id).all()
    targets = db.query(Target).filter(Target.task_id == task_id).all()
    ai_rules = db.query(AIRule).filter(AIRule.task_id == task_id).all()

    source_list = ", ".join([str(s.chat_id) for s in sources]) or "(none)"
    target_list = ", ".join([str(t.chat_id) for t in targets]) or "(none)"
    ai_rule_list = ", ".join([r.rule_type for r in ai_rules]) or "(none)"

    return f"""
---
**Task: {task.name}**
- **Sources:** {source_list}
- **Targets:** {target_list}
- **AI Rules:** {ai_rule_list}
---
    """


async def task_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE, message_prefix: str = ""
) -> int:
    """Displays the main task configuration menu."""
    task_id = context.user_data["task_id"]
    db = SessionLocal()
    summary = await _get_task_summary(task_id, db)
    db.close()

    message = f"{message_prefix}\n{summary}"

    await update.callback_query.edit_message_text(
        message, reply_markup=task_menu_keyboard(), parse_mode="Markdown"
    )
    return MENU


# --- Main Conversation Flow ---


async def create_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: Starts the task creation conversation."""
    await update.callback_query.edit_message_text(
        "Let's set up a new forwarding task. What would you like to name it? (e.g., 'Crypto News to Main Channel')"
    )
    return NAME


async def received_task_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's reply with the task name and creates the task."""
    task_name = update.message.text
    telegram_id = update.message.from_user.id

    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == telegram_id).first()

    new_task = Task(name=task_name, user_id=user.user_id)
    db.add(new_task)
    db.commit()

    context.user_data["task_id"] = new_task.task_id
    summary = await _get_task_summary(new_task.task_id, db)
    db.close()

    message = f'Great! Your task is named "{task_name}".\n\nNow, let\'s configure it.{summary}'
    await update.message.reply_text(
        message, reply_markup=task_menu_keyboard(), parse_mode="Markdown"
    )
    return MENU


# --- Source Management Flow ---


async def manage_sources(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Displays the source management menu."""
    task_id = context.user_data["task_id"]
    db = SessionLocal()
    sources = db.query(Source).filter(Source.task_id == task_id).all()
    db.close()

    keyboard = []
    message = "**Manage Sources**\n\n"
    if not sources:
        message += "There are no source chats yet. A source is where I'll listen for new messages."
    else:
        for source in sources:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"🗑️ {source.chat_id}",
                        callback_data=f"remove_source_{source.source_id}",
                    )
                ]
            )

    keyboard.append([InlineKeyboardButton("➕ Add Source", callback_data="add_source")])
    keyboard.append(
        [InlineKeyboardButton("⬅️ Back to Task Menu", callback_data="back_to_task_menu")]
    )

    await update.callback_query.edit_message_text(
        message, reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SOURCES_MENU


async def prompt_for_source(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks the user to send a chat ID for a new source."""
    await update.callback_query.edit_message_text(
        "Please send the chat ID of the source channel or group.\n\n"
        "You can also send a public channel's username (e.g., `@channel_name`).\n\n"
        "(For help finding a chat ID, see `/help`.)"
    )
    return AWAITING_SOURCE


async def received_source(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's reply with the new source chat ID."""
    chat_id_str = update.message.text
    task_id = context.user_data["task_id"]

    try:
        # This is a simplification. A real implementation would need to handle usernames vs IDs.
        chat_id = int(chat_id_str)
    except ValueError:
        await update.message.reply_text("Invalid Chat ID. Please send a numeric ID.")
        return AWAITING_SOURCE

    db = SessionLocal()
    try:
        chat = await context.bot.get_chat(chat_id)
        chat_type = chat.type
    except Exception as e:
        print(f"Could not get chat type for {chat_id}: {e}")
        chat_type = "unknown"

    new_source = Source(task_id=task_id, chat_id=chat_id, chat_type=chat_type)
    db.add(new_source)
    db.commit()
    db.close()

    # We need to simulate a callback query to go back to the source menu
    update.callback_query = update.message.reply_text(
        "Source added.", reply_markup=InlineKeyboardMarkup([[]])
    )
    await manage_sources(update, context)
    return SOURCES_MENU


async def remove_source(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Removes a source from the task."""
    source_id = int(update.callback_query.data.split("_")[2])
    db = SessionLocal()
    source = db.query(Source).filter(Source.source_id == source_id).first()
    if source:
        db.delete(source)
        db.commit()
    db.close()

    await update.callback_query.answer("Source removed.")
    return await manage_sources(update, context)


# --- Target Management Flow ---


async def manage_targets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Displays the target management menu."""
    task_id = context.user_data["task_id"]
    db = SessionLocal()
    targets = db.query(Target).filter(Target.task_id == task_id).all()
    db.close()

    keyboard = []
    message = "**Manage Targets**\n\n"
    if not targets:
        message += "There are no target chats yet. A target is where I'll send the processed messages."
    else:
        for target in targets:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"🗑️ {target.chat_id}",
                        callback_data=f"remove_target_{target.target_id}",
                    )
                ]
            )

    keyboard.append([InlineKeyboardButton("➕ Add Target", callback_data="add_target")])
    keyboard.append(
        [InlineKeyboardButton("⬅️ Back to Task Menu", callback_data="back_to_task_menu")]
    )

    await update.callback_query.edit_message_text(
        message, reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return TARGETS_MENU


async def prompt_for_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks the user to send a chat ID for a new target."""
    await update.callback_query.edit_message_text(
        "Please send the chat ID of the target channel or group."
    )
    return AWAITING_TARGET


async def received_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's reply with the new target chat ID."""
    chat_id_str = update.message.text
    task_id = context.user_data["task_id"]

    try:
        chat_id = int(chat_id_str)
    except ValueError:
        await update.message.reply_text("Invalid Chat ID. Please send a numeric ID.")
        return AWAITING_TARGET

    db = SessionLocal()
    try:
        chat = await context.bot.get_chat(chat_id)
        chat_type = chat.type
    except Exception as e:
        print(f"Could not get chat type for {chat_id}: {e}")
        chat_type = "unknown"

    new_target = Target(task_id=task_id, chat_id=chat_id, chat_type=chat_type)
    db.add(new_target)
    db.commit()
    db.close()

    update.callback_query = update.message.reply_text(
        "Target added.", reply_markup=InlineKeyboardMarkup([[]])
    )
    await manage_targets(update, context)
    return TARGETS_MENU


async def remove_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Removes a target from the task."""
    target_id = int(update.callback_query.data.split("_")[2])
    db = SessionLocal()
    target = db.query(Target).filter(Target.target_id == target_id).first()
    if target:
        db.delete(target)
        db.commit()
    db.close()

    await update.callback_query.answer("Target removed.")
    return await manage_targets(update, context)


# --- AI Rule Management Flow ---


async def manage_ai_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Displays the AI rule management menu."""
    task_id = context.user_data["task_id"]
    db = SessionLocal()
    rules = (
        db.query(AIRule)
        .filter(AIRule.task_id == task_id)
        .order_by(AIRule.rule_id)
        .all()
    )
    db.close()

    keyboard = []
    message = (
        "**Manage AI Rules**\n\nRules are applied in the order they are listed.\n\n"
    )
    if not rules:
        message += "There are no AI rules yet."
    else:
        for i, rule in enumerate(rules):
            message += f"{i+1}. `{rule.rule_type}`: `{rule.config}`\n"
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"🗑️ Remove Rule {i+1}",
                        callback_data=f"remove_rule_{rule.rule_id}",
                    )
                ]
            )

    keyboard.append([InlineKeyboardButton("➕ Add AI Rule", callback_data="add_rule")])
    keyboard.append(
        [InlineKeyboardButton("⬅️ Back to Task Menu", callback_data="back_to_task_menu")]
    )

    await update.callback_query.edit_message_text(
        message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
    return AI_RULES_MENU


async def prompt_for_ai_rule_type(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Asks the user to select an AI rule type."""
    keyboard = [
        [InlineKeyboardButton("Reword Content", callback_data="rule_reword")],
        [InlineKeyboardButton("Summarize", callback_data="rule_summarize")],
        [InlineKeyboardButton("Translate", callback_data="rule_translate")],
        [
            InlineKeyboardButton(
                "Replace Watermark", callback_data="rule_replace_watermark"
            )
        ],
        [
            InlineKeyboardButton(
                "Add Header/Footer", callback_data="rule_add_header_footer"
            )
        ],
        [InlineKeyboardButton("Cancel", callback_data="cancel_add_rule")],
    ]
    await update.callback_query.edit_message_text(
        "Please select the type of AI rule you want to add:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return AWAITING_AI_RULE_TYPE


async def received_ai_rule_type(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handles the selection of an AI rule type and prompts for its config."""
    rule_type = update.callback_query.data.split("_")[1]
    context.user_data["new_rule_type"] = rule_type

    # This is a simplified config flow. A real implementation would have more steps.
    if rule_type == "reword":
        prompt = "Please send the desired tone and audience, separated by a comma (e.g., `Professional, Experts`)."
    elif rule_type == "summarize":
        prompt = "Please send the desired format and length, separated by a comma (e.g., `bullet_points, medium`)."
    else:  # Fallback for simple rules
        prompt = "Please send the configuration for this rule."

    await update.callback_query.edit_message_text(prompt)
    return AWAITING_AI_RULE_CONFIG


async def received_ai_rule_config(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handles the user's reply with the rule configuration and saves the rule."""
    config_str = update.message.text
    rule_type = context.user_data.pop("new_rule_type", None)
    task_id = context.user_data["task_id"]

    if not rule_type:
        await update.message.reply_text("An error occurred. Please try again.")
        return await task_menu(update, context)

    # Simplified config parsing
    config = {}
    if rule_type == "reword":
        parts = [p.strip() for p in config_str.split(",")]
        if len(parts) == 2:
            config = {"tone": parts[0], "audience": parts[1]}
    elif rule_type == "summarize":
        parts = [p.strip() for p in config_str.split(",")]
        if len(parts) == 2:
            config = {"format": parts[0], "length": parts[1]}

    if not config:
        await update.message.reply_text(
            "Invalid configuration format. Please try again."
        )
        # A real implementation would loop back to the config prompt
        return await manage_ai_rules(update, context)

    db = SessionLocal()
    new_rule = AIRule(task_id=task_id, rule_type=rule_type, config=config)
    db.add(new_rule)
    db.commit()
    db.close()

    update.callback_query = update.message.reply_text(
        "AI Rule added.", reply_markup=InlineKeyboardMarkup([[]])
    )
    await manage_ai_rules(update, context)
    return AI_RULES_MENU


async def remove_ai_rule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Removes an AI rule from the task."""
    rule_id = int(update.callback_query.data.split("_")[2])
    db = SessionLocal()
    rule = db.query(AIRule).filter(AIRule.rule_id == rule_id).first()
    if rule:
        db.delete(rule)
        db.commit()
    db.close()

    await update.callback_query.answer("AI Rule removed.")
    return await manage_ai_rules(update, context)


# --- Fallbacks and Endpoints ---


async def save_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves the task and ends the conversation."""
    task_id = context.user_data.get("task_id")
    enable = update.callback_query.data == "save_enable"

    db = SessionLocal()
    task = db.query(Task).filter(Task.task_id == task_id).first()

    if task:
        # Here we would run the validation checks
        task.enabled = enable
        db.commit()
        status = "enabled" if enable else "disabled"
        await update.callback_query.edit_message_text(
            f"✅ Task '{task.name}' has been saved and is now {status}.",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await update.callback_query.edit_message_text(
            "Error: Could not find the task to save.", reply_markup=main_menu_keyboard()
        )

    db.close()
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_task_creation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Cancels the conversation and deletes the created task."""
    task_id = context.user_data.get("task_id")
    if task_id:
        db = SessionLocal()
        task = db.query(Task).filter(Task.task_id == task_id).first()
        if task:
            db.delete(task)
            db.commit()
        db.close()

    await update.callback_query.edit_message_text(
        "Task creation cancelled.", reply_markup=main_menu_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END


# --- Conversation Handler Definition ---


def get_create_task_conv_handler() -> ConversationHandler:
    """Returns the full ConversationHandler for creating a new task."""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(create_task_start, pattern="^create_task$")],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_task_name)],
            MENU: [
                CallbackQueryHandler(manage_sources, pattern="^mng_sources$"),
                CallbackQueryHandler(manage_targets, pattern="^mng_targets$"),
                CallbackQueryHandler(manage_ai_rules, pattern="^mng_ai_rules$"),
                CallbackQueryHandler(save_task, pattern="^save_enable$"),
                CallbackQueryHandler(save_task, pattern="^save_disable$"),
            ],
            SOURCES_MENU: [
                CallbackQueryHandler(prompt_for_source, pattern="^add_source$"),
                CallbackQueryHandler(remove_source, pattern="^remove_source_"),
                CallbackQueryHandler(task_menu, pattern="^back_to_task_menu$"),
            ],
            AWAITING_SOURCE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_source)
            ],
            TARGETS_MENU: [
                CallbackQueryHandler(prompt_for_target, pattern="^add_target$"),
                CallbackQueryHandler(remove_target, pattern="^remove_target_"),
                CallbackQueryHandler(task_menu, pattern="^back_to_task_menu$"),
            ],
            AWAITING_TARGET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_target)
            ],
            AI_RULES_MENU: [
                CallbackQueryHandler(prompt_for_ai_rule_type, pattern="^add_rule$"),
                CallbackQueryHandler(remove_ai_rule, pattern="^remove_rule_"),
                CallbackQueryHandler(task_menu, pattern="^back_to_task_menu$"),
            ],
            AWAITING_AI_RULE_TYPE: [
                CallbackQueryHandler(received_ai_rule_type, pattern="^rule_")
            ],
            AWAITING_AI_RULE_CONFIG: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_ai_rule_config)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_task_creation, pattern="^cancel_creation$"),
            CommandHandler("cancel", cancel_task_creation),  # Allow /cancel command
        ],
    )
