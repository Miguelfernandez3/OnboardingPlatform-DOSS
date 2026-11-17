import os
import tempfile
import unittest

from Database import Database, Device


class DatabaseDeleteDeviceTests(unittest.TestCase):
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

    def test_delete_device_removes_policies_logs_notifications_secrets(self):
        did = "device-cascade-delete-1"
        self.assertTrue(
            self.db.createDevice(
                None,
                None,
                None,
                did,
                None,
                None,
                None,
                None,
                None,
            )
        )
        dev = self.db.getDevice(did)
        self.assertIsNotNone(dev)

        user = self.db.createUser("cascade@test.example", "secret-pass-9")
        self.assertIsNotNone(user)

        pol = self.db.createPolicy(did, "p1", "<mspl/>")
        self.assertIsNotNone(pol)

        self.db.createPolicyExecutionLog(
            device_id=did,
            policy_id=None,
            policy_name="log1",
            profile_id=None,
            run_mode="execute",
            result="completed",
            is_test=False,
        )

        self.db.upsertDeviceEnforcementSecret(
            did,
            "bearer_token",
            ciphertext="ct",
            nonce="nv",
            key_version="kv1",
        )
        self.assertIsNotNone(self.db.getDeviceEnforcementSecret(did, "bearer_token"))

        note = self.db.createNotification(
            user_id=user.id,
            device_id=did,
            notification_type="missing_mitigation_fields",
            language="es",
            message="test",
            deduplication_key=f"dedup-{did}-1",
        )
        self.assertIsNotNone(note)

        ok = self.db.deleteDevice(dev)
        self.assertTrue(ok)

        self.assertIsNone(self.db.getDevice(did))
        self.assertEqual(len(self.db.getPoliciesByDevice(did)), 0)
        self.assertEqual(len(self.db.listPolicyExecutionLogs(device_id=did, limit=50)), 0)
        self.assertIsNone(self.db.getDeviceEnforcementSecret(did, "bearer_token"))

        rows, total = self.db.getNotificationsForUser(user.id, per_page=50)
        self.assertEqual(total, 0)
        self.assertEqual(len(rows), 0)


if __name__ == "__main__":
    unittest.main()
