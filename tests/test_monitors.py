# tests/test_monitors.py

import unittest
from unittest.mock import patch, MagicMock
from monitors import RSSMonitor, TweetData

class TestMonitors(unittest.TestCase):
    """Unit tests for the monitoring module."""

    @patch('feedparser.parse')
    def test_rss_monitor_fetch(self, mock_parse):
        """Tests that RSSMonitor correctly parses feed entries."""
        # Mock feedparser response
        mock_feed = MagicMock()
        mock_entry = MagicMock()
        mock_entry.link = "https://nitter.net/user/status/123456789#m"
        mock_entry.title = "Hello world"
        mock_entry.description = '<img src="/pic/media/img.jpg" />'
        mock_entry.id = "123456789"
        mock_feed.entries = [mock_entry]
        mock_parse.return_value = mock_feed

        monitor = RSSMonitor(nitter_instances=["https://nitter.net"])
        tweets = monitor.fetch_latest_tweets("user")

        self.assertEqual(len(tweets), 1)
        self.assertEqual(tweets[0].id, "123456789")
        self.assertEqual(tweets[0].text, "Hello world")
        self.assertEqual(tweets[0].media_urls[0], "https://nitter.net/pic/media/img.jpg")
        self.assertEqual(tweets[0].author, "user")

    def test_tweet_data_structure(self):
        """Verifies the TweetData dataclass."""
        tweet = TweetData(id="1", text="test", media_urls=[], author="auth", url="url")
        self.assertEqual(tweet.id, "1")
        self.assertEqual(tweet.author, "auth")

if __name__ == '__main__':
    unittest.main()
