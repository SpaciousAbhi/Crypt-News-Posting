# providers/publishers/telegram.py

from telegram import Bot
from telegram.constants import ParseMode
from services.logger import logger
from services.utils import retry_async
from typing import List, Optional

class TelegramPublisher:
    def __init__(self, bot: Bot):
        self.bot = bot

    @retry_async(retries=3, delay=2.0)
    async def publish(self, chat_id: str, text: str, media_urls: List[str] = []) -> bool:
        """Publishes content with auto-splitting for long texts. Returns True on success."""
        try:
            # 1. Handle Text Splitting (> 4096 chars)
            max_len = 4000
            chunks = [text[i:i+max_len] for i in range(0, len(text), max_len)]
            
            if not media_urls:
                for chunk in chunks:
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=chunk,
                        parse_mode=ParseMode.MARKDOWN
                    )
            elif len(media_urls) == 1:
                # Single media item
                url = media_urls[0]
                caption = chunks[0] if chunks else ""
                
                if ".mp4" in url.lower():
                    await self.bot.send_video(chat_id=chat_id, video=url, caption=caption, parse_mode=ParseMode.MARKDOWN)
                else:
                    await self.bot.send_photo(chat_id=chat_id, photo=url, caption=caption, parse_mode=ParseMode.MARKDOWN)
                
                # Send remaining chunks if any
                for extra_chunk in chunks[1:]:
                    await self.bot.send_message(chat_id=chat_id, text=extra_chunk, parse_mode=ParseMode.MARKDOWN)
            else:
                # Multiple media
                from telegram import InputMediaPhoto, InputMediaVideo
                media_group = []
                for i, url in enumerate(media_urls[:10]):
                    caption = chunks[0] if i == 0 else None
                    if ".mp4" in url.lower():
                        media_group.append(InputMediaVideo(url, caption=caption, parse_mode=ParseMode.MARKDOWN))
                    else:
                        media_group.append(InputMediaPhoto(url, caption=caption, parse_mode=ParseMode.MARKDOWN))
                
                await self.bot.send_media_group(chat_id=chat_id, media=media_group)
                
                # Send remaining chunks
                for extra_chunk in chunks[1:]:
                    await self.bot.send_message(chat_id=chat_id, text=extra_chunk, parse_mode=ParseMode.MARKDOWN)
            
            logger.info(f"[Telegram] Successfully published to {chat_id}")
            return True
        except Exception as e:
            logger.error(f"[Telegram] Publish failed to {chat_id}: {e}")
            return False
