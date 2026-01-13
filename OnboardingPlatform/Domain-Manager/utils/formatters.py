# utils/formatters.py
"""
Functions for formatting device data and other objects
"""
from datetime import datetime, timezone

def device_to_dict(device):
    """
    Converts a Device SQLAlchemy object to dictionary according to DeviceData interface.
    Maintains exactly the same behavior as the original function.
    """
    # Format dates to ISO 8601 if they exist
    # Use getattr() for compatibility with old devices that don't have these fields
    created_at = None
    updated_at = None
    created_at_val = getattr(device, 'created_at', None)
    updated_at_val = getattr(device, 'updated_at', None)
    
    if created_at_val:
        created_at = created_at_val.isoformat()
    if updated_at_val:
        updated_at = updated_at_val.isoformat()
    
    return {
        'id': device.identifier or str(device.id),
        'name': getattr(device, 'name', None) or device.model or '',
        'type': getattr(device, 'type', None) or '',
        'manufacturer': getattr(device, 'manufacturer', None) or '',
        'model': device.model or '',
        'status': getattr(device, 'status', None) or 'active',
        'createdAt': created_at,
        'updatedAt': updated_at,
        'ip': device.ip,
        'mac': device.mac,
        'identifier': device.identifier,
        'mudurl': device.mudurl,
        'mudfile': device.mudfile,
        'mitigation_actions': device.mitigation_actions,
        'inventory_id': device.dsp_id,
        'edk': getattr(device, 'edk', None)
    }

