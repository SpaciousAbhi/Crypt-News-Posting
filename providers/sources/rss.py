# providers/sources/rss.py

import feedparser
import re
import time
from typing import List, Optional
from dataclasses import dataclass
from services.logger import logger

@dataclass
class SourceItem:
    id: str
    text: str
    media_urls: List[str]
    author: str
    url: str
    timestamp: float

class RSSSource:
    """Robust RSS feed monitor with mirror rotation."""
    
    DEFAULT_MIRRORS = [
        "https://nitter.net", 
        "https://nitter.cz",
        "https://nitter.privacydev.net",
        "https://nitter.tokhmi.xyz",
        "https://nitter.moomoo.me"
    ]

    def __init__(self, mirrors: Optional[List[str]] = None):
        self.mirrors = mirrors or self.DEFAULT_MIRRORS

    def fetch_latest(self, identifier: str) -> List[SourceItem]:
        """Fetches latest updates from the RSS identifier."""
        items = []
        errors = []

        for mirror in self.mirrors:
            rss_url = f"{mirror}/{identifier.strip('@')}/rss"
            try:
                logger.info(f"[RSS] Fetching from mirror: {mirror}")
                feed = feedparser.parse(rss_url)
                
                if feed.bozo:
                    raise Exception(f"Feed parsing error: {feed.bozo_exception}")

                if not feed.entries:
                    logger.warning(f"[RSS] No entries found for {identifier} on {mirror}")
                    continue

                for entry in feed.entries:
                    # Extract ID from link or entry.id
                    item_id = self._extract_id_from_link(entry.link) or entry.id
                    
                    # Clean up text
                    text = self._sanitize_text(entry.title)
                    if not text and hasattr(entry, 'description'):
                        text = self._sanitize_text(entry.description)
                    
                    # Extract media (images/videos)
                    desc = getattr(entry, 'description', '')
                    media_urls = self._extract_media(desc, mirror)
                    
                    items.append(SourceItem(
                        id=item_id,
                        text=text,
                        media_urls=media_urls,
                        author=identifier,
                        url=entry.link,
                        timestamp=time.mktime(entry.published_parsed) if hasattr(entry, 'published_parsed') else time.time()
                    ))
                
                logger.info(f"[RSS] Successfully fetched {len(items)} items from {mirror}")
                return items # Stop rotation on success

            except Exception as e:
                logger.error(f"[RSS] Mirror {mirror} failed: {e}")
                errors.append(str(e))
                continue

        logger.error(f"[RSS] All mirrors failed for {identifier}. Errors: {errors}")
        return []

    def _extract_id_from_link(self, link: str) -> Optional[str]:
        """Extracts Tweet ID from a status link."""
        match = re.search(r"/status/(\d+)", link)
        return match.group(1) if match else None

    def _sanitize_text(self, text: str) -> str:
        """Strips HTML tags and simplifies text."""
        if not text: return ""
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', text)
        # Decode entities (basic)
        clean = clean.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        return clean.strip()

    def _extract_media(self, description: str, mirror: str) -> List[str]:
        """Extracts media URLs from the HTML description."""
        # Find <img> and <source>/<video> tags
        img_urls = re.findall(r'<img src="([^"]+)"', description)
        video_urls = re.findall(r'<source src="([^"]+)"', description)
        poster_urls = re.findall(r'poster="([^"]+)"', description)
        
        all_urls = img_urls + video_urls + poster_urls
        # Fix relative URLs and remove duplicates
        return list(set([url if url.startswith("http") else f"{mirror}{url}" for url in all_urls]))
