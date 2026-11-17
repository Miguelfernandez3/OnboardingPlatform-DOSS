"""
Merge and validate REST enforcement template context (device, MSPL, operator).
"""
from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

# Keep in sync with policy_enforcement_service PLACEHOLDER_REGEX
PLACEHOLDER_REGEX = re.compile(r"\{\{([a-zA-Z0-9_\-\.]+)\}\}")


def normalize_key(key: str) -> str:
    return key.strip().lower().replace("_", "-")


@dataclass
class EnforcementContextResult:
    context: Dict[str, Any]
    """Merged flat string context with normalized and raw keys (same as PolicyEnforcementService)."""
    missing: List[Dict[str, Any]]
    """Each item: key (normalized), source, label (optional), sensitive (optional)."""
    warnings: List[str] = field(default_factory=list)


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (dict, list)) and not value:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _profile_template_blobs(profile) -> List[str]:
    blobs: List[str] = []
    for name in ("endpoint_template", "headers_template", "payload_template"):
        raw = getattr(profile, name, None)
        if not raw:
            continue
        if isinstance(raw, (dict, list)):
            blobs.append(json.dumps(raw, ensure_ascii=True))
        else:
            blobs.append(str(raw))
    return blobs


def derive_placeholder_keys_from_profile(profile) -> Set[str]:
    """Placeholders in endpoint / headers / payload; keys normalized."""
    out: Set[str] = set()
    for s in _profile_template_blobs(profile):
        for m in PLACEHOLDER_REGEX.finditer(s):
            out.add(normalize_key(m.group(1)))
    return out


def parse_context_spec_from_profile(profile) -> List[Dict[str, Any]]:
    """
    context_spec JSON:
      { "requirements": [ { "key", "source"?, "optional"?, "sensitive"?, "label"?, "bearerForAuth"? } ] }
    or a list treated as requirements.
    """
    raw = getattr(profile, "context_spec", None) if profile is not None else None
    return _parse_requirements_from_context_spec_raw(raw)


def _parse_requirements_from_context_spec_raw(raw: Any) -> List[Dict[str, Any]]:
    if not raw or (isinstance(raw, str) and not str(raw).strip()):
        return []
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict) and "requirements" in data:
        req = data.get("requirements")
        if isinstance(req, list):
            return [x for x in req if isinstance(x, dict)]
    return []


def _is_bearer_for_auth_flag(req: Dict[str, Any]) -> bool:
    v = req.get("bearerForAuth")
    if v is True:
        return True
    if isinstance(v, str) and v.strip().lower() in {"1", "true", "yes"}:
        return True
    return False


