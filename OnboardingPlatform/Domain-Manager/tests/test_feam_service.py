import json
import os
import time
import unittest

from services.feam_service import (
    FEAMBusinessError,
    FEAMService,
    _extract_gendsp_id_from_insdsp_payload,
    _http_status_from_problem_details,
)


class DummyDB:
    def __init__(self):
        self.logs = []
        self.catalogs = []
        self.sync_states = []

    def createPolicyExecutionLog(self, **data):
        self.logs.append(data)
        return data

    def upsertFeamCatalogSnapshot(self, snapshot):
        self.catalogs.append(snapshot)
        return snapshot

    def upsertFeamPilotSyncState(self, pilot_id, status, error=None):
        self.sync_states.append({"pilot_id": pilot_id, "status": status, "error": error})
        return self.sync_states[-1]


class DummyFEAMClient:
    def __init__(self):
        self.stop_called = False

    def stop_forget_pin_timer(self):
        self.stop_called = True
        return True

    def check_pin(self, pin):
        return {"status": "ok", "pin": pin}

    def get_functions_own(self):
        return {
            "ok": True,
            "status_code": 200,
            "body": {
                "functions": [
                    # CERTH primero: la resolución debe ignorarlo y usar solo 1bfae6a6 (BME).
                    {
                        "id": "2bfae6a6-a268-4d90-ad87-3b8817f0852c",
                        "operations": [
                            {"id": "2bfae6a6-b492-4267-9ef5-92b15f22a394"},
                            {"id": "2bfae6a6-cc5b-44e9-adce-159aee6c0c6d"},
                        ],
                    },
                    {
                        "id": "1bfae6a6-a268-4d90-ad87-3b8817f0852c",
                        "operations": [
                            {"id": "1bfae6a6-b492-4267-9ef5-92b15f22a394"},
                            {"id": "1bfae6a6-cc5b-44e9-adce-159aee6c0c6d"},
                        ],
                    },
                    {
                        "id": "1bfae6a6-9281-4d38-ad18-b851ef9b86a0",
                        "operations": [
                            {"id": "1bfae6a6-4637-487c-a71a-9cba257304af"},
                            {"id": "1bfae6a6-0539-4440-be7d-ba743f8c4ada"},
                        ],
                    },
                    {
                        "id": "1bfae6a6-8394-469d-bd91-4ba6abfe7965",
                        "operations": [
                            {"id": "1bfae6a6-ad05-4b4f-a4df-6551238ca72b"},
                        ],
                    },
                ]
            },
            "raw_text": "",
            "error": None,
            "json_parse_error": None,
            "attempts": [
                {"attempt": 1, "elapsed_ms": 12.3, "status_code": 200, "ok": True, "error": None},
            ],
        }

    def call_resource_server(self, function_id, operation_id, extra_values=None, session_id=None):
        return {
            "ok": True,
            "status_code": 200,
            "body": {
                "status": "ok",
                "responseJson": '{"id":"demo"}',
                "functionId": function_id,
                "operationId": operation_id,
                "extraValues": extra_values,
            },
            "raw_text": "",
            "error": None,
            "json_parse_error": None,
            "attempts": [
                {"attempt": 1, "elapsed_ms": 8.7, "status_code": 200, "ok": True, "error": None},
            ],
        }


