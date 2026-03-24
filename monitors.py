# monitors.py

import feedparser
import re
from dataclasses import dataclass
from typing import List, Optional
from twikit import Client

@dataclass
class TweetData:
    id: str
    text: str
    media_urls: List[str]
    author: str
    url: str

class RSSMonitor:
    """Monitors Tweet updates via Nitter RSS feeds."""
    
    def __init__(self, nitter_instances: List[str] = ["https://nitter.net"]):
        self.nitter_instances = nitter_instances

    def fetch_latest_tweets(self, username: str) -> List[TweetData]:
        """Fetches the latest tweets for a user from Nitter RSS."""
        tweets = []
        # Try different instances if one fails
        for instance in self.nitter_instances:
            rss_url = f"{instance}/{username}/rss"
            try:
                feed = feedparser.parse(rss_url)
                if feed.entries:
                    for entry in feed.entries:
                        # Extract Tweet ID from link (usually ends with /status/ID#m)
                        match = re.search(r"/status/(\d+)", entry.link)
                        tweet_id = match.group(1) if match else entry.id
                        
                        # Extract media URLs from description (Nitter embeds images in <img> tags)
                        media_urls = re.findall(r'<img src="([^"]+)"', entry.description)
                        # Fix relative URLs if any
                        media_urls = [url if url.startswith("http") else f"{instance}{url}" for url in media_urls]
                        
                        tweets.append(TweetData(
                            id=tweet_id,
                            text=entry.title, # Title usually contains the tweet text
                            media_urls=media_urls,
                            author=username,
                            url=entry.link
                        ))
                    break # Success, stop trying instances
            except Exception as e:
                print(f"[Error] RSS fetch failed for {instance}: {e}")
                continue
        return tweets

class TwitterMonitor:
    """Fallback monitor using twikit (requires login)."""
    
    def __init__(self, username: str, password: str):
        self.client = Client('en-US')
        self.auth_username = username
        self.auth_password = password
        self.is_logged_in = False

    async def _login(self):
        if not self.is_logged_in:
            await self.client.login(auth_info_1=self.auth_username, password=self.auth_password)
            self.is_logged_in = True

    async def fetch_latest_tweets(self, username: str) -> List[TweetData]:
        """Fetches latest tweets using twikit."""
        try:
            await self._login()
            user = await self.client.get_user_by_screen_name(username)
            tweets = await user.get_tweets('Tweets')
            
            tweet_list = []
            for t in tweets:
                media_urls = [m['media_url_https'] for m in t.media] if hasattr(t, 'media') and t.media else []
                tweet_list.append(TweetData(
                    id=t.id,
                    text=t.full_text,
                    media_urls=media_urls,
                    author=username,
                    url=f"https://x.com/{username}/status/{t.id}"
                ))
            return tweet_list
        except Exception as e:
            print(f"[Error] Twikit fetch failed: {e}")
            return []
