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

@policies_bp.route('/api/devices/<device_id>/apply-policy', methods=['POST'])
@handle_api_errors
@require_auth
@require_device
def apply_policy(device_id, device, current_user):
    """Applies an MSPL policy directly to a device"""
    dadm = get_dadm_instance()
    
    # Get XML from body (can come as XML or JSON with msplXml field)
    content_type = request.headers.get('Content-Type', '')
    mspl_xml = None
    policy_name = None
    
    if 'application/xml' in content_type:
        mspl_xml = request.data.decode('utf-8')
    elif 'application/json' in content_type:
        data = request.get_json()
        mspl_xml = data.get('msplXml') or data.get('mspl')
        policy_name = data.get('name')
        
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
        policy = dadm.db.createPolicy(
            device_id=device_id,
            name=policy_name_final,
            mspl_xml=mspl_xml,
            policy_type='manual',
            source='user',
            status='pending',
            enforcement_status='pending'
        )
        
        if policy:
            # Call reconfigureDevice to apply the policy
            dadm.reconfigureDevice(mspl_xml, device)
            
            return jsonify({
                'status': 'pending',
                'message': 'Policy application initiated'
            }), 200
        else:
            return jsonify({
                'error': 'Failed to create policy',
                'code': 'POLICY_CREATION_FAILED',
                'details': {}
            }), 500
    except Exception as e:
        logging.error(f"Error creating policy: {e}", exc_info=True)
        raise

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
        'policy': {
            'id': str(policy.id),
            'deviceId': policy.device_id,
            'name': policy.name,
            'status': policy.status,
            'enforcementStatus': policy.enforcement_status,
            'appliedAt': policy.applied_at.isoformat() if policy.applied_at else None
        }
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

