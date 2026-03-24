# services/ai_service.py

import os
from groq import Groq
from services.logger import logger
from services.config_service import config

class AIService:
    def __init__(self):
        self.client = None
        self._init_client()

    def _init_client(self):
        api_key = config.groq_key
        if api_key:
            try:
                self.client = Groq(api_key=api_key)
                logger.info("[AI] Groq client initialized successfully.")
            except Exception as e:
                logger.error(f"[AI] Failed to initialize Groq client: {e}")

    def process_content(self, text: str, options: dict) -> str:
        """Transforms content into a premium format using LLaMA3."""
        if not self.client:
            return text

        # Professional Redesign Strategy
        system_instructions = (
            "You are a Senior Content Strategist for high-end news and tech media.\n"
            "Your goal is to transform raw input into a polished, premium, and highly engaging social media post.\n\n"
            "🛠️ **Requirements:**\n"
            "1. **Structure:** Use clean spacing and bullet points for readability.\n"
            "2. **Style:** Professional yet exciting. Use a tone appropriate for global news.\n"
            "3. **Visuals:** Use relevant emojis sparingly (max 1-2 per section) to guide the eye.\n"
            "4. **SEO:** Ensure key entities (names, tech terms) are prominent.\n\n"
            "⚠️ **Constraint:** Return ONLY the transformed text. Do not include 'Here is the redesigned post' or any preamble."
        )

        user_prompts = []
        if options.get("redesign", True): # Default to redesign if not specified
            user_prompts.append("Fully redesign this post for maximum engagement.")
        if options.get("summarize"):
            user_prompts.append("Extract the most critical points into a concise summary.")
        if options.get("reword"):
            user_prompts.append("Reword the text to flow more naturally and professionally.")

        refinement_prompt = " ".join(user_prompts)
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_instructions},
                    {"role": "user", "content": f"Task: {refinement_prompt}\n\nContent:\n{text}"}
                ],
                model="llama-3.1-70b-versatile",
                temperature=0.7,
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"[AI] Processing failed: {e}")
            return text

# Global Instance
ai_service = AIService()
