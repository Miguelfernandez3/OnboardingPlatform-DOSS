"""
Service for enforcing policies using DB-backed configuration.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import time
import json
import logging
import re
import shlex

import requests
import xmltodict

from services.enforcement_context import (
    build_merged_enforcement_context,
    get_bearer_context_key_pair,
    parse_context_spec_options_from_profile,
)
from services.enforcement_secret_manager import EnforcementSecretManager, SecretManagerError
from services.simulated_sdn_service import SimulatedSDNService

_SENSITIVE_KEY_FRAGMENTS: frozenset = frozenset(
    {
        "authorization",
        "proxy-authorization",
        "x-api-key",
        "x-auth-token",
        "apikey",
        "api-key",
        "password",
        "secret",
        "token",
        "bearer",
        "accesstoken",
        "refreshtoken",
        "idtoken",
        "client_secret",
        "set-cookie",
        "cookie",
    }
)
_REDACT = "*****"


PLACEHOLDER_REGEX = re.compile(r"\{\{([a-zA-Z0-9_\-\.]+)\}\}")
logger = logging.getLogger(__name__)


class EnforcementNotConfiguredError(Exception):
    """Raised when enforcement configuration is missing in database."""


class EnforcementValidationError(Exception):
    """Raised when enforcement profile configuration is invalid."""


class EnforcementPrerequisitesError(Exception):
    """Raised when REST enforcement context is missing required values (IP, token, etc.)."""

    def __init__(self, message: str = "Enforcement prerequisites not satisfied", missing: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message)
        self.missing = list(missing or [])


class EnforcementDependencyError(Exception):
    """
    Enforce REST llamó a un servicio dependiente (p. ej. Home Assistant) y respondió con error HTTP.
    El API debe exponer 424 Failed Dependency.
    """

    def __init__(
        self,
        message: str,
        *,
        downstream_url: str = "",
        downstream_status: int = 0,
        response_excerpt: str = "",
        replicable_request: Optional[Dict[str, Any]] = None,
        replicable_curl: str = "",
    ):
        super().__init__(message)
        self.downstream_url = downstream_url
        self.downstream_status = int(downstream_status)
        self.response_excerpt = response_excerpt or ""
        self.replicable_request: Dict[str, Any] = dict(replicable_request) if replicable_request else {}
        self.replicable_curl = replicable_curl or ""


class PolicyEnforcementService:
    """
    Executes policy enforcement actions from MSPL using DB-configured profiles and mappings.
    """

    def __init__(self, db, legacy_enforcer):
        """
        Args:
            db: Database instance
            legacy_enforcer: Callable with signature legacy_enforcer(mspl_xml, device)
        """
        self.db = db
        self.legacy_enforcer = legacy_enforcer
        self.secret_manager = EnforcementSecretManager()
        self.simulated_sdn_service = SimulatedSDNService()

    @staticmethod
    def _safe_preview(value: Any, max_length: int = 500) -> str:
        """Builds a compact preview string for logging."""
        try:
            if isinstance(value, (dict, list)):
                preview = json.dumps(value, ensure_ascii=True)
            else:
                preview = str(value)
        except Exception:
            preview = str(value)

        if len(preview) <= max_length:
            return preview
        remaining = len(preview) - max_length
        return f"{preview[:max_length]}...(truncated {remaining} chars)"

    @staticmethod
    def normalize_key(key: str) -> str:
        """Normalizes a key for tolerant matching."""
        return key.strip().lower().replace("_", "-")

    @staticmethod
    def mspl_xml_to_json(mspl_xml: str) -> Dict[str, Any]:
        """Converts MSPL XML to dict."""
        return xmltodict.parse(mspl_xml)

    @staticmethod
    def mspl_json_to_xml(mspl_json: Dict[str, Any]) -> str:
        """Converts MSPL dict to XML with root tag 'mspl'."""
        if "mspl" in mspl_json:
            payload = mspl_json
        else:
            payload = {"mspl": mspl_json}
        return xmltodict.unparse(payload, pretty=False)

    def _parse_allowed_hosts(self) -> set[str]:
        raw = (self._get_env_value('ENFORCEMENT_ALLOWED_HOSTS') or '').strip()
        if not raw:
            return {'localhost', '127.0.0.1', '::1'}
        hosts: set[str] = set()
        for part in raw.split(','):
            item = part.strip().lower()
            if item:
                hosts.add(item)
        return hosts

    def _is_allow_all_hosts(self, allowed_hosts: set[str]) -> bool:
        """True if ENFORCEMENT_ALLOWED_HOSTS is set to * (allow any domain)."""
        return '*' in allowed_hosts

    @staticmethod
    def _get_env_value(name: str) -> Optional[str]:
        import os
        return os.getenv(name)

    @staticmethod
    def _host_matches_allowed(host: str, allowed_host: str) -> bool:
        if allowed_host.startswith('.'):
            return host.endswith(allowed_host)
        return host == allowed_host

    def validate_endpoint_template(self, endpoint_template: str):
        if not isinstance(endpoint_template, str) or not endpoint_template.strip():
            raise EnforcementValidationError("endpointTemplate is required")
        parsed = urlparse(endpoint_template.strip())
        if parsed.scheme not in {'http', 'https'}:
            raise EnforcementValidationError("endpointTemplate must start with http:// or https://")
        if not parsed.hostname:
            raise EnforcementValidationError("endpointTemplate must include a valid hostname")

        host = parsed.hostname.lower()
        allowed_hosts = self._parse_allowed_hosts()
        if self._is_allow_all_hosts(allowed_hosts):
            return
        if not any(self._host_matches_allowed(host, allowed) for allowed in allowed_hosts):
            raise EnforcementValidationError(
                f"Host '{host}' is not allowed by ENFORCEMENT_ALLOWED_HOSTS"
            )

    def is_configured(self) -> bool:
        active_profiles = self.db.getActiveEnforcementProfiles()
        return len(active_profiles) > 0

    def _parse_json_template(self, raw_value: Any, default_value: Any):
        if raw_value is None:
            return deepcopy(default_value)
        if isinstance(raw_value, (dict, list)):
            return deepcopy(raw_value)
        if isinstance(raw_value, str):
            text = raw_value.strip()
            if not text:
                return deepcopy(default_value)
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return raw_value
        return raw_value

    def _sensitive_key(self, name: str) -> bool:
        k = str(name).lower()
        for frag in _SENSITIVE_KEY_FRAGMENTS:
            if frag in k:
                return True
        return False

    def _redact_sensitive(self, value: Any) -> Any:
        if isinstance(value, dict):
            result: Dict[str, Any] = {}
            for key, item in value.items():
                if self._sensitive_key(key):
                    result[key] = _REDACT
                else:
                    result[key] = self._redact_sensitive(item)
            return result
        if isinstance(value, list):
            return [self._redact_sensitive(item) for item in value]
        if isinstance(value, str) and value[:7].lower() == "bearer ":
            return f"Bearer {_REDACT}"
        return value

    @staticmethod
    def _curl_replication_hint(redacted: Dict[str, Any]) -> str:
        """Línea curl aproximada (secretos ya enmascarados) para reproducir la petición."""
        try:
            m = str(redacted.get("method", "GET") or "GET").strip().upper()
            url = str(redacted.get("url", "") or "").strip()
            if not url:
                return ""
            try:
                timeout_s = int(float(redacted.get("timeout", 10) or 10))
            except (TypeError, ValueError):
                timeout_s = 10
            parts: List[str] = ["curl", "-sS", "-X", m, shlex.quote(url), "--connect-timeout", str(timeout_s)]
            headers = redacted.get("headers")
            if isinstance(headers, dict):
                for hk, hv in headers.items():
                    if hv is None:
                        continue
                    parts.extend(["-H", shlex.quote(f"{hk}: {hv}")])
            j = redacted.get("json")
            d = redacted.get("data")
            if j is not None:
                if not (isinstance(headers, dict) and any(str(x).lower() == "content-type" for x in headers)):
                    parts.extend(["-H", shlex.quote("Content-Type: application/json")])
                body = json.dumps(j, ensure_ascii=True)
                parts.extend(["--data-raw", shlex.quote(body)])
            elif d not in (None, ""):
                parts.extend(["--data-raw", shlex.quote(str(d))])
            return " ".join(parts)
        except Exception as exc:
            logger.debug("curl replication hint failed: %s", exc, exc_info=True)
            return ""

    def _log_execution(
        self,
        *,
        device_id: Optional[str],
        policy_id: Optional[str],
        policy_name: Optional[str],
        profile_id: Optional[int],
        run_mode: str,
        result: str,
        is_test: bool,
        event_type: str = "policy_execution",
        correlation_id: Optional[str] = None,
        step_name: Optional[str] = None,
        elapsed_ms: Optional[float] = None,
        request_preview: Optional[Dict[str, Any]] = None,
        response_status: Optional[int] = None,
        response_excerpt: Optional[str] = None,
        error_message: Optional[str] = None,
        requested_by: Optional[str] = None,
    ):
        payload = {
            'device_id': device_id,
            'policy_id': policy_id,
            'policy_name': policy_name,
            'profile_id': profile_id,
            'run_mode': run_mode,
            'result': result,
            'is_test': is_test,
            'event_type': event_type,
            'correlation_id': correlation_id,
            'step_name': step_name,
            'elapsed_ms': elapsed_ms,
            'request_preview': json.dumps(self._redact_sensitive(request_preview), ensure_ascii=True) if request_preview else None,
            'response_status': response_status,
            'response_excerpt': response_excerpt,
            'error_message': error_message,
            'requested_by': requested_by,
            'executed_at': datetime.now(timezone.utc),
        }
        try:
            return self.db.createPolicyExecutionLog(**payload)
        except Exception as exc:
            logger.error("Could not persist policy execution log: %s", exc, exc_info=True)
            return None

    def record_execution(
        self,
        *,
        device_id: Optional[str],
        policy_id: Optional[str],
        policy_name: Optional[str],
        profile_id: Optional[int],
        result: str,
        run_mode: str = 'execute',
        is_test: bool = False,
        event_type: str = "policy_execution",
        correlation_id: Optional[str] = None,
        step_name: Optional[str] = None,
        elapsed_ms: Optional[float] = None,
        request_preview: Optional[Dict[str, Any]] = None,
        response_status: Optional[int] = None,
        response_excerpt: Optional[str] = None,
        error_message: Optional[str] = None,
        requested_by: Optional[str] = None,
    ):
        self._log_execution(
            device_id=device_id,
            policy_id=policy_id,
            policy_name=policy_name,
            profile_id=profile_id,
            run_mode=run_mode,
            result=result,
            is_test=is_test,
            event_type=event_type,
            correlation_id=correlation_id,
            step_name=step_name,
            elapsed_ms=elapsed_ms,
            request_preview=request_preview,
            response_status=response_status,
            response_excerpt=response_excerpt,
            error_message=error_message,
            requested_by=requested_by,
        )

    def extract_policy_metadata(self, mspl_xml: str) -> Dict[str, Optional[str]]:
        """
        Extracts metadata used for mapping/enforcement decisions.
        """
        try:
            mspl_node, flat_values = self._extract_mspl_and_flat_values(mspl_xml)
        except Exception as exc:
            logger.warning("Could not parse MSPL metadata: %s", exc)
            return {
                "policyType": None,
                "capability": None,
                "enforcementProfile": None,
            }

        policy_type = self._pick_first(
            flat_values,
            ["type", "policy-type", "mspl-type", "policytype"],
        )
        capability = self._pick_first(
            flat_values,
            [
                "capability",
                "configuration-capability",
                "configuration.capability",
                "configuration.capability.name",
                "itresource.configuration.capability",
                "itresource.configuration.capability.name",
            ],
        )
        explicit_profile = self._pick_first(
            flat_values,
            ["enforcement-profile", "profile-id", "execution-profile"],
        )

        if policy_type is None and isinstance(mspl_node, dict):
            raw_type = mspl_node.get("type")
            if isinstance(raw_type, str) and raw_type.strip():
                policy_type = raw_type.strip()
        if capability is None and isinstance(mspl_node, dict):
            capability = self._extract_capability_name(mspl_node)

        logger.debug(
            "MSPL metadata extracted: policyType='%s', capability='%s', explicitProfile='%s'",
            policy_type,
            capability,
            explicit_profile,
        )
        return {
            "policyType": policy_type,
            "capability": capability,
            "enforcementProfile": explicit_profile,
        }

    def enforce_policy(
        self,
        mspl_xml: str,
        device,
        policy_name: Optional[str] = None,
        policy_id: Optional[str] = None,
        *,
        run_mode: str = 'execute',
        is_test: bool = False,
        requested_by: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes enforcement according to DB configured profile.
        """
        device_id = getattr(device, "identifier", "") or ""
        device_ip = getattr(device, "ip", "") or ""
        logger.info(
            "Policy enforcement started: policyName='%s', policyId='%s', deviceId='%s', deviceIp='%s', msplSize=%d",
            policy_name or "",
            policy_id or "",
            device_id,
            device_ip,
            len(mspl_xml or ""),
        )

        mspl_node, flat_values = self._extract_mspl_and_flat_values(mspl_xml)
        metadata = self.extract_policy_metadata(mspl_xml)
        if self._is_simulated_sdn_policy(metadata):
            execution_data = self._execute_simulated_sdn_policy(
                mspl_xml,
                device_id=device_id,
                policy_id=policy_id,
                policy_name=policy_name,
                run_mode=run_mode,
                is_test=is_test,
                requested_by=requested_by,
                correlation_id=correlation_id,
            )
            logger.info(
                "Policy enforcement completed in simulated SDN mode: policyName='%s', deviceId='%s'",
                policy_name or "",
                device_id,
            )
            return {
                "status": "completed",
                "message": "Policy compiled to simulated SDN rules and marked as applied",
                "profileId": None,
                "policyType": metadata.get("policyType"),
                "capability": metadata.get("capability"),
                "execution": execution_data,
            }

        if not self.is_configured():
            raise EnforcementNotConfiguredError("No active enforcement profiles configured in database")

        profile_id, profile = self._resolve_profile(metadata)
        mode = str(profile.mode or "era").strip().lower()

        base_context = {
            "policy_name": policy_name or "",
            "policy_id": policy_id or "",
            "device_id": device_id,
            "device_ip": device_ip,
            "policy_type": metadata.get("policyType") or "",
            "capability": metadata.get("capability") or "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if mode == "era":
            start = time.perf_counter()
            logger.info(
                "Policy enforcement executing ERA mode: policyName='%s', profileId='%s', deviceId='%s'",
                policy_name or "",
                profile_id,
                device_id,
            )
            try:
                self.legacy_enforcer(mspl_xml, device)
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                self._log_execution(
                    device_id=device_id,
                    policy_id=policy_id,
                    policy_name=policy_name,
                    profile_id=profile.id,
                    run_mode=run_mode,
                    result='failed',
                    is_test=is_test,
                    event_type="policy_execution",
                    correlation_id=correlation_id,
                    step_name=policy_name or run_mode,
                    elapsed_ms=elapsed_ms,
                    error_message=str(exc),
                    requested_by=requested_by,
                )
                raise

            elapsed_ms = (time.perf_counter() - start) * 1000.0
            self._log_execution(
                device_id=device_id,
                policy_id=policy_id,
                policy_name=policy_name,
                profile_id=profile.id,
                run_mode=run_mode,
                result='completed',
                is_test=is_test,
                request_preview={'mode': 'era'},
                event_type="policy_execution",
                correlation_id=correlation_id,
                step_name=policy_name or run_mode,
                elapsed_ms=elapsed_ms,
                requested_by=requested_by,
            )
            execution_data: Dict[str, Any] = {
                "profileId": profile_id,
                "mode": "era",
                "target": "device",
            }
        elif mode == "rest":
            ec = build_merged_enforcement_context(
                profile,
                device,
                base_context,
                flat_values,
                extra_context,
                db=self.db,
                secret_manager=self.secret_manager,
            )
            if ec.missing:
                raise EnforcementPrerequisitesError(
                    "Enforcement prerequisites not satisfied",
                    missing=ec.missing,
                )
            context: Dict[str, Any] = ec.context
            execution_data = self._execute_rest_profile(
                profile,
                context,
                policy_id=policy_id,
                policy_name=policy_name,
                device_id=device_id,
                run_mode=run_mode,
                is_test=is_test,
                requested_by=requested_by,
                correlation_id=correlation_id,
            )
        else:
            raise ValueError(f"Unsupported enforcement mode '{mode}' for profile '{profile_id}'")

        logger.info(
            "Policy enforcement completed: policyName='%s', profileId='%s', mode='%s', resultStatus='completed'",
            policy_name or "",
            profile_id,
            mode,
        )
        return {
            "status": "completed",
            "message": f"Policy enforced using profile '{profile_id}'",
            "profileId": str(profile_id),
            "policyType": metadata.get("policyType"),
            "capability": metadata.get("capability"),
            "execution": execution_data,
        }

    def resolve_enforcement_profile(self, mspl_xml: str) -> Dict[str, Optional[str]]:
        """
        Resolves profile for a given MSPL without executing enforcement.
        """
        metadata = self.extract_policy_metadata(mspl_xml)
        if self._is_simulated_sdn_policy(metadata):
            return {
                "profileId": None,
                "mode": "sdn-simulated",
                "policyType": metadata.get("policyType"),
                "capability": metadata.get("capability"),
            }
        profile_id, profile = self._resolve_profile(metadata)
        return {
            "profileId": str(profile_id),
            "mode": str(profile.mode or 'era').strip().lower(),
            "policyType": metadata.get("policyType"),
            "capability": metadata.get("capability"),
        }

    def compute_enforcement_gaps(
        self,
        mspl_xml: str,
        device,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Resolves the enforcement profile and returns missing context keys (no HTTP).
        """
        device_id = getattr(device, "identifier", "") or ""
        device_ip = getattr(device, "ip", "") or ""
        _, flat_values = self._extract_mspl_and_flat_values(mspl_xml)
        metadata = self.extract_policy_metadata(mspl_xml)
        if self._is_simulated_sdn_policy(metadata):
            return {
                "mode": "sdn-simulated",
                "profileId": None,
                "missing": [],
                "warnings": [],
            }
        if not self.is_configured():
            raise EnforcementNotConfiguredError("No active enforcement profiles configured in database")
        profile_id, profile = self._resolve_profile(metadata)
        mode = str(profile.mode or "era").strip().lower()
        if mode != "rest":
            return {
                "mode": mode,
                "profileId": str(profile_id),
                "missing": [],
                "warnings": [],
            }
        base_context = {
            "policy_name": "",
            "policy_id": "",
            "device_id": device_id,
            "device_ip": device_ip,
            "policy_type": metadata.get("policyType") or "",
            "capability": metadata.get("capability") or "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        ec = build_merged_enforcement_context(
            profile,
            device,
            base_context,
            flat_values,
            extra_context,
            db=self.db,
            secret_manager=self.secret_manager,
        )
        return {
            "mode": "rest",
            "profileId": str(profile_id),
            "missing": ec.missing,
            "warnings": ec.warnings,
        }

    def _is_simulated_sdn_policy(self, metadata: Dict[str, Optional[str]]) -> bool:
        capability = self.normalize_key(metadata.get("capability") or "")
        policy_type = self.normalize_key(metadata.get("policyType") or "")
        return capability == "filtering-l4" or policy_type in {"ipv4-mspl-type", "ipv6-mspl-type"}

    def test_profile(
        self,
        profile_id: int,
        run_mode: str,
        context: Optional[Dict[str, Any]] = None,
        requested_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        profile = self.db.getEnforcementProfile(profile_id)
        if profile is None:
            raise ValueError(f"Profile with id '{profile_id}' not found")
        if not profile.is_active:
            raise ValueError(f"Profile '{profile_id}' is inactive")
        if str(profile.mode or '').strip().lower() != 'rest':
            raise ValueError("Test endpoint supports only REST profiles")

        run_mode_normalized = str(run_mode or '').strip().lower()
        if run_mode_normalized not in {'preview', 'execute'}:
            raise ValueError("runMode must be 'preview' or 'execute'")

        if context is None:
            context = {}
        base_context = {
            "policy_name": "admin-test",
            "policy_id": "",
            "device_id": str(context.get("device_id", "") or ""),
            "device_ip": str(context.get("device_ip", "") or ""),
            "policy_type": "",
            "capability": "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        ec = build_merged_enforcement_context(
            profile,
            None,
            base_context,
            {},
            context,
            db=self.db,
            secret_manager=self.secret_manager,
        )
        if ec.missing:
            raise EnforcementPrerequisitesError(
                "Enforcement prerequisites not satisfied for profile test",
                missing=ec.missing,
            )

        execution = self._execute_rest_profile(
            profile,
            ec.context,
            policy_id=None,
            policy_name='admin-test',
            device_id=context.get('device_id') if isinstance(context, dict) else None,
            run_mode=run_mode_normalized,
            is_test=True,
            requested_by=requested_by,
        )
        return {
            'status': 'completed',
            'profileId': str(profile_id),
            'execution': execution,
        }

    def _resolve_explicit_profile(self, explicit_profile: str):
        normalized = self.normalize_key(explicit_profile)
        if explicit_profile.isdigit():
            profile = self.db.getEnforcementProfile(int(explicit_profile))
            if profile and profile.is_active:
                return profile

        # Match by profile name (normalized)
        for profile in self.db.getActiveEnforcementProfiles():
            if self.normalize_key(profile.name) == normalized:
                return profile

        # Explicit profile alias via mapping
        aliases = self.db.findEnforcementMappings('explicitProfile', normalized)
        for alias in aliases:
            profile = self.db.getEnforcementProfile(alias.profile_id)
            if profile and profile.is_active:
                return profile

        return None

    def _resolve_profile(self, metadata: Dict[str, Optional[str]]):
        """Resolves the enforcement profile for a policy."""
        if not self.is_configured():
            raise EnforcementNotConfiguredError("No active enforcement profiles configured in database")

        explicit_profile = metadata.get("enforcementProfile")
        if explicit_profile:
            profile = self._resolve_explicit_profile(explicit_profile)
            if profile is not None:
                return profile.id, profile
            raise ValueError(f"Explicit enforcement profile '{explicit_profile}' is not configured")

        policy_type = metadata.get('policyType')
        if policy_type:
            mappings = self.db.findEnforcementMappings('policyType', self.normalize_key(policy_type))
            for mapping in mappings:
                profile = self.db.getEnforcementProfile(mapping.profile_id)
                if profile is not None and profile.is_active:
                    return profile.id, profile

        capability = metadata.get('capability')
        if capability:
            mappings = self.db.findEnforcementMappings('capability', self.normalize_key(capability))
            for mapping in mappings:
                profile = self.db.getEnforcementProfile(mapping.profile_id)
                if profile is not None and profile.is_active:
                    return profile.id, profile

        default_profile = self.db.getDefaultEnforcementProfile()
        if default_profile is not None and default_profile.is_active:
            return default_profile.id, default_profile

        raise EnforcementNotConfiguredError("No default enforcement profile configured")

    def _execute_rest_profile(
        self,
        profile,
        context: Dict[str, Any],
        *,
        policy_id: Optional[str],
        policy_name: Optional[str],
        device_id: Optional[str],
        run_mode: str,
        is_test: bool,
        requested_by: Optional[str],
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        start = time.perf_counter()
        endpoint_template = profile.endpoint_template
        if not endpoint_template:
            raise ValueError(f"Profile '{profile.id}' requires endpointTemplate")

        endpoint = self._render_value(endpoint_template, context)
        self.validate_endpoint_template(endpoint)

        method = str(profile.method or "POST").strip().upper()
        timeout_seconds = float(profile.timeout_seconds or 10)

        headers_template = self._parse_json_template(profile.headers_template, {})
        if headers_template is None:
            headers_template = {}
        if not isinstance(headers_template, dict):
            raise ValueError(f"Profile '{profile.id}' has invalid headersTemplate (must be JSON object)")
        headers = deepcopy(self._render_value(headers_template, context))

        auth_type = str(profile.auth_type or 'none').strip().lower()
        auth_source = 'none'
        token = None
        if auth_type == 'bearer':
            if profile.auth_secret_id:
                secret = self.db.getEnforcementSecret(profile.auth_secret_id)
                if secret is None:
                    raise ValueError(f"Profile '{profile.id}' references missing secret id {profile.auth_secret_id}")
                try:
                    token = self.secret_manager.decrypt(
                        ciphertext=secret.ciphertext,
                        nonce=secret.nonce,
                        key_version=secret.key_version,
                    )
                    auth_source = f"db_secret:{secret.id}"
                except SecretManagerError as exc:
                    raise ValueError(f"Unable to decrypt secret for profile '{profile.id}'") from exc

            if not token:
                bk_norm, _bk_raw = get_bearer_context_key_pair(profile)
                if bk_norm:
                    v = self._context_value_for_key(context, bk_norm)
                    if v is not None and str(v).strip():
                        token = str(v).strip()
                        spec_opts = parse_context_spec_options_from_profile(profile)
                        if spec_opts.get("requireStoredDeviceBearer"):
                            auth_source = "device_stored_context"
                        elif bool(getattr(profile, 'allow_mspl_token', False)):
                            auth_source = 'mspl_context'
                        else:
                            auth_source = "context_bearer_key"

            if not token:
                raise ValueError(f"Profile '{profile.id}' uses bearer auth but no token is available")

            headers["Authorization"] = f"Bearer {token}"

        payload_template = self._parse_json_template(profile.payload_template, {})
        payload = self._render_value(payload_template, context) if payload_template is not None else {}

        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                pass

        json_payload = payload if isinstance(payload, (dict, list)) else None
        data_payload = payload if isinstance(payload, str) else None

        request_payload = {
            "method": method,
            "url": endpoint,
            "headers": headers,
            "json": json_payload,
            "data": data_payload,
            "timeout": timeout_seconds,
            "authType": auth_type,
            "authSource": auth_source,
        }

        run_mode_normalized = str(run_mode or 'execute').strip().lower()
        if run_mode_normalized not in {'execute', 'preview'}:
            raise ValueError("run_mode must be 'execute' or 'preview'")

        if run_mode_normalized == 'preview' or bool(profile.dry_run):
            result_mode = 'rest-preview' if run_mode_normalized == 'preview' else 'rest-dry-run'
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            self._log_execution(
                device_id=device_id,
                policy_id=policy_id,
                policy_name=policy_name,
                profile_id=profile.id,
                run_mode=run_mode_normalized,
                result='completed',
                is_test=is_test,
                event_type="policy_execution",
                correlation_id=correlation_id,
                step_name=policy_name or run_mode_normalized,
                elapsed_ms=elapsed_ms,
                request_preview=request_payload,
                response_status=None,
                response_excerpt='preview only, no HTTP request sent',
                requested_by=requested_by,
            )
            return {
                "profileId": str(profile.id),
                "mode": result_mode,
                "endpoint": endpoint,
                "method": method,
                "dryRun": bool(profile.dry_run),
                "request": self._redact_sensitive(request_payload),
            }

        response_status = None
        response_excerpt = None
        try:
            response = requests.request(
                method=method,
                url=endpoint,
                headers=headers,
                json=json_payload,
                data=data_payload,
                timeout=timeout_seconds,
            )
            response_status = response.status_code
            response.raise_for_status()
            response_excerpt = response.text[:500] if response.text else ""
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            self._log_execution(
                device_id=device_id,
                policy_id=policy_id,
                policy_name=policy_name,
                profile_id=profile.id,
                run_mode=run_mode_normalized,
                result='completed',
                is_test=is_test,
                event_type="policy_execution",
                correlation_id=correlation_id,
                step_name=policy_name or run_mode_normalized,
                elapsed_ms=elapsed_ms,
                request_preview=request_payload,
                response_status=response_status,
                response_excerpt=response_excerpt,
                requested_by=requested_by,
            )
            return {
                "profileId": str(profile.id),
                "mode": "rest",
                "endpoint": endpoint,
                "method": method,
                "httpStatus": response.status_code,
                "responseExcerpt": response_excerpt,
            }
        except requests.HTTPError as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            resp = getattr(exc, "response", None)
            if resp is not None:
                response_status = resp.status_code
                try:
                    response_excerpt = (resp.text or "")[:500]
                except Exception:
                    response_excerpt = None
            self._log_execution(
                device_id=device_id,
                policy_id=policy_id,
                policy_name=policy_name,
                profile_id=profile.id,
                run_mode=run_mode_normalized,
                result="failed",
                is_test=is_test,
                event_type="policy_execution",
                correlation_id=correlation_id,
                step_name=policy_name or run_mode_normalized,
                elapsed_ms=elapsed_ms,
                request_preview=request_payload,
                response_status=response_status,
                response_excerpt=response_excerpt,
                error_message=str(exc),
                requested_by=requested_by,
            )
            if resp is not None:
                redacted = self._redact_sensitive(deepcopy(request_payload))
                curl = self._curl_replication_hint(redacted)
                raise EnforcementDependencyError(
                    f"Downstream service returned HTTP {response_status}",
                    downstream_url=endpoint,
                    downstream_status=int(response_status or 0),
                    response_excerpt=response_excerpt or "",
                    replicable_request=redacted,
                    replicable_curl=curl,
                ) from exc
            raise
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            if getattr(exc, 'response', None) is not None:
                response_status = getattr(exc.response, 'status_code', None)
                try:
                    response_excerpt = (exc.response.text or '')[:500]
                except Exception:
                    response_excerpt = None

            self._log_execution(
                device_id=device_id,
                policy_id=policy_id,
                policy_name=policy_name,
                profile_id=profile.id,
                run_mode=run_mode_normalized,
                result='failed',
                is_test=is_test,
                event_type="policy_execution",
                correlation_id=correlation_id,
                step_name=policy_name or run_mode_normalized,
                elapsed_ms=elapsed_ms,
                request_preview=request_payload,
                response_status=response_status,
                response_excerpt=response_excerpt,
                error_message=str(exc),
                requested_by=requested_by,
            )
            raise

    def _execute_simulated_sdn_policy(
        self,
        mspl_xml: str,
        *,
        device_id: Optional[str],
        policy_id: Optional[str],
        policy_name: Optional[str],
        run_mode: str,
        is_test: bool,
        requested_by: Optional[str],
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        start = time.perf_counter()
        try:
            generated_rules = self.simulated_sdn_service.compile_mspl(mspl_xml, device_id or "device")
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            self._log_execution(
                device_id=device_id,
                policy_id=policy_id,
                policy_name=policy_name,
                profile_id=None,
                run_mode=run_mode,
                result="failed",
                is_test=is_test,
                event_type="policy_execution",
                correlation_id=correlation_id,
                step_name=policy_name or run_mode,
                elapsed_ms=elapsed_ms,
                error_message=str(exc),
                requested_by=requested_by,
            )
            raise

        request_preview = {
            "mode": "sdn-simulated",
            "generatedRules": generated_rules,
        }
        response_excerpt = "Policy sent to SDN and applied (simulated mode)"
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self._log_execution(
            device_id=device_id,
            policy_id=policy_id,
            policy_name=policy_name,
            profile_id=None,
            run_mode=run_mode,
            result="completed",
            is_test=is_test,
            event_type="policy_execution",
            correlation_id=correlation_id,
            step_name=policy_name or run_mode,
            elapsed_ms=elapsed_ms,
            request_preview=request_preview,
            response_excerpt=response_excerpt,
            requested_by=requested_by,
        )
        logger.info(
            "Simulated SDN enforcement generated %d iptables rule(s) for device '%s': %s",
            len(generated_rules),
            device_id or "",
            generated_rules,
        )
        logger.info("Policy sent to SDN and applied (simulated mode) for device '%s'", device_id or "")
        return {
            "profileId": None,
            "mode": "sdn-simulated",
            "simulated": True,
            "target": "sdn",
            "generatedRules": generated_rules,
        }

    def _extract_mspl_and_flat_values(self, mspl_xml: str) -> tuple[Dict[str, Any], Dict[str, str]]:
        """Parses MSPL XML and extracts flat scalar values."""
        parsed = self.mspl_xml_to_json(mspl_xml)
        mspl_node = self._get_mspl_node(parsed)
        if not isinstance(mspl_node, dict):
            raise ValueError("MSPL root node is missing or invalid")
        flat_values = self._extract_scalar_values(mspl_node)
        return mspl_node, flat_values

    @staticmethod
    def _get_mspl_node(parsed: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Gets the node that represents the MSPL root."""
        if not isinstance(parsed, dict):
            return None
        if "mspl" in parsed:
            return parsed["mspl"]
        if "root" in parsed:
            return parsed["root"]
        if len(parsed) == 1:
            only_key = next(iter(parsed))
            value = parsed[only_key]
            if isinstance(value, dict):
                return value
        return None

    def _extract_scalar_values(self, node: Any, prefix: str = "") -> Dict[str, str]:
        """Extracts scalar string values from a nested structure."""
        result: Dict[str, str] = {}
        if isinstance(node, dict):
            text_value = node.get("#text")
            if text_value is not None:
                as_text = str(text_value).strip()
                if as_text:
                    leaf_key = prefix.split(".")[-1] if prefix else "value"
                    result[leaf_key] = as_text
                    if prefix:
                        result[prefix] = as_text
            for key, value in node.items():
                if str(key).startswith("@") or key == "#text":
                    continue
                norm_key = self.normalize_key(str(key))
                next_prefix = f"{prefix}.{norm_key}" if prefix else norm_key
                result.update(self._extract_scalar_values(value, next_prefix))
        elif isinstance(node, list):
            for item in node:
                result.update(self._extract_scalar_values(item, prefix))
        elif node is not None:
            as_text = str(node).strip()
            if as_text:
                leaf_key = prefix.split(".")[-1] if prefix else "value"
                result[leaf_key] = as_text
                result[prefix] = as_text
        return result

    @staticmethod
    def _context_value_for_key(context: Dict[str, Any], normalized_key: str) -> Any:
        """First non-empty value for a key (merged context stores normalized keys)."""
        v = context.get(normalized_key)
        if v is not None and str(v).strip():
            return v
        return None

    @staticmethod
    def _pick_first(values: Dict[str, Any], keys: list[str]) -> Optional[str]:
        """Returns first non-empty value by key candidates."""
        for key in keys:
            if key in values and str(values[key]).strip():
                return str(values[key]).strip()
        return None

    @staticmethod
    def _extract_capability_name(mspl_node: Dict[str, Any]) -> Optional[str]:
        """
        Extract capability value from structured MSPL representations.

        Supports both scalar capability values and object forms such as
        capability -> Name emitted by the visual builder.
        """
        if not isinstance(mspl_node, dict):
            return None

        def _as_dict(value: Any) -> Optional[Dict[str, Any]]:
            return value if isinstance(value, dict) else None

        configurations: list[Any] = [mspl_node.get("configuration")]
        it_resource = _as_dict(mspl_node.get("ITResource"))
        if it_resource is not None:
            configurations.append(it_resource.get("configuration"))

        for config in configurations:
            config_dict = _as_dict(config)
            if config_dict is None:
                continue
            capability = config_dict.get("capability")
            if isinstance(capability, str) and capability.strip():
                return capability.strip()
            capability_dict = _as_dict(capability)
            if capability_dict is None:
                continue
            for key in ("Name", "name", "value"):
                value = capability_dict.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return None

    def _render_value(self, value: Any, context: Dict[str, Any]) -> Any:
        """Renders placeholders in strings recursively for dict/list structures."""
        if isinstance(value, dict):
            return {k: self._render_value(v, context) for k, v in value.items()}
        if isinstance(value, list):
            return [self._render_value(item, context) for item in value]
        if not isinstance(value, str):
            return value

        def replace_placeholder(match: re.Match) -> str:
            raw_key = match.group(1)
            key = self.normalize_key(raw_key)
            val = context.get(key)
            if val is None:
                return ""
            return str(val)

        return PLACEHOLDER_REGEX.sub(replace_placeholder, value)
