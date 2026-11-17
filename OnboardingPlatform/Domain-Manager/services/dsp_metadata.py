"""
Extract canonical device identity fields from a GenDSP doss-dsp document.

Uses a single fixed path per UI field (no cross-field OR fallbacks).
Source component: local-definitions.components where type == "this-system".
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from services.mud_service import _get_doss_dsp

_THIS_SYSTEM_TYPE = "this-system"
_PROP_VENDOR = "vendor"
_PROP_MODEL = "model"


def _this_system_component(doss_dsp: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    components = (doss_dsp.get("local-definitions") or {}).get("components") or []
    for component in components:
        if isinstance(component, dict) and str(component.get("type") or "").strip() == _THIS_SYSTEM_TYPE:
            return component
    return None


def _prop_value(component: Dict[str, Any], prop_name: str) -> Optional[str]:
    for prop in component.get("props") or []:
        if not isinstance(prop, dict):
            continue
        if str(prop.get("name") or "").strip() != prop_name:
            continue
        value = prop.get("value")
        if value is None:
            return None
        text = str(value).strip()
        return text or None
    return None


def extract_device_identity_from_gendsp(dsp_json: Any) -> Dict[str, Optional[str]]:
    """
    Returns name, manufacturer, model from GenDSP using fixed doss-dsp paths.

    type is always None: doss-dsp only defines component.type == "this-system"
    (schema role), not a device category such as sensor or gateway.
    """
    result: Dict[str, Optional[str]] = {
        "name": None,
        "manufacturer": None,
        "model": None,
        "type": None,
    }
    if dsp_json is None:
        return result

    if isinstance(dsp_json, str):
        try:
            dsp_data = json.loads(dsp_json)
        except json.JSONDecodeError:
            return result
    elif isinstance(dsp_json, dict):
        dsp_data = dsp_json
    else:
        return result

    doss_dsp = _get_doss_dsp(dsp_data)
    if not doss_dsp:
        return result

    this_system = _this_system_component(doss_dsp)
    if not this_system:
        return result

    title = this_system.get("title")
    if title is not None:
        text = str(title).strip()
        if text:
            result["name"] = text

    result["manufacturer"] = _prop_value(this_system, _PROP_VENDOR)
    result["model"] = _prop_value(this_system, _PROP_MODEL)
    return result
