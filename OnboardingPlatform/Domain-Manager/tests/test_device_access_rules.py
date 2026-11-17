import os
import tempfile
import unittest

from Database import Database, User


class DeviceAccessRuleTests(unittest.TestCase):
    def setUp(self):
        self._orig = os.environ.get("DADM_DATABASE_PATH")
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.db_path = tmp.name
        os.environ["DADM_DATABASE_PATH"] = self.db_path
        self.db = Database()

        # Two devices, different manufacturer / dsp_id
        self.db.createDevice(None, None, "m1", "dev-cisco", None, None, None,
                             "dsp-100", None, name="A", manufacturer="Cisco")
        self.db.createDevice(None, None, "m2", "dev-hp", None, None, None,
                             "dsp-200", None, name="B", manufacturer="HP")

        self.user = User(email="u@x.com", password_hash="x", role="user")
        self.admin = User(email="a@x.com", password_hash="x", role="admin")
        self.db.session.add_all([self.user, self.admin])
        self.db.session.commit()

    def tearDown(self):
        self.db.session.close()
        self.db.engine.dispose()
        if self._orig is None:
            os.environ.pop("DADM_DATABASE_PATH", None)
        else:
            os.environ["DADM_DATABASE_PATH"] = self._orig
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _cu(self, u):
        return {"id": u.id, "email": u.email, "role": u.role}

    def test_no_rules_denies_everything(self):
        assert self.db.getDevicesForUser(self.user.id) == []
        cisco = self.db.getDevice("dev-cisco")
        assert self.db.userCanAccessDevice(self._cu(self.user), cisco) is False

    def test_explicit_device_rule(self):
        self.db.createAccessRule(self.user.id, "device", "dev-cisco")
        idents = {d.identifier for d in self.db.getDevicesForUser(self.user.id)}
        assert idents == {"dev-cisco"}
        assert self.db.userCanAccessDevice(self._cu(self.user), self.db.getDevice("dev-cisco")) is True
        assert self.db.userCanAccessDevice(self._cu(self.user), self.db.getDevice("dev-hp")) is False

    def test_manufacturer_rule_matches_dynamically(self):
        self.db.createAccessRule(self.user.id, "manufacturer", "Cisco")
        assert {d.identifier for d in self.db.getDevicesForUser(self.user.id)} == {"dev-cisco"}
        # A new Cisco device shows up with no reprocessing.
        self.db.createDevice(None, None, "m3", "dev-cisco-2", None, None, None,
                             "dsp-300", None, name="C", manufacturer="Cisco")
        assert {d.identifier for d in self.db.getDevicesForUser(self.user.id)} == {"dev-cisco", "dev-cisco-2"}

    def test_idsp_rule(self):
        self.db.createAccessRule(self.user.id, "idsp", "dsp-200")
        assert {d.identifier for d in self.db.getDevicesForUser(self.user.id)} == {"dev-hp"}

    def test_admin_sees_all_regardless_of_rules(self):
        cu = self._cu(self.admin)
        assert self.db.userCanAccessDevice(cu, self.db.getDevice("dev-cisco")) is True
        assert self.db.userCanAccessDevice(cu, self.db.getDevice("dev-hp")) is True

    def test_delete_rule_revokes_access(self):
        rule = self.db.createAccessRule(self.user.id, "manufacturer", "Cisco")
        assert self.db.getDevicesForUser(self.user.id)
        assert self.db.deleteAccessRule(self.user.id, rule.id) is True
        assert self.db.getDevicesForUser(self.user.id) == []
        # Deleting someone else's / missing rule returns False.
        assert self.db.deleteAccessRule(self.user.id, 99999) is False


if __name__ == "__main__":
    unittest.main()
