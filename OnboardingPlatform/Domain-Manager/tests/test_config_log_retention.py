import os
import unittest

from core.config import Config


class ConfigLogRetentionTests(unittest.TestCase):
    def setUp(self):
        self._vars = {
            "LOG_RETENTION_DAYS": os.environ.get("LOG_RETENTION_DAYS"),
            "LOG_RETENTION_INTERVAL_SECONDS": os.environ.get("LOG_RETENTION_INTERVAL_SECONDS"),
            "LOG_RETENTION_VACUUM_ENABLED": os.environ.get("LOG_RETENTION_VACUUM_ENABLED"),
            "LOG_RETENTION_VACUUM_INTERVAL_SECONDS": os.environ.get("LOG_RETENTION_VACUUM_INTERVAL_SECONDS"),
        }
        self.config = Config("config.yaml")

    def tearDown(self):
        for key, value in self._vars.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_log_retention_defaults(self):
        os.environ.pop("LOG_RETENTION_DAYS", None)
        os.environ.pop("LOG_RETENTION_INTERVAL_SECONDS", None)
        os.environ.pop("LOG_RETENTION_VACUUM_ENABLED", None)
        os.environ.pop("LOG_RETENTION_VACUUM_INTERVAL_SECONDS", None)
        cfg = Config("config.yaml")

        self.assertEqual(cfg.log_retention_days, 3)
        self.assertEqual(cfg.log_retention_interval_seconds, 21600)
        self.assertTrue(cfg.log_retention_vacuum_enabled)
        self.assertEqual(cfg.log_retention_vacuum_interval_seconds, 86400)

    def test_log_retention_env_overrides(self):
        os.environ["LOG_RETENTION_DAYS"] = "7"
        os.environ["LOG_RETENTION_INTERVAL_SECONDS"] = "1200"
        os.environ["LOG_RETENTION_VACUUM_ENABLED"] = "false"
        os.environ["LOG_RETENTION_VACUUM_INTERVAL_SECONDS"] = "7200"
        cfg = Config("config.yaml")

        self.assertEqual(cfg.log_retention_days, 7)
        self.assertEqual(cfg.log_retention_interval_seconds, 1200)
        self.assertFalse(cfg.log_retention_vacuum_enabled)
        self.assertEqual(cfg.log_retention_vacuum_interval_seconds, 7200)


if __name__ == "__main__":
    unittest.main()
