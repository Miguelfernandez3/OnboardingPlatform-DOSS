# api/threats.py
"""
Endpoints related to threats.
"""
from flask import Blueprint, jsonify, request
from utils.error_handlers import handle_api_errors, require_device
from utils.app_context import get_dadm_instance
from core.auth.decorators import require_auth
import logging

threats_bp = Blueprint('threats', __name__)

@threats_bp.route('/api/devices/<device_id>/threats', methods=['GET'])
@handle_api_errors
@require_auth
@require_device
def get_device_threats(device_id, device, current_user):
    """Gets threats associated with a device"""
    logging.info(f"get_device_threats called for device_id: {device_id}")
    logging.debug(f"Device found: identifier={device.identifier}, type={type(device.identifier)}")
    
    # Validate that device.identifier exists
    if not device.identifier:
        logging.warning(f"Device {device_id} has no identifier, returning empty threats list")
        return jsonify({
            'threats': []
        }), 200
    
    # Get threats from ThreatMUDManager via REST API
    dadm = get_dadm_instance()
    logging.debug(f"Calling get_threats_from_threatmud_manager with identifier: {device.identifier}")
    threats_data = dadm.get_threats_from_threatmud_manager(device.identifier)
    logging.debug(f"Received threats_data: type={type(threats_data)}, length={len(threats_data) if isinstance(threats_data, list) else 'N/A'}")
    
    # Validate that threats_data is a list
    if not isinstance(threats_data, list):
        logging.error(f"threats_data is not a list: {type(threats_data)} = {threats_data}")
        threats_data = []
    
    threats = []
    logging.debug(f"Processing {len(threats_data)} threats")
    for idx, threat_data in enumerate(threats_data):
        try:
            logging.debug(f"Processing threat {idx}: type={type(threat_data)}, keys={list(threat_data.keys()) if isinstance(threat_data, dict) else 'N/A'}")
            if not isinstance(threat_data, dict):
                logging.warning(f"threat_data[{idx}] is not a dict: {type(threat_data)}")
                continue
            
            threats.append({
                'id': threat_data.get('id'),
                'identifier': threat_data.get('identifier'),
                'threat_mud_url': threat_data.get('threat_mud_url'),
                'threat_mud_file': threat_data.get('threat_mud_file'),
                'mitigation_actions': threat_data.get('mitigation_actions'),
                'deviceId': device_id
            })
        except Exception as e:
            logging.error(f"Error processing threat_data[{idx}]: {e}", exc_info=True)
            continue
    
    logging.info(f"Returning {len(threats)} threats for device {device_id}")
    return jsonify({
        'threats': threats
    }), 200

@threats_bp.route('/newthreat', methods=['POST'])
@handle_api_errors
@require_auth
def newThreat(current_user):
    """Legacy endpoint for new threat"""
    data = request.get_json()
    logging.info(f"Received new threat: {data}")
    return jsonify({'status': 'success', 'message': 'New threat received'}), 200

