# services/feam_service.py
"""
Service for handling FEAM-related logic.
Centralizes FEAM operations in a single internal service.
"""
from typing import Optional, Dict, Any, List, TYPE_CHECKING
import logging
import json
import os
import threading
import time

if TYPE_CHECKING:
    from clients.feam_client import FEAMClient

class FEAMBusinessError(RuntimeError):
    """Raised when FEAM returns an application-level error payload."""

    def __init__(self, message: str, *, http_status: Optional[int] = None):
        super().__init__(message)
        self.http_status = http_status

    @staticmethod
    def insdsp_failure_should_try_gendsp(exc: BaseException) -> bool:
        """403/404 on Instance-DSP often means the id is generic or access is denied; try GenDSP read."""
        if isinstance(exc, FEAMBusinessError) and exc.http_status in (403, 404):
            return True
        msg = str(exc)
        if "status=403" in msg or "status=404" in msg:
            return True
        if "title=Forbidden" in msg and "403" in msg:
            return True
        if "title=Not Found" in msg and "404" in msg:
            return True
        return False


def _http_status_from_problem_details(problem: Optional[Dict[str, Any]]) -> Optional[int]:
    """RFC7807 status on the problem or nested JSON inside `detail` (DSPP sometimes double-wraps)."""
    if not isinstance(problem, dict):
        return None
    try:
        code = int(problem.get("status"))
        if code >= 400:
            return code
    except (TypeError, ValueError):
        pass
    detail = problem.get("detail")
    if isinstance(detail, str):
        try:
            inner = json.loads(detail)
        except Exception:
            return None
        if isinstance(inner, dict):
            try:
                code = int(inner.get("status"))
                if code >= 400:
                    return code
            except (TypeError, ValueError):
                pass
    return None


def _feam_response_json_as_str(response_json: Any) -> Optional[str]:
    if response_json is None:
        return None
    if isinstance(response_json, str):
        return response_json
    try:
        return json.dumps(response_json)
    except Exception:
        return None


def _parse_feam_response_json(body: Dict[str, Any]) -> Any:
    if not isinstance(body, dict) or str(body.get("status", "")).lower() != "ok":
        return None
    response_json = body.get("responseJson")
    if response_json is None:
        return None
    if isinstance(response_json, str):
        try:
            return json.loads(response_json)
        except json.JSONDecodeError:
            return None
    return response_json


def _generic_dsp_link_rels() -> set:
    raw = os.getenv("GENERIC_DSP_REL", "Generic DSP").strip()
    if not raw:
        return {"Generic DSP"}
    return {rel.strip() for rel in raw.split(",") if rel.strip()}


def _is_generic_dsp_link(link: Dict[str, Any]) -> bool:
    rel = str(link.get("rel") or "").strip()
    return rel in _generic_dsp_link_rels()


def _doss_dsp_uuid(dsp_file: Any) -> Optional[str]:
    if not isinstance(dsp_file, dict):
        return None
    doss = dsp_file.get("doss-dsp")
    if not isinstance(doss, dict):
        doss = dsp_file if "local-definitions" in dsp_file and "metadata" in dsp_file else None
    if not isinstance(doss, dict):
        return None
    uid = doss.get("uuid")
    if uid is None:
        return None
    return str(uid).strip()


def _doss_dsp_metadata_version(dsp_file: Any) -> Optional[str]:
    if not isinstance(dsp_file, dict):
        return None
    doss = dsp_file.get("doss-dsp")
    if not isinstance(doss, dict):
        return None
    version = (doss.get("metadata") or {}).get("version")
    if version is None:
        return None
    text = str(version).strip()
    return text or None


def _extract_gendsp_id_from_insdsp_payload(insdsp_payload: Any) -> Optional[str]:
    """
    Extracts the generic DSP UUID from a FEAM InsDSP read response.
    Supports the combined {genericDsp, instanceDsp} envelope returned by DSPP.
    """
    if not isinstance(insdsp_payload, dict):
        return None

    generic = insdsp_payload.get("genericDsp")
    if isinstance(generic, dict):
        uid = _doss_dsp_uuid(generic.get("dspFile"))
        if uid:
            return uid

    instance = insdsp_payload.get("instanceDsp")
    if isinstance(instance, dict):
        dsp_file = instance.get("dspFile")
        if isinstance(dsp_file, dict):
            doss = dsp_file.get("doss-dsp")
            if isinstance(doss, dict):
                for link in (doss.get("metadata") or {}).get("links") or []:
                    if isinstance(link, dict) and _is_generic_dsp_link(link):
                        href = str(link.get("href") or "").strip()
                        if href:
                            return href

    return None


def _extract_gendsp_version_from_insdsp_payload(insdsp_payload: Any) -> Optional[str]:
    """Reads GenDSP semantic version from genericDsp metadata when present in InsDSP response."""
    if not isinstance(insdsp_payload, dict):
        return None
    generic = insdsp_payload.get("genericDsp")
    if isinstance(generic, dict):
        version = _doss_dsp_metadata_version(generic.get("dspFile"))
        if version:
            return version
    return None


