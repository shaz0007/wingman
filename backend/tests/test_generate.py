import json
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.ai import extract_json, sanitize_reply, validate_and_clean_replies


class TestGenerateReplies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_json_extraction_with_markdown_fences(self):
        fenced_input = """Here is the JSON response:
```json
{
  "replies": [
    {"tone": "Natural", "text": "hey what's up", "explanation": "Friendly greeting"},
    {"tone": "Natural", "text": "not much here, you?", "explanation": "Casual return"},
    {"tone": "Natural", "text": "long day honestly", "explanation": "Direct honest reply"}
  ]
}
```
Hope this helps!"""
        result = extract_json(fenced_input)
        self.assertIn("replies", result)
        self.assertEqual(len(result["replies"]), 3)

    def test_sanitize_reply_truncates_excess_words(self):
        overlong_text = "word " * 30  # 30 words
        reply = sanitize_reply({"text": overlong_text, "explanation": "test"}, "Natural")
        self.assertLessEqual(len(reply.text.split()), 20)

    def test_validate_and_clean_pads_to_three_replies(self):
        only_one = [{"text": "single reply", "explanation": "one"}]
        replies = validate_and_clean_replies(only_one, "Natural")
        self.assertEqual(len(replies), 3)

    def test_generate_empty_message_returns_validation_error(self):
        response = self.client.post("/api/generate", json={"message": "", "tone": "Natural"})
        self.assertEqual(response.status_code, 422)

    @patch("backend.app.services.ai.call_gemini")
    def test_generate_gemini_success(self, mock_gemini):
        mock_gemini.return_value = json.dumps({
            "replies": [
                {"tone": "Natural", "text": "sounds good to me", "explanation": "Easygoing response"},
                {"tone": "Natural", "text": "down for that!", "explanation": "Upbeat reaction"},
                {"tone": "Natural", "text": "what time were you thinking?", "explanation": "Follow-up question"}
            ]
        })

        response = self.client.post(
            "/api/generate",
            json={"message": "Want to grab coffee this weekend?", "tone": "Natural"}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["provider"], "gemini")
        self.assertEqual(len(data["replies"]), 3)
        self.assertEqual(data["replies"][0]["text"], "sounds good to me")

    @patch("backend.app.services.ai.call_gemini")
    @patch("backend.app.services.ai.call_groq")
    def test_generate_fallback_to_groq(self, mock_groq, mock_gemini):
        # Gemini fails
        mock_gemini.side_effect = RuntimeError("Gemini 503 Overloaded")
        # Groq succeeds
        mock_groq.return_value = json.dumps({
            "replies": [
                {"tone": "Playful", "text": "only if coffee is on you", "explanation": "Playful tease"},
                {"tone": "Playful", "text": "depends on the spot!", "explanation": "Light banter"},
                {"tone": "Playful", "text": "i could be persuaded", "explanation": "Intriguing response"}
            ]
        })

        response = self.client.post(
            "/api/generate",
            json={"message": "Coffee?", "tone": "Playful"}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["provider"], "groq")
        self.assertEqual(len(data["replies"]), 3)

    @patch("backend.app.services.ai.call_gemini")
    @patch("backend.app.services.ai.call_groq")
    def test_generate_both_fail_returns_502(self, mock_groq, mock_gemini):
        mock_gemini.side_effect = RuntimeError("Gemini error")
        mock_groq.side_effect = RuntimeError("Groq error")

        response = self.client.post(
            "/api/generate",
            json={"message": "Hello", "tone": "Natural"}
        )

        self.assertEqual(response.status_code, 502)
        data = response.json()
        self.assertFalse(data["success"])


if __name__ == "__main__":
    unittest.main()
