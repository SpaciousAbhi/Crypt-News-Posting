# services/utils.py

import asyncio
import functools
from services.logger import logger

def retry_async(retries: int = 3, delay: float = 2.0, backoff: float = 2.0, exceptions=(Exception,)):
    """
    Decorator for retrying async functions with exponential backoff.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            attempt_delay = delay
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == retries - 1:
                        logger.error(f"[Retry] {func.__name__} failed after {retries} attempts: {e}")
                        raise
                    
                    logger.warning(f"[Retry] {func.__name__} attempt {attempt + 1} failed: {e}. Retrying in {attempt_delay}s...")
                    await asyncio.sleep(attempt_delay)
                    attempt_delay *= backoff
            return None
        return wrapper
    return decorator
