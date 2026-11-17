# api/mitigations.py
"""
Endpoints related to mitigations.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from utils.error_handlers import handle_api_errors, require_device
from utils.app_context import get_dadm_instance
from core.auth.decorators import require_auth
from utils.formatters import user_for_log
from services.mitigation_service import MitigationService
from services.policy_enforcement_service import EnforcementPrerequisitesError
from services.notifications.service import NotificationService
from datetime import datetime, timezone
import logging

mitigations_bp = Blueprint('mitigations', __name__)


@mitigations_bp.route('/api/devices/<device_id>/mitigations', methods=['GET'])
@handle_api_errors
@require_auth
@require_device
def get_device_mitigations(device_id, device, current_user):
    """Gets mitigations associated with a device."""
    dadm = get_dadm_instance()
    mitigations = dadm.mitigation_service.get_device_mitigations(device_id, device)
    return jsonify({
        'mitigations': mitigations
    }), 200


@mitigations_bp.route('/api/devices/<device_id>/mitigations/<mitigation_id>/enforce', methods=['POST'])
@handle_api_errors
@require_auth
@require_device
def enforce_mitigation(device_id, device, mitigation_id, current_user):
    """Applies (enforce) a mitigation on a device."""
    dadm = get_dadm_instance()
    logging.debug("Enforcing mitigation %s for device %s", mitigation_id, device_id)

    if not mitigation_id.startswith('threat-mitigation-'):
        return jsonify({
            'error': f'Mitigation with id {mitigation_id} not found',
            'code': 'MITIGATION_NOT_FOUND',
            'details': {}
        }), 404

    threat_id_str = mitigation_id.replace('threat-mitigation-', '')
    threat_data = dadm.threat_service.get_matching_threat_by_id(device, threat_id_str)
    if not threat_data:
        logging.warning("Threat mitigation %s not found for device %s", mitigation_id, device_id)
        return jsonify({
            'error': f'Mitigation with id {mitigation_id} not found',
            'code': 'MITIGATION_NOT_FOUND',
            'details': {}
        }), 404

    mitigation_actions = MitigationService._as_mspl_list(threat_data.get('mitigation_actions'))
    if not mitigation_actions:
        logging.warning("Threat %s has no mitigation actions", threat_id_str)
        return jsonify({
            'error': f'Mitigation with id {mitigation_id} has no actions',
            'code': 'MITIGATION_EMPTY',
            'details': {}
        }), 400

    body = request.get_json(silent=True) or {}
    user_extra = body.get('extraContext') if isinstance(body.get('extraContext'), dict) else {}
    base_extra = {
        'threat_id': threat_id_str,
        'threat_mud_url': threat_data.get('threat_mud_url'),
    }
    merged_extra = {**base_extra, **user_extra}

    execution_results = []
    requested_by = user_for_log(current_user)
    mitigation_name = f'Threat Mitigation {threat_id_str}'
    threat_mud_url = threat_data.get('threat_mud_url')
    for idx, mspl_xml in enumerate(mitigation_actions):
        try:
            execution_results.append(
                dadm.policy_enforcement_service.enforce_policy(
                    mspl_xml,
                    device,
                    policy_name=f'{mitigation_name} #{idx + 1}',
                    policy_id=f'{mitigation_id}-{idx + 1}',
                    requested_by=requested_by,
                    extra_context=dict(merged_extra),
                )
            )
        except EnforcementPrerequisitesError as exc:
            try:
                NotificationService(dadm.db).notify_mitigation_prerequisites(
                    device=device,
                    threat_id=threat_id_str,
                    mitigation_id=mitigation_id,
                    threat_mud_url=threat_mud_url,
                    mitigation_name=f'{mitigation_name} #{idx + 1}',
                    missing=list(exc.missing or []),
                    mspl_index=idx,
                )
            except Exception as notify_exc:
                logging.warning(
                    "Mitigation prerequisite notification failed: %s",
                    notify_exc,
                    exc_info=True,
                )
            raise

    enforced_at = datetime.now(timezone.utc).isoformat()
    snapshot = dadm.mitigation_service.build_applied_snapshot(threat_data, applied_at=enforced_at)
    success = dadm.db.updateDeviceMitigationActions(device_id, snapshot)
    if not success:
        return jsonify({
            'error': 'Failed to persist mitigation state',
            'code': 'MITIGATION_PERSIST_FAILED',
            'details': {}
        }), 500

    logging.info("Successfully enforced mitigation %s for device %s", mitigation_id, device_id)
    return jsonify({
        'mitigation': {
            'id': mitigation_id,
            'deviceId': device_id,
            'threatId': threat_id_str,
            'name': mitigation_name,
            'mitigation_actions': mitigation_actions,
            'is_enforced': True,
            'last_enforced': enforced_at,
            'enforcement_timestamp': enforced_at,
            'executionResults': execution_results,
        }
    }), 200


@mitigations_bp.route('/api/devices/<device_id>/mitigations/<mitigation_id>/revoke', methods=['POST'])
@handle_api_errors
@require_auth
@require_device
def revoke_mitigation(device_id, device, mitigation_id, current_user):
    """Revokes (revoke) a mitigation on a device."""
    dadm = get_dadm_instance()
    snapshot = dadm.mitigation_service.parse_applied_snapshot(getattr(device, 'mitigation_actions', None))
    success = dadm.db.updateDeviceMitigationActions(device_id, None)

    if success:
        dadm.policy_enforcement_service.record_execution(
            device_id=device_id,
            policy_id=str(snapshot.get('threatId') or mitigation_id) if snapshot else mitigation_id,
            policy_name=str(snapshot.get('name') or mitigation_id) if snapshot else mitigation_id,
            profile_id=None,
            result='completed',
            run_mode='revoke',
            is_test=False,
            response_excerpt='Threat mitigation revoked locally (no REST/firewall rollback in demo mode)',
            requested_by=user_for_log(current_user),
        )
        logging.info("Successfully revoked mitigation %s for device %s", mitigation_id, device_id)
        return jsonify({
            'mitigation': {
                'id': mitigation_id,
                'deviceId': device_id,
                'mitigation_actions': None,
                'is_enforced': False,
                'last_enforced': None,
                'enforcement_timestamp': None
            }
        }), 200

    return jsonify({
        'error': 'Failed to revoke mitigation',
        'code': 'REVOKE_FAILED',
        'details': {}
    }), 500
