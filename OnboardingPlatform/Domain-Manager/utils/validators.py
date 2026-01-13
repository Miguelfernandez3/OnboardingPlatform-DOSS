# utils/validators.py
"""
Common validation functions
"""
import logging

def validate_device_identifier(device_identifier):
    """
    Validates that device_identifier is a valid string.
    Returns the validated string or None if invalid.
    """
    if device_identifier is None:
        return None
    
    device_identifier_str = str(device_identifier) if device_identifier else None
    if not device_identifier_str or device_identifier_str == 'None':
        logging.warning(f"Invalid device_identifier: {device_identifier}")
        return None
    
    return device_identifier_str