def _dspfile_json_from_gendsp_payload(gendsp_payload: Any) -> Optional[str]:
    """Normalizes a GenDSP FEAM payload to a dspFile JSON string."""
    if not isinstance(gendsp_payload, dict):
        return None
    dsp_file = gendsp_payload.get("dspFile")
    if isinstance(dsp_file, dict):
        return json.dumps(dsp_file)
    if "doss-dsp" in gendsp_payload:
        return json.dumps(gendsp_payload)
    return None


def _dspfile_json_from_insdsp_payload(insdsp_payload: Any) -> Optional[str]:
    """Returns embedded genericDsp dspFile when the InsDSP read already includes it."""
    if not isinstance(insdsp_payload, dict):
        return None
    generic = insdsp_payload.get("genericDsp")
    if isinstance(generic, dict):
        return _dspfile_json_from_gendsp_payload(generic)
    return None


def _is_infrastructure_failure(response: Dict[str, Any]) -> bool:
    if response.get("ok"):
        return False
    status = response.get("status_code")
    if status is None:
        return True
    return status == 408 or status >= 500


class FEAMService:
    """
    Service for FEAM-related operations.
    """
    _FORBIDDEN_ENDPOINTS = {"init", "register", "activate"}
    # Primer fragmento del UUID FEAM (DSPP-BME). Todas las operaciones callResourceServer
    # se resuelven contra funciones de este servidor aunque el catálogo liste otros pilotos.
    _FEAM_FORCED_SERVER_PREFIX = "1bfae6a6"

    def __init__(self, feam_client: "FEAMClient", db=None):
        """
        Args:
            feam_client: Client for communicating with FEAM
        """
        self.feam_client = feam_client
        self.db = db
        self._catalog_cache: Dict[str, Any] = {"timestamp": 0.0, "data": None}
        self._catalog_ttl_seconds = 60
        self._catalog_last_error_at = 0.0
        self._catalog_last_error: Optional[str] = None
        self._catalog_retry_cooldown_seconds = self._parse_int_env(
            "FEAM_CATALOG_RETRY_COOLDOWN_SECONDS",
            default=60,
            minimum=1,
        )
        self._operation_resolve_mode = self._parse_operation_resolve_mode()
        self._sync_interval_seconds = 60
        self._sync_stop_event = threading.Event()
        self._sync_thread = None

    @staticmethod
    def _parse_int_env(env_name: str, *, default: int, minimum: int) -> int:
        raw_value = os.getenv(env_name)
        if raw_value is None:
            return default
        try:
            return max(minimum, int(raw_value))
        except ValueError:
            logging.warning(
                "Invalid %s='%s'. Falling back to default %s.",
                env_name,
                raw_value,
                default,
            )
            return default

    @staticmethod
    def _parse_operation_resolve_mode() -> str:
        raw_value = str(os.getenv("FEAM_OPERATION_RESOLVE_MODE", "forced_prefix")).strip().lower()
        if raw_value in {"legacy_catalog_first_match", "legacy", "catalog_first"}:
            return "legacy_catalog_first_match"
        if raw_value in {"forced_prefix", "strict", "bme_only"}:
            return "forced_prefix"
        logging.warning(
            "Unknown FEAM_OPERATION_RESOLVE_MODE='%s'. Falling back to 'forced_prefix'.",
            raw_value,
        )
        return "forced_prefix"
    
    def prepare(self) -> None:
        """
        Prepares FEAM client state using only allowed endpoints.
        """
        # /init is explicitly forbidden by policy. Keep allowed maintenance only.
        # self.feam_client.stop_forget_pin_timer()
        logging.info("FEAM preparation completed (init/register/activate are blocked by policy)")
    
    def check_pin(self, pin: int = 1234) -> Optional[dict]:
        """
        Checks a PIN in FEAM.
        Equivalent to FEAMcheckPIN() from the original code.
        
        Args:
            pin: PIN to check (default: 1234)
            
        Returns:
            dict with response or None if error
        """
        return self.feam_client.check_pin(pin)

    def _extract_body(self, normalized_response: Dict[str, Any]) -> Dict[str, Any]:
        body = normalized_response.get("body")
        if isinstance(body, dict):
            return body
        return {"text": normalized_response.get("raw_text", "")}

    def _extract_problem_details(self, payload: Any) -> Optional[Dict[str, Any]]:
        """
        Detects RFC7807-like payloads returned by FEAM or downstream APIs.
        """
        if not isinstance(payload, dict):
            return None
        if "title" in payload and "status" in payload:
            status_value = payload.get("status")
            try:
                numeric_status = int(status_value)
            except (TypeError, ValueError):
                numeric_status = None
            if numeric_status is None or numeric_status >= 400:
                return payload
        return None

    def _raise_if_business_error(self, body: Any, *, operation_name: str) -> None:
        """
        Raises FEAMBusinessError when FEAM answers with business-level errors despite HTTP 200.
        """
        if not isinstance(body, dict):
            return

        # FEAM style error envelope: {"status":"error", ...}
        if str(body.get("status", "")).lower() == "error":
            raise FEAMBusinessError(
                f"{operation_name} failed with FEAM status=error: {body.get('error') or body}"
            )

        # FEAM/Downstream problem details directly in body.
        problem = self._extract_problem_details(body)
        if problem is not None:
            raise FEAMBusinessError(
                f"{operation_name} failed with FEAM problem details: "
                f"title={problem.get('title')} status={problem.get('status')} detail={problem.get('detail')}",
                http_status=_http_status_from_problem_details(problem),
            )

        # Wrapped result where responseJson itself contains a problem-details JSON string/object.
        response_json = body.get("responseJson")
        parsed_response_json = None
        if isinstance(response_json, str):
            try:
                parsed_response_json = json.loads(response_json)
            except Exception:
                parsed_response_json = None
        elif isinstance(response_json, dict):
            parsed_response_json = response_json

        problem = self._extract_problem_details(parsed_response_json)
        if problem is not None:
            raise FEAMBusinessError(
                f"{operation_name} failed in responseJson: "
                f"title={problem.get('title')} status={problem.get('status')} detail={problem.get('detail')}",
                http_status=_http_status_from_problem_details(problem),
            )

    def _record_execution(
        self,
        *,
        device_id: Optional[str] = None,
        pilot_id: Optional[str],
        function_id: Optional[str],
        operation_id: Optional[str],
        endpoint: str,
        result: str,
        elapsed_ms: float,
        correlation_id: Optional[str] = None,
        request_preview_data: Optional[Dict[str, Any]] = None,
        response_status: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        if self.db is None:
            return
        request_payload = {
            "pilotId": pilot_id,
            "functionId": function_id,
            "operationId": operation_id,
            "endpoint": endpoint,
        }
        if request_preview_data:
            request_payload.update(request_preview_data)
        request_preview = json.dumps(request_payload)
        self.db.createPolicyExecutionLog(
            device_id=device_id,
            policy_id=None,
            policy_name=f"feam:{endpoint}",
            profile_id=None,
            run_mode="feam-internal",
            result=result,
            is_test=False,
            event_type="feam_execution",
            correlation_id=correlation_id,
            step_name=endpoint,
            elapsed_ms=elapsed_ms,
            request_preview=request_preview,
            response_status=response_status,
            response_excerpt=None,
            error_message=error_message,
            requested_by="system",
        )

    def _maybe_notify_admins_feam_unavailable(self, *, endpoint: str, response: Dict[str, Any]) -> None:
        if not _is_infrastructure_failure(response) or self.db is None:
            return
        try:
            from services.notifications import feam_health

            feam_health.record_infrastructure_failure(
                endpoint=endpoint,
                error_message=str(response.get("error") or "unknown error"),
                status_code=response.get("status_code"),
                db=self.db,
            )
        except Exception as exc:
            logging.warning(
                "Failed to record FEAM unavailability notification state (endpoint=%s): %s",
                endpoint,
                exc,
                exc_info=True,
            )

    def _on_feam_infrastructure_recovered(self, endpoint: str) -> None:
        try:
            from services.notifications import feam_health

            feam_health.record_infrastructure_success(endpoint)
        except Exception as exc:
            logging.warning(
                "Failed to record FEAM infrastructure recovery (endpoint=%s): %s",
                endpoint,
                exc,
                exc_info=True,
            )

    def execute_operation(
        self,
        function_id: str,
        operation_id: str,
        extra_values: Optional[List[str]] = None,
        pilot_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        operation_name: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        # FEAM policy (best-effort): try checkPin before callResourceServer, but do not block if it fails.
        pin_start = time.perf_counter()
        pin_response = self.check_pin()
        pin_elapsed_ms = (time.perf_counter() - pin_start) * 1000.0
        pin_ok = bool(pin_response) and (
            not isinstance(pin_response, dict) or pin_response.get("status") in (None, "ok")
        )
        self._record_execution(
            device_id=device_id,
            pilot_id=pilot_id,
            function_id=None,
            operation_id=None,
            endpoint="checkPin",
            result="completed" if pin_ok else "failed",
            elapsed_ms=pin_elapsed_ms,
            correlation_id=correlation_id,
            request_preview_data={"operationName": operation_name},
            error_message=None if pin_ok else f"checkPin response={pin_response}",
        )
        if not pin_response or (isinstance(pin_response, dict) and pin_response.get("status") not in (None, "ok")):
            logging.warning(
                "FEAM checkPin failed before callResourceServer; continuing anyway. response=%s",
                pin_response,
            )

        start = time.perf_counter()
        response = self.feam_client.call_resource_server(
            function_id=function_id,
            operation_id=operation_id,
            extra_values=extra_values,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        if not response.get("ok"):
            for attempt in response.get("attempts", []):
                attempt_num = attempt.get("attempt")
                self._record_execution(
                    device_id=device_id,
                    pilot_id=pilot_id,
                    function_id=function_id,
                    operation_id=operation_id,
                    endpoint=f"callResourceServer_attempt_{attempt_num}",
                    result="failed",
                    elapsed_ms=float(attempt.get("elapsed_ms") or 0.0),
                    correlation_id=correlation_id,
                    request_preview_data={
                        "attempt": attempt_num,
                        "operationName": operation_name,
                    },
                    response_status=attempt.get("status_code"),
                    error_message=attempt.get("error"),
                )
            self._record_execution(
                device_id=device_id,
                pilot_id=pilot_id,
                function_id=function_id,
                operation_id=operation_id,
                endpoint="callResourceServer",
                result="failed",
                elapsed_ms=elapsed_ms,
                correlation_id=correlation_id,
                request_preview_data={"operationName": operation_name},
                response_status=response.get("status_code"),
                error_message=response.get("error"),
            )
            self._maybe_notify_admins_feam_unavailable(endpoint="callResourceServer", response=response)
            raise RuntimeError(f"FEAM callResourceServer failed: {response.get('error')}")
        for attempt in response.get("attempts", []):
            attempt_num = attempt.get("attempt")
            self._record_execution(
                device_id=device_id,
                pilot_id=pilot_id,
                function_id=function_id,
                operation_id=operation_id,
                endpoint=f"callResourceServer_attempt_{attempt_num}",
                result="completed" if bool(attempt.get("ok")) else "failed",
                elapsed_ms=float(attempt.get("elapsed_ms") or 0.0),
                correlation_id=correlation_id,
                request_preview_data={
                    "attempt": attempt_num,
                    "operationName": operation_name,
                },
                response_status=attempt.get("status_code"),
                error_message=attempt.get("error"),
            )
        self._record_execution(
            device_id=device_id,
            pilot_id=pilot_id,
            function_id=function_id,
            operation_id=operation_id,
            endpoint="callResourceServer",
            result="completed",
            elapsed_ms=elapsed_ms,
            correlation_id=correlation_id,
            request_preview_data={"operationName": operation_name},
            response_status=response.get("status_code"),
        )
        self._on_feam_infrastructure_recovered("callResourceServer")
        body = self._extract_body(response)
        self._raise_if_business_error(body, operation_name="callResourceServer")
        return body

    def refresh_catalog(self) -> Dict[str, Any]:
        # FEAM policy (best-effort): try checkPin before getFunctionsOwn, but do not block if it fails.
        pin_start = time.perf_counter()
        pin_response = self.check_pin()
        pin_elapsed_ms = (time.perf_counter() - pin_start) * 1000.0
        pin_ok = bool(pin_response) and (
            not isinstance(pin_response, dict) or pin_response.get("status") in (None, "ok")
        )
        self._record_execution(
            pilot_id=None,
            function_id=None,
            operation_id=None,
            endpoint="checkPin",
            result="completed" if pin_ok else "failed",
            elapsed_ms=pin_elapsed_ms,
            request_preview_data={"operationName": "getFunctionsOwn"},
            error_message=None if pin_ok else f"checkPin response={pin_response}",
        )
        if not pin_response or (isinstance(pin_response, dict) and pin_response.get("status") not in (None, "ok")):
            logging.warning(
                "FEAM checkPin failed before getFunctionsOwn; continuing anyway. response=%s",
                pin_response,
            )

        start = time.perf_counter()
        response = self.feam_client.get_functions_own()
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        for attempt in response.get("attempts", []):
            attempt_num = attempt.get("attempt")
            self._record_execution(
                pilot_id=None,
                function_id=None,
                operation_id=None,
                endpoint=f"getFunctionsOwn_attempt_{attempt_num}",
                result="completed" if bool(attempt.get("ok")) else "failed",
                elapsed_ms=float(attempt.get("elapsed_ms") or 0.0),
                request_preview_data={"attempt": attempt_num},
                response_status=attempt.get("status_code"),
                error_message=attempt.get("error"),
            )
        if not response.get("ok"):
            self._catalog_last_error_at = time.time()
            self._catalog_last_error = str(response.get("error") or "getFunctionsOwn failed")
            self._record_execution(
                pilot_id=None,
                function_id=None,
                operation_id=None,
                endpoint="getFunctionsOwn",
                result="failed",
                elapsed_ms=elapsed_ms,
                response_status=response.get("status_code"),
                error_message=response.get("error"),
            )
            self._maybe_notify_admins_feam_unavailable(endpoint="getFunctionsOwn", response=response)
            raise RuntimeError(f"FEAM getFunctionsOwn failed: {response.get('error')}")
        body = self._extract_body(response)
        try:
            self._raise_if_business_error(body, operation_name="getFunctionsOwn")
        except Exception as exc:
            self._catalog_last_error_at = time.time()
            self._catalog_last_error = str(exc)
            raise
        self._catalog_cache = {
            "timestamp": time.time(),
            "data": body,
        }
        self._catalog_last_error_at = 0.0
        self._catalog_last_error = None
        self._record_execution(
            pilot_id=None,
            function_id=None,
            operation_id=None,
            endpoint="getFunctionsOwn",
            result="completed",
            elapsed_ms=elapsed_ms,
            response_status=response.get("status_code"),
        )
        self._on_feam_infrastructure_recovered("getFunctionsOwn")
        if self.db is not None:
            self.db.upsertFeamCatalogSnapshot(body)
        return body

    def get_catalog(self, force_refresh: bool = False) -> Dict[str, Any]:
        now = time.time()
        if force_refresh or self._catalog_cache["data"] is None:
            if (
                not force_refresh
                and self._catalog_cache["data"] is None
                and self._catalog_last_error_at > 0
                and (now - self._catalog_last_error_at) < self._catalog_retry_cooldown_seconds
            ):
                raise RuntimeError(
                    "FEAM catalog refresh is in cooldown after previous error: "
                    f"{self._catalog_last_error or 'unknown error'}"
                )
            return self.refresh_catalog()
        if (now - self._catalog_cache["timestamp"]) > self._catalog_ttl_seconds:
            return self.refresh_catalog()
        return self._catalog_cache["data"]

    def resolve_pilot_from_function_id(self, function_id: str) -> Optional[str]:
        if not function_id or len(function_id) < 8:
            return None
        prefix = function_id.split("-", 1)[0].lower()
        pilot_map = {
            "0bfae6a6": "ATOS",
            "1bfae6a6": "BME",
            "2bfae6a6": "CERTH",
            "3bfae6a6": "TECNALIA",
            "dbfae6a6": "DEV",
        }
        return pilot_map.get(prefix, prefix)

    def resolve_pilot_from_alias(self, alias: str) -> Optional[str]:
        if not alias:
            return None
        normalized = alias.strip().upper()
        if "TECNALIA" in normalized:
            return "TECNALIA"
        if "CERTH" in normalized:
            return "CERTH"
        if "BME" in normalized:
            return "BME"
        if "ATOS" in normalized:
            return "ATOS"
        if "DEV" in normalized or "LOCALHOST" in normalized:
            return "DEV"
        return None

    def resolve_pilot_from_dsp(self, dsp_json: Any) -> Optional[str]:
        try:
            dsp_data = json.loads(dsp_json) if isinstance(dsp_json, str) else dsp_json
        except Exception:
            return None
        components = (
            dsp_data.get("dspFile", {})
            .get("doss-dsp", {})
            .get("local-definitions", {})
            .get("components", [])
        )
        for component in components:
            links = component.get("links", [])
            for link in links:
                href = str(link.get("href", "")).lower()
                if "tecnalia" in href:
                    return "TECNALIA"
                if "certh" in href:
                    return "CERTH"
                if "bme" in href:
                    return "BME"
                if "atos" in href:
                    return "ATOS"
        return None

    def _resolve_operation_forced_prefix(self, *, operation_suffix: str, pilot_id: Optional[str]) -> Dict[str, str]:
        catalog = self.get_catalog(force_refresh=False)
        functions = catalog.get("functions", []) if isinstance(catalog, dict) else []
        forced_prefix = self._FEAM_FORCED_SERVER_PREFIX.lower()
        for function in functions:
            function_id = function.get("id")
            if not function_id:
                continue
            fn_prefix = str(function_id).split("-", 1)[0].lower()
            if fn_prefix != forced_prefix:
                continue
            for operation in function.get("operations", []):
                op_id = operation.get("id")
                if op_id and op_id.endswith(operation_suffix):
                    return {"functionId": function_id, "operationId": op_id}
        raise RuntimeError(
            f"FEAM operation not found for suffix {operation_suffix} "
            f"on server prefix {self._FEAM_FORCED_SERVER_PREFIX} (pilot_id hint {pilot_id} is ignored for server choice)"
        )

    def _resolve_operation_legacy_catalog_first_match(
        self, *, operation_suffix: str, pilot_id: Optional[str]
    ) -> Dict[str, str]:
        catalog = self.get_catalog(force_refresh=False)
        functions = catalog.get("functions", []) if isinstance(catalog, dict) else []
        for function in functions:
            function_id = function.get("id")
            if not function_id:
                continue
            for operation in function.get("operations", []):
                op_id = operation.get("id")
                if op_id and op_id.endswith(operation_suffix):
                    logging.info(
                        "FEAM legacy catalog resolution: suffix=%s functionId=%s (pilot_id hint %s)",
                        operation_suffix,
                        function_id,
                        pilot_id,
                    )
                    return {"functionId": function_id, "operationId": op_id}
        raise RuntimeError(
            f"FEAM operation not found for suffix {operation_suffix} in catalog "
            f"(legacy_catalog_first_match; pilot_id hint {pilot_id})"
        )

    def _resolve_operation(self, *, operation_suffix: str, pilot_id: Optional[str]) -> Dict[str, str]:
        if self._operation_resolve_mode == "legacy_catalog_first_match":
            return self._resolve_operation_legacy_catalog_first_match(
                operation_suffix=operation_suffix,
                pilot_id=pilot_id,
            )
        return self._resolve_operation_forced_prefix(
            operation_suffix=operation_suffix,
            pilot_id=pilot_id,
        )

    def get_insdsp_by_id(
        self,
        dsp_id: str,
        version: str = "1.0.0",
        pilot_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        operation = self._resolve_operation(operation_suffix="b492-4267-9ef5-92b15f22a394", pilot_id=pilot_id)
        audit_pilot = self.resolve_pilot_from_function_id(operation["functionId"]) or pilot_id
        payload = [json.dumps({"id": dsp_id, "version": version})]
        body = self.execute_operation(
            function_id=operation["functionId"],
            operation_id=operation["operationId"],
            extra_values=payload,
            pilot_id=audit_pilot,
            correlation_id=correlation_id,
            operation_name="get_insdsp_by_id",
            device_id=device_id,
        )
        self._raise_if_business_error(
            body,
            operation_name=f"get_insdsp_by_id(dsp_id={dsp_id}, version={version})",
        )
        return body

    def get_gendsp_by_id(
        self,
        dsp_id: str,
        version: Optional[str] = "1.0.0",
        pilot_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        operation = self._resolve_operation(operation_suffix="4637-487c-a71a-9cba257304af", pilot_id=pilot_id)
        audit_pilot = self.resolve_pilot_from_function_id(operation["functionId"]) or pilot_id
        request_obj: Dict[str, str] = {"id": dsp_id}
        if version:
            request_obj["version"] = version
        payload = [json.dumps(request_obj)]
        body = self.execute_operation(
            function_id=operation["functionId"],
            operation_id=operation["operationId"],
            extra_values=payload,
            pilot_id=audit_pilot,
            correlation_id=correlation_id,
            operation_name="get_gendsp_by_id",
            device_id=device_id,
        )
        version_label = version or "latest"
        self._raise_if_business_error(
            body,
            operation_name=f"get_gendsp_by_id(dsp_id={dsp_id}, version={version_label})",
        )
        return body

    def _dspfile_json_for_id_from_list_body(
        self,
        body: Dict[str, Any],
        dsp_id: str,
        *,
        operation_name: str,
    ) -> Optional[str]:
        """
        Parses list InsDSP / GenDSP responseJson (array of {signature, certificate, dspFile}).
        Returns JSON string of dspFile (wraps doss-dsp for MUDService).
        """
        self._raise_if_business_error(body, operation_name=operation_name)
        if not isinstance(body, dict) or str(body.get("status", "")).lower() != "ok":
            return None
        rj = body.get("responseJson")
        if isinstance(rj, str):
            try:
                items = json.loads(rj)
            except json.JSONDecodeError:
                return None
        elif isinstance(rj, list):
            items = rj
        else:
            return None
        if not isinstance(items, list):
            return None
        target = str(dsp_id).strip().lower()
        for item in items:
            if not isinstance(item, dict):
                continue
            dsp_file = item.get("dspFile")
            if not isinstance(dsp_file, dict):
                continue
            doss = dsp_file.get("doss-dsp")
            if isinstance(doss, dict):
                uid = doss.get("uuid")
                if uid is not None and str(uid).strip().lower() == target:
                    return json.dumps(dsp_file)
        return None

    def _find_dspfile_json_via_active_lists(
        self,
        dsp_id: str,
        pilot_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> Optional[str]:
        try:
            start = time.perf_counter()
            body = self.list_gendsp(
                {"status": "Active"},
                pilot_id=pilot_id,
                correlation_id=correlation_id,
                device_id=device_id,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            hit = self._dspfile_json_for_id_from_list_body(
                body,
                dsp_id,
                operation_name="list_gendsp(Active)",
            )
            self._record_execution(
                device_id=device_id,
                pilot_id=pilot_id,
                function_id=None,
                operation_id=None,
                endpoint="list_gendsp_active",
                result="completed",
                elapsed_ms=elapsed_ms,
                correlation_id=correlation_id,
            )
            if hit:
                logging.info("FEAM: matched dsp_id=%s in active GenDSP list", dsp_id)
                return hit
        except Exception as exc:
            self._record_execution(
                device_id=device_id,
                pilot_id=pilot_id,
                function_id=None,
                operation_id=None,
                endpoint="list_gendsp_active",
                result="failed",
                elapsed_ms=0.0,
                correlation_id=correlation_id,
                error_message=str(exc),
            )
            logging.warning("FEAM list GenDSP (Active) failed for dsp_id=%s: %s", dsp_id, exc)
        try:
            start = time.perf_counter()
            body = self.list_insdsp(
                {"status": "Active"},
                pilot_id=pilot_id,
                correlation_id=correlation_id,
                device_id=device_id,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            hit = self._dspfile_json_for_id_from_list_body(
                body,
                dsp_id,
                operation_name="list_insdsp(Active)",
            )
            self._record_execution(
                device_id=device_id,
                pilot_id=pilot_id,
                function_id=None,
                operation_id=None,
                endpoint="list_insdsp_active",
                result="completed",
                elapsed_ms=elapsed_ms,
                correlation_id=correlation_id,
            )
            if hit:
                logging.info("FEAM: matched dsp_id=%s in active InsDSP list", dsp_id)
                return hit
        except Exception as exc:
            self._record_execution(
                device_id=device_id,
                pilot_id=pilot_id,
                function_id=None,
                operation_id=None,
                endpoint="list_insdsp_active",
                result="failed",
                elapsed_ms=0.0,
                correlation_id=correlation_id,
                error_message=str(exc),
            )
            logging.warning("FEAM list InsDSP (Active) failed for dsp_id=%s: %s", dsp_id, exc)
        return None

    def fetch_gendsp_payload_from_idsp_id(
        self,
        idsp_id: str,
        version: str = "1.0.0",
        pilot_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Resolves generic DSP JSON for onboarding from an Instance DSP ID.
        1) Read InsDSP via FEAM.
        2) Extract linked GenDSP UUID from the InsDSP response.
        3) Read GenDSP via FEAM and return its dspFile JSON.
        """
        idsp_id = str(idsp_id).strip()
        if not idsp_id:
            return None

        try:
            ins_start = time.perf_counter()
            ins_body = self.get_insdsp_by_id(
                idsp_id,
                version=version,
                pilot_id=pilot_id,
                correlation_id=correlation_id,
                device_id=device_id,
            )
            self._record_execution(
                device_id=device_id,
                pilot_id=pilot_id,
                function_id=None,
                operation_id=None,
                endpoint="get_insdsp_by_id",
                result="completed",
                elapsed_ms=(time.perf_counter() - ins_start) * 1000.0,
                correlation_id=correlation_id,
            )
        except Exception as exc:
            self._record_execution(
                device_id=device_id,
                pilot_id=pilot_id,
                function_id=None,
                operation_id=None,
                endpoint="get_insdsp_by_id",
                result="failed",
                elapsed_ms=0.0,
                correlation_id=correlation_id,
                error_message=str(exc),
            )
            logging.error("FEAM InsDSP failed for idsp_id=%s: %s", idsp_id, exc)
            return None

        ins_payload = _parse_feam_response_json(ins_body)
        embedded_gendsp = _dspfile_json_from_insdsp_payload(ins_payload)
        if embedded_gendsp:
            logging.info(
                "FEAM: using embedded genericDsp from InsDSP response for idsp_id=%s",
                idsp_id,
            )
            return embedded_gendsp

        gendsp_id = _extract_gendsp_id_from_insdsp_payload(ins_payload)
        if not gendsp_id:
            logging.error(
                "FEAM InsDSP response for idsp_id=%s did not contain a Generic DSP reference",
                idsp_id,
            )
            return None

        gendsp_version = _extract_gendsp_version_from_insdsp_payload(ins_payload)

        logging.info(
            "FEAM: resolved idsp_id=%s -> gendsp_id=%s gendsp_version=%s",
            idsp_id,
            gendsp_id,
            gendsp_version or "(latest)",
        )

        gen_body = self._read_gendsp_by_id_with_version_fallback(
            gendsp_id=gendsp_id,
            version=gendsp_version,
            pilot_id=pilot_id,
            correlation_id=correlation_id,
            device_id=device_id,
            idsp_id=idsp_id,
        )
        if gen_body is None:
            return None

        gen_payload = _parse_feam_response_json(gen_body)
        dspfile_json = _dspfile_json_from_gendsp_payload(gen_payload)
        if not dspfile_json:
            logging.error(
                "FEAM GenDSP response for gendsp_id=%s (from idsp_id=%s) did not contain dspFile",
                gendsp_id,
                idsp_id,
            )
        return dspfile_json

    def _read_gendsp_by_id_with_version_fallback(
        self,
        *,
        gendsp_id: str,
        version: Optional[str],
        pilot_id: Optional[str],
        correlation_id: Optional[str],
        device_id: Optional[str],
        idsp_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Tries GenDSP read by id; prefers explicit version, then latest (no version in payload)."""
        versions_to_try: List[Optional[str]] = []
        if version:
            versions_to_try.append(version)
        versions_to_try.append(None)

        last_exc: Optional[Exception] = None
        for attempt_version in versions_to_try:
            try:
                gen_start = time.perf_counter()
                gen_body = self.get_gendsp_by_id(
                    gendsp_id,
                    version=attempt_version,
                    pilot_id=pilot_id,
                    correlation_id=correlation_id,
                    device_id=device_id,
                )
                self._record_execution(
                    device_id=device_id,
                    pilot_id=pilot_id,
                    function_id=None,
                    operation_id=None,
                    endpoint="get_gendsp_by_id",
                    result="completed",
                    elapsed_ms=(time.perf_counter() - gen_start) * 1000.0,
                    correlation_id=correlation_id,
                )
                if attempt_version is None and version:
                    logging.info(
                        "FEAM: get_gendsp_by_id succeeded without version for gendsp_id=%s (from idsp_id=%s)",
                        gendsp_id,
                        idsp_id,
                    )
                return gen_body
            except Exception as exc:
                last_exc = exc
                self._record_execution(
                    device_id=device_id,
                    pilot_id=pilot_id,
                    function_id=None,
                    operation_id=None,
                    endpoint="get_gendsp_by_id",
                    result="failed",
                    elapsed_ms=0.0,
                    correlation_id=correlation_id,
                    error_message=str(exc),
                )
                msg = str(exc)
                is_forbidden = "403" in msg or "Forbidden" in msg
                if not is_forbidden or attempt_version is None:
                    break
                logging.info(
                    "FEAM: get_gendsp_by_id version=%s failed for gendsp_id=%s, will retry without version",
                    attempt_version,
                    gendsp_id,
                )

        logging.error(
            "FEAM GenDSP failed for gendsp_id=%s (from idsp_id=%s): %s",
            gendsp_id,
            idsp_id,
            last_exc,
        )
        return None

    def list_insdsp(
        self,
        filter_obj: Dict[str, Any],
        pilot_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        operation = self._resolve_operation(operation_suffix="cc5b-44e9-adce-159aee6c0c6d", pilot_id=pilot_id)
        audit_pilot = self.resolve_pilot_from_function_id(operation["functionId"]) or pilot_id
        payload = [json.dumps(filter_obj or {})]
        return self.execute_operation(
            function_id=operation["functionId"],
            operation_id=operation["operationId"],
            extra_values=payload,
            pilot_id=audit_pilot,
            correlation_id=correlation_id,
            operation_name="list_insdsp",
            device_id=device_id,
        )

    def list_gendsp(
        self,
        filter_obj: Dict[str, Any],
        pilot_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        operation = self._resolve_operation(operation_suffix="0539-4440-be7d-ba743f8c4ada", pilot_id=pilot_id)
        audit_pilot = self.resolve_pilot_from_function_id(operation["functionId"]) or pilot_id
        payload = [json.dumps(filter_obj or {})]
        return self.execute_operation(
            function_id=operation["functionId"],
            operation_id=operation["operationId"],
            extra_values=payload,
            pilot_id=audit_pilot,
            correlation_id=correlation_id,
            operation_name="list_gendsp",
            device_id=device_id,
        )

    def list_reports(self, filter_obj: Dict[str, Any], pilot_id: str) -> Dict[str, Any]:
        operation = self._resolve_operation(operation_suffix="ad05-4b4f-a4df-6551238ca72b", pilot_id=pilot_id)
        audit_pilot = self.resolve_pilot_from_function_id(operation["functionId"]) or pilot_id
        payload = [json.dumps(filter_obj or {})]
        return self.execute_operation(
            function_id=operation["functionId"],
            operation_id=operation["operationId"],
            extra_values=payload,
            pilot_id=audit_pilot,
        )

    def sync_pilot_read_models(self, pilot_id: str) -> Dict[str, Any]:
        result = {
            "pilotId": pilot_id,
            "gendsp": None,
            "insdsp": None,
            "reports": None,
            "ok": True,
            "error": None,
        }
        try:
            result["gendsp"] = self.list_gendsp({}, pilot_id=pilot_id)
            result["insdsp"] = self.list_insdsp({}, pilot_id=pilot_id)
            result["reports"] = self.list_reports({}, pilot_id=pilot_id)
            if self.db is not None:
                self.db.upsertFeamPilotSyncState(pilot_id=pilot_id, status="ok", error=None)
        except Exception as exc:
            result["ok"] = False
            result["error"] = str(exc)
            if self.db is not None:
                self.db.upsertFeamPilotSyncState(pilot_id=pilot_id, status="failed", error=str(exc))
        return result

    def sync_all_pilots_read_models(self) -> Dict[str, Any]:
        pilots = ["ATOS", "BME", "CERTH", "TECNALIA", "DEV"]
        sync_results = []
        for pilot in pilots:
            sync_results.append(self.sync_pilot_read_models(pilot))
        return {"results": sync_results}

    def _run_sync_loop(self) -> None:
        while not self._sync_stop_event.is_set():
            try:
                self.sync_all_pilots_read_models()
            except Exception as exc:
                logging.warning("FEAM sync loop iteration failed: %s", exc, exc_info=True)
            self._sync_stop_event.wait(self._sync_interval_seconds)

    def start_sync_jobs(self, interval_seconds: int = 60) -> None:
        self._sync_interval_seconds = max(10, int(interval_seconds or 60))
        if self._sync_thread and self._sync_thread.is_alive():
            return
        self._sync_stop_event.clear()
        self._sync_thread = threading.Thread(target=self._run_sync_loop, name="feam-sync", daemon=True)
        self._sync_thread.start()

    def stop_sync_jobs(self) -> None:
        self._sync_stop_event.set()
    
    def get_gendsp_from_idsp_id(self, idsp_id: str) -> Optional[str]:
        """
        Gets a generic DSP from FEAM using an Instance DSP ID.
        
        Args:
            idsp_id: Instance DSP ID
            
        Returns:
            str: FEAM-like JSON envelope or None if error
        """
        payload = self.fetch_gendsp_payload_from_idsp_id(idsp_id, version="1.0.0", pilot_id=None)
        if not payload:
            return None
        return json.dumps({"status": "ok", "responseJson": payload})
