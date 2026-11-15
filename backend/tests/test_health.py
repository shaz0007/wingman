import unittest
from fastapi.testclient import TestClient
from backend.app.main import app


class TestHealthAndDiagnostics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "running")
        self.assertIn("version", data)

    def test_health_check_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "wingman-backend")
        self.assertIn("providers", data)
        self.assertIn("gemini", data["providers"])
        self.assertIn("groq", data["providers"])
        self.assertIn("gnani", data["providers"])

    def test_api_test_connection(self):
        response = self.client.get("/api/test")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["product"], "WINGMAN")

    def test_security_headers_present(self):
        response = self.client.get("/health")
        self.assertEqual(response.headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(response.headers.get("x-frame-options"), "DENY")
        self.assertIn("x-process-time", response.headers)


if __name__ == "__main__":
    unittest.main()
