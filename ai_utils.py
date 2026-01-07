# ai_utils.py

import requests


def _call_ai_model(prompt: str, groq_api_key: str) -> str:
    """
    Calls the Groq LLaMA3 model with a specific prompt.
    """
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 200,
        }
        res = requests.post(url, headers=headers, json=payload)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.RequestException as e:
        print(f"[Error] AI model call failed: {e}")
        return None


def modify_message(text: str, options: dict, groq_api_key: str) -> str:
    """
    Modifies a message using AI based on the provided options.
    """
    modified_text = text

    # Watermark replacement
    if "watermark" in options and options["watermark"]:
        from_text = options["watermark"].get("replace_from")
        to_text = options["watermark"].get("replace_to")
        if from_text and to_text:
            modified_text = modified_text.replace(from_text, to_text)

    # AI-based rewording or summarization
    if options.get("reword"):
        prompt = (
            "Rewrite this text for clarity and engagement, while preserving "
            "the core meaning. Add relevant emojis to enhance tone:\n\n"
            f'"{modified_text}"'
        )
        ai_result = _call_ai_model(prompt, groq_api_key)
        if ai_result:
            modified_text = ai_result
    elif options.get("summarize"):
        length = options.get("summary_length", 100)
        prompt = (
            f"Summarize the following text in under {length} words, "
            "focusing on the key information. Use emojis to highlight "
            f'important points:\n\n"{modified_text}"'
        )
        ai_result = _call_ai_model(prompt, groq_api_key)
        if ai_result:
            modified_text = ai_result

    # Add header and footer
    if options.get("header"):
        modified_text = f"{options['header']}\n\n{modified_text}"
    if options.get("footer"):
        modified_text = f"{modified_text}\n\n{options['footer']}"

    return modified_text
