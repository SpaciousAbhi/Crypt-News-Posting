# providers/publishers/twitter.py

import os
from twikit import Client
from services.logger import logger
from typing import List

class TwitterPublisher:
    def __init__(self, username: str, password: str, cookies_path: str = "cookies_tw.json"):
        self.client = Client('en-US')
        self.username = username
        self.password = password
        self.cookies_path = cookies_path
        self._is_logged_in = False

    async def _ensure_login(self):
        if self._is_logged_in:
            return
            
        try:
            if os.path.exists(self.cookies_path):
                self.client.load_cookies(self.cookies_path)
                logger.info("[Twitter] Logged in using cached cookies.")
            else:
                await self.client.login(auth_info_1=self.username, password=self.password)
                self.client.save_cookies(self.cookies_path)
                logger.info("[Twitter] Logged in successfully.")
            self._is_logged_in = True
        except Exception as e:
            logger.error(f"[Twitter] Login failed: {e}")
            raise

    async def publish(self, text: str, media_urls: List[str] = []):
        """Publishes content to Twitter."""
        try:
            await self._ensure_login()
            
            media_ids = []
            for url in media_urls[:4]: # Twitter limit
                # We'd need to download the media locally first to upload it
                # For now, let's keep it simple or implement a quick downloader
                # await self.client.upload_media(local_file)
                pass # TODO: Download and upload media logic
                
            await self.client.create_tweet(text=text, media_ids=media_ids if media_ids else None)
            logger.info("[Twitter] Successfully published tweet.")
            return True
        except Exception as e:
            logger.error(f"[Twitter] Publish failed: {e}")
            return False
