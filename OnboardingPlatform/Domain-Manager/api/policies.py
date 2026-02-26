# api/policies.py
"""
Endpoints related to MSPL policies.
"""
from flask import Blueprint, jsonify, request
from utils.error_handlers import handle_api_errors, require_device
from utils.app_context import get_dadm_instance
from core.auth.decorators import require_auth
from datetime import datetime, timezone
import logging

policies_bp = Blueprint('policies', __name__)
logger = logging.getLogger(__name__)


def _user_for_log(current_user) -> str:
    """Returns a compact user identifier for logs."""
    if isinstance(current_user, dict):
        return str(
            current_user.get('username')
            or current_user.get('email')
            or current_user.get('id')
            or 'unknown'
        )
    return str(
        getattr(current_user, 'username', None)
        or getattr(current_user, 'email', None)
        or getattr(current_user, 'id', None)
        or 'unknown'
    )


def _policy_to_response(policy) -> dict:
    """Serializes a policy DB model to API response format."""
    return {
        'id': str(policy.id),
        'deviceId': policy.device_id,
        'name': policy.name,
        'status': policy.status,
        'enforcementStatus': policy.enforcement_status,
        'appliedAt': policy.applied_at.isoformat() if policy.applied_at else None,
        'policyType': policy.policy_type,
        'source': policy.source,
    }

@policies_bp.route('/api/devices/<device_id>/policies', methods=['GET'])
@handle_api_errors
@require_auth
@require_device
def get_device_policies(device_id, device, current_user):
    """Gets MSPL policies applied to a device"""
    dadm = get_dadm_instance()
    policies = dadm.policy_service.get_device_policies(device_id, device)
    return jsonify({
        'policies': policies
    }), 200

@policies_bp.route('/api/policies/translate-mud', methods=['POST'])
@handle_api_errors
@require_auth
def translate_mud(current_user):
    """
    Translates a full MUD JSON into MSPL policies and enrichment metadata.
    """
    dadm = get_dadm_instance()
    data = request.get_json(silent=True) or {}
    mud_json = data.get('mud') if isinstance(data.get('mud'), dict) else data

    if not isinstance(mud_json, dict):
        return jsonify({
            'error': 'A valid MUD JSON object is required',
            'code': 'INVALID_REQUEST',
            'details': {}
        }), 400

    try:
        policies = dadm.policy_service.translate_mud_json_to_policies(mud_json)
        logger.info(
            "MUD JSON translated to MSPL policies: translatedCount=%d, requestedBy='%s'",
            len(policies),
            _user_for_log(current_user),
        )
        return jsonify({
            'policies': policies
        }), 200
    except Exception as exc:
        logger.error("Error translating MUD JSON: %s", exc, exc_info=True)
        return jsonify({
            'error': str(exc),
            'code': 'TRANSLATION_FAILED',
            'details': {}
        }), 500

