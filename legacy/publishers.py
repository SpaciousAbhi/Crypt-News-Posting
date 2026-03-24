# publishers.py

from telegram import Bot
from twikit import Client
import asyncio
import requests
import io

class TelegramPublisher:
    """Publishes content to Telegram channels."""
    
    def __init__(self, bot: Bot):
        self.bot = bot

    async def publish(self, target_id: int, text: str, media_urls: list):
        """Sends text and media to a Telegram channel."""
        try:
            if media_urls:
                # If there's only one image, send it with caption
                if len(media_urls) == 1:
                    await self.bot.send_photo(chat_id=target_id, photo=media_urls[0], caption=text)
                else:
                    # For multiple images, we'd use send_media_group, but for simplicity:
                    await self.bot.send_message(chat_id=target_id, text=text)
                    for url in media_urls:
                        await self.bot.send_photo(chat_id=target_id, photo=url)
            else:
                await self.bot.send_message(chat_id=target_id, text=text)
            return True
        except Exception as e:
            print(f"[Error] Telegram publish failed for {target_id}: {e}")
            return False

class TwitterPublisher:
    """Publishes content to Twitter (X) using twikit."""
    
    def __init__(self, username: str, password: str):
        self.client = Client('en-US')
        self.auth_username = username
        self.auth_password = password
        self.is_logged_in = False

    async def _login(self):
        if not self.is_logged_in:
            await self.client.login(auth_info_1=self.auth_username, password=self.auth_password)
            self.is_logged_in = True

    async def publish(self, text: str, media_urls: list):
        """Posts a tweet with optional media."""
        try:
            await self._login()
            media_ids = []
            for url in media_urls[:4]: # Twitter allows up to 4 images
                resp = requests.get(url)
                if resp.status_code == 200:
                    # Upload media to Twitter
                    media_id = await self.client.upload_media(io.BytesIO(resp.content))
                    media_ids.append(media_id)
            
            await self.client.create_tweet(text=text, media_ids=media_ids if media_ids else None)
            return True
        except Exception as e:
            print(f"[Error] Twitter publish failed: {e}")
            return False
