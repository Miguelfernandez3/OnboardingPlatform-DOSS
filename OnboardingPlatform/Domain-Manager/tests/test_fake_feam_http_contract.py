"""
HTTP contract: Fake-FEAM served with werkzeug, FEAMClient + FEAMService real calls.
Run from OnboardingPlatform/Domain-Manager: python -m pytest tests/test_fake_feam_http_contract.py -q
"""
import importlib.util
import os
import sys
import threading
import time
import unittest
from pathlib import Path

# OnboardingPlatform/Domain-Manager/tests/ -> OnboardingPlatform
ONBOARDING_ROOT = Path(__file__).resolve().parents[2]
FAKEFEAM_DIR = ONBOARDING_ROOT / "Fake-FEAM"

os.environ["FAKEFEAM_FILES_DIR"] = str(FAKEFEAM_DIR / "files")

_spec = importlib.util.spec_from_file_location("fakefeam_http_app", FAKEFEAM_DIR / "app.py")
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules["fakefeam_http_app"] = _mod
_spec.loader.exec_module(_mod)
_FAKEFEAM_FLASK = _mod.app

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_feam_service import DummyDB
from clients.feam_client import FEAMClient
from services.feam_service import FEAMService
from werkzeug.serving import make_server


class TestFakeFEAMHttpContract(unittest.TestCase):
    _httpd = None
    _thread = None
    _port = None

    @classmethod
    def setUpClass(cls):
        cls._httpd = make_server("127.0.0.1", 0, _FAKEFEAM_FLASK, threaded=True)
        cls._port = cls._httpd.server_port
        cls._thread = threading.Thread(target=cls._httpd.serve_forever, daemon=True)
        cls._thread.start()
        time.sleep(0.15)
        cls._base = f"http://127.0.0.1:{cls._port}"

    @classmethod
    def tearDownClass(cls):
        if cls._httpd is not None:
            cls._httpd.shutdown()
        if cls._thread is not None:
            cls._thread.join(timeout=2.0)

    def test_check_pin_get_functions_ok(self):
        c = FEAMClient(self._base, session_id="s1", timeout=5)
        pin = c.check_pin(1234)
        self.assertIsNotNone(pin)
        r = c.get_functions_own()
        self.assertTrue(r.get("ok"))
        body = r.get("body")
        self.assertIsInstance(body, dict)
        self.assertIn("functions", body)
        self.assertTrue(any(str(f.get("id", "")).startswith("1bfae6a6") for f in body["functions"]))

    def test_fetch_gendsp_from_idsp_matches_fake_feam_sample(self):
        c = FEAMClient(self._base, session_id="s2", timeout=10)
        svc = FEAMService(c, db=DummyDB())
        payload = svc.fetch_gendsp_payload_from_idsp_id(
            "11111111-1111-1111-1111-111111111111"
        )
        self.assertIsNotNone(payload, "idsp flow should resolve linked gendsp via FEAM")
        self.assertIn("doss-dsp", payload)
        self.assertIn("bbae8107-3deb-599c-909a-bb60ab37aae1", payload)

    def test_call_resource_list_gendsp_json(self):
        import json

        import requests

        r = requests.post(
            f"{self._base}/callResourceServer",
            json={
                "sessionId": "x",
                "functionId": "1bfae6a6-9281-4d38-ad18-b851ef9b86a0",
                "operationId": "1bfae6a6-0539-4440-be7d-ba743f8c4ada",
                "extraValues": [json.dumps({"status": "Active"})],
            },
            headers={"content-type": "application/json"},
            timeout=5,
        )
        r.raise_for_status()
        b = r.json()
        self.assertEqual(b.get("status"), "ok")
        items = json.loads(b["responseJson"])
        self.assertIsInstance(items, list)
        self.assertTrue(len(items) >= 1)
        self.assertIn("dspFile", items[0])
