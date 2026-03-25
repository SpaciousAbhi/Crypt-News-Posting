# providers/publishers/twitter.py

import os
from twikit import Client
from services.logger import logger
from services.utils import retry_async
from typing import List, Optional, Any

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

    async def _download_media(self, url: str, client: Any) -> Optional[str]:
        """Downloads media to a temporary file using provided client."""
        import tempfile
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                ext = url.split(".")[-1].split("?")[0] or "jpg"
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
                temp_file.write(resp.content)
                temp_file.close()
                return temp_file.name
        except Exception as e:
            logger.error(f"[Twitter] Download failed for {url}: {e}")
        return None

    @retry_async(retries=3, delay=5.0)
    async def publish(self, text: str, media_urls: List[str] = []):
        """Publishes content to Twitter with media support."""
        media_ids = []
        temp_files = []
        try:
            await self._ensure_login()
            
            # Twitter allows up to 4 images
            import httpx
            from typing import Any
            async with httpx.AsyncClient(timeout=15) as client:
                for url in media_urls[:4]:
                    local_path = await self._download_media(url, client)
                    if local_path:
                        temp_files.append(local_path)
                        try:
                            mid = await self.client.upload_media(local_path)
                            media_ids.append(mid)
                        except Exception as e:
                            logger.error(f"[Twitter] Upload failed for {url}: {e}")

            await self.client.create_tweet(text=text, media_ids=media_ids if media_ids else None)
            logger.info(f"[Twitter] Published tweet with {len(media_ids)} media items.")
            return True
        except Exception as e:
            logger.error(f"[Twitter] Publish failed: {e}")
            return False
        finally:
            # Always cleanup temporary files
            for f in temp_files:
                try:
                    if os.path.exists(f): os.remove(f)
                except:
                    pass
