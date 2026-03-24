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
        """Transforms content based on AI options (redesign, summarize, etc.)"""
        if not self.client or not any(options.values()):
            return text

        prompts = []
        if options.get("redesign"):
            prompts.append("Redesign this post to be clean, professional, and visually engaging for a global audience.")
        if options.get("summarize"):
            prompts.append("Summarize the key information while maintaining the original tone.")
        if options.get("reword"):
            prompts.append("Reword the content to be more engaging and natural.")

        full_prompt = " ".join(prompts)
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": f"You are an expert content strategist. {full_prompt} Return ONLY the transformed content. No extra commentary."
                    },
                    {
                        "role": "user",
                        "content": text,
                    }
                ],
                model="llama-3.1-70b-versatile",
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"[AI] Processing failed: {e}")
            return text

# Global Instance
ai_service = AIService()
