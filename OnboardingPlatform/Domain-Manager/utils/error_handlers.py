# utils/error_handlers.py
"""
Decorators and functions for centralized error handling in API endpoints
"""
from functools import wraps
from flask import jsonify
from Database import DatabaseError
import logging
from utils.app_context import get_dadm_instance

def handle_api_errors(f):
    """
    Decorator to handle errors consistently across all endpoints.
    Maintains exactly the same behavior as the original code.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except DatabaseError as e:
            logging.error(f"Database error in {f.__name__}: {e.message}", exc_info=True)
            return jsonify({
                'error': e.message,
                'code': 'DATABASE_ERROR',
                'details': {
                    'original_error': str(e.original_error) if e.original_error else None
                }
            }), 500
        except Exception as e:
            logging.error(f"Unexpected error in {f.__name__}: {e}", exc_info=True)
            return jsonify({
                'error': str(e),
                'code': 'INTERNAL_ERROR',
                'details': {}
            }), 500
    return decorated_function

def require_device(f):
    """
    Decorator to validate that a device exists before executing the endpoint.
    Injects the device object as the second parameter.
    """
    @wraps(f)
    def decorated_function(device_id, *args, **kwargs):
        dadm = get_dadm_instance()
        if dadm is None:
            return jsonify({
                'error': 'DeviceDomainManager not initialized',
                'code': 'INITIALIZATION_ERROR',
                'details': {}
            }), 500
        
        device = dadm.db.getDevice(device_id)
        if device is None:
            return jsonify({
                'error': f'Device with id {device_id} not found',
                'code': 'DEVICE_NOT_FOUND',
                'details': {}
            }), 404
        
        return f(device_id, device, *args, **kwargs)
    return decorated_function

