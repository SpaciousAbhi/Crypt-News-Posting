# providers/sources/rss.py

import feedparser
import re
import time
import httpx
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from services.logger import logger
from database.manager import db

@dataclass
class SourceItem:
    id: str
    text: str
    media_urls: List[str]
    author: str
    url: str
    timestamp: float

class RSSSource:
    """Robust RSS feed monitor with mirror rotation and health tracking."""
    
    DEFAULT_MIRRORS = [
        "https://twiiit.com", # Smart Redirector
        "https://nitter.privacydev.net",
        "https://nitter.cz",
        "https://nitter.moomoo.me",
        "https://nitter.tokhmi.xyz",
        "https://nitter.no-logs.com",
        "https://nitter.on-p.me",
        "https://nitter.rawbit.ninja",
        "https://nitter.perennialte.ch",
        "https://nitter.poast.org"
    ]

    def __init__(self, mirrors: Optional[List[str]] = None):
        self.mirrors = mirrors or self.DEFAULT_MIRRORS
        # Register mirrors in DB if not present
        try:
            for m in self.mirrors:
                db.register_mirror(m)
        except Exception:
            pass

    def fetch_latest(self, identifier: str) -> List[SourceItem]:
        """Fetches from mirrors with intelligent rotation and health tracking."""
        username = identifier.strip('@')
        
        # 1. Try health-ranked mirrors
        try:
            active_mirrors = db.get_active_mirrors()
        except Exception:
            active_mirrors = []
            
        if not active_mirrors: active_mirrors = self.mirrors
        
        errors = []
        for mirror in active_mirrors:
            rss_url = f"{mirror}/{username}/rss"
            try:
                logger.info(f"[RSS] Fetching from mirror: {mirror}")
                items = self._fetch_from_url(rss_url, username)
                if items:
                    try: db.update_mirror_status(mirror, True)
                    except Exception: pass
                    return items
                else:
                    raise Exception("Empty or invalid feed")
            except Exception as e:
                err_msg = str(e)
                logger.error(f"[RSS] Mirror {mirror} failed: {err_msg}")
                errors.append(err_msg)
                try: db.update_mirror_status(mirror, False)
                except Exception: pass
                time.sleep(1) # Grace period
                
        logger.error(f"[RSS] All mirrors failed for {username}. Errors: {errors}")
        return []

    def _fetch_from_url(self, rss_url: str, identifier: str) -> List[SourceItem]:
        """Internal helper to fetch and parse a specific RSS URL."""
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            resp = client.get(rss_url)
            resp.raise_for_status()
            xml_content = resp.text
        
        feed = feedparser.parse(xml_content)
        if feed.bozo:
            raise Exception(f"Feed parsing error: {feed.bozo_exception}")

        if not feed.entries:
            return []

        items = []
        for entry in feed.entries:
            # Extract ID and handle timestamp
            entry_id = entry.get('id', entry.get('link', ''))
            ts = time.mktime(entry.published_parsed) if 'published_parsed' in entry else time.time()
            
            # Basic text extraction
            text = entry.get('title', '')
            if 'summary' in entry:
                text = re.sub(r'<[^>]+>', '', entry.summary)
            
            # Media extraction (Nitter usually puts it in description or media:content)
            media_urls = []
            if 'summary' in entry:
                media_matches = re.findall(r'src="([^"]+)"', entry.summary)
                media_urls.extend(media_matches)
            
            items.append(SourceItem(
                id=entry_id,
                text=text,
                media_urls=media_urls,
                author=identifier,
                url=entry.get('link', ''),
                timestamp=ts
            ))
        return items
