import unittest
from fastapi.testclient import TestClient
from backend.app.config import settings
from backend.app.main import app


class TestSecurityAndRateLimiter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_security_headers_in_response(self):
        response = self.client.get("/")
        self.assertEqual(response.headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(response.headers.get("x-frame-options"), "DENY")
        self.assertEqual(response.headers.get("x-xss-protection"), "1; mode=block")
        self.assertEqual(response.headers.get("referrer-policy"), "strict-origin-when-cross-origin")
        self.assertIn("permissions-policy", response.headers)

    def test_rate_limiter_blocks_excessive_requests(self):
        # We simulate rapid hits from a specific client IP to a rate-limited endpoint
        original_limit = settings.RATE_LIMIT_PER_MINUTE
        settings.RATE_LIMIT_PER_MINUTE = 5
        client = TestClient(app)

        try:
            blocked = False
            headers = {"x-forwarded-for": "198.51.100.42"}
            for _ in range(8):
                res = client.get("/api/test", headers=headers)
                if res.status_code == 429:
                    blocked = True
                    self.assertIn("Retry-After", res.headers)
                    break
            self.assertTrue(blocked, "Rate limiter should have returned 429 status.")
        finally:
            settings.RATE_LIMIT_PER_MINUTE = original_limit


if __name__ == "__main__":
    unittest.main()