@policies_bp.route('/api/devices/<device_id>/apply-policy', methods=['POST'])
@handle_api_errors
@require_auth
@require_device
def apply_policy(device_id, device, current_user):
    """Creates an MSPL policy for a device and leaves it ready for enforcement."""
    dadm = get_dadm_instance()
    user_id = _user_for_log(current_user)
    
    # Get XML from body (can come as XML or JSON with msplXml field)
    content_type = request.headers.get('Content-Type', '')
    mspl_xml = None
    policy_name = None
    policy_type = 'manual'
    source = 'user'
    enforce_now = False
    logger.info(
        "Policy creation request received: deviceId='%s', contentType='%s', requestedBy='%s'",
        device_id,
        content_type,
        user_id,
    )
    
    if 'application/xml' in content_type:
        mspl_xml = request.data.decode('utf-8')
        policy_name = request.args.get('name')
    elif 'application/json' in content_type:
        data = request.get_json(silent=True) or {}
        mspl_xml = data.get('msplXml') or data.get('mspl')
        policy_name = data.get('name')
        policy_type = data.get('policyType') or data.get('policy_type') or 'manual'
        source = data.get('source') or 'user'
        enforce_now = bool(data.get('enforceNow', False))
        
        if not mspl_xml:
            return jsonify({
                'error': 'msplXml is required',
                'code': 'INVALID_REQUEST',
                'details': {}
            }), 400
    else:
        return jsonify({
            'error': 'Content-Type must be application/xml or application/json',
            'code': 'INVALID_CONTENT_TYPE',
            'details': {}
        }), 400
    
    # Create policy in Policy table (separate from mitigations)
    try:
        policy_name_final = policy_name or f'Policy {datetime.now().isoformat()}'
        logger.info(
            "Creating policy record: deviceId='%s', policyName='%s', policyType='%s', source='%s', enforceNow=%s, requestedBy='%s'",
            device_id,
            policy_name_final,
            policy_type,
            source,
            enforce_now,
            user_id,
        )
        policy = dadm.db.createPolicy(
            device_id=device_id,
            name=policy_name_final,
            mspl_xml=mspl_xml,
            policy_type=policy_type,
            source=source,
            status='pending',
            enforcement_status='pending'
        )
        
        if not policy:
            return jsonify({
                'error': 'Failed to create policy',
                'code': 'POLICY_CREATION_FAILED',
                'details': {}
            }), 500

        logger.info(
            "Policy record created: deviceId='%s', policyId='%s', policyName='%s', status='%s', enforcementStatus='%s'",
            device_id,
            str(policy.id),
            policy_name_final,
            policy.status,
            policy.enforcement_status,
        )

        # Optional compatibility mode: enforce immediately when explicitly requested.
        if enforce_now:
            try:
                logger.info(
                    "Immediate policy enforcement requested: deviceId='%s', policyId='%s', policyName='%s'",
                    device_id,
                    str(policy.id),
                    policy_name_final,
                )
                dadm.policy_enforcement_service.enforce_policy(mspl_xml, device, policy_name_final)
                policy.status = 'active'
                policy.enforcement_status = 'completed'
                policy.applied_at = datetime.now(timezone.utc)
                logger.info(
                    "Immediate policy enforcement completed: deviceId='%s', policyId='%s', policyName='%s'",
                    device_id,
                    str(policy.id),
                    policy_name_final,
                )
            except Exception as exc:
                logger.error(
                    "Immediate policy enforcement failed: deviceId='%s', policyId='%s', policyName='%s', error='%s'",
                    device_id,
                    str(policy.id),
                    policy_name_final,
                    exc,
                    exc_info=True,
                )
                policy.status = 'failed'
                policy.enforcement_status = 'failed'
            finally:
                dadm.db.updatePolicy(policy)
                logger.info(
                    "Immediate enforcement result persisted: deviceId='%s', policyId='%s', status='%s', enforcementStatus='%s'",
                    device_id,
                    str(policy.id),
                    policy.status,
                    policy.enforcement_status,
                )
        
        logger.info(
            "Policy creation flow finished: deviceId='%s', policyId='%s', policyName='%s', finalStatus='%s', finalEnforcementStatus='%s'",
            device_id,
            str(policy.id),
            policy_name_final,
            policy.status,
            policy.enforcement_status,
        )
        return jsonify({
            'status': policy.enforcement_status or 'pending',
            'message': 'Policy saved and ready for enforcement',
            'policy': _policy_to_response(policy)
        }), 200
    except Exception as e:
        logger.error(
            "Error creating policy: deviceId='%s', policyName='%s', requestedBy='%s', error='%s'",
            device_id,
            policy_name,
            user_id,
            e,
            exc_info=True,
        )
        raise

