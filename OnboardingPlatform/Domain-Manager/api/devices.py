# api/devices.py
"""
Endpoints related to devices.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from utils.error_handlers import handle_api_errors, require_device
from utils.app_context import get_dadm_instance
from utils.formatters import device_to_dict
from core.auth.decorators import require_auth
from services.device_service import DeviceRegistrationError
from services.policy_enforcement_service import EnforcementNotConfiguredError
import logging
import json
import Database

devices_bp = Blueprint('devices', __name__)

logger = logging.getLogger(__name__)


def _canonical_device_identifier(device) -> str | None:
    """
    Clave única para secretos cifrados por dispositivo (FK a device.identifier).
    Debe ser siempre el identificador FDO del registro, nunca dsp_id ni el parámetro de ruta
    si este difiere (p. ej. id numérico de fila).
    """
    ident = getattr(device, "identifier", None)
    if ident is None:
        return None
    s = str(ident).strip()
    return s or None


def _register_device_from_dsp_payload():
    """Shared implementation for DSP-based device registration endpoints."""
    dadm = get_dadm_instance()
    data = request.get_json() or {}

    logging.info("[POST /api/dsp] Request received. Payload keys: %s", list(data.keys()))
    logging.debug("[POST /api/dsp] Full payload: %s", data)

    try:
        device = dadm.device_service.register_device_from_dsp_payload(data)
        logging.info("[POST /api/dsp] Device registered successfully: device_id=%s, dsp_id=%s",
                     getattr(device, 'identifier', None), getattr(device, 'dsp_id', None))
    except DeviceRegistrationError as exc:
        logging.warning("[POST /api/dsp] Registration failed: code=%s message=%s details=%s",
                        exc.code, exc.message, exc.details)
        return jsonify({
            'error': exc.message,
            'code': exc.code,
            'details': exc.details
        }), exc.status_code

    return jsonify({
        'status': 'success',
        'message': 'Device registered successfully',
        'device': device_to_dict(device)
    }), 201

@devices_bp.route('/api/devices', methods=['GET'])
@handle_api_errors
@require_auth
def get_devices(current_user):
    """Gets the list of devices the current user may access (all of them for admins)."""
    dadm = get_dadm_instance()
    if current_user.get('role') in ('admin', 'superadmin'):
        devices = dadm.db.getAllDevices()
    else:
        devices = dadm.db.getDevicesForUser(current_user['id'])
    if devices is None:
        devices = []
    
    devices_list = []
    for device in devices:
        device_dict = device_to_dict(device)
        devices_list.append(device_dict)
    
    return jsonify({
        'devices': devices_list
    }), 200

@devices_bp.route('/api/devices/<device_id>', methods=['GET'])
@handle_api_errors
@require_auth
@require_device
def get_device(device_id, device, current_user):
    """Gets a specific device by ID"""
    dadm = get_dadm_instance()
    if str(device_id).strip() != str(_canonical_device_identifier(device) or ""):
        logger.debug(
            "get_device: route id=%r resolved device identifier=%r",
            device_id,
            getattr(device, "identifier", None),
        )
    device_dict = device_to_dict(device)
    try:
        scope = _canonical_device_identifier(device)
        device_dict['bearerTokenConfigured'] = bool(
            scope and dadm.db.getDeviceEnforcementSecret(scope, 'bearer_token') is not None
        )
    except Exception:  # pylint: disable=broad-except
        device_dict['bearerTokenConfigured'] = False
    return jsonify({
        'device': device_dict
    }), 200

@devices_bp.route('/api/devices/<device_id>', methods=['PUT'])
@handle_api_errors
@require_auth
@require_device
def update_device(device_id, device, current_user):
    """Updates device information"""
    dadm = get_dadm_instance()
    data = request.get_json()
    
    # Update allowed fields
    if 'name' in data:
        device.name = data['name']
    if 'ip' in data:
        device.ip = data['ip']
    if 'mac' in data:
        device.mac = data['mac']
    if 'model' in data:
        device.model = data['model']
    if 'type' in data:
        device.type = data['type']
    if 'manufacturer' in data:
        device.manufacturer = data['manufacturer']
    if 'status' in data:
        device.status = data['status']
    if 'edk' in data:
        device.edk = data['edk']
    if 'pilotId' in data:
        device.pilot_id = data['pilotId']
    if 'bearerToken' in data:
        btv = data.get('bearerToken')
        scope = _canonical_device_identifier(device)
        if btv is not None and isinstance(btv, str) and btv.strip():
            if not scope:
                return jsonify({
                    'error': 'Device has no identifier; cannot store encrypted bearer token',
                    'code': 'DEVICE_IDENTIFIER_REQUIRED',
                    'details': {}
                }), 400
            try:
                sm = dadm.policy_enforcement_service.secret_manager
                sm.ensure_ready_for_encryption()
            except Exception as exc:  # SecretKeyConfigurationError, etc.
                return jsonify({
                    'error': f'Enforcement secret encryption is not configured: {exc!s}',
                    'code': 'SECRET_ENCRYPTION_UNCONFIGURED',
                    'details': {}
                }), 503
            try:
                enc = sm.encrypt(btv.strip())
                dadm.db.upsertDeviceEnforcementSecret(
                    scope,
                    'bearer_token',
                    ciphertext=enc['ciphertext'],
                    nonce=enc['nonce'],
                    key_version=enc['key_version'],
                )
            except Exception as exc:
                logging.exception("Failed to store device bearer token")
                return jsonify({
                    'error': str(exc),
                    'code': 'DEVICE_SECRET_STORE_FAILED',
                    'details': {}
                }), 500
        elif btv is None or btv == '':
            if scope:
                try:
                    dadm.db.deleteDeviceEnforcementSecret(scope, 'bearer_token')
                except Exception as exc:
                    logging.warning("Delete device bearer secret: %s", exc)
    if 'enforcementContext' in data:
        enc = data['enforcementContext']
        if enc is None or enc == {}:
            device.enforcement_context = None
        elif isinstance(enc, dict):
            device.enforcement_context = json.dumps(enc, ensure_ascii=True)
        else:
            return jsonify({
                'error': 'enforcementContext must be a JSON object or null',
                'code': 'INVALID_REQUEST',
                'details': {}
            }), 400
    # MUD URL compatibility (snake_case, camelCase and legacy key)
    if 'mudurl' in data:
        device.mudurl = data['mudurl']
    elif 'mud_url' in data:
        device.mudurl = data['mud_url']
    elif 'mudUrl' in data:
        device.mudurl = data['mudUrl']
    
    success = dadm.db.updateDevice(device)
    if success:
        updated_device = dadm.db.getDevice(_canonical_device_identifier(device) or device_id)
        out = device_to_dict(updated_device) if updated_device else device_to_dict(device)
        try:
            scope = _canonical_device_identifier(updated_device) if updated_device else _canonical_device_identifier(device)
            out['bearerTokenConfigured'] = bool(
                scope and dadm.db.getDeviceEnforcementSecret(scope, 'bearer_token') is not None
            )
        except Exception:  # pylint: disable=broad-except
            out['bearerTokenConfigured'] = False
        return jsonify({
            'device': out
        }), 200
    else:
        return jsonify({
            'error': 'Failed to update device',
            'code': 'UPDATE_FAILED',
            'details': {}
        }), 500

@devices_bp.route('/api/devices/<device_id>/enforcement-gaps', methods=['POST'])
@handle_api_errors
@require_auth
@require_device
def post_device_enforcement_gaps(device_id, device, current_user):
    """
    Returns missing enforcement context for arbitrary MSPL (e.g. threat mitigations
    that are not resolvable as persisted policy ids).
    Body: { "msplXml": "...", "extraContext": { } optional }
    """
    data = request.get_json(silent=True) or {}
    mspl = data.get('msplXml') or data.get('mspl_xml')
    if not mspl or not isinstance(mspl, str) or not mspl.strip():
        return jsonify({
            'error': 'msplXml (or mspl_xml) is required and must be a non-empty string',
            'code': 'INVALID_REQUEST',
            'details': {}
        }), 400
    extra = data.get('extraContext') if isinstance(data.get('extraContext'), dict) else None
    dadm = get_dadm_instance()
    try:
        gaps = dadm.policy_enforcement_service.compute_enforcement_gaps(mspl.strip(), device, extra)
        return jsonify(gaps), 200
    except EnforcementNotConfiguredError as exc:
        return jsonify({
            'error': str(exc),
            'code': 'ENFORCEMENT_NOT_CONFIGURED',
            'details': {'deviceId': device_id}
        }), 503

@devices_bp.route('/api/devices/<device_id>', methods=['DELETE'])
@handle_api_errors
@require_auth
@require_device
def delete_device(device_id, device, current_user):
    """Deletes a device"""
    dadm = get_dadm_instance()
    success = dadm.db.deleteDevice(device)
    if success:
        return jsonify({}), 200
    else:
        return jsonify({
            'error': 'Failed to delete device',
            'code': 'DELETE_FAILED',
            'details': {}
        }), 500

@devices_bp.route('/api/devices/<device_id>/passport', methods=['GET'])
@handle_api_errors
@require_auth
@require_device
def get_device_passport(device_id, device, current_user):
    """Gets the digital passport (DSP) of a device"""
    # DSP is stored in device.dsp as JSON string
    dsp_data = {}
    if device.dsp:
        try:
            dsp_data = json.loads(device.dsp)
        except json.JSONDecodeError:
            dsp_data = {'raw': device.dsp}
    
    return jsonify({
        'deviceId': device_id,
        'data': dsp_data
    }), 200

@devices_bp.route('/api/devices/<device_id>/mud', methods=['GET'])
@handle_api_errors
@require_auth
@require_device
def get_device_mud(device_id, device, current_user):
    """Gets the MUD file of a device"""
    mud_data = {}
    if device.mudfile:
        try:
            mud_json = json.loads(device.mudfile)
            mud_data = mud_json
        except json.JSONDecodeError:
            mud_data = {'raw': device.mudfile}
    
    # Extract MUD information according to specification
    mud_info = {
        'id': device.mudurl or f'mud-{device_id}',
        'deviceId': device_id,
        'mudVersion': None,
        'mudUrl': device.mudurl,
        'lastUpdate': None,
        'cacheValidity': None,
        'isSupported': True,
        'systeminfo': None,
        'mfgName': None,
        'documentation': None,
        'modelName': None,
        'mudData': mud_data
    }
    
    # Try to extract metadata from MUD
    if isinstance(mud_data, dict):
        mud_section = mud_data.get('ietf-mud:mud', {})
        mud_info['mudVersion'] = mud_section.get('mud-version')
        mud_info['mfgName'] = mud_section.get('mfg-name', '')
        mud_info['modelName'] = mud_section.get('model-name', '')
        mud_info['documentation'] = mud_section.get('documentation', '')
        mud_info['systeminfo'] = mud_section.get('systeminfo', '')
        mud_info['lastUpdate'] = mud_section.get('last-update', '')
        mud_info['cacheValidity'] = mud_section.get('cache-validity')
        mud_info['isSupported'] = mud_section.get('is-supported', True)
    
    return jsonify(mud_info), 200


@devices_bp.route('/api/devices/<device_id>/logs', methods=['GET'])
@handle_api_errors
@require_auth
@require_device
def get_device_logs(device_id, device, current_user):
    """
    Returns onboarding timeline logs grouped by correlation_id.
    Includes:
      - onboarding_step rows (one per onboarding step)
      - policy_execution rows created by auto-enforce (when correlation_id is propagated)
      - policy_execution rows triggered manually (correlation_id is null)
    """
    dadm = get_dadm_instance()

    try:
        logs = (
            dadm.db.session.query(Database.PolicyExecutionLog)
            .filter(Database.PolicyExecutionLog.device_id == device_id)
            .filter(Database.PolicyExecutionLog.event_type.in_(["onboarding_step", "policy_execution", "feam_execution"]))
            .order_by(Database.PolicyExecutionLog.executed_at.asc(), Database.PolicyExecutionLog.id.asc())
            .all()
        )
    except Exception as exc:
        logging.error("Failed to query onboarding logs for device_id=%s: %s", device_id, exc, exc_info=True)
        return jsonify({
            "error": "Failed to list onboarding logs",
            "code": "ONBOARDING_LOGS_FAILED",
            "details": {},
        }), 500

    groups: dict[str, dict] = {}

    def _parse_request_preview(raw: str | None) -> dict | None:
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
        except Exception:
            return None
        return parsed if isinstance(parsed, dict) else None
    for log in logs:
        # Keep onboarding grouped by their real correlation_id.
        # Manual policy executions (correlation_id is null) are grouped under a synthetic id
        # so they are also visible in the device logs timeline.
        cid = log.correlation_id or f"manual-{log.id}"
        if cid not in groups:
            groups[cid] = {
                "correlationId": cid,
                "startedAt": log.executed_at.isoformat() if getattr(log, "executed_at", None) else None,
                "totalElapsedMs": 0.0,
                "bestCaseFetchDspMs": None,
                "_bestCheckPinMs": None,
                "_bestListMs": None,
                "steps": [],
            }

        if log.event_type == "onboarding_step" and log.elapsed_ms is not None:
            groups[cid]["totalElapsedMs"] += float(log.elapsed_ms)

        groups[cid]["steps"].append({
            "id": log.id,
            "eventType": log.event_type,
            "stepName": log.step_name,
            "elapsedMs": log.elapsed_ms,
            "result": log.result,
            "executedAt": log.executed_at.isoformat() if getattr(log, "executed_at", None) else None,
            "policyName": log.policy_name,
            "errorMessage": log.error_message,
            "requestPreview": log.request_preview,
        })

        if (
            log.event_type == "feam_execution"
            and str(log.step_name or "").startswith("callResourceServer_attempt_1")
            and log.elapsed_ms is not None
        ):
            preview = _parse_request_preview(log.request_preview)
            operation_name = str((preview or {}).get("operationName") or "").strip()
            if operation_name in {"list_insdsp", "list_gendsp"}:
                elapsed = float(log.elapsed_ms)
                current = groups[cid]["_bestListMs"]
                if current is None or elapsed < float(current):
                    groups[cid]["_bestListMs"] = elapsed

        if (
            log.event_type == "feam_execution"
            and str(log.step_name or "").strip() == "checkPin"
            and log.elapsed_ms is not None
        ):
            elapsed = float(log.elapsed_ms)
            current = groups[cid]["_bestCheckPinMs"]
            if current is None or elapsed < float(current):
                groups[cid]["_bestCheckPinMs"] = elapsed

    for group in groups.values():
        list_ms = group.get("_bestListMs")
        checkpin_ms = group.get("_bestCheckPinMs")
        if list_ms is not None and checkpin_ms is not None:
            group["bestCaseFetchDspMs"] = float(list_ms) + float(checkpin_ms)
        elif list_ms is not None:
            group["bestCaseFetchDspMs"] = float(list_ms)
        else:
            group["bestCaseFetchDspMs"] = None
        group.pop("_bestCheckPinMs", None)
        group.pop("_bestListMs", None)

    # Deterministic ordering by startedAt
    onboardings = list(groups.values())
    onboardings.sort(key=lambda o: o.get("startedAt") or "")

    return jsonify({
        "onboardings": onboardings
    }), 200

@devices_bp.route('/api/devices/<device_id>/apply-idsp2', methods=['POST'])
@handle_api_errors
@require_auth
def apply_idsp2(device_id, current_user):
    """Applies an IDSP2 ID to a device"""
    dadm = get_dadm_instance()
    data = request.get_json()
    idsp2_id = data.get('idsp2Id') if data else None
    
    if not idsp2_id:
        return jsonify({
            'error': 'idsp2Id is required',
            'code': 'INVALID_REQUEST',
            'details': {}
        }), 400
    
    device = dadm.db.getDevice(device_id)
    if device is not None and not dadm.db.userCanAccessDevice(current_user, device):
        return jsonify({
            'error': f'Device with id {device_id} not found',
            'code': 'DEVICE_NOT_FOUND',
            'details': {}
        }), 404
    if device is None:
        # If device doesn't exist, create a new one
        device = dadm.db.parseDeviceJson({
            'device_id': device_id,
            'DSP_id': idsp2_id
        })
    
    # Register DSP using existing method
    device.dsp_id = idsp2_id
    result = dadm.register_dsp(device)
    
    if result:
        return jsonify({
            'status': 'pending',
            'message': 'IDSP2 application initiated'
        }), 200
    else:
        return jsonify({
            'error': 'Failed to apply IDSP2',
            'code': 'APPLICATION_FAILED',
            'details': {}
        }), 500

@devices_bp.route('/api/dsp', methods=['POST'])
@handle_api_errors
@require_auth
def register_dsp_device(current_user):
    """API endpoint for registering a device directly from its DSP ID."""
    logging.info("[POST /api/dsp] register_dsp_device called (user=%s)", getattr(current_user, 'username', current_user))
    return _register_device_from_dsp_payload()

# Legacy endpoints (maintain compatibility)
@devices_bp.route('/dsp', methods=['GET', 'POST'])
@handle_api_errors
def post_DSP():
    """Legacy endpoint for registering DSP"""
    if request.method == 'POST':
        data = request.get_json() or {}
        logging.info(f"Received registration: idsp_id={data.get('idsp_id') or data.get('idspId')} DSP_id={data.get('DSP_id') or data.get('dspId')} device_id={data.get('device_id') or data.get('deviceId')}")
        return _register_device_from_dsp_payload()
    elif request.method == 'GET':
        return jsonify({'status': 'success', 'message': 'GET request received'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Invalid request method'}), 405

@devices_bp.route('/devices', methods=['GET'])
@handle_api_errors
@require_auth
def printDevices(current_user):
    """Legacy endpoint for listing devices (admin only — leaks the full device list)"""
    if current_user.get('role') not in ('admin', 'superadmin'):
        return jsonify({'error': 'Forbidden', 'code': 'FORBIDDEN', 'details': {}}), 403
    dadm = get_dadm_instance()
    devices = dadm.printAllDevices()
    return jsonify({'status': 'success', 'message': 'Devices printed to console', 'data': devices}), 200

@devices_bp.route('/', methods=['GET'])
def list_endpoints():
    """Lists all available endpoints"""
    endpoints = [
        {
            'method': 'POST',
            'route': '/register_device',
            'description': 'Route to register device for the software upgrade use case.',
            'parameters': {
                'type': 'JSON',
                'fields': [
                    'mac: string',
                    'firmware_version: string',
                    'name: string',
                    'group_id: string',
                    'device_id: string',
                    'v_cred: JSON'
                ]
            }
        },
        {
            'method': 'POST',
            'route': '/register_software',
            'description': 'Route to register software versions in software upgrade case.',
            'parameters': {
                'type': 'JSON',
                'fields': [
                    'sw_identifier: string',
                    'sw_version: string',
                    'name: string'
                ]
            }
        },
        {
            'method': 'POST',
            'route': '/get_software',
            'description': 'Route to register software versions in software upgrade case.',
            'parameters': {
                'type': 'JSON',
                'fields': [
                    'sw_identifier: string',
                    'v_cred: JSON'
                ]
            }
        },
        {
            'method': 'POST',
            'route': '/update_status',
            'description': 'Update device status after update in the software upgrade use case.',
            'parameters': {
                'type': 'JSON',
                'fields': [
                    'device_id: string',
                    'update_id: string',
                    'status: string'
                ]
            }
        },
        {
            'method': 'POST',
            'route': '/boostrapping',
            'description': 'New device is finished the bootstrapping proccess',
            'parameters': {
                'type': 'JSON',
                'fields': [
                    'uuid: string',
                    'device: string',
                    'ip_address: string',
                    "mud-url: string"
                ]
            }
        }
    ]
    return endpoints
