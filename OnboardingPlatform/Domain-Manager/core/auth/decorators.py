# core/auth/decorators.py
"""
Decorators for authentication and authorization.
"""
from functools import wraps
from flask import jsonify, request
import logging
from core.auth.jwt_service import verify_token, get_token_from_request
from core.auth.exceptions import AuthenticationError, AuthorizationError, TokenExpiredError
from utils.app_context import get_dadm_instance

def require_auth(f):
    """
    Decorator que requiere un token JWT válido.
    Inyecta 'current_user' dict en kwargs con información del usuario.
    
    Uso:
        @require_auth
        def my_endpoint(current_user, ...):
            # current_user contiene: {'id': int, 'email': str, 'role': str}
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Extraer token del request
            token = get_token_from_request(request)
            if not token:
                return jsonify({
                    'error': 'Authentication required',
                    'code': 'AUTHENTICATION_REQUIRED',
                    'details': {}
                }), 401
            
            # Verificar token
            payload = verify_token(token)
            
            # Verificar que el usuario existe y está activo
            dadm = get_dadm_instance()
            if dadm is None:
                return jsonify({
                    'error': 'DeviceDomainManager not initialized',
                    'code': 'INITIALIZATION_ERROR',
                    'details': {}
                }), 500
            
            user = dadm.db.getUserById(payload['user_id'])
            if user is None:
                return jsonify({
                    'error': 'User not found',
                    'code': 'USER_NOT_FOUND',
                    'details': {}
                }), 401
            
            if not user.is_active:
                return jsonify({
                    'error': 'User account is inactive',
                    'code': 'USER_INACTIVE',
                    'details': {}
                }), 401
            
            # Inyectar current_user en kwargs
            kwargs['current_user'] = {
                'id': user.id,
                'email': user.email,
                'role': user.role
            }
            
            return f(*args, **kwargs)
        except TokenExpiredError as e:
            return jsonify({
                'error': str(e.message),
                'code': 'TOKEN_EXPIRED',
                'details': {}
            }), 401
        except AuthenticationError as e:
            return jsonify({
                'error': str(e.message),
                'code': 'AUTHENTICATION_ERROR',
                'details': {}
            }), 401
        except Exception as e:
            logging.error(f"Unexpected error in require_auth decorator: {e}", exc_info=True)
            return jsonify({
                'error': 'Authentication failed',
                'code': 'AUTHENTICATION_FAILED',
                'details': {}
            }), 401
    return decorated_function

def require_admin(f):
    """
    Decorator que requiere un token JWT válido y rol de administrador.
    Inyecta 'current_user' dict en kwargs con información del usuario.
    
    Uso:
        @require_admin
        def admin_endpoint(current_user, ...):
            # current_user contiene: {'id': int, 'email': str, 'role': str}
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Extraer token del request
            token = get_token_from_request(request)
            if not token:
                return jsonify({
                    'error': 'Authentication required',
                    'code': 'AUTHENTICATION_REQUIRED',
                    'details': {}
                }), 401
            
            # Verificar token
            payload = verify_token(token)
            
            # Verificar rol de administrador
            if payload.get('role') != 'admin':
                return jsonify({
                    'error': 'Admin access required',
                    'code': 'AUTHORIZATION_ERROR',
                    'details': {}
                }), 403
            
            # Verificar que el usuario existe y está activo
            dadm = get_dadm_instance()
            if dadm is None:
                return jsonify({
                    'error': 'DeviceDomainManager not initialized',
                    'code': 'INITIALIZATION_ERROR',
                    'details': {}
                }), 500
            
            user = dadm.db.getUserById(payload['user_id'])
            if user is None:
                return jsonify({
                    'error': 'User not found',
                    'code': 'USER_NOT_FOUND',
                    'details': {}
                }), 401
            
            if not user.is_active:
                return jsonify({
                    'error': 'User account is inactive',
                    'code': 'USER_INACTIVE',
                    'details': {}
                }), 401
            
            if user.role != 'admin':
                return jsonify({
                    'error': 'Admin access required',
                    'code': 'AUTHORIZATION_ERROR',
                    'details': {}
                }), 403
            
            # Inyectar current_user en kwargs
            kwargs['current_user'] = {
                'id': user.id,
                'email': user.email,
                'role': user.role
            }
            
            return f(*args, **kwargs)
        except TokenExpiredError as e:
            return jsonify({
                'error': str(e.message),
                'code': 'TOKEN_EXPIRED',
                'details': {}
            }), 401
        except AuthenticationError as e:
            return jsonify({
                'error': str(e.message),
                'code': 'AUTHENTICATION_ERROR',
                'details': {}
            }), 401
        except Exception as e:
            logging.error(f"Unexpected error in require_admin decorator: {e}", exc_info=True)
            return jsonify({
                'error': 'Authentication failed',
                'code': 'AUTHENTICATION_FAILED',
                'details': {}
            }), 401
    return decorated_function

def optional_auth(f):
    """
    Decorator que opcionalmente valida un token JWT si está presente.
    Inyecta 'current_user' dict en kwargs solo si el token es válido.
    
    Uso:
        @optional_auth
        def public_endpoint(current_user=None, ...):
            if current_user:
                # Usuario autenticado
            else:
                # Usuario anónimo
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Extraer token del request
            token = get_token_from_request(request)
            if token:
                try:
                    # Verificar token
                    payload = verify_token(token)
                    
                    # Verificar que el usuario existe y está activo
                    dadm = get_dadm_instance()
                    if dadm:
                        user = dadm.db.getUserById(payload['user_id'])
                        if user and user.is_active:
                            kwargs['current_user'] = {
                                'id': user.id,
                                'email': user.email,
                                'role': user.role
                            }
                except Exception:
                    # Si hay error, simplemente no inyectar current_user
                    pass
        except Exception:
            # Si hay error, simplemente no inyectar current_user
            pass
        
        return f(*args, **kwargs)
    return decorated_function