class FEAMServiceTests(unittest.TestCase):
    def setUp(self):
        self.db = DummyDB()
        self.client = DummyFEAMClient()
        self._old_catalog_cooldown = os.environ.get("FEAM_CATALOG_RETRY_COOLDOWN_SECONDS")
        self._old_operation_resolve_mode = os.environ.get("FEAM_OPERATION_RESOLVE_MODE")
        os.environ["FEAM_CATALOG_RETRY_COOLDOWN_SECONDS"] = "60"
        self.service = FEAMService(self.client, self.db)

    def tearDown(self):
        if self._old_catalog_cooldown is None:
            os.environ.pop("FEAM_CATALOG_RETRY_COOLDOWN_SECONDS", None)
        else:
            os.environ["FEAM_CATALOG_RETRY_COOLDOWN_SECONDS"] = self._old_catalog_cooldown
        if self._old_operation_resolve_mode is None:
            os.environ.pop("FEAM_OPERATION_RESOLVE_MODE", None)
        else:
            os.environ["FEAM_OPERATION_RESOLVE_MODE"] = self._old_operation_resolve_mode

    def test_prepare_does_not_call_stop_forget_pin_in_current_policy(self):
        self.service.prepare()
        self.assertFalse(self.client.stop_called)

    def test_resolve_pilot_from_function_id(self):
        pilot = self.service.resolve_pilot_from_function_id("2bfae6a6-b492-4267-9ef5-92b15f22a394")
        self.assertEqual(pilot, "CERTH")

    def test_execute_operation_writes_internal_execution_log(self):
        result = self.service.execute_operation(
            function_id="2bfae6a6-a268-4d90-ad87-3b8817f0852c",
            operation_id="2bfae6a6-b492-4267-9ef5-92b15f22a394",
            extra_values=['{"id":"abc","version":"1.0.0"}'],
            pilot_id="CERTH",
        )
        self.assertEqual(result.get("status"), "ok")
        self.assertTrue(any(log.get("event_type") == "feam_execution" for log in self.db.logs))
        self.assertTrue(any(log.get("step_name") == "callResourceServer_attempt_1" for log in self.db.logs))

    def test_get_insdsp_by_id_uses_bme_server_prefix_not_certh(self):
        self.service._catalog_cache = {"timestamp": time.time(), "data": None}
        self.service.refresh_catalog()
        self.client.last_crs = None
        original_crs = self.client.call_resource_server

        def capture_crs(**kwargs):
            self.client.last_crs = kwargs
            return original_crs(**kwargs)

        self.client.call_resource_server = capture_crs
        self.service.get_insdsp_by_id(dsp_id="abc", version="1.0.0", pilot_id="CERTH")
        self.assertIsNotNone(self.client.last_crs)
        self.assertTrue(str(self.client.last_crs["function_id"]).startswith("1bfae6a6"))
        self.assertTrue(str(self.client.last_crs["operation_id"]).startswith("1bfae6a6"))

    def test_insdsp_failure_should_try_gendsp_for_403_404(self):
        self.assertTrue(
            FEAMBusinessError.insdsp_failure_should_try_gendsp(
                FEAMBusinessError("msg", http_status=403)
            )
        )
        self.assertTrue(
            FEAMBusinessError.insdsp_failure_should_try_gendsp(
                FEAMBusinessError("msg", http_status=404)
            )
        )
        self.assertFalse(
            FEAMBusinessError.insdsp_failure_should_try_gendsp(
                FEAMBusinessError("msg", http_status=500)
            )
        )

    def test_http_status_from_nested_problem_detail(self):
        nested = '{"type":"https://tools.ietf.org/html/rfc9110#section-15.5.4","status":403}'
        problem = {
            "title": "Forbidden",
            "status": 403,
            "detail": nested,
        }
        self.assertEqual(_http_status_from_problem_details(problem), 403)

    def test_dspfile_json_for_id_from_list_body_matches_uuid(self):
        sample = {
            "status": "ok",
            "responseJson": json.dumps(
                [
                    {"dspFile": {"doss-dsp": {"uuid": "bbae8107-3deb-599c-909a-bb60ab37aae1", "x": 1}}},
                    {"dspFile": {"doss-dsp": {"uuid": "other"}}},
                ]
            ),
        }
        hit = self.service._dspfile_json_for_id_from_list_body(
            sample,
            "bbae8107-3deb-599c-909a-bb60ab37aae1",
            operation_name="test_list",
        )
        self.assertIsNotNone(hit)
        parsed = json.loads(hit)
        self.assertEqual(parsed["doss-dsp"]["uuid"], "bbae8107-3deb-599c-909a-bb60ab37aae1")

    def test_get_gendsp_by_id_uses_gen_read_operation(self):
        self.service._catalog_cache = {"timestamp": time.time(), "data": None}
        self.service.refresh_catalog()
        self.client.last_crs = None
        original_crs = self.client.call_resource_server

        def capture_crs(**kwargs):
            self.client.last_crs = kwargs
            return original_crs(**kwargs)

        self.client.call_resource_server = capture_crs
        self.service.get_gendsp_by_id(dsp_id="abc", version="1.0.0", pilot_id="CERTH")
        self.assertIsNotNone(self.client.last_crs)
        self.assertIn("4637-487c-a71a-9cba257304af", str(self.client.last_crs["operation_id"]))
        self.assertTrue(str(self.client.last_crs["function_id"]).startswith("1bfae6a6"))

    def test_legacy_resolve_uses_first_catalog_function_for_suffix(self):
        os.environ["FEAM_OPERATION_RESOLVE_MODE"] = "legacy_catalog_first_match"
        legacy_service = FEAMService(self.client, self.db)
        legacy_service._catalog_cache = {"timestamp": time.time(), "data": None}
        legacy_service.refresh_catalog()
        self.client.last_crs = None
        original_crs = self.client.call_resource_server

        def capture_crs(**kwargs):
            self.client.last_crs = kwargs
            return original_crs(**kwargs)

        self.client.call_resource_server = capture_crs
        try:
            legacy_service.get_insdsp_by_id(dsp_id="abc", version="1.0.0", pilot_id="CERTH")
            self.assertIsNotNone(self.client.last_crs)
            self.assertTrue(str(self.client.last_crs["function_id"]).startswith("2bfae6a6"))
        finally:
            self.client.call_resource_server = original_crs

    def test_extract_gendsp_id_from_combined_insdsp_response(self):
        payload = {
            "genericDsp": {
                "dspFile": {
                    "doss-dsp": {
                        "uuid": "8609d843-3ba5-4eb1-a010-cdff3aca270f",
                    }
                }
            },
            "instanceDsp": {
                "dspFile": {
                    "doss-dsp": {
                        "uuid": "feb87ebb-d5cb-5c8d-9e36-a947a8e813b5",
                        "metadata": {
                            "links": [
                                {
                                    "href": "8609d843-3ba5-4eb1-a010-cdff3aca270f",
                                    "rel": "Generic DSP",
                                }
                            ]
                        },
                    }
                }
            },
        }
        self.assertEqual(
            _extract_gendsp_id_from_insdsp_payload(payload),
            "8609d843-3ba5-4eb1-a010-cdff3aca270f",
        )

    def test_fetch_gendsp_from_idsp_logs_operation_steps(self):
        self.service.fetch_gendsp_payload_from_idsp_id("abc", correlation_id="corr-1")
        step_names = [log.get("step_name") for log in self.db.logs if log.get("event_type") == "feam_execution"]
        self.assertIn("callResourceServer_attempt_1", step_names)

    def test_fetch_gendsp_from_idsp_uses_embedded_generic_dsp(self):
        original_ins = self.service.get_insdsp_by_id
        original_gen = self.service.get_gendsp_by_id
        try:
            def ok_ins(*args, **kwargs):
                return {
                    "status": "ok",
                    "responseJson": json.dumps(
                        {
                            "genericDsp": {
                                "dspFile": {
                                    "doss-dsp": {"uuid": "gen-embedded", "title": "embedded"},
                                }
                            },
                            "instanceDsp": {
                                "dspFile": {
                                    "doss-dsp": {"uuid": "ins-1"},
                                }
                            },
                        }
                    ),
                }

            def should_not_call_gen(*args, **kwargs):
                raise AssertionError("get_gendsp_by_id must not be called when genericDsp is embedded")

            self.service.get_insdsp_by_id = ok_ins
            self.service.get_gendsp_by_id = should_not_call_gen

            payload = self.service.fetch_gendsp_payload_from_idsp_id("ins-1")
            self.assertIsNotNone(payload)
            parsed = json.loads(payload)
            self.assertEqual(parsed["doss-dsp"]["uuid"], "gen-embedded")
        finally:
            self.service.get_insdsp_by_id = original_ins
            self.service.get_gendsp_by_id = original_gen

    def test_fetch_gendsp_from_idsp_resolves_via_insdsp_then_gendsp(self):
        original_ins = self.service.get_insdsp_by_id
        original_gen = self.service.get_gendsp_by_id
        try:
            def ok_ins(*args, **kwargs):
                return {
                    "status": "ok",
                    "responseJson": json.dumps(
                        {
                            "instanceDsp": {
                                "dspFile": {
                                    "doss-dsp": {
                                        "uuid": "ins-1",
                                        "metadata": {
                                            "links": [
                                                {"href": "gen-1", "rel": "Generic DSP"},
                                            ]
                                        },
                                    }
                                }
                            },
                        }
                    ),
                }

            def ok_gen(*args, **kwargs):
                return {
                    "status": "ok",
                    "responseJson": json.dumps(
                        {
                            "signature": "sig",
                            "certificate": "cert",
                            "dspFile": {"doss-dsp": {"uuid": "gen-1", "title": "generic"}},
                        }
                    ),
                }

            self.service.get_insdsp_by_id = ok_ins
            self.service.get_gendsp_by_id = ok_gen

            payload = self.service.fetch_gendsp_payload_from_idsp_id("ins-1", correlation_id="corr-idsp")
            self.assertIsNotNone(payload)
            parsed = json.loads(payload)
            self.assertEqual(parsed["doss-dsp"]["uuid"], "gen-1")
        finally:
            self.service.get_insdsp_by_id = original_ins
            self.service.get_gendsp_by_id = original_gen

    def test_fetch_gendsp_from_idsp_returns_none_without_generic_reference(self):
        original_ins = self.service.get_insdsp_by_id
        try:
            def empty_ins(*args, **kwargs):
                return {"status": "ok", "responseJson": json.dumps({"instanceDsp": {}})}

            self.service.get_insdsp_by_id = empty_ins
            payload = self.service.fetch_gendsp_payload_from_idsp_id("ins-1")
            self.assertIsNone(payload)
        finally:
            self.service.get_insdsp_by_id = original_ins

    def test_get_catalog_uses_cooldown_after_failed_refresh(self):
        class FailingCatalogClient(DummyFEAMClient):
            def __init__(self):
                super().__init__()
                self.calls = 0

            def get_functions_own(self):
                self.calls += 1
                return {
                    "ok": False,
                    "status_code": 503,
                    "body": {},
                    "raw_text": "",
                    "error": "unavailable",
                    "json_parse_error": None,
                    "attempts": [
                        {"attempt": 1, "elapsed_ms": 1.0, "status_code": 503, "ok": False, "error": "unavailable"},
                    ],
                }

        failing_service = FEAMService(FailingCatalogClient(), DummyDB())
        with self.assertRaises(RuntimeError):
            failing_service.get_catalog()
        with self.assertRaises(RuntimeError):
            failing_service.get_catalog()
        self.assertEqual(failing_service.feam_client.calls, 1)


if __name__ == "__main__":
    unittest.main()
