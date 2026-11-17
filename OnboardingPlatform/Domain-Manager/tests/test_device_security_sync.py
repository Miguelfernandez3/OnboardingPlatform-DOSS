import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.device_service import DeviceService


class _FakeDB:
    def __init__(self, device, policies=None):
        self.device = device
        self.policies = list(policies or [])
        self.created_policies = []
        self.updated_policies = []
        self.security_updates = []
        self.execution_logs = []

    def getDevice(self, identifier):
        return self.device if self.device.identifier == identifier else None

    def getAllDevices(self):
        return [self.device]

    def updateDeviceSecuritySnapshot(
        self,
        device_identifier,
        dsp,
        discovered_threat_mud_urls,
        *,
        mudurl=None,
        mudfile=None,
        update_mud=False,
        pilot_id=None,
    ):
        self.security_updates.append(
            {
                "device_identifier": device_identifier,
                "dsp": dsp,
                "discovered_threat_mud_urls": discovered_threat_mud_urls,
                "mudurl": mudurl,
                "mudfile": mudfile,
                "update_mud": update_mud,
                "pilot_id": pilot_id,
            }
        )
        self.device.dsp = dsp
        self.device.discovered_threat_mud_urls = discovered_threat_mud_urls
        if update_mud:
            self.device.mudurl = mudurl
            self.device.mudfile = mudfile
        if pilot_id:
            self.device.pilot_id = pilot_id
        return True

    def getPoliciesByDevice(self, device_id):
        return [p for p in self.policies if p.device_id == device_id]

    def createPolicy(self, **kwargs):
        policy = SimpleNamespace(
            id=len(self.policies) + 1,
            applied_at=None,
            enforcement_blockers=None,
            **kwargs,
        )
        self.policies.append(policy)
        self.created_policies.append(policy)
        return policy

    def updatePolicy(self, policy):
        self.updated_policies.append(policy)
        return True

    def getEnforcementProfile(self, profile_id):
        return SimpleNamespace(
            id=profile_id,
            is_active=True,
            mode="rest",
            auto_enforce_on_registration=True,
        )

    def createPolicyExecutionLog(self, **data):
        self.execution_logs.append(data)
        return SimpleNamespace(id=len(self.execution_logs), **data)


class _FakeMUDService:
    def __init__(self, mud_url="https://mud/new", mud_file=None, threat_urls=None):
        self.mud_url = mud_url
        self.mud_file = mud_file
        self.threat_urls = threat_urls or []
        self.mud_manager_client = MagicMock()
        self.mud_manager_client.get_mud_file.return_value = (
            {"mudurl": mud_url, "mudfile": mud_file}
            if mud_file is not None
            else None
        )

    def get_threat_mud_urls_from_dsp(self, _dsp):
        return list(self.threat_urls)

    def get_mud_url_from_dsp(self, _dsp):
        return self.mud_url


class _FakeFEAMService:
    feam_client = MagicMock()

    def __init__(self, dsp_payload="new-dsp", pilot_id="BME"):
        self.dsp_payload = dsp_payload
        self.pilot_id = pilot_id

    def fetch_gendsp_payload_from_idsp_id(self, *_args, **_kwargs):
        return self.dsp_payload

    def resolve_pilot_from_dsp(self, _dsp):
        return self.pilot_id


class _FakePolicyService:
    @staticmethod
    def _hash_mspl(mspl_xml):
        return str(mspl_xml or "")

    @staticmethod
    def _policy_rank(policy):
        priority = {
            "completed": 3,
            "pending": 1,
            "deferred": 1,
            "failed": 0,
            "superseded": -1,
        }.get(str(getattr(policy, "enforcement_status", "") or ""), 0)
        return priority, int(getattr(policy, "id", 0) or 0)

    def translate_mud_json_to_policies(self, mud_json, device_id="preview"):
        return [
            {
                "id": f"mud-policy-{idx}",
                "deviceId": device_id,
                "name": f"MUD Policy {idx + 1}",
                "msplXml": mspl,
                "policyType": "mud",
            }
            for idx, mspl in enumerate(mud_json.get("policies", []))
        ]


class _FakePolicyEnforcement:
    def __init__(self):
        self.enforced = []
        self.logs = []

    def resolve_enforcement_profile(self, _mspl_xml):
        return {"mode": "rest", "profileId": "1"}

    def enforce_policy(self, mspl_xml, _device, **kwargs):
        self.enforced.append({"mspl": mspl_xml, **kwargs})
        return {"profileId": "1", "execution": {"mode": "rest"}}

    def record_execution(self, **kwargs):
        self.logs.append(kwargs)


