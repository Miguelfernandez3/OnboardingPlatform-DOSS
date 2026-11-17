import unittest

from services.log_retention_service import LogRetentionService


class _DummyDB:
    def __init__(self):
        self.purge_calls = 0
        self.vacuum_calls = 0
        self.last_days = None

    def purgePolicyExecutionLogsOlderThanDays(self, days):
        self.purge_calls += 1
        self.last_days = days
        return 5

    def vacuumSqlite(self):
        self.vacuum_calls += 1
        return True


class LogRetentionServiceTests(unittest.TestCase):
    def test_run_once_purges_and_vacuums_when_enabled(self):
        db = _DummyDB()
        service = LogRetentionService(db)
        service.configure(
            retention_days=3,
            interval_seconds=600,
            vacuum_enabled=True,
            vacuum_interval_seconds=3600,
        )

        service.run_once()

        self.assertEqual(db.purge_calls, 1)
        self.assertEqual(db.last_days, 3)
        self.assertEqual(db.vacuum_calls, 1)

    def test_run_once_skips_vacuum_when_disabled(self):
        db = _DummyDB()
        service = LogRetentionService(db)
        service.configure(
            retention_days=3,
            interval_seconds=600,
            vacuum_enabled=False,
            vacuum_interval_seconds=3600,
        )

        service.run_once()

        self.assertEqual(db.purge_calls, 1)
        self.assertEqual(db.vacuum_calls, 0)


if __name__ == "__main__":
    unittest.main()
