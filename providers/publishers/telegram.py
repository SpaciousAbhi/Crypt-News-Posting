# providers/publishers/telegram.py

from telegram import Bot
from telegram.constants import ParseMode
from services.logger import logger
from typing import List, Optional

class TelegramPublisher:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def publish(self, chat_id: str, text: str, media_urls: List[str] = []):
        """Publishes content to a Telegram chat."""
        try:
            if not media_urls:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=ParseMode.MARKDOWN
                )
            elif len(media_urls) == 1:
                # Single media item
                url = media_urls[0]
                if ".mp4" in url.lower():
                    await self.bot.send_video(chat_id=chat_id, video=url, caption=text, parse_mode=ParseMode.MARKDOWN)
                else:
                    await self.bot.send_photo(chat_id=chat_id, photo=url, caption=text, parse_mode=ParseMode.MARKDOWN)
            else:
                # Multiple media (InputMediaPhoto/Video)
                from telegram import InputMediaPhoto, InputMediaVideo
                media_group = []
                for i, url in enumerate(media_urls[:10]): # Max 10 per group
                    caption = text if i == 0 else None
                    if ".mp4" in url.lower():
                        media_group.append(InputMediaVideo(url, caption=caption, parse_mode=ParseMode.MARKDOWN))
                    else:
                        media_group.append(InputMediaPhoto(url, caption=caption, parse_mode=ParseMode.MARKDOWN))
                
                await self.bot.send_media_group(chat_id=chat_id, media=media_group)
            
            logger.info(f"[Telegram] Successfully published to {chat_id}")
            return True
        except Exception as e:
            logger.error(f"[Telegram] Publish failed to {chat_id}: {e}")
            return False
