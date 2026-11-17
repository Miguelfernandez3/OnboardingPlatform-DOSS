import unittest

from api.service_logs import clean_lines


class ServiceLogsCleanTests(unittest.TestCase):
    def test_drops_debug_and_noise(self):
        raw = (
            "2024-01-01 10:00:00,001 - dm - DEBUG - noisy internal state\n"
            "2024-01-01 10:00:00,002 - dm - INFO - server started\n"
            "Waiting for message or event/error in poll()\n"
        )
        lines = clean_lines(raw)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['level'], 'INFO')
        self.assertEqual(lines[0]['message'], 'server started')

    def test_redacts_secrets(self):
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abcDEF-_123"
        raw = (
            f"2024-01-01 10:00:00,003 - auth - INFO - login token={jwt}\n"
            "2024-01-01 10:00:00,004 - auth - ERROR - Authorization: Bearer secret123\n"
            f"raw unparsed line with password=hunter2 and {jwt}\n"
        )
        lines = clean_lines(raw)
        joined = " ".join(l['message'] for l in lines)
        self.assertNotIn(jwt, joined)
        self.assertNotIn('hunter2', joined)
        self.assertNotIn('secret123', joined)
        self.assertIn('‹redacted›', joined)
        # unparsed line is kept but redacted
        self.assertTrue(any(l['level'] is None for l in lines))


if __name__ == '__main__':
    unittest.main()
