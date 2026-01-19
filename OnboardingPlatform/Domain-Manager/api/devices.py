# api/devices.py
"""
Endpoints related to devices.
"""
from flask import Blueprint, jsonify, request
from utils.error_handlers import handle_api_errors, require_device
from utils.app_context import get_dadm_instance
from utils.formatters import device_to_dict
from core.auth.decorators import require_auth
from Database import DatabaseError
import logging
import json
from datetime import datetime

devices_bp = Blueprint('devices', __name__)

@devices_bp.route('/api/devices', methods=['GET'])
@handle_api_errors
@require_auth
def get_devices(current_user):
    """Gets the list of all devices"""
    dadm = get_dadm_instance()
    devices = dadm.db.getAllDevices()
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
    device_dict = device_to_dict(device)
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
    
    success = dadm.db.updateDevice(device)
    if success:
        updated_device = dadm.db.getDevice(device_id)
        return jsonify({
            'device': device_to_dict(updated_device)
        }), 200
    else:
        return jsonify({
            'error': 'Failed to update device',
            'code': 'UPDATE_FAILED',
            'details': {}
        }), 500

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

# Legacy endpoints (maintain compatibility)
@devices_bp.route('/dsp', methods=['GET', 'POST'])
@handle_api_errors
@require_auth
def post_DSP(current_user):
    """Legacy endpoint for registering DSP"""
    dadm = get_dadm_instance()
    if request.method == 'POST':
        data = request.get_json()
        logging.info(f"Received DSP ID: {data.get('DSP_id')} for Device ID: {data.get('device_id')}")
        device = dadm.db.parseDeviceJson(data)
        if dadm.register_dsp(device):
            return jsonify({'status': 'success', 'message': 'Data received and processed'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Device already exists'}), 400
    elif request.method == 'GET':
        return jsonify({'status': 'success', 'message': 'GET request received'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Invalid request method'}), 405

@devices_bp.route('/devices', methods=['GET'])
@handle_api_errors
@require_auth
def printDevices(current_user):
    """Legacy endpoint for listing devices"""
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

