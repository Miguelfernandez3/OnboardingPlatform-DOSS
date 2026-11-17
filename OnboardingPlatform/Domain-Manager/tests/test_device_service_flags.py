import os
import unittest

from services.device_service import DeviceService


class _DummyDB:
    pass


class _DummyMUDService:
    pass


class _DummyFEAMService:
    pass


class DeviceServiceFlagTests(unittest.TestCase):
    def setUp(self):
        self._original = os.environ.get("ALLOW_DSP_FALLBACK")
        self.service = DeviceService(_DummyDB(), _DummyMUDService(), _DummyFEAMService())

    def tearDown(self):
        if self._original is None:
            os.environ.pop("ALLOW_DSP_FALLBACK", None)
        else:
            os.environ["ALLOW_DSP_FALLBACK"] = self._original

    def test_fallback_disabled_for_false_string(self):
        os.environ["ALLOW_DSP_FALLBACK"] = "false"
        self.assertFalse(self.service._should_use_dsp_fallback())

    def test_fallback_enabled_for_true_string(self):
        os.environ["ALLOW_DSP_FALLBACK"] = "true"
        self.assertTrue(self.service._should_use_dsp_fallback())


if __name__ == "__main__":
    unittest.main()
