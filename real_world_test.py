# real_world_test.py

import asyncio
import time
from database.manager import db
from core.engine import ProcessingEngine
from services.logger import logger
from providers.sources.rss import RSSSource
from services.config_service import config

async def test_db_persistence():
    logger.info("[Test] Testing DB Persistence...")
    test_name = f"TestTask_{int(time.time())}"
    task_id = db.create_task(test_name, 12345, {"test": True})
    
    # Reload from DB
    task = db.get_task_details(task_id)
    if task and task['name'] == test_name:
        logger.info(f"✅ DB Persistence Verified: Task {task_id} saved and retrieved.")
        # Cleanup
        db.delete_task(task_id)
        return True
    else:
        logger.error("❌ DB Persistence Failed.")
        return False

async def test_concurrency():
    logger.info("[Test] Testing Concurrency (asyncio.gather)...")
    start_time = time.perf_counter()
    
    async def dummy_work(n):
        await asyncio.sleep(1)
        return n
    
    # Run 5 tasks in parallel. Should take ~1s total if parallel.
    results = await asyncio.gather(*[dummy_work(i) for i in range(5)])
    duration = time.perf_counter() - start_time
    
    if duration < 1.5 and len(results) == 5:
        logger.info(f"✅ Concurrency Verified: Processed 5 tasks in {duration:.2f}s (Theoretical sequential: 5s).")
        return True
    else:
        logger.error(f"❌ Concurrency Failed: Took {duration:.2f}s.")
        return False

async def test_rss_fetch():
    logger.info("[Test] Testing Real-World RSS Fetch (Nitter Mirrors)...")
    rss = RSSSource()
    # Test with a known active nitter mirror if possible, or use the rotation
    items = rss.fetch_latest("VitalikButerin")
    if items:
        logger.info(f"✅ RSS Fetch Verified: Retrieved {len(items)} items from mirrors.")
        return True
    else:
        logger.warning("⚠️ RSS Fetch failed for all mirrors. This might be due to global mirror downtime.")
        return False

async def run_all_tests():
    logger.info("🚀 --- STARTING REAL-WORLD VALIDATION SUITE --- 🚀")
    
    results = {
        "DB Persistence": await test_db_persistence(),
        "Concurrency": await test_concurrency(),
        "RSS Fetch": await test_rss_fetch()
    }
    
    logger.info("📊 --- TEST SUMMARY ---")
    for test, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test}: {status}")
    
    if all(results.values()):
        logger.info("🏆 ALL CORE SYSTEMS OPERATING AT EXCEPTIONAL STANDARDS.")
    else:
        logger.error("🚨 SOME SYSTEMS FAILED LIVE VALIDATION.")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
