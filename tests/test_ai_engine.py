# tests/test_ai_engine.py

import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Mock the database models before importing the engine
class MockAIRule:
    def __init__(self, rule_id, rule_type, config, version="1.0"):
        self.rule_id = rule_id
        self.rule_type = rule_type
        self.config = config
        self.version = version

# Now import the module to be tested
from ai_engine import transform_message, get_prompt


class TestAIEngine(unittest.TestCase):
    """Unit tests for the AI Engine module."""

    def test_get_prompt_found(self):
        """Tests that a prompt is correctly retrieved."""
        # This requires mocking the internal _prompts dictionary
        with patch('ai_engine._prompts', {
            "reword": {
                "1.0": "Reword this: {message_text} in a {tone} tone for {audience}."
            },
            "summarize": {
                "1.0": {
                    "bullet_points": "Summarize this: {message_text} into bullet points.",
                    "paragraph": "Summarize this: {message_text} into a paragraph."
                }
            }
        }):
            prompt = get_prompt("reword", "1.0", {})
            self.assertIn("Reword this", prompt)

            prompt = get_prompt("summarize", "1.0", {"format": "bullet_points"})
            self.assertIn("bullet points", prompt)

    def test_get_prompt_not_found(self):
        """Tests that None is returned for a missing prompt."""
        with patch('ai_engine._prompts', {}):
            prompt = get_prompt("nonexistent", "1.0", {})
            self.assertIsNone(prompt)

    def test_local_transformations(self):
        """Tests local rules like header, footer, and watermark that don't call an AI."""

        async def run_test():
            rules = [
                MockAIRule(1, "add_header", {"text": "Header from {source_chat_name}"}),
                MockAIRule(3, "add_footer", {"text": "Footer!"}),
                MockAIRule(2, "replace_watermark", {"replace_from": "old", "replace_to": "new"}),
            ]

            text = "This is the old content."
            modified = await transform_message(text, rules, "TestSource")

            expected = "Header from TestSource\n\nThis is the new content.\n\nFooter!"
            self.assertEqual(modified, expected)

        asyncio.run(run_test())

    @patch('ai_engine.groq_client.chat.completions.create')
    @patch('ai_engine.get_prompt')
    def test_ai_transformation_success(self, mock_get_prompt, mock_groq_create):
        """Tests a successful AI transformation."""

        async def run_test():
            # Mock the prompt lookup
            mock_get_prompt.return_value = "Reword this: {message_text} in a {tone} tone."

            # Mock the Groq API response
            mock_completion = MagicMock()
            mock_completion.choices = [MagicMock()]
            mock_completion.choices[0].message.content = "This is the reworded text."
            mock_groq_create.return_value = mock_completion

            rules = [MockAIRule(1, "reword", {"tone": "professional"})]
            text = "some original text"

            modified = await transform_message(text, rules, "TestSource")

            self.assertEqual(modified, "This is the reworded text.")
            mock_get_prompt.assert_called_once_with("reword", "1.0", {"tone": "professional"})
            mock_groq_create.assert_called_once()

        asyncio.run(run_test())

    @patch('ai_engine.groq_client.chat.completions.create', side_effect=Exception("API Down"))
    @patch('ai_engine.get_prompt', return_value="Some prompt")
    @patch('ai_engine.send_admin_notification', new_callable=AsyncMock)
    def test_ai_transformation_failure(self, mock_send_notification, mock_get_prompt, mock_groq_create):
        """Tests that the function returns None and sends a notification on AI failure."""

        async def run_test():
            rules = [MockAIRule(1, "reword", {"tone": "professional"})]
            text = "some original text"

            modified = await transform_message(text, rules, "TestSource")

            self.assertIsNone(modified)
            mock_groq_create.assert_called_once()
            mock_send_notification.assert_called_once()

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