def get_bearer_context_key_pair(profile) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (normalized_key, raw_key) from the unique requirement with bearerForAuth set.
    If zero or more than one such requirement, returns (None, None).
    """
    spec_list = parse_context_spec_from_profile(profile)
    return _bearer_key_pair_from_requirement_list(spec_list)


def get_bearer_context_key_pair_from_spec_value(value: Any) -> Tuple[Optional[str], Optional[str]]:
    """Same as get_bearer_context_key_pair but from a contextSpec string or dict (API body)."""
    reqs = _parse_requirements_from_context_spec_raw(value)
    return _bearer_key_pair_from_requirement_list(reqs)


def _bearer_key_pair_from_requirement_list(spec_list: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[str]]:
    raw_keys: List[str] = []
    for req in spec_list:
        if not _is_bearer_for_auth_flag(req):
            continue
        key = req.get("key")
        if isinstance(key, str) and key.strip():
            raw_keys.append(key.strip())
    if len(raw_keys) != 1:
        return (None, None)
    rk = raw_keys[0]
    return (normalize_key(rk), rk)


def parse_context_spec_options_from_profile(profile) -> Dict[str, Any]:
    """Options bag inside context_spec JSON, e.g. { \"options\": { \"requireStoredDeviceBearer\": true } }."""
    if profile is None:
        return {}
    raw = getattr(profile, "context_spec", None)
    if not raw or not str(raw).strip():
        return {}
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return {}
    if isinstance(data, dict) and isinstance(data.get("options"), dict):
        return dict(data["options"])
    return {}


def _device_bearer_from_encrypted_store(
    device, db, secret_manager, raw_context_key: str
) -> Dict[str, str]:
    """Load Bearer token from device encrypted store and expose it only under the profile's context key."""
    if device is None or db is None or secret_manager is None:
        return {}
    if not (raw_context_key and str(raw_context_key).strip()):
        return {}
    did = getattr(device, "identifier", None) or ""
    if not did:
        return {}
    try:
        row = db.getDeviceEnforcementSecret(did, "bearer_token")
    except Exception:  # pylint: disable=broad-except
        return {}
    if row is None:
        return {}
    try:
        token = secret_manager.decrypt(
            ciphertext=row.ciphertext, nonce=row.nonce, key_version=row.key_version
        )
    except Exception:  # pylint: disable=broad-except
        return {}
    v = str(token)
    if not v.strip():
        return {}
    return {raw_context_key.strip(): v}


def list_required_keys(profile) -> Tuple[Set[str], str]:
    """
    Returns (required_key_set, mode) where mode is 'spec' or 'derived'.
    System-only keys (always filled by service for non-empty device_id) are still validated if empty.
    """
    spec_reqs = parse_context_spec_from_profile(profile)
    if spec_reqs:
        keys: Set[str] = set()
        for req in spec_reqs:
            key = req.get("key")
            if not key or not isinstance(key, str):
                continue
            nk = normalize_key(key)
            if req.get("optional") is True:
                continue
            if str(req.get("source", "")).strip().lower() == "system":
                continue
            keys.add(nk)
        return keys, "spec"
    return derive_placeholder_keys_from_profile(profile), "derived"


def ordered_spec_required_keys(profile) -> List[str]:
    """
    Same keys as spec mode in list_required_keys, in the order they appear in context_spec.requirements.
    """
    spec_reqs = parse_context_spec_from_profile(profile)
    out: List[str] = []
    seen: Set[str] = set()
    for req in spec_reqs:
        key = req.get("key")
        if not key or not isinstance(key, str):
            continue
        nk = normalize_key(key)
        if req.get("optional") is True:
            continue
        if str(req.get("source", "")).strip().lower() == "system":
            continue
        if nk in seen:
            continue
        seen.add(nk)
        out.append(nk)
    return out


def _parse_device_enforcement_context(device) -> Dict[str, Any]:
    if device is None:
        return {}
    raw = getattr(device, "enforcement_context", None)
    if not raw or (isinstance(raw, str) and not raw.strip()):
        return {}
    if isinstance(raw, dict):
        return deepcopy(raw)
    try:
        j = json.loads(str(raw))
        if isinstance(j, dict):
            return j
    except (json.JSONDecodeError, TypeError):
        return {}
    return {}


def merge_context_layers(
    base_context: Dict[str, Any],
    flat_mspl: Dict[str, str],
    device_map: Dict[str, Any],
    extra_context: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Precedence: base, MSPL, device enforcement JSON, extra (wins on conflict).
    Each layer applies normalize_key for duplicate access.
    """
    ctx: Dict[str, Any] = {}

    def _apply(layer: Dict[str, Any]) -> None:
        for k, v in layer.items():
            if k is None:
                continue
            key_str = str(k)
            ctx[key_str] = v
            ctx[normalize_key(key_str)] = v

    _apply({k: v for k, v in base_context.items()})
    _apply({k: v for k, v in (flat_mspl or {}).items() if isinstance(k, (str, int))})
    _apply({k: v for k, v in (device_map or {}).items()})
    if isinstance(extra_context, dict):
        _apply(extra_context)
    return ctx


def _context_get(context: Dict[str, Any], nk: str) -> Any:
    v = context.get(nk)
    if v is not None and _is_present(v):
        return v
    return None


def _bearer_satisfied_in_context(
    profile,
    context: Dict[str, Any],
    token_from_db: Optional[str],
) -> bool:
    auth = str(getattr(profile, "auth_type", "none") or "none").strip().lower()
    if auth != "bearer":
        return True
    if getattr(profile, "auth_secret_id", None):
        return _is_present(token_from_db)
    nk, _rk = get_bearer_context_key_pair(profile)
    if not nk:
        return False
    return _is_present(_context_get(context, nk))


def build_merged_enforcement_context(
    profile,
    device,
    base_context: Dict[str, Any],
    flat_values: Dict[str, str],
    extra_context: Optional[Dict[str, Any]],
    *,
    db=None,
    secret_manager=None,
    profile_secret_token: Optional[str] = None,
) -> EnforcementContextResult:
    """
    Merges context and computes missing required keys. DB/secret only used for deciding bearer 'satisfied' when
    profile uses auth_secret_id; pass profile_secret_token if pre-decrypted.
    """
    device_map = _parse_device_enforcement_context(device)
    _bk_norm, bk_raw = get_bearer_context_key_pair(profile)
    if device is not None and db is not None and secret_manager is not None and bk_raw:
        st = _device_bearer_from_encrypted_store(device, db, secret_manager, bk_raw)
        if st:
            device_map = {**device_map, **st}
    ctx = merge_context_layers(base_context, flat_values, device_map, extra_context)
    warnings: List[str] = []

    required, mode = list_required_keys(profile)
    if mode == "derived" and not required and not parse_context_spec_from_profile(profile):
        if str(getattr(profile, "auth_type", "none") or "none").strip().lower() != "bearer":
            return EnforcementContextResult(context=ctx, missing=[], warnings=warnings)

    if mode == "spec":
        required_iter: Sequence[str] = ordered_spec_required_keys(profile)
    else:
        required_iter = sorted(required)

    missing: List[Dict[str, Any]] = []

    spec_list = parse_context_spec_from_profile(profile) if mode == "spec" else []
    by_key: Dict[str, Dict[str, Any]] = {}
    for req in spec_list:
        if not isinstance(req.get("key"), str):
            continue
        by_key[normalize_key(req["key"])] = req

    for nk in required_iter:
        if nk not in required:
            continue
        if not _is_present(_context_get(ctx, nk)):
            meta = by_key.get(nk, {})
            item = {
                "key": nk,
                "source": meta.get("source") or ("operator" if mode == "derived" else "unknown"),
                "label": meta.get("label") or nk,
            }
            if meta.get("sensitive"):
                item["sensitive"] = True
            missing.append(item)

    # Bearer token: when not using profile DB secret
    token_db = None
    if str(getattr(profile, "auth_type", "none") or "none").strip().lower() == "bearer":
        if profile_secret_token is not None:
            token_db = profile_secret_token
        elif (
            db is not None
            and secret_manager is not None
            and getattr(profile, "auth_secret_id", None)
        ):
            secret = db.getEnforcementSecret(profile.auth_secret_id)
            if secret is not None:
                try:
                    token_db = secret_manager.decrypt(
                        ciphertext=secret.ciphertext,
                        nonce=secret.nonce,
                        key_version=secret.key_version,
                    )
                except Exception:  # SecretManagerError or missing key
                    token_db = None

    if str(getattr(profile, "auth_type", "none") or "none").strip().lower() == "bearer":
        if getattr(profile, "auth_secret_id", None) and not _is_present(token_db):
            if not any(m.get("key") == "auth_profile_secret" for m in missing):
                missing.append(
                    {
                        "key": "auth_profile_secret",
                        "source": "admin",
                        "label": "Bearer secret configured on the profile (decrypt failed or missing row)",
                    }
                )
        elif not getattr(profile, "auth_secret_id", None) and not _bearer_satisfied_in_context(
            profile, ctx, None
        ):
            miss_nk, _miss_rk = get_bearer_context_key_pair(profile)
            miss_key = miss_nk or "bearer"
            if not any(m.get("key") == miss_key for m in missing):
                missing.append(
                    {
                        "key": miss_key,
                        "source": "mspl" if bool(getattr(profile, "allow_mspl_token", False)) else "operator",
                        "label": "Bearer token",
                    }
                )

    spec_options = parse_context_spec_options_from_profile(profile)
    miss_nk, _miss_rk = get_bearer_context_key_pair(profile)
    miss_key = miss_nk or "bearer"
    if (
        spec_options.get("requireStoredDeviceBearer")
        and str(getattr(profile, "auth_type", "none") or "none").strip().lower() == "bearer"
        and not getattr(profile, "auth_secret_id", None)
        and device is not None
        and db is not None
        and getattr(device, "identifier", None)
    ):
        if db.getDeviceEnforcementSecret(device.identifier, "bearer_token") is None:
            device_row = {
                "key": miss_key,
                "source": "operator",
                "label": "Bearer token",
                "sensitive": True,
                "deviceEncryptedBearer": True,
            }
            replaced = False
            for i, m in enumerate(missing):
                if m.get("key") == miss_key:
                    missing[i] = device_row
                    replaced = True
                    break
            if not replaced:
                missing.append(device_row)

    return EnforcementContextResult(context=ctx, missing=missing, warnings=warnings)
