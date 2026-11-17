import unittest
from unittest.mock import patch, Mock
import requests

from clients.feam_client import FEAMClient


class FEAMClientTests(unittest.TestCase):
    def test_forbidden_endpoints_are_blocked(self):
        client = FEAMClient(base_url="http://localhost:8181", session_id="session")
        for endpoint in ("/init", "/register", "/activate"):
            response = client.post_raw(endpoint, {"sessionId": "session"})
            self.assertFalse(response.get("ok"))
            self.assertIn("Forbidden FEAM endpoint", response.get("error", ""))

    @patch("clients.feam_client.requests.post")
    def test_post_raw_collects_attempts_until_success(self, mock_post):
        timeout_exc = requests.exceptions.Timeout("boom")
        success_response = Mock()
        success_response.status_code = 200
        success_response.text = '{"status":"ok"}'
        success_response.json.return_value = {"status": "ok"}
        mock_post.side_effect = [timeout_exc, success_response]

        client = FEAMClient(base_url="http://localhost:8181", session_id="session")
        client.max_attempts = 2
        client.retry_backoff_seconds = 0.0

        response = client.post_raw("/checkPin", {"sessionId": "session"})
        self.assertTrue(response.get("ok"))
        attempts = response.get("attempts", [])
        self.assertEqual(len(attempts), 2)
        self.assertFalse(attempts[0].get("ok"))
        self.assertTrue(attempts[1].get("ok"))


if __name__ == "__main__":
    unittest.main()
