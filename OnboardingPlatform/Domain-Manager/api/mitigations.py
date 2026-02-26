# api/mitigations.py
"""
Endpoints related to mitigations.
"""
from flask import Blueprint, jsonify
from utils.error_handlers import handle_api_errors, require_device
from utils.app_context import get_dadm_instance
from core.auth.decorators import require_auth
from datetime import datetime
import logging

mitigations_bp = Blueprint('mitigations', __name__)

@mitigations_bp.route('/api/devices/<device_id>/mitigations', methods=['GET'])
@handle_api_errors
@require_auth
@require_device
def get_device_mitigations(device_id, device, current_user):
    """Gets mitigations associated with a device"""
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
    """Applies (enforce) a mitigation on a device"""
    dadm = get_dadm_instance()
    
    # Search for the mitigation
    # If it's a threat mitigation, get it from ThreatMUDManager via REST API
    logging.debug(f"Enforcing mitigation {mitigation_id} for device {device_id}")
    if mitigation_id.startswith('threat-mitigation-'):
        threat_id_str = mitigation_id.replace('threat-mitigation-', '')
        logging.debug(f"Extracted threat_id: {threat_id_str}")
        
        threat_data = dadm.get_threat_by_id_from_threatmud_manager(threat_id_str)
        logging.debug(f"Received threat_data: type={type(threat_data)}, is None: {threat_data is None}")
        
        if threat_data:
            if not isinstance(threat_data, dict):
                logging.error(f"threat_data is not a dict: {type(threat_data)}")
            else:
                logging.debug(f"threat_data keys: {list(threat_data.keys())}")
                mitigation_actions = threat_data.get('mitigation_actions')
                logging.debug(f"mitigation_actions: type={type(mitigation_actions)}, is None: {mitigation_actions is None}")
                
                if mitigation_actions:
                    logging.info(f"Applying mitigation actions to device {device_id}")
                    # Apply mitigation to device
                    success = dadm.db.updateDeviceMitigationActions(device_id, mitigation_actions)
                    logging.debug(f"Device update success: {success}")
                    
                    if success:
                        # Call reconfigureDevice to apply the mitigation
                        # We need to get the updated device for reconfigureDevice
                        logging.debug(f"Calling reconfigureDevice for device {device_id}")
                        try:
                            # Get updated device for reconfigureDevice
                            updated_device = dadm.db.getDevice(device_id)
                            if updated_device:
                                dadm.reconfigureDevice(mitigation_actions, updated_device)
                                logging.info(f"Successfully enforced mitigation {mitigation_id}")
                        except Exception as e:
                            logging.error(f"Error in reconfigureDevice: {e}", exc_info=True)
                        
                        return jsonify({
                            'mitigation': {
                                'id': mitigation_id,
                                'deviceId': device_id,
                                'threatId': threat_id_str,
                                'name': f'Threat Mitigation {threat_id_str}',
                                'mitigation_actions': mitigation_actions,
                                'is_enforced': True,
                                'last_enforced': datetime.now().isoformat(),
                                'enforcement_timestamp': datetime.now().isoformat()
                            }
                        }), 200
                else:
                    logging.warning(f"threat_data has no mitigation_actions")
        else:
            logging.warning(f"threat_data is None for threat_id {threat_id_str}")
    
    return jsonify({
        'error': f'Mitigation with id {mitigation_id} not found',
        'code': 'MITIGATION_NOT_FOUND',
        'details': {}
    }), 404

@mitigations_bp.route('/api/devices/<device_id>/mitigations/<mitigation_id>/revoke', methods=['POST'])
@handle_api_errors
@require_auth
@require_device
def revoke_mitigation(device_id, device, mitigation_id, current_user):
    """Revokes (revoke) a mitigation on a device"""
    dadm = get_dadm_instance()
    
    # Revoke mitigation by removing mitigation_actions
    success = dadm.db.updateDeviceMitigationActions(device_id, None)
    
    if success:
        # Call reconfigureDevice to revoke the mitigation
        dadm.reconfigureDevice(None, device)
        logging.info(f"Successfully revoked mitigation {mitigation_id}")
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
    else:
        return jsonify({
            'error': 'Failed to revoke mitigation',
            'code': 'REVOKE_FAILED',
            'details': {}
        }), 500

