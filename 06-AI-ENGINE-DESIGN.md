# Part 6: AI Transformation Engine Design

This document details the architecture and functionality of the AI Transformation Engine, the core component responsible for all intelligent message modifications.

## 1. Engine Overview

The AI Transformation Engine is a modular component that receives raw message content and a set of rules, then applies those rules sequentially to produce the final, modified output.

-   **Sequential Processing:** AI rules defined for a task are applied in the order they are listed. The output of one rule becomes the input for the next.
-   **AI Provider:** The engine is designed to interface with a powerful Large Language Model (LLM) via an API. The primary choice is the **Groq API** for its high speed, but it can be adapted to other providers like OpenAI or Anthropic.
-   **Deterministic Behavior:** The engine uses a "prompt versioning" system. Each AI rule is tied to a specific version of a prompt template. This ensures that even if prompts are improved in the future, existing tasks will continue to behave predictably until they are explicitly upgraded.

## 2. AI Rule Definitions

Below are the specifications for each supported AI rule type.

### a) `reword`

-   **Purpose:** Rephrases the entire message to match a specific tone or style, without losing the original meaning.
-   **Config (`JSONB`):**
    ```json
    {
      "tone": "string",
      "audience": "string"
    }
    ```
    -   `tone`: (Required) The desired tone. Examples: `Formal`, `Casual`, `Professional`, `Enthusiastic`, `Objective`.
    -   `audience`: (Required) The target audience. Examples: `General Public`, `Expert Traders`, `Beginners`, `Developers`.
-   **Prompt Version 1.0:**
    ```
    Rephrase the following text to have a {tone} tone, suitable for an audience of {audience}. Do not add any new information or commentary. Preserve the original meaning and any factual data, like numbers or links.

    Original text:
    """
    {message_text}
    """
    ```

### b) `summarize`

-   **Purpose:** Condenses a long message into a more concise format.
-   **Config (`JSONB`):**
    ```json
    {
      "format": "string",
      "length": "string"
    }
    ```
    -   `format`: (Required) The output format. Can be `paragraph`, `bullet_points`.
    -   `length`: (Required) The desired length of the summary. Can be `short` (1-2 sentences), `medium` (a short paragraph or 3-5 bullet points), `long` (a detailed summary).
-   **Prompt Version 1.0 (paragraph):**
    ```
    Summarize the key information in the following text into a {length} paragraph. Focus on the main conclusions and actionable insights.

    Original text:
    """
    {message_text}
    """
    ```
-   **Prompt Version 1.0 (bullet_points):**
    ```
    Summarize the key information in the following text into a list of {length} bullet points. Each bullet point should be concise and impactful.

    Original text:
    """
    {message_text}
    """
    ```

### c) `add_header` / `add_footer`

-   **Purpose:** Appends a static or dynamic piece of text to the beginning or end of the message. This rule is processed **locally** and does not require an AI API call.
-   **Config (`JSONB`):**
    ```json
    {
      "text": "string"
    }
    ```
    -   `text`: (Required) The text to add. It supports variables that the bot will replace.
-   **Supported Variables:**
    -   `{source_chat_name}`: The display name of the source channel/group.
    -   `{source_chat_id}`: The ID of the source chat.
    -   `{message_timestamp}`: The date and time the original message was posted.
    -   `{task_name}`: The name of the forwarding task.

### d) `replace_watermark`

-   **Purpose:** A simple, local find-and-replace operation. Useful for removing or replacing recurring text like advertisements or channel links. This rule is processed **locally**.
-   **Config (`JSONB`):**
    ```json
    {
      "replace_from": "string",
      "replace_to": "string"
    }
    ```
    -   `replace_from`: (Required) The exact text to find.
    -   `replace_to`: (Required) The text to replace it with. Can be an empty string (`""`) to simply remove the text.

### e) `translate`

-   **Purpose:** Translates the message text into a different language.
-   **Config (`JSONB`):**
    ```json
    {
      "target_language": "string"
    }
    ```
    -   `target_language`: (Required) The language to translate the text into (e.g., `Spanish`, `Japanese`, `German`).
-   **Prompt Version 1.0:**
    ```
    Translate the following text into {target_language}. Preserve the original formatting, such as line breaks and links, as much as possible.

    Original text:
    """
    {message_text}
    """
    ```

## 3. Data Flow within the Engine

The `AIEngine` will have a primary method, `transform(text, rules)`, which operates as follows:

```python
def transform(text: str, rules: list[AIRule]) -> str:
    current_text = text
    for rule in rules:
        if rule.type == "add_header":
            # Locally process header
            header = substitute_variables(rule.config["text"])
            current_text = f"{header}\n\n{current_text}"

        elif rule.type == "replace_watermark":
            # Locally process watermark
            current_text = current_text.replace(
                rule.config["replace_from"],
                rule.config["replace_to"]
            )

        elif rule.type in ["reword", "summarize", "translate"]:
            # Remotely process with AI
            prompt = get_prompt(rule.type, rule.version, rule.config)
            filled_prompt = prompt.format(
                message_text=current_text, **rule.config
            )
            current_text = ai_api_call(filled_prompt)

        elif rule.type == "add_footer":
            # Locally process footer
            footer = substitute_variables(rule.config["text"])
            current_text = f"{current_text}\n\n{footer}"

    return current_text
```

## 4. Prompt Versioning and Management

-   **Storage:** All prompt templates will be stored in a dedicated, non-executable file (e.g., `prompts.json`) within the application's codebase.
-   **Structure:**
    ```json
    {
      "summarize": {
        "1.0": {
          "paragraph": "Summarize the key information...",
          "bullet_points": "Summarize the key information..."
        },
        "1.1": {
          "paragraph": "An improved summary prompt...",
          "bullet_points": "An improved bullet point prompt..."
        }
      },
      "translate": {
        "1.0": "Translate the following text..."
      }
    }
    ```
-   **Upgrading:** When a user edits a task, the UI can show a notification if a newer prompt version is available for one of their rules, giving them the option to upgrade. This ensures a smooth and controlled evolution of the AI's capabilities.
