# providers/sources/twitter.py

import os
from twikit import Client
from typing import List, Optional
from dataclasses import dataclass
from services.logger import logger
from providers.sources.rss import SourceItem

class TwikitSource:
    """Fallback Twitter source using twikit (requires login)."""
    
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
                logger.info("[TwikitSource] Logged in using cached cookies.")
            else:
                await self.client.login(auth_info_1=self.username, password=self.password)
                self.client.save_cookies(self.cookies_path)
                logger.info("[TwikitSource] Logged in successfully.")
            self._is_logged_in = True
        except Exception as e:
            logger.error(f"[TwikitSource] Login failed: {e}")
            raise

    async def verify_credentials(self) -> bool:
        """Verifies if the credentials are valid by attempting login."""
        try:
            await self.client.login(auth_info_1=self.username, password=self.password)
            self.client.save_cookies(self.cookies_path)
            self._is_logged_in = True
            return True
        except Exception as e:
            logger.error(f"[TwikitSource] Verification failed: {e}")
            return False

    async def fetch_latest(self, username: str) -> List[SourceItem]:
        """Fetches latest tweets using twikit."""
        try:
            await self._ensure_login()
            user = await self.client.get_user_by_screen_name(username.strip('@'))
            tweets = await user.get_tweets('Tweets')
            
            items = []
            for t in tweets:
                media_urls = [m['media_url_https'] for m in t.media] if hasattr(t, 'media') and t.media else []
                items.append(SourceItem(
                    id=t.id,
                    text=t.full_text,
                    media_urls=media_urls,
                    author=username,
                    url=f"https://x.com/{username}/status/{t.id}",
                    timestamp=t.created_at_datetime.timestamp() if hasattr(t, 'created_at_datetime') else 0
                ))
            return items
        except Exception as e:
            logger.error(f"[TwikitSource] Fetch failed for {username}: {e}")
            return []
