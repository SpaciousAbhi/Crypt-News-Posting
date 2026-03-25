# providers/sources/telegram.py

from telegram import Bot
from typing import List, Optional
from services.logger import logger
from providers.sources.rss import SourceItem
import time

class TelegramSource:
    """Source provider for Telegram channels using the Bot API."""
    
    def __init__(self, bot: Bot):
        self.bot = bot

    async def fetch_latest(self, identifier: str) -> List[SourceItem]:
        """
        Fetches latest messages from the local source_items table.
        Items are captured in real-time by the main bot loop.
        """
        try:
            # Pull from Captured Items table
            raw_items = db.get_unread_source_items(str(identifier), "telegram")
            
            items = []
            for raw in raw_items:
                media_urls = json.loads(raw['media_json']) if raw['media_json'] else []
                items.append(SourceItem(
                    id=raw['item_id'],
                    text=raw['content'] or "",
                    media_urls=media_urls,
                    author=identifier,
                    url=f"https://t.me/c/{str(identifier).replace('-100', '')}/{raw['item_id']}",
                    timestamp=raw['created_at'].timestamp() if hasattr(raw['created_at'], 'timestamp') else time.time()
                ))
            return items
            
        except Exception as e:
            logger.error(f"[TelegramSource] Fetch failed for {identifier}: {e}")
            return []
