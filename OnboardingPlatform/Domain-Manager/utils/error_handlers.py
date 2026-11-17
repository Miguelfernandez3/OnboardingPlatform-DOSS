# utils/error_handlers.py
"""
Decorators and functions for centralized error handling in API endpoints
"""
from functools import wraps
from flask import jsonify
from Database import DatabaseError
from core.auth.exceptions import AuthenticationError, AuthorizationError, TokenExpiredError, InvalidCredentialsError
from services.policy_enforcement_service import EnforcementPrerequisitesError, EnforcementDependencyError
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
        except AuthenticationError as e:
            logging.error(f"Authentication error in {f.__name__}: {e.message}", exc_info=True)
            return jsonify({
                'error': e.message,
                'code': 'AUTHENTICATION_ERROR',
                'details': {
                    'original_error': str(e.original_error) if e.original_error else None
                }
            }), 401
        except AuthorizationError as e:
            logging.error(f"Authorization error in {f.__name__}: {e.message}", exc_info=True)
            return jsonify({
                'error': e.message,
                'code': 'AUTHORIZATION_ERROR',
                'details': {
                    'original_error': str(e.original_error) if e.original_error else None
                }
            }), 403
        except TokenExpiredError as e:
            logging.error(f"Token expired error in {f.__name__}: {e.message}", exc_info=True)
            return jsonify({
                'error': e.message,
                'code': 'TOKEN_EXPIRED',
                'details': {
                    'original_error': str(e.original_error) if e.original_error else None
                }
            }), 401
        except InvalidCredentialsError as e:
            logging.error(f"Invalid credentials error in {f.__name__}: {e.message}", exc_info=True)
            return jsonify({
                'error': e.message,
                'code': 'INVALID_CREDENTIALS',
                'details': {
                    'original_error': str(e.original_error) if e.original_error else None
                }
            }), 401
        except DatabaseError as e:
            logging.error(f"Database error in {f.__name__}: {e.message}", exc_info=True)
            return jsonify({
                'error': e.message,
                'code': 'DATABASE_ERROR',
                'details': {
                    'original_error': str(e.original_error) if e.original_error else None
                }
            }), 500
        except EnforcementPrerequisitesError as e:
            logging.info(
                "Enforcement prerequisites in %s: %s missing=%s",
                f.__name__,
                e,
                getattr(e, "missing", None),
            )
            return jsonify({
                'error': 'Enforcement prerequisites not satisfied',
                'code': 'ENFORCEMENT_PREREQUISITES',
                'missing': list(getattr(e, 'missing', None) or []),
                'details': {},
            }), 409
        except EnforcementDependencyError as e:
            logging.warning(
                "Enforcement dependency failed in %s: %s status=%s url=%s",
                f.__name__,
                e,
                e.downstream_status,
                e.downstream_url,
            )
            return jsonify({
                'error': str(e) or 'Downstream enforcement service returned an error',
                'code': 'ENFORCEMENT_DEPENDENCY_FAILED',
                'details': {
                    'downstreamStatus': e.downstream_status,
                    'downstreamUrl': e.downstream_url,
                    'responseExcerpt': (e.response_excerpt or '')[:500],
                    'replicableRequest': e.replicable_request,
                    'replicableCurl': e.replicable_curl,
                },
            }), 424
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

        # Per-user access control. Return 404 (not 403) so users can't probe which
        # device ids exist. current_user is injected by require_auth (outer decorator);
        # if absent (unauthenticated route), skip the check.
        current_user = kwargs.get('current_user')
        if current_user is not None and not dadm.db.userCanAccessDevice(current_user, device):
            return jsonify({
                'error': f'Device with id {device_id} not found',
                'code': 'DEVICE_NOT_FOUND',
                'details': {}
            }), 404

        return f(device_id, device, *args, **kwargs)
    return decorated_function

