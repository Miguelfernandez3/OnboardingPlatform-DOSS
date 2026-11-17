"""Tests for proactive mitigation prerequisite notifications after DSP registration."""
import unittest
from unittest.mock import MagicMock, patch

from services.device_service import DeviceService


class _DummyMUDService:
    pass


class _DummyFEAMService:
    pass


class MitigationGapNotifyTests(unittest.TestCase):
    def test_skips_when_no_mitigation_service(self):
        svc = DeviceService(MagicMock(), _DummyMUDService(), _DummyFEAMService())
        dev = MagicMock(identifier="d1")
        with patch("services.device_service.NotificationService") as NS:
            svc._notify_unapplied_mitigation_gaps_if_any(dev)
            NS.assert_not_called()

    def test_notifies_when_threat_mitigation_has_gaps(self):
        db = MagicMock()
        svc = DeviceService(db, _DummyMUDService(), _DummyFEAMService())
        ms = MagicMock()
        ms.threat_service.get_matching_threat_by_id.return_value = {
            "threat_mud_url": "https://threat.example/mud",
        }
        ms.get_device_mitigations.return_value = [
            {
                "id": "threat-mitigation-42",
                "threatId": "42",
                "name": "Threat Mitigation 42",
                "is_enforced": False,
                "enforcementGaps": {"ready": False, "missing": [{"key": "device-ip", "label": "IP"}]},
            }
        ]
        svc.set_mitigation_service(ms)
        dev = MagicMock()
        dev.identifier = "d1"
        dev.name = "Camera"
        with patch("services.device_service.NotificationService") as NS:
            svc._notify_unapplied_mitigation_gaps_if_any(dev)
            NS.assert_called_once_with(db)
            NS.return_value.notify_mitigation_prerequisites.assert_called_once()
            kwargs = NS.return_value.notify_mitigation_prerequisites.call_args.kwargs
            self.assertEqual(kwargs["threat_id"], "42")
            self.assertEqual(kwargs["mitigation_id"], "threat-mitigation-42")
            self.assertEqual(kwargs["threat_mud_url"], "https://threat.example/mud")
            self.assertEqual(kwargs["missing"], [{"key": "device-ip", "label": "IP"}])


class NotificationCopyTests(unittest.TestCase):
    def test_missing_fields_human_prefers_label(self):
        from services.notifications.service import _missing_fields_human

        self.assertEqual(
            _missing_fields_human([{"key": "device-port", "label": "PORT"}, {"key": "device-ip", "label": "IP"}]),
            "PORT, IP",
        )

    def test_skips_enforced_mitigation(self):
        svc = DeviceService(MagicMock(), _DummyMUDService(), _DummyFEAMService())
        ms = MagicMock()
        ms.get_device_mitigations.return_value = [
            {
                "id": "threat-mitigation-1",
                "threatId": "1",
                "is_enforced": True,
                "enforcementGaps": {"ready": False, "missing": [{"key": "x"}]},
            }
        ]
        svc.set_mitigation_service(ms)
        with patch("services.device_service.NotificationService") as NS:
            svc._notify_unapplied_mitigation_gaps_if_any(MagicMock(identifier="d1"))
            NS.assert_not_called()


if __name__ == "__main__":
    unittest.main()