@policies_bp.route('/api/devices/<device_id>/policies/<policy_id>/enforce', methods=['POST'])
@handle_api_errors
@require_auth
@require_device
def enforce_policy(device_id, device, policy_id, current_user):
    """Enforces a policy by ID using the configured type->enforcement mapping."""
    dadm = get_dadm_instance()
    user_id = _user_for_log(current_user)
    logger.info(
        "Policy enforcement request received: deviceId='%s', policyId='%s', requestedBy='%s'",
        device_id,
        policy_id,
        user_id,
    )

    policy_data = dadm.policy_service.get_policy_for_enforcement(device_id, policy_id, device)
    if policy_data is None:
        logger.warning(
            "Policy enforcement target not found: deviceId='%s', policyId='%s', requestedBy='%s'",
            device_id,
            policy_id,
            user_id,
        )
        return jsonify({
            'error': f'Policy with id {policy_id} not found',
            'code': 'POLICY_NOT_FOUND',
            'details': {}
        }), 404

    policy_name = policy_data.get('name')
    mspl_xml = policy_data.get('msplXml')
    if not mspl_xml:
        logger.warning(
            "Policy enforcement rejected due to missing MSPL: deviceId='%s', policyId='%s', policyName='%s', requestedBy='%s'",
            device_id,
            policy_id,
            policy_name,
            user_id,
        )
        return jsonify({
            'error': 'Policy has no MSPL content',
            'code': 'INVALID_POLICY',
            'details': {'policyId': policy_id}
        }), 400

    logger.info(
        "Policy enforcement target resolved: deviceId='%s', policyId='%s', policyName='%s', source='%s', policyType='%s', persisted=%s",
        device_id,
        policy_id,
        policy_name,
        policy_data.get('source'),
        policy_data.get('policyType'),
        policy_data.get('isPersisted'),
    )

    persisted_policy = policy_data.get('policyModel')
    try:
        logger.info(
            "Policy enforcement execution started: deviceId='%s', policyId='%s', policyName='%s'",
            device_id,
            policy_id,
            policy_name,
        )
        enforcement_result = dadm.policy_enforcement_service.enforce_policy(
            mspl_xml,
            device,
            policy_name
        )
        logger.info(
            "Policy enforcement execution completed: deviceId='%s', policyId='%s', policyName='%s', profileId='%s', mode='%s'",
            device_id,
            policy_id,
            policy_name,
            enforcement_result.get('profileId'),
            (enforcement_result.get('execution') or {}).get('mode'),
        )

        if policy_data.get('isPersisted'):
            persisted_policy.status = 'active'
            persisted_policy.enforcement_status = 'completed'
            persisted_policy.applied_at = datetime.now(timezone.utc)
            if not persisted_policy.policy_type:
                persisted_policy.policy_type = policy_data.get('policyType')
            if not persisted_policy.source:
                persisted_policy.source = policy_data.get('source') or 'user'
            dadm.db.updatePolicy(persisted_policy)
            logger.info(
                "Policy enforcement persisted existing policy: deviceId='%s', policyId='%s', status='%s', enforcementStatus='%s'",
                device_id,
                str(persisted_policy.id),
                persisted_policy.status,
                persisted_policy.enforcement_status,
            )
        else:
            persisted_policy = dadm.db.createPolicy(
                device_id=device_id,
                name=policy_name or f'MUD Policy {policy_id}',
                mspl_xml=mspl_xml,
                policy_type=policy_data.get('policyType') or enforcement_result.get('policyType') or 'mud',
                source=policy_data.get('source') or 'mud_file',
                status='active',
                enforcement_status='completed'
            )
            logger.info(
                "Policy enforcement persisted dynamic MUD policy: deviceId='%s', policyId='%s', persistedPolicyId='%s'",
                device_id,
                policy_id,
                str(persisted_policy.id) if persisted_policy else None,
            )

        logger.info(
            "Policy enforcement flow finished successfully: deviceId='%s', policyId='%s', policyName='%s'",
            device_id,
            policy_id,
            policy_name,
        )
        return jsonify({
            'status': 'completed',
            'message': 'Policy enforcement completed',
            'policy': _policy_to_response(persisted_policy) if persisted_policy else None,
            'execution': enforcement_result.get('execution'),
            'profileId': enforcement_result.get('profileId'),
            'policyType': enforcement_result.get('policyType'),
        }), 200
    except Exception as exc:
        logger.error(
            "Policy enforcement failed: deviceId='%s', policyId='%s', policyName='%s', source='%s', policyType='%s', requestedBy='%s', error='%s'",
            device_id,
            policy_id,
            policy_name,
            policy_data.get('source'),
            policy_data.get('policyType'),
            user_id,
            exc,
            exc_info=True,
        )

        if policy_data.get('isPersisted') and persisted_policy is not None:
            persisted_policy.status = 'failed'
            persisted_policy.enforcement_status = 'failed'
            persisted_policy.applied_at = datetime.now(timezone.utc)
            dadm.db.updatePolicy(persisted_policy)
            logger.info(
                "Failed enforcement status persisted on existing policy: deviceId='%s', policyId='%s'",
                device_id,
                str(persisted_policy.id),
            )
        elif not policy_data.get('isPersisted'):
            # Persist failed executions from dynamic MUD policy for traceability.
            failed_policy = dadm.db.createPolicy(
                device_id=device_id,
                name=policy_name or f'MUD Policy {policy_id}',
                mspl_xml=mspl_xml,
                policy_type=policy_data.get('policyType') or 'mud',
                source=policy_data.get('source') or 'mud_file',
                status='failed',
                enforcement_status='failed'
            )
            logger.info(
                "Failed enforcement persisted for dynamic MUD policy: deviceId='%s', originalPolicyId='%s', persistedPolicyId='%s'",
                device_id,
                policy_id,
                str(failed_policy.id) if failed_policy else None,
            )

        return jsonify({
            'error': str(exc),
            'code': 'ENFORCEMENT_FAILED',
            'details': {
                'policyId': policy_id,
                'deviceId': device_id
            }
        }), 500

