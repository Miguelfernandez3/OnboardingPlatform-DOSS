import json
import unittest

from services.dsp_metadata import extract_device_identity_from_gendsp


class DspMetadataTests(unittest.TestCase):
    def test_extracts_from_this_system_component(self):
        dsp = {
            "dspFile": {
                "doss-dsp": {
                    "metadata": {"title": "Wrong title should be ignored"},
                    "local-definitions": {
                        "components": [
                            {
                                "type": "software",
                                "title": "Qt library",
                                "props": [{"name": "vendor", "value": "QT"}],
                            },
                            {
                                "type": "this-system",
                                "title": "Dust Concentration Sensor",
                                "props": [
                                    {"name": "vendor", "value": "BME IIT"},
                                    {"name": "model", "value": "DCS-1"},
                                ],
                            },
                        ]
                    },
                }
            }
        }
        identity = extract_device_identity_from_gendsp(dsp)
        self.assertEqual(identity["name"], "Dust Concentration Sensor")
        self.assertEqual(identity["manufacturer"], "BME IIT")
        self.assertEqual(identity["model"], "DCS-1")
        self.assertIsNone(identity["type"])

    def test_returns_empty_when_no_this_system(self):
        dsp = {"doss-dsp": {"local-definitions": {"components": [{"type": "software"}]}}}
        identity = extract_device_identity_from_gendsp(json.dumps(dsp))
        self.assertIsNone(identity["name"])
        self.assertIsNone(identity["manufacturer"])
        self.assertIsNone(identity["model"])


if __name__ == "__main__":
    unittest.main()
