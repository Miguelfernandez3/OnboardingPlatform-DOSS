import json
import unittest
from types import SimpleNamespace

from services.threat_service import ThreatService


class _FakeThreatClient:
    """Returns the full catalog regardless of device; import is a no-op."""

    def __init__(self, catalog):
        self.catalog = catalog

    def get_threats(self, device_identifier=None):
        return list(self.catalog)

    def get_tmud_file(self, tmudurl):
        return None


def _device(model="Home Assistant Green", discovered=None):
    return SimpleNamespace(
        model=model,
        identifier="19bdfb7e-32b4-4057-8c7d-468ab17be73a",
        discovered_threat_mud_urls=json.dumps(discovered) if discovered is not None else None,
    )


# Catalog threat whose model would have matched the device under the old logic.
_CATALOG = [
    {
        "id": "t1",
        "threat_mud_url": "https://threat/ha-green",
        "threat_mud_file": json.dumps(
            {"ietf-threatmud:mud": {"models-affected": "Home Assistant Green"}}
        ),
    }
]


class ThreatDspDrivenTest(unittest.TestCase):
    def test_no_dsp_tmud_means_no_match(self):
        svc = ThreatService(_FakeThreatClient(_CATALOG))
        # DSP declares no TMUD -> even a model-matching catalog threat must not apply.
        self.assertEqual(svc.get_matching_threats(_device(discovered=[])), [])

    def test_dsp_tmud_declared_matches(self):
        svc = ThreatService(_FakeThreatClient(_CATALOG))
        matches = svc.get_matching_threats(_device(discovered=["https://threat/ha-green"]))
        self.assertEqual([t["id"] for t in matches], ["t1"])

    def test_url_match_tolerates_trailing_slash(self):
        svc = ThreatService(_FakeThreatClient(_CATALOG))
        matches = svc.get_matching_threats(_device(discovered=["https://threat/ha-green/"]))
        self.assertEqual([t["id"] for t in matches], ["t1"])


if __name__ == "__main__":
    unittest.main()
