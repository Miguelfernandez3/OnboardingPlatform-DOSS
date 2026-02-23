"""
Service for enforcing policies based on a fixed type->enforcement mapping.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import json
import logging
import os
import re

import requests
import xmltodict


PLACEHOLDER_REGEX = re.compile(r"\{\{([a-zA-Z0-9_\-\.]+)\}\}")
logger = logging.getLogger(__name__)


class PolicyEnforcementService:
    """
    Executes policy enforcement actions from MSPL using fixed profiles.
    """

    def __init__(self, config, legacy_enforcer):
        """
        Args:
            config: Config instance
            legacy_enforcer: Callable with signature legacy_enforcer(mspl_xml, device)
        """
        self.config = config
        self.legacy_enforcer = legacy_enforcer
        self.enforcement_config = self.config.policy_enforcement_config

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
            ["capability", "configuration-capability"],
        )
        explicit_profile = self._pick_first(
            flat_values,
            ["enforcement-profile", "profile-id", "execution-profile"],
        )

        if policy_type is None and isinstance(mspl_node, dict):
            raw_type = mspl_node.get("type")
            if isinstance(raw_type, str) and raw_type.strip():
                policy_type = raw_type.strip()

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

    def enforce_policy(self, mspl_xml: str, device, policy_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes enforcement according to configured profile.
        """
        device_id = getattr(device, "identifier", "") or ""
        device_ip = getattr(device, "ip", "") or ""
        logger.info(
            "Policy enforcement started: policyName='%s', deviceId='%s', deviceIp='%s', msplSize=%d",
            policy_name or "",
            device_id,
            device_ip,
            len(mspl_xml or ""),
        )
        mspl_node, flat_values = self._extract_mspl_and_flat_values(mspl_xml)
        metadata = self.extract_policy_metadata(mspl_xml)

        profile_id, profile = self._resolve_profile(metadata)
        mode = str(profile.get("mode", "era")).strip().lower()
        logger.info(
            "Policy enforcement profile resolved: policyName='%s', policyType='%s', capability='%s', profileId='%s', mode='%s'",
            policy_name or "",
            metadata.get("policyType"),
            metadata.get("capability"),
            profile_id,
            mode,
        )
        logger.debug(
            "Policy enforcement MSPL scalar extraction: policyName='%s', scalarCount=%d, sampleKeys=%s",
            policy_name or "",
            len(flat_values),
            sorted(flat_values.keys())[:20],
        )

        base_context = {
            "policy_name": policy_name or "",
            "device_id": device_id,
            "device_ip": device_ip,
            "policy_type": metadata.get("policyType") or "",
            "capability": metadata.get("capability") or "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        context: Dict[str, Any] = {}
        for key, value in base_context.items():
            context[key] = value
            context[self.normalize_key(key)] = value

        # Add scalar values from MSPL for template substitutions.
        for key, value in flat_values.items():
            context[key] = value
            context[self.normalize_key(key)] = value

        if mode == "era":
            logger.info(
                "Policy enforcement executing ERA mode: policyName='%s', profileId='%s', deviceId='%s'",
                policy_name or "",
                profile_id,
                device_id,
            )
            self.legacy_enforcer(mspl_xml, device)
            logger.info(
                "Policy enforcement ERA mode completed: policyName='%s', profileId='%s', deviceId='%s'",
                policy_name or "",
                profile_id,
                device_id,
            )
            execution_data: Dict[str, Any] = {
                "profileId": profile_id,
                "mode": "era",
                "target": "device",
            }
        elif mode == "rest":
            logger.info(
                "Policy enforcement executing REST mode: policyName='%s', profileId='%s', deviceId='%s'",
                policy_name or "",
                profile_id,
                device_id,
            )
            execution_data = self._execute_rest_profile(profile_id, profile, context)
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
            "profileId": profile_id,
            "policyType": metadata.get("policyType"),
            "capability": metadata.get("capability"),
            "execution": execution_data,
        }

    def resolve_enforcement_profile(self, mspl_xml: str) -> Dict[str, Optional[str]]:
        """
        Resolves profile for a given MSPL without executing enforcement.
        """
        metadata = self.extract_policy_metadata(mspl_xml)
        profile_id, profile = self._resolve_profile(metadata)
        logger.debug(
            "Enforcement profile resolution (preview): policyType='%s', capability='%s', profileId='%s', mode='%s'",
            metadata.get("policyType"),
            metadata.get("capability"),
            profile_id,
            str(profile.get("mode", "era")).strip().lower(),
        )
        return {
            "profileId": profile_id,
            "mode": str(profile.get("mode", "era")).strip().lower(),
            "policyType": metadata.get("policyType"),
            "capability": metadata.get("capability"),
        }

    def _execute_rest_profile(self, profile_id: str, profile: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a REST profile."""
        endpoint_template = profile.get("endpoint")
        if not endpoint_template:
            raise ValueError(f"Profile '{profile_id}' requires 'endpoint'")

        endpoint = self._render_value(endpoint_template, context)
        method = str(profile.get("method", "POST")).strip().upper()
        timeout_seconds = float(profile.get("timeout_seconds", 10))
        headers = deepcopy(profile.get("headers", {}))

        auth_cfg = profile.get("auth", {}) if isinstance(profile.get("auth"), dict) else {}
        auth_type = str(auth_cfg.get("type", "none")).strip().lower()
        auth_source = "none"

        if auth_type == "bearer":
            token = None
            if isinstance(auth_cfg.get("token"), str) and auth_cfg["token"].strip():
                token = self._render_value(auth_cfg["token"], context)
                auth_source = "profile.token"
            if token is None and isinstance(auth_cfg.get("token_env"), str):
                token = os.getenv(auth_cfg["token_env"])
                auth_source = f"env:{auth_cfg['token_env']}"
            if token is None and bool(auth_cfg.get("allow_mspl_token", False)):
                token = self._pick_first(
                    context,
                    ["token", "bearer-token", "auth-token", "authorization-token"],
                )
                auth_source = "mspl"
            if not token:
                raise ValueError(
                    f"Profile '{profile_id}' uses bearer auth but no token is available"
                )
            headers["Authorization"] = f"Bearer {token}"

        payload_template = profile.get("payload_template")
        payload = self._render_value(payload_template, context) if payload_template is not None else {}

        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                # Keep plain string payload if not JSON.
                pass

        json_payload = payload if isinstance(payload, (dict, list)) else None
        data_payload = payload if isinstance(payload, str) else None
        dry_run = bool(profile.get("dry_run", False))

        safe_headers = deepcopy(headers)
        if "Authorization" in safe_headers:
            safe_headers["Authorization"] = "Bearer ***"
        logger.info(
            "REST enforcement request: profileId='%s', method='%s', endpoint='%s', timeoutSeconds=%s, authType='%s', authSource='%s'",
            profile_id,
            method,
            endpoint,
            timeout_seconds,
            auth_type,
            auth_source,
        )
        logger.debug(
            "REST enforcement request details: profileId='%s', headers=%s, payloadPreview=%s",
            profile_id,
            self._safe_preview(safe_headers),
            self._safe_preview(payload),
        )

        if dry_run:
            dry_run_request = {
                "method": method,
                "url": endpoint,
                "headers": headers,
                "json": json_payload,
                "data": data_payload,
                "timeout": timeout_seconds,
            }
            logger.warning(
                "REST enforcement dry-run enabled for profile '%s'. Real HTTP request is skipped.",
                profile_id,
            )
            logger.info(
                "REST enforcement dry-run full request: %s",
                self._safe_preview(dry_run_request, max_length=8000),
            )
            return {
                "profileId": profile_id,
                "mode": "rest-dry-run",
                "endpoint": endpoint,
                "method": method,
                "dryRun": True,
                "request": dry_run_request,
            }

        response = requests.request(
            method=method,
            url=endpoint,
            headers=headers,
            json=json_payload,
            data=data_payload,
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        logger.info(
            "REST enforcement response: profileId='%s', httpStatus=%s, endpoint='%s'",
            profile_id,
            response.status_code,
            endpoint,
        )

        response_excerpt = response.text[:300] if response.text else ""
        if response_excerpt:
            logger.debug(
                "REST enforcement response excerpt: profileId='%s', excerpt=%s",
                profile_id,
                self._safe_preview(response_excerpt),
            )
        return {
            "profileId": profile_id,
            "mode": "rest",
            "endpoint": endpoint,
            "method": method,
            "httpStatus": response.status_code,
            "responseExcerpt": response_excerpt,
        }

    def _resolve_profile(self, metadata: Dict[str, Optional[str]]) -> tuple[str, Dict[str, Any]]:
        """Resolves the enforcement profile for a policy."""
        profiles = self.enforcement_config.get("profiles", {})
        mappings = self.enforcement_config.get("type_mappings", {})
        default_profile = self.enforcement_config.get("default_profile", "era-default")

        explicit_profile = metadata.get("enforcementProfile")
        if explicit_profile:
            normalized_profile = self.normalize_key(explicit_profile)
            for profile_id, profile_cfg in profiles.items():
                if self.normalize_key(profile_id) == normalized_profile:
                    logger.debug(
                        "Enforcement profile selected from explicit MSPL profile: explicitProfile='%s' -> profileId='%s'",
                        explicit_profile,
                        profile_id,
                    )
                    return profile_id, profile_cfg
            raise ValueError(f"Explicit enforcement profile '{explicit_profile}' is not configured")

        candidates = [metadata.get("policyType"), metadata.get("capability")]
        for candidate in candidates:
            if not candidate:
                continue
            normalized_candidate = self.normalize_key(candidate)
            for mapping_key, mapping_profile in mappings.items():
                if self.normalize_key(mapping_key) == normalized_candidate:
                    profile_cfg = profiles.get(mapping_profile)
                    if profile_cfg is None:
                        raise ValueError(
                            f"Mapping '{mapping_key}' points to unknown profile '{mapping_profile}'"
                        )
                    logger.debug(
                        "Enforcement profile selected from type mapping: candidate='%s', mappingKey='%s', profileId='%s'",
                        candidate,
                        mapping_key,
                        mapping_profile,
                    )
                    return mapping_profile, profile_cfg

        profile_cfg = profiles.get(default_profile)
        if profile_cfg is None:
            raise ValueError(f"Default profile '{default_profile}' is not configured")
        logger.debug(
            "Enforcement profile selected from default profile: defaultProfile='%s'",
            default_profile,
        )
        return default_profile, profile_cfg

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
            for key, value in node.items():
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
    def _pick_first(values: Dict[str, str], keys: list[str]) -> Optional[str]:
        """Returns first non-empty value by key candidates."""
        for key in keys:
            if key in values and str(values[key]).strip():
                return str(values[key]).strip()
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
