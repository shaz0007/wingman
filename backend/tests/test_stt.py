import io
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from backend.app.main import app


class TestSpeechToText(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_transcribe_unsupported_file_extension(self):
        file_content = b"fake audio content"
        files = {"audio_file": ("test.exe", io.BytesIO(file_content), "application/octet-stream")}
        response = self.client.post("/api/transcribe", files=files)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("Unsupported audio format", data["error"])

    def test_transcribe_empty_file(self):
        files = {"audio_file": ("empty.wav", io.BytesIO(b""), "audio/wav")}
        response = self.client.post("/api/transcribe", files=files)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("empty", data["error"].lower())

    @patch("backend.app.services.stt.requests.post")
    def test_transcribe_successful_mock(self, mock_post):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "transcript": "Hey, what are your thoughts on meeting tomorrow around noon?",
            "detected_language_code": "en",
            "model": "prisma-v3.0"
        }
        mock_post.return_value = mock_response

        files = {"audio_file": ("voice.wav", io.BytesIO(b"RIFF....WAVEfmt "), "audio/wav")}
        response = self.client.post("/api/transcribe", files=files)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["transcript"], "Hey, what are your thoughts on meeting tomorrow around noon?")
        self.assertEqual(data["language"], "en")


if __name__ == "__main__":
    unittest.main()
