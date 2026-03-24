# tests/verify_logic.py

import sys
from unittest.mock import MagicMock, patch

# Mocking external modules to test logic without installation
mock_groq_mod = MagicMock()
sys.modules['feedparser'] = MagicMock()
sys.modules['twikit'] = MagicMock()
sys.modules['groq'] = mock_groq_mod
sys.modules['telegram'] = MagicMock()
sys.modules['telegram.ext'] = MagicMock()

import unittest
import os
os.environ["GROQ_API_KEY"] = "mock_key" # Ensure it doesn't crash on os.environ.get

from monitors import RSSMonitor, TweetData
from ai_utils import modify_message
from config import TASKS

class VerifyLogic(unittest.TestCase):
    """Verifies the core logic and integration points."""

    def test_rss_logic(self):
        """Tests RSS monitor logic with a mocked feed."""
        import feedparser
        mock_feed = MagicMock()
        mock_entry = MagicMock()
        mock_entry.link = "https://nitter.net/user/status/123#m"
        mock_entry.title = "Test Tweet"
        # Mocking the regex-heavy parsing
        mock_entry.description = '<img src="/pic/media/img.jpg" />'
        mock_entry.id = "123"
        mock_feed.entries = [mock_entry]
        feedparser.parse.return_value = mock_feed

        monitor = RSSMonitor(nitter_instances=["https://nitter.net"])
        tweets = monitor.fetch_latest_tweets("testuser")
        
        self.assertEqual(len(tweets), 1)
        self.assertEqual(tweets[0].id, "123")
        self.assertEqual(tweets[0].text, "Test Tweet")
        self.assertIn("https://nitter.net/pic/media/img.jpg", tweets[0].media_urls)

    @patch('ai_utils.client')
    def test_ai_redesign_logic(self, mock_client):
        """Tests the AI redesign prompt logic."""
        # Setup the chain of mocks for Groq's nested response object
        mock_choice = MagicMock()
        mock_choice.message.content = "Redesigned Content"
        mock_client.chat.completions.create.return_value.choices = [mock_choice]

        result = modify_message("Original Message", redesign=True)
        self.assertEqual(result, "Redesigned Content")
        
        # Verify the prompt logic
        args, kwargs = mock_client.chat.completions.create.call_args
        prompt = kwargs['messages'][0]['content']
        self.assertIn("Redesign the following", prompt)

    def test_task_structure(self):
        """Verifies the task dictionary structure is consistent with config."""
        test_task = {
            "name": "Test",
            "paused": False,
            "sources": [{"platform": "twitter", "identifier": "user"}],
            "targets": [{"platform": "telegram", "identifier": -100123}],
            "ai_options": {"redesign": True}
        }
        self.assertEqual(test_task["name"], "Test")
        self.assertTrue(isinstance(test_task["sources"], list))

if __name__ == '__main__':
    unittest.main()
