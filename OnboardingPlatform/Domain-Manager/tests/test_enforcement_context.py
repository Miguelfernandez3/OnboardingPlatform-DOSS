"""Unit tests for enforcement context merge and requirements."""
import json
import unittest
from types import SimpleNamespace

from services.enforcement_context import (
    build_merged_enforcement_context,
    derive_placeholder_keys_from_profile,
    list_required_keys,
    merge_context_layers,
    normalize_key,
)


class TestEnforcementContext(unittest.TestCase):
    def test_normalize_key(self):
        self.assertEqual(normalize_key("device_ip"), "device-ip")
        self.assertEqual(normalize_key("Device-IP"), "device-ip")

    def test_merge_context_layers_precedence(self):
        base = {"device_id": "d1", "device_ip": ""}
        mspl = {"foo": "from_mspl"}
        dev = {"device_ip": "10.0.0.1"}
        extra = {"device_ip": "10.0.0.2"}
        ctx = merge_context_layers(base, mspl, dev, extra)
        self.assertEqual(ctx[normalize_key("device_ip")], "10.0.0.2")

    def test_derive_placeholders_from_profile(self):
        p = SimpleNamespace(
            endpoint_template="http://{{device_ip}}:80/{{device_id}}",
            headers_template='{"H":"{{token}}"}',
            payload_template=None,
        )
        keys = derive_placeholder_keys_from_profile(p)
        self.assertIn("device-ip", keys)
        self.assertIn("device-id", keys)
        self.assertIn("token", keys)

    def test_missing_device_ip_in_derived_mode(self):
        p = SimpleNamespace(
            endpoint_template="http://{{device_ip}}:80/api",
            headers_template="{}",
            payload_template="{}",
            context_spec=None,
            auth_type="none",
            allow_mspl_token=False,
        )
        device = SimpleNamespace(
            identifier="dev-1", ip=None, enforcement_context=None
        )
        base = {
            "device_id": "dev-1",
            "device_ip": "",
            "policy_name": "p",
            "policy_id": "1",
            "policy_type": "",
            "capability": "",
            "timestamp": "t",
        }
        r = build_merged_enforcement_context(
            p, device, base, {}, None, db=None, secret_manager=None
        )
        self.assertTrue(any(m.get("key") == "device-ip" for m in r.missing), msg=str(r.missing))

    def test_device_enrichment_satisfies_placeholder(self):
        p = SimpleNamespace(
            endpoint_template="http://{{device_ip}}:80/api",
            headers_template="{}",
            payload_template="{}",
            context_spec=None,
            auth_type="none",
        )
        device = SimpleNamespace(
            identifier="dev-1",
            ip=None,
            enforcement_context=json.dumps({"device_ip": "192.168.1.5"}),
        )
        base = {
            "device_id": "dev-1",
            "device_ip": "",
            "policy_name": "p",
            "policy_id": "1",
            "policy_type": "",
            "capability": "",
            "timestamp": "t",
        }
        r = build_merged_enforcement_context(
            p, device, base, {}, None, db=None, secret_manager=None
        )
        self.assertEqual(r.missing, [])

    def test_list_required_from_spec(self):
        p = SimpleNamespace(
            context_spec=json.dumps(
                {
                    "requirements": [
                        {"key": "custom_key", "optional": False, "source": "operator", "label": "CK"}
                    ]
                }
            ),
            endpoint_template="https://127.0.0.1/x",
            headers_template="{}",
            payload_template="{}",
        )
        keys, mode = list_required_keys(p)
        self.assertEqual(mode, "spec")
        self.assertIn("custom-key", keys)

    def test_bearer_context_key_pair_single(self):
        from services.enforcement_context import get_bearer_context_key_pair

        p = SimpleNamespace(
            context_spec=json.dumps(
                {
                    "options": {"requireStoredDeviceBearer": True},
                    "requirements": [
                        {"key": "device_ip", "source": "device"},
                        {"key": "api_token", "bearerForAuth": True, "sensitive": True},
                    ],
                }
            )
        )
        nk, rk = get_bearer_context_key_pair(p)
        self.assertEqual(nk, "api-token")
        self.assertEqual(rk, "api_token")

    def test_ordered_spec_required_keys_follows_json_order(self):
        from services.enforcement_context import ordered_spec_required_keys

        p = SimpleNamespace(
            context_spec=json.dumps(
                {
                    "requirements": [
                        {"key": "device_port", "label": "PORT", "source": "device"},
                        {"key": "device_ip", "label": "IP", "source": "device"},
                        {"key": "bearer_token", "label": "TOKEN", "source": "device", "bearerForAuth": True},
                    ]
                }
            ),
        )
        self.assertEqual(
            ordered_spec_required_keys(p),
            ["device-port", "device-ip", "bearer-token"],
        )

    def test_bearer_context_key_pair_rejects_zero_or_many(self):
        from services.enforcement_context import get_bearer_context_key_pair

        p0 = SimpleNamespace(
            context_spec=json.dumps({"requirements": [{"key": "x"}]}),
        )
        self.assertEqual(get_bearer_context_key_pair(p0), (None, None))

        p2 = SimpleNamespace(
            context_spec=json.dumps(
                {
                    "requirements": [
                        {"key": "a", "bearerForAuth": True},
                        {"key": "b", "bearerForAuth": True},
                    ]
                }
            ),
        )
        self.assertEqual(get_bearer_context_key_pair(p2), (None, None))


if __name__ == "__main__":
    unittest.main()
