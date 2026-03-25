# providers/sources/twitter.py

import os
from twikit import Client
from typing import List, Optional, Any
from dataclasses import dataclass
from services.logger import logger
from services.utils import retry_async
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
            err_msg = str(e)
            if "KEY_BYTE" in err_msg or "ClientTransaction" in err_msg:
                logger.error(f"[TwikitSource] Critical Library Failure: {err_msg}. Twitter API internal structure has changed.")
            else:
                logger.error(f"[TwikitSource] Login failed: {err_msg}")
            raise # Let engine handle fallback

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

    @retry_async(retries=3, delay=5.0, backoff=2.0)
    async def fetch_latest(self, username: str) -> List[SourceItem]:
        """Fetches latest tweets using twikit (Async with Retries)."""
        username = username.strip('@')
        try:
            await self._ensure_login()
            user = await self.client.get_user_by_screen_name(username)
            tweets = await user.get_tweets('Tweets')
            
            items = []
            for t in tweets:
                # Handle both dict and object access safely
                t_id = getattr(t, 'id', None)
                t_text = getattr(t, 'full_text', getattr(t, 'text', ""))
                t_created = getattr(t, 'created_at_datetime', None)
                t_media = getattr(t, 'media', [])

                media_urls = [m['media_url_https'] for m in t_media] if t_media else []
                
                items.append(SourceItem(
                    id=str(t_id),
                    text=t_text,
                    media_urls=media_urls,
                    author=username,
                    url=f"https://x.com/{username}/status/{t_id}",
                    timestamp=t_created.timestamp() if t_created else 0
                ))
            return items
        except Exception as e:
            logger.error(f"[TwikitSource] Fetch failed for {username}: {e}")
            raise # Triggers retry
