# ai_engine.py

import os
import json
from groq import Groq, APIConnectionError

from database import AIRule
from observability import send_admin_notification

# --- Groq Client Initialization ---
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# --- Prompt Management ---
try:
    with open("prompts.json", "r") as f:
        _prompts = json.load(f)
except FileNotFoundError:
    print("CRITICAL: prompts.json not found. AI features will not work.")
    _prompts = {}


def get_prompt(rule_type: str, version: str, config: dict) -> str | None:
    """Retrieves a prompt template from the loaded JSON."""
    try:
        prompt_template = _prompts[rule_type][version]
        if rule_type == "summarize":
            return prompt_template[config["format"]]
        return prompt_template
    except KeyError:
        return None


# --- Local Transformations ---


def _substitute_variables(text: str, source_chat_name: str) -> str:
    """Replaces dynamic variables in header/footer text."""
    return text.format(source_chat_name=source_chat_name)


# --- Main Transformation Logic ---


async def transform_message(
    original_text: str, rules: list[AIRule], source_chat_name: str
) -> str | None:
    """
    Applies a list of AI rules to a message text sequentially.
    Returns the transformed text, or None if a critical AI error occurred.
    """
    modified_text = original_text

    for rule in sorted(rules, key=lambda r: r.rule_id):
        if rule.rule_type == "add_header":
            header = _substitute_variables(rule.config["text"], source_chat_name)
            modified_text = f"{header}\n\n{modified_text}"

        elif rule.rule_type == "add_footer":
            footer = _substitute_variables(rule.config["text"], source_chat_name)
            modified_text = f"{modified_text}\n\n{footer}"

        elif rule.rule_type == "replace_watermark":
            modified_text = modified_text.replace(
                rule.config["replace_from"], rule.config["replace_to"]
            )

        elif rule.rule_type in ["reword", "summarize", "translate"]:
            prompt_template = get_prompt(rule.rule_type, rule.version, rule.config)
            if not prompt_template:
                print(
                    f"ERROR: Prompt not found for rule {rule.rule_type} v{rule.version}. Skipping rule."
                )
                continue

            filled_prompt = prompt_template.format(
                message_text=modified_text, **rule.config
            )

            try:
                print(f"Calling Groq API for rule: {rule.rule_type}")
                chat_completion = groq_client.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": filled_prompt,
                        }
                    ],
                    model=os.getenv("AI_MODEL", "llama3-8b-8192"),
                )
                ai_response = chat_completion.choices[0].message.content
                if ai_response:
                    modified_text = ai_response
                else:
                    print(
                        f"WARNING: AI returned an empty response for rule {rule.rule_type}."
                    )

            except APIConnectionError as e:
                error_message = f"🔴 **AI Engine Failure**\n\n**Rule:** `{rule.rule_type}`\n**Error:** Could not connect to Groq API.\n**Reason:** `{e.__cause__}`"
                print(error_message)
                await send_admin_notification(error_message)
                return None  # Signal failure
            except Exception as e:
                error_message = f"🔴 **AI Engine Failure**\n\n**Rule:** `{rule.rule_type}`\n**Error:** An unexpected error occurred.\n**Reason:** `{e}`"
                print(error_message)
                await send_admin_notification(error_message)
                return None  # Signal failure

    return modified_text
