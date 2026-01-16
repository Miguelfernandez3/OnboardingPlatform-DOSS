# shared_auth/decorators.py
"""
Decorators for authentication and authorization (shared across projects).
"""
from functools import wraps
from flask import jsonify, request
import logging
import os
import sys

# Importaciones relativas dentro del módulo shared_auth
# Si shared_auth está en el path, importamos directamente
# Si no, intentamos import relativo
try:
    from jwt_validator import verify_token, get_token_from_request
    from config import get_jwt_secret_key, get_jwt_algorithm
except ImportError:
    # Fallback: intentar importar como módulo
    try:
        from shared_auth.jwt_validator import verify_token, get_token_from_request
        from shared_auth.config import get_jwt_secret_key, get_jwt_algorithm
    except ImportError:
        # Último fallback: importar desde el directorio actual
        import importlib.util
        current_dir = os.path.dirname(os.path.abspath(__file__))
        jwt_validator_path = os.path.join(current_dir, 'jwt_validator.py')
        config_path = os.path.join(current_dir, 'config.py')
        
        spec_validator = importlib.util.spec_from_file_location("jwt_validator", jwt_validator_path)
        jwt_validator = importlib.util.module_from_spec(spec_validator)
        spec_validator.loader.exec_module(jwt_validator)
        
        spec_config = importlib.util.spec_from_file_location("config", config_path)
        config_module = importlib.util.module_from_spec(spec_config)
        spec_config.loader.exec_module(config_module)
        
        verify_token = jwt_validator.verify_token
        get_token_from_request = jwt_validator.get_token_from_request
        get_jwt_secret_key = config_module.get_jwt_secret_key
        get_jwt_algorithm = config_module.get_jwt_algorithm

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
            # Buscar config.yaml en el directorio de trabajo actual (donde se ejecuta la app)
            # Esto debería ser el directorio del proyecto (Extended-MUD-Manager o Extended-MUD-Server)
            config_path = os.path.join(os.getcwd(), 'config.yaml')
            if not os.path.exists(config_path):
                # Fallback: buscar en el directorio del archivo actual
                current_dir = os.path.dirname(os.path.abspath(__file__))
                parent_dir = os.path.dirname(current_dir)
                config_path = os.path.join(parent_dir, 'config.yaml')
            
            # Extraer token del request
            token = get_token_from_request(request, config_path)
            if not token:
                return jsonify({
                    'error': 'Authentication required',
                    'code': 'AUTHENTICATION_REQUIRED',
                    'details': {}
                }), 401
            
            # Verificar token
            secret_key = get_jwt_secret_key(config_path)
            algorithm = get_jwt_algorithm(config_path)
            payload = verify_token(token, secret_key, algorithm, config_path)
            
            # Inyectar current_user en kwargs
            kwargs['current_user'] = {
                'id': payload['user_id'],
                'email': payload['email'],
                'role': payload['role']
            }
            
            return f(*args, **kwargs)
        except Exception as e:
            error_message = str(e)
            if 'expired' in error_message.lower():
                return jsonify({
                    'error': error_message,
                    'code': 'TOKEN_EXPIRED',
                    'details': {}
                }), 401
            else:
                logging.error(f"Authentication error in {f.__name__}: {error_message}", exc_info=True)
                return jsonify({
                    'error': 'Authentication failed',
                    'code': 'AUTHENTICATION_ERROR',
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
            # Buscar config.yaml en el directorio de trabajo actual (donde se ejecuta la app)
            # Esto debería ser el directorio del proyecto (Extended-MUD-Manager o Extended-MUD-Server)
            config_path = os.path.join(os.getcwd(), 'config.yaml')
            if not os.path.exists(config_path):
                # Fallback: buscar en el directorio del archivo actual
                current_dir = os.path.dirname(os.path.abspath(__file__))
                parent_dir = os.path.dirname(current_dir)
                config_path = os.path.join(parent_dir, 'config.yaml')
            
            # Extraer token del request
            token = get_token_from_request(request, config_path)
            if not token:
                return jsonify({
                    'error': 'Authentication required',
                    'code': 'AUTHENTICATION_REQUIRED',
                    'details': {}
                }), 401
            
            # Verificar token
            secret_key = get_jwt_secret_key(config_path)
            algorithm = get_jwt_algorithm(config_path)
            payload = verify_token(token, secret_key, algorithm, config_path)
            
            # Verificar rol de administrador
            if payload.get('role') != 'admin':
                return jsonify({
                    'error': 'Admin access required',
                    'code': 'AUTHORIZATION_ERROR',
                    'details': {}
                }), 403
            
            # Inyectar current_user en kwargs
            kwargs['current_user'] = {
                'id': payload['user_id'],
                'email': payload['email'],
                'role': payload['role']
            }
            
            return f(*args, **kwargs)
        except Exception as e:
            error_message = str(e)
            if 'expired' in error_message.lower():
                return jsonify({
                    'error': error_message,
                    'code': 'TOKEN_EXPIRED',
                    'details': {}
                }), 401
            else:
                logging.error(f"Authentication error in {f.__name__}: {error_message}", exc_info=True)
                return jsonify({
                    'error': 'Authentication failed',
                    'code': 'AUTHENTICATION_ERROR',
                    'details': {}
                }), 401
    return decorated_function