def _device(**overrides):
    data = {
        "identifier": "device-1",
        "dsp_id": "dsp-1",
        "dsp": "old-dsp",
        "mudurl": "https://mud/old",
        "mudfile": json.dumps({"policies": ["OLD"]}),
        "discovered_threat_mud_urls": json.dumps(["https://threat/old"]),
        "pilot_id": None,
        "name": "Device",
        "model": "model",
        "mitigation_actions": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _policy(mspl, **overrides):
    data = {
        "id": 1,
        "device_id": "device-1",
        "name": "MUD Policy 1",
        "mspl_xml": mspl,
        "policy_type": "mud",
        "source": "mud_file",
        "status": "active",
        "enforcement_status": "completed",
        "applied_at": None,
        "enforcement_blockers": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


class DeviceSecuritySyncTests(unittest.TestCase):
    def test_dsp_change_updates_mud_and_supersedes_old_policy(self):
        device = _device()
        old_policy = _policy("OLD")
        db = _FakeDB(device, [old_policy])
        mud_service = _FakeMUDService(
            mud_file=json.dumps({"policies": ["NEW"]}),
            threat_urls=["https://threat/new"],
        )
        svc = DeviceService(db, mud_service, _FakeFEAMService())
        policy_enforcement = _FakePolicyEnforcement()

        updated = svc._sync_device_security_snapshot(
            device,
            active_db=db,
            services={
                "feam": _FakeFEAMService(),
                "policy": _FakePolicyService(),
                "policy_enforcement": policy_enforcement,
                "threat": None,
                "mitigation": None,
            },
            dsp_snapshot_cache={},
        )

        self.assertTrue(updated)
        self.assertEqual(device.dsp, "new-dsp")
        self.assertEqual(device.mudurl, "https://mud/new")
        self.assertEqual(json.loads(device.mudfile), {"policies": ["NEW"]})
        self.assertEqual(old_policy.status, "superseded")
        self.assertEqual(old_policy.enforcement_status, "superseded")
        self.assertEqual(len(db.created_policies), 1)
        self.assertEqual(db.created_policies[0].mspl_xml, "NEW")
        self.assertEqual(db.created_policies[0].enforcement_status, "completed")
        self.assertEqual(policy_enforcement.enforced[0]["policy_id"], str(db.created_policies[0].id))

    def test_mud_fetch_failure_preserves_existing_mud_and_policies(self):
        device = _device()
        old_policy = _policy("OLD")
        db = _FakeDB(device, [old_policy])
        mud_service = _FakeMUDService(mud_file=None, threat_urls=["https://threat/new"])
        svc = DeviceService(db, mud_service, _FakeFEAMService())

        updated = svc._sync_device_security_snapshot(
            device,
            active_db=db,
            services={
                "feam": _FakeFEAMService(),
                "policy": _FakePolicyService(),
                "policy_enforcement": _FakePolicyEnforcement(),
                "threat": None,
                "mitigation": None,
            },
            dsp_snapshot_cache={},
        )

        self.assertTrue(updated)
        self.assertEqual(device.dsp, "new-dsp")
        self.assertEqual(device.mudurl, "https://mud/old")
        self.assertEqual(json.loads(device.mudfile), {"policies": ["OLD"]})
        self.assertEqual(old_policy.enforcement_status, "completed")
        self.assertEqual(db.created_policies, [])

    def test_auto_enforce_reuses_existing_pending_policy(self):
        device = _device(mudfile=json.dumps({"policies": ["CURRENT"]}))
        pending_policy = _policy(
            "CURRENT",
            status="pending",
            enforcement_status="pending",
        )
        db = _FakeDB(device, [pending_policy])
        svc = DeviceService(db, _FakeMUDService(), _FakeFEAMService())
        policy_enforcement = _FakePolicyEnforcement()

        svc._auto_enforce_mud_policies(
            device,
            db_override=db,
            policy_service=_FakePolicyService(),
            policy_enforcement_service=policy_enforcement,
        )

        self.assertEqual(db.created_policies, [])
        self.assertEqual(policy_enforcement.enforced[0]["policy_id"], str(pending_policy.id))
        self.assertEqual(pending_policy.status, "active")
        self.assertEqual(pending_policy.enforcement_status, "completed")

    def test_detected_threat_mud_imports_and_notifies_gaps(self):
        device = _device()
        db = _FakeDB(device)
        svc = DeviceService(db, _FakeMUDService(), _FakeFEAMService())
        threat_service = MagicMock()
        mitigation_service = MagicMock()
        mitigation_service.threat_service.get_matching_threat_by_id.return_value = {
            "threat_mud_url": "https://threat/new",
        }
        mitigation_service.get_device_mitigations.return_value = [
            {
                "id": "threat-mitigation-7",
                "threatId": "7",
                "name": "Threat Mitigation 7",
                "is_enforced": False,
                "enforcementGaps": {
                    "ready": False,
                    "missing": [{"key": "device-ip", "label": "IP"}],
                },
            }
        ]

        with patch("services.device_service.NotificationService") as notification_service:
            svc._import_threat_muds_and_notify(
                device,
                services={
                    "db": db,
                    "threat": threat_service,
                    "mitigation": mitigation_service,
                },
            )

        threat_service.get_matching_threats.assert_called_once_with(device)
        notification_service.assert_called_once_with(db)
        notification_service.return_value.notify_mitigation_prerequisites.assert_called_once()

    def test_poller_uses_db_override_for_thread_local_sync(self):
        main_db = _FakeDB(_device(identifier="main"))
        poll_db = _FakeDB(_device(identifier="poll"))
        svc = DeviceService(main_db, _FakeMUDService(), _FakeFEAMService())
        services = {"feam": _FakeFEAMService()}
        svc._build_polling_services = MagicMock(return_value=services)
        svc._sync_device_security_snapshot = MagicMock(return_value=True)

        svc.poll_dsp_threat_updates_once(db_override=poll_db)

        svc._build_polling_services.assert_called_once_with(poll_db)
        self.assertEqual(
            svc._sync_device_security_snapshot.call_args.kwargs["active_db"],
            poll_db,
        )


if __name__ == "__main__":
    unittest.main()
