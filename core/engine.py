# core/engine.py

import asyncio
from typing import List, Dict, Any
from telegram import Bot
from database.manager import db
from services.logger import logger
from services.ai_service import ai_service
from providers.sources.rss import RSSSource
from providers.sources.twitter import TwikitSource
from providers.sources.telegram import TelegramSource
from providers.publishers.telegram import TelegramPublisher
from providers.publishers.twitter import TwitterPublisher

class ProcessingEngine:
    def __init__(self, telegram_token: str):
        self.bot = Bot(telegram_token)
        self.rss = RSSSource()
        self.tg_src = TelegramSource(self.bot)
        self.tw_src = None # Lazy-init per task if needed
        self._loop_active = False

    async def start(self, interval: int = 60):
        """Starts the background monitoring loop."""
        self._loop_active = True
        logger.info(f"[Engine] Starting processing loop with interval: {interval}s")
        
        while self._loop_active:
            try:
                await self.process_all_tasks()
            except Exception as e:
                logger.error(f"[Engine] Loop error: {e}")
            
            await asyncio.sleep(interval)

    async def stop(self):
        self._loop_active = False

    async def process_all_tasks(self):
        """Fetches and processes all active tasks concurrently."""
        tasks = db.get_tasks()
        active_tasks = [t for t in tasks if t['is_active']]
        
        if not active_tasks:
            return

        # Process all tasks in parallel with error isolation
        logger.debug(f"[Engine] Processing {len(active_tasks)} active tasks...")
        await asyncio.gather(
            *[self._safe_process_task(t['id']) for t in active_tasks],
            return_exceptions=True
        )

    async def _safe_process_task(self, task_id: int):
        """Wraps process_task with high-level crash protection and data refresh."""
        try:
            task = db.get_task_details(task_id)
            if task:
                await self.process_task(task)
        except Exception as e:
            logger.error(f"[Engine] Task ID {task_id} crashed: {e}", exc_info=True)

    async def process_task(self, task: Dict[str, Any]):
        """Processes a single task: Fetch -> Transform -> Publish."""
        task_id = task['id']
        sources = task['sources']
        destinations = task['destinations']
        task_config = task.get('config', {})

        # 1. Fetch from all sources in parallel
        source_results = await asyncio.gather(
            *[self._fetch_from_source(s) for s in sources],
            return_exceptions=True
        )

        all_new_items = []
        for i, result in enumerate(source_results):
            if isinstance(result, Exception):
                logger.error(f"[Engine] Source fetch failed: {result}")
                continue
            
            source_id = sources[i]['id']
            for item in result:
                if not db.is_item_processed(task_id, source_id, item.id):
                    all_new_items.append((source_id, item))

        if not all_new_items:
            return

        # Sort by timestamp to preserve order
        all_new_items.sort(key=lambda x: x[1].timestamp)

        # 2. Process items (Sequentially to respect time order, but parallel destinations)
        for source_id, item in all_new_items:
            await self._process_item(task, source_id, item, destinations)

    async def _fetch_from_source(self, source: Dict[str, Any]) -> List[Any]:
        """Isolated source fetching logic with automatic fallback."""
        platform = source['platform']
        identifier = source['identifier']
        
        try:
            if platform == "twitter_rss":
                return self.rss.fetch_latest(identifier)
            elif platform == "twitter":
                tw_user = db.get_setting("TWITTER_USERNAME")
                tw_pass = db.get_setting("TWITTER_PASSWORD")
                if tw_user and tw_pass:
                    try:
                        tw_src = TwikitSource(tw_user, tw_pass)
                        return await tw_src.fetch_latest(identifier)
                    except Exception as e:
                        logger.warning(f"[Engine] Direct Twitter fetch failed for {identifier}: {e}. Falling back to RSS...")
                        return self.rss.fetch_latest(identifier)
                else:
                    logger.warning(f"[Engine] Twitter credentials missing. Using RSS as default for {identifier}.")
                    return self.rss.fetch_latest(identifier)
            elif platform == "telegram":
                return await self.tg_src.fetch_latest(identifier)
        except Exception as e:
            logger.error(f"[Engine] Source {platform}:{identifier} critical failure: {e}")
            
        return []

    async def _process_item(self, task: Dict[str, Any], source_id: int, item: Any, destinations: List[Dict[str, Any]]):
        """Processes a single item and publishes to all destinations."""
        task_id = task['id']
        task_config = task.get('config', {})
        
        try:
            logger.info(f"[Engine] Task {task['name']}: Processing item {item.id}")
            
            # AI Transformation
            ai_options = task_config.get('ai_options', {})
            # Offload CPU-bound/blocking AI to thread if necessary, 
            # but Groq is mostly network-bound
            processed_text = ai_service.process_content(item.text, ai_options)
            
            # 3. Publish to all destinations concurrently
            pub_results = await asyncio.gather(
                *[self._publish_to_destination(dest, processed_text, item.media_urls) for dest in destinations],
                return_exceptions=True
            )
            
            for res in pub_results:
                if isinstance(res, Exception):
                    logger.error(f"[Engine] Destination publish crash: {res}")

            # 4. Success! Mark as processed
            db.mark_item_processed(task_id, source_id, item.id)
            
        except Exception as e:
            logger.error(f"[Engine] Item processing failed: {e}", exc_info=True)

    async def _publish_to_destination(self, dest: Dict[str, Any], text: str, media_urls: List[str]):
        """Isolated publication logic."""
        dest_platform = dest['platform']
        dest_id = dest['identifier']
        
        if dest_platform == "telegram":
            tg_pub = TelegramPublisher(self.bot)
            success = await tg_pub.publish(dest_id, text, media_urls)
            if not success:
                raise Exception(f"Telegram publication failed for {dest_id}")
        elif dest_platform == "twitter":
            tw_user = db.get_setting("TWITTER_USERNAME")
            tw_pass = db.get_setting("TWITTER_PASSWORD")
            if tw_user and tw_pass:
                tw_pub = TwitterPublisher(tw_user, tw_pass)
                success = await tw_pub.publish(text, media_urls)
                if not success:
                    raise Exception(f"Twitter publication failed for {dest_id}")
            else:
                logger.error("[Engine] Twitter credentials missing for destination")
