# core/engine.py

import asyncio
from typing import List, Dict, Any
from telegram import Bot
from database.manager import db
from services.logger import logger
from services.ai_service import ai_service
from providers.sources.rss import RSSSource
from providers.sources.twitter import TwikitSource
from providers.publishers.telegram import TelegramPublisher
from providers.publishers.twitter import TwitterPublisher

class ProcessingEngine:
    def __init__(self, telegram_token: str):
        self.bot = Bot(telegram_token)
        self.rss = RSSSource()
        self.tw_pub = None
        self.tw_src = None
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
        """Fetches and processes all active tasks."""
        tasks = db.get_tasks()
        active_tasks = [t for t in tasks if t['is_active']]
        
        if not active_tasks:
            # logger.debug("[Engine] No active tasks to process.")
            return

        for task_row in active_tasks:
            task = db.get_task_details(task_row['id'])
            if not task:
                continue
            
            # Isolated task processing
            try:
                # logger.info(f"[Engine] Processing task: {task['name']}")
                await self.process_task(task)
            except Exception as e:
                logger.error(f"[Engine] Task '{task['name']}' failed: {e}", exc_info=True)

    async def process_task(self, task: Dict[str, Any]):
        """Processes a single task: Fetch -> Transform -> Publish."""
        task_id = task['id']
        sources = task['sources']
        destinations = task['destinations']

        # 1. Fetch from all sources
        all_new_items = []
        for source in sources:
            source_id = source['id']
            platform = source['platform']
            identifier = source['identifier']
            
            items = []
            if platform == "twitter_rss":
                # Primarily RSS
                items = self.rss.fetch_latest(identifier)
            elif platform == "twitter_source":
                # Fallback to Twikit if configured (would need account settings)
                # This would be implemented if user provides keys via Settings UI
                pass

            for item in items:
                if not db.is_item_processed(task_id, source_id, item.id):
                    all_new_items.append((source_id, item))

        if not all_new_items:
            return

        # Sort by timestamp to process chronologically
        all_new_items.sort(key=lambda x: x[1].timestamp)

        # 2. Process and Publish
        for source_id, item in all_new_items:
            logger.info(f"[Engine] New item found for Task {task['name']}: {item.id}")
            
            # AI Transformation
            # Here we'd get AI options from task config
            # task['config'] currently not in schema, let's assume ai_options are there
            ai_options = {} # TODO: Implement task-specific AI options persistence
            processed_text = ai_service.process_content(item.text, ai_options)
            
            # 3. Publish to all destinations
            success_all = True
            for dest in destinations:
                dest_platform = dest['platform']
                dest_id = dest['identifier']
                
                if dest_platform == "telegram":
                    tg_pub = TelegramPublisher(self.bot)
                    res = await tg_pub.publish(dest_id, processed_text, item.media_urls)
                    if not res: success_all = False
                elif dest_platform == "twitter":
                    # Fetch twitter credentials from Settings
                    tw_user = db.get_setting("TWITTER_USERNAME")
                    tw_pass = db.get_setting("TWITTER_PASSWORD")
                    if tw_user and tw_pass:
                        tw_pub = TwitterPublisher(tw_user, tw_pass)
                        res = await tw_pub.publish(processed_text, item.media_urls)
                        if not res: success_all = False

            # 4. Mark as processed if at least one publication succeeded or skip if failed?
            # Usually we mark as processed anyway to avoid loops unless it's a transient error
            db.mark_item_processed(task_id, source_id, item.id)
            logger.info(f"[Engine] Marked item {item.id} as processed for task {task['name']}")