@policies_bp.route('/api/devices/<device_id>/policies/<policy_id>/enforcement-status', methods=['POST'])
@handle_api_errors
@require_auth
def update_policy_enforcement_status(device_id, policy_id, current_user):
    """
    Callback endpoint to receive enforcement status updates
    from DSP Enforcer/ERA after applying a policy
    """
    dadm = get_dadm_instance()
    logging.info(f"Received enforcement status update request for policy {policy_id} on device {device_id}")
    
    # 1. Validate request body
    data = request.get_json()
    if not data:
        logging.warning(f"Empty request body for enforcement status update")
        return jsonify({
            'error': 'Request body is required',
            'code': 'INVALID_REQUEST',
            'details': {}
        }), 400
    
    new_status = data.get('status')
    message = data.get('message', '')
    timestamp_str = data.get('timestamp')
    
    logging.debug(f"Enforcement status update data: status={new_status}, message={message}, timestamp={timestamp_str}")
    
    # 2. Validate status
    if new_status not in ['completed', 'failed']:
        logging.warning(f"Invalid status received: {new_status}")
        return jsonify({
            'error': 'Invalid status. Must be "completed" or "failed"',
            'code': 'INVALID_STATUS',
            'details': {
                'received_status': new_status,
                'valid_statuses': ['completed', 'failed']
            }
        }), 400
    
    # 3. Get policy
    policy = dadm.db.getPolicy(policy_id)
    if policy is None:
        logging.warning(f"Policy {policy_id} not found")
        return jsonify({
            'error': f'Policy with id {policy_id} not found',
            'code': 'POLICY_NOT_FOUND',
            'details': {}
        }), 404
    
    # 4. Verify that policy belongs to device
    if policy.device_id != device_id:
        logging.warning(f"Policy {policy_id} does not belong to device {device_id}. Policy belongs to {policy.device_id}")
        return jsonify({
            'error': 'Policy does not belong to this device',
            'code': 'POLICY_DEVICE_MISMATCH',
            'details': {
                'policy_device_id': policy.device_id,
                'requested_device_id': device_id
            }
        }), 400
    
    # 5. Update status
    old_enforcement_status = policy.enforcement_status
    old_status = policy.status
    
    policy.enforcement_status = new_status
    policy.status = 'active' if new_status == 'completed' else 'failed'
    
    # 6. Update applied_at if timestamp is provided
    if timestamp_str:
        try:
            # Parse timestamp (supports ISO 8601 with and without Z)
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str.replace('Z', '+00:00')
            policy.applied_at = datetime.fromisoformat(timestamp_str)
            logging.debug(f"Applied timestamp from request: {policy.applied_at}")
        except ValueError as e:
            logging.warning(f"Invalid timestamp format '{timestamp_str}': {e}. Using current time.")
            policy.applied_at = datetime.now(timezone.utc)
    else:
        # If no timestamp provided and still doesn't have applied_at, use now
        if policy.applied_at is None:
            policy.applied_at = datetime.now(timezone.utc)
            logging.debug(f"Set applied_at to current time: {policy.applied_at}")
    
    # 7. Save changes using updatePolicy
    policy.updated_at = datetime.now(timezone.utc)
    success = dadm.db.updatePolicy(policy)
    
    if not success:
        logging.error(f"Failed to update policy {policy_id} in database")
        return jsonify({
            'error': 'Failed to update policy',
            'code': 'UPDATE_FAILED',
            'details': {}
        }), 500
    
    logging.info(f"Policy {policy_id} enforcement status updated: {old_enforcement_status} -> {new_status}, status: {old_status} -> {policy.status}")
    
    # 8. Return response
    return jsonify({
        'status': 'success',
        'message': 'Enforcement status updated',
        'policy': _policy_to_response(policy)
    }), 200

@policies_bp.route('/api/devices/<device_id>/enforcement-status', methods=['GET'])
@handle_api_errors
@require_auth
@require_device
def get_enforcement_status(device_id, device, current_user):
    """Gets the enforcement status of a device based on real policies"""
    dadm = get_dadm_instance()
    status = dadm.policy_service.get_enforcement_status(device_id, device)
    return jsonify(status), 200
