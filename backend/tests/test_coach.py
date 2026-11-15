import json
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.main import app


class TestCoachConversation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_coach_empty_message_returns_validation_error(self):
        response = self.client.post("/api/coach", json={"message": ""})
        self.assertEqual(response.status_code, 422)

    @patch("backend.app.services.ai.call_gemini")
    def test_coach_successful_analysis(self, mock_gemini):
        mock_gemini.return_value = json.dumps({
            "vibe": "Engaged and playful",
            "subtext": "She wants to see if you can banter without taking things too seriously.",
            "interest_level": "High",
            "recommended_strategy": "Respond with light teasing. Don't over-explain your plans.",
            "avoid": [
                "Sending an interview question",
                "Self-deprecating humor",
                "Replying with a dry single word"
            ]
        })

        response = self.client.post(
            "/api/coach",
            json={
                "message": "Haha you think you can beat me at mini golf? Bold claim",
                "chat_history": "Planning our Saturday date",
                "context": "Second date coming up"
            }
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["vibe"], "Engaged and playful")
        self.assertEqual(data["interest_level"], "High")
        self.assertEqual(len(data["avoid"]), 3)
        self.assertEqual(data["provider"], "gemini")

    @patch("backend.app.services.ai.call_gemini")
    @patch("backend.app.services.ai.call_groq")
    def test_coach_fallback_to_groq(self, mock_groq, mock_gemini):
        mock_gemini.side_effect = RuntimeError("Gemini down")
        mock_groq.return_value = json.dumps({
            "vibe": "Polite but reserved",
            "subtext": "Testing the waters cautiously.",
            "interest_level": "Moderate",
            "recommended_strategy": "Keep it low pressure.",
            "avoid": ["Pushing too fast", "Overwhelming with text"]
        })

        response = self.client.post(
            "/api/coach",
            json={"message": "Hey there! How has your week been going so far?"}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["provider"], "groq")


if __name__ == "__main__":
    unittest.main()
