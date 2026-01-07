# tests/test_ai_utils.py

import unittest
from unittest.mock import patch
from ai_utils import modify_message

class TestAIUtils(unittest.TestCase):
    """Unit tests for the AI utilities module."""

    @patch('ai_utils._call_ai_model')
    def test_modify_message_reword(self, mock_call_ai):
        """Tests the rewording functionality."""
        mock_call_ai.return_value = "This is a reworded message. ✨"

        text = "This is the original message."
        options = {"reword": True}

        modified = modify_message(text, options, "fake_api_key")

        self.assertEqual(modified, "This is a reworded message. ✨")
        mock_call_ai.assert_called_once()

    @patch('ai_utils._call_ai_model')
    def test_modify_message_summarize(self, mock_call_ai):
        """Tests the summarization functionality."""
        mock_call_ai.return_value = "This is a summary."

        text = "This is a very long message that needs to be summarized."
        options = {"summarize": True, "summary_length": 50}

        modified = modify_message(text, options, "fake_api_key")

        self.assertEqual(modified, "This is a summary.")
        mock_call_ai.assert_called_once()

    def test_add_header_and_footer(self):
        """Tests adding a header and footer."""
        text = "This is the content."
        options = {
            "header": "📢 Breaking News",
            "footer": "Powered by MyBrand"
        }

        expected = (
            "📢 Breaking News\n\n"
            "This is the content.\n\n"
            "Powered by MyBrand"
        )

        modified = modify_message(text, options, "fake_api_key")
        self.assertEqual(modified, expected)

    def test_watermark_replacement(self):
        """Tests the watermark replacement functionality."""
        text = "Check out this news from Example.com!"
        options = {
            "watermark": {
                "replace_from": "Example.com",
                "replace_to": "MyBrand"
            }
        }

        expected = "Check out this news from MyBrand!"
        modified = modify_message(text, options, "fake_api_key")
        self.assertEqual(modified, expected)

    def test_no_modification(self):
        """Tests that the message is unchanged if no options are provided."""
        text = "This is a simple message."
        options = {}

        modified = modify_message(text, options, "fake_api_key")
        self.assertEqual(modified, text)

if __name__ == '__main__':
    unittest.main()
