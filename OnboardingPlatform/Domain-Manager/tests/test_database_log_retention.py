import os
import tempfile
import unittest
from datetime import datetime, timezone, timedelta

from Database import Database


class DatabaseLogRetentionTests(unittest.TestCase):
    def setUp(self):
        self._original_db_path = os.environ.get("DADM_DATABASE_PATH")
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.db_path = tmp.name
        os.environ["DADM_DATABASE_PATH"] = self.db_path
        self.db = Database()

    def tearDown(self):
        self.db.session.close()
        self.db.engine.dispose()
        if self._original_db_path is None:
            os.environ.pop("DADM_DATABASE_PATH", None)
        else:
            os.environ["DADM_DATABASE_PATH"] = self._original_db_path
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_purge_policy_execution_logs_older_than_days(self):
        old_ts = datetime.now(timezone.utc) - timedelta(days=5)
        new_ts = datetime.now(timezone.utc) - timedelta(hours=12)

        self.db.createPolicyExecutionLog(
            device_id="device-a",
            policy_id=None,
            policy_name="old-log",
            profile_id=None,
            run_mode="execute",
            result="completed",
            is_test=False,
            executed_at=old_ts,
        )
        self.db.createPolicyExecutionLog(
            device_id="device-a",
            policy_id=None,
            policy_name="new-log",
            profile_id=None,
            run_mode="execute",
            result="completed",
            is_test=False,
            executed_at=new_ts,
        )

        deleted = self.db.purgePolicyExecutionLogsOlderThanDays(3)
        remaining = self.db.listPolicyExecutionLogs(limit=100)

        self.assertEqual(deleted, 1)
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].policy_name, "new-log")

    def test_vacuum_sqlite_returns_true(self):
        self.assertTrue(self.db.vacuumSqlite())


if __name__ == "__main__":
    unittest.main()
