"""
Fake-FEAM: HTTP stub compatible with Domain-Manager FEAMClient (checkPin, getFunctionsOwn, callResourceServer).
DSP files: files/gendsp/<uuid>.json and files/insdsp/<uuid>.json (each file = dspFile object with doss-dsp).
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, request

logging.basicConfig(level=logging.INFO)

# Suffixes must match FEAMService / feam_service.py (endswith on full operationId).
SUFFIX_GET_INSDSP = "b492-4267-9ef5-92b15f22a394"
SUFFIX_GET_GENDSP = "4637-487c-a71a-9cba257304af"
SUFFIX_LIST_INSDSP = "cc5b-44e9-adce-159aee6c0c6d"
SUFFIX_LIST_GENDSP = "0539-4440-be7d-ba743f8c4ada"
SUFFIX_LIST_REPORTS = "ad05-4b4f-a4df-6551238ca72b"

app = Flask(__name__)


def _base_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def files_root() -> str:
    return os.getenv("FAKEFEAM_FILES_DIR", os.path.join(_base_dir(), "files"))


def _catalog_path() -> str:
    return os.getenv("FAKEFEAM_CATALOG_PATH", os.path.join(_base_dir(), "catalog.json"))


def load_catalog() -> Dict[str, Any]:
    path = _catalog_path()
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _dsp_path(kind: str, uuid: str) -> str:
    u = str(uuid).strip().lower()
    return os.path.join(files_root(), kind, f"{u}.json")


def _load_json_file(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_dspfile_by_id(kind: str, dsp_id: str) -> Optional[Dict[str, Any]]:
    path = _dsp_path(kind, dsp_id)
    if not os.path.isfile(path):
        return None
    return _load_json_file(path)


def _build_list_entries(kind: str) -> List[Dict[str, Any]]:
    directory = os.path.join(files_root(), kind)
    if not os.path.isdir(directory):
        return []
    out: List[Dict[str, Any]] = []
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json"):
            continue
        p = os.path.join(directory, name)
        data = _load_json_file(p)
        out.append(
            {
                "signature": "fake",
                "certificate": "fake",
                "dspFile": data,
            }
        )
    return out


def _wrap_dsp_entry(dspfile: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "signature": "fake",
        "certificate": "fake",
        "dspFile": dspfile,
    }


def _extract_gendsp_id_from_dspfile(dspfile: Dict[str, Any]) -> Optional[str]:
    doss = dspfile.get("doss-dsp")
    if not isinstance(doss, dict):
        return None
    for link in (doss.get("metadata") or {}).get("links") or []:
        if not isinstance(link, dict):
            continue
        if str(link.get("rel") or "").strip() == "Generic DSP":
            href = str(link.get("href") or "").strip()
            if href:
                return href
    return None


def _parse_extra_dsp_id(extra_values: List[Any]) -> Optional[str]:
    if not extra_values:
        return None
    first = extra_values[0]
    if isinstance(first, str):
        try:
            obj = json.loads(first)
        except json.JSONDecodeError:
            return None
    elif isinstance(first, dict):
        obj = first
    else:
        return None
    if not isinstance(obj, dict):
        return None
    raw = obj.get("id")
    if raw is None:
        return None
    return str(raw).strip()


def call_resource_handler(body: Dict[str, Any]) -> Dict[str, Any]:
    operation_id = str(body.get("operationId") or "")
    extra = body.get("extraValues") or []

    if operation_id.endswith(SUFFIX_LIST_GENDSP):
        items = _build_list_entries("gendsp")
        return {"status": "ok", "responseJson": json.dumps(items)}

    if operation_id.endswith(SUFFIX_LIST_INSDSP):
        items = _build_list_entries("insdsp")
        return {"status": "ok", "responseJson": json.dumps(items)}

    if operation_id.endswith(SUFFIX_LIST_REPORTS):
        return {"status": "ok", "responseJson": "[]"}

    dsp_id = _parse_extra_dsp_id(extra)
    if not dsp_id:
        return {"status": "error", "error": "missing or invalid extraValues[0] id for by-id call"}

    if operation_id.endswith(SUFFIX_GET_INSDSP):
        dsp = _load_dspfile_by_id("insdsp", dsp_id)
        if dsp is None:
            return {"status": "ok", "responseJson": None}
        gendsp_id = _extract_gendsp_id_from_dspfile(dsp)
        generic_entry = None
        if gendsp_id:
            gendsp = _load_dspfile_by_id("gendsp", gendsp_id)
            if gendsp is not None:
                generic_entry = _wrap_dsp_entry(gendsp)
        payload = {
            "instanceDsp": _wrap_dsp_entry(dsp),
        }
        if generic_entry is not None:
            payload["genericDsp"] = generic_entry
        return {"status": "ok", "responseJson": json.dumps(payload)}

    if operation_id.endswith(SUFFIX_GET_GENDSP):
        dsp = _load_dspfile_by_id("gendsp", dsp_id)
        if dsp is None:
            return {"status": "ok", "responseJson": None}
        return {"status": "ok", "responseJson": json.dumps(_wrap_dsp_entry(dsp))}

    return {"status": "error", "error": f"unknown operationId suffix: {operation_id!r}"}


@app.route("/checkPin", methods=["POST"])
def check_pin():
    _ = request.get_json(silent=True)
    return jsonify({"status": "ok"}), 200


@app.route("/getFunctionsOwn", methods=["POST"])
def get_functions_own():
    _ = request.get_json(silent=True)
    catalog = load_catalog()
    return jsonify(catalog), 200


@app.route("/callResourceServer", methods=["POST"])
def call_resource_server():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"status": "error", "error": "invalid json body"}), 400
    out = call_resource_handler(body)
    if str(out.get("status", "")).lower() == "error":
        code = 200
        return jsonify(out), code
    return jsonify(out), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", os.getenv("FAKEFEAM_LISTEN", "8181")))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FAKEFEAM_DEBUG", "").lower() in ("1", "true", "yes"))
