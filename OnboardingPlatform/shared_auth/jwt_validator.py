# shared_auth/jwt_validator.py
"""
JWT token validation for shared use across projects.
"""
import jwt
import logging
from flask import request

# Importación relativa dentro del módulo shared_auth
try:
    from config import get_jwt_secret_key, get_jwt_algorithm
except ImportError:
    # Fallback: intentar importar como módulo
    try:
        from shared_auth.config import get_jwt_secret_key, get_jwt_algorithm
    except ImportError:
        # Último fallback: importar desde el directorio actual
        import importlib.util
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(current_dir, 'config.py')
        
        spec = importlib.util.spec_from_file_location("config", config_path)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        
        get_jwt_secret_key = config_module.get_jwt_secret_key
        get_jwt_algorithm = config_module.get_jwt_algorithm

def verify_token(token, secret_key=None, algorithm=None, config_path='config.yaml'):
    """
    Verifica y decodifica un token JWT.
    
    Args:
        token: Token JWT a verificar
        secret_key: Secret key para verificar (si no se proporciona, se obtiene de config)
        algorithm: Algoritmo JWT (si no se proporciona, se obtiene de config)
        config_path: Ruta al archivo config.yaml
    
    Returns:
        dict: Payload decodificado del token
    
    Raises:
        Exception: Si el token es inválido o ha expirado
    """
    if secret_key is None:
        secret_key = get_jwt_secret_key(config_path)
    if algorithm is None:
        algorithm = get_jwt_algorithm(config_path)
    
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception("Token has expired")
    except jwt.InvalidTokenError as e:
        raise Exception(f"Invalid token: {str(e)}")
    except Exception as e:
        logging.error(f"Error verifying token: {e}", exc_info=True)
        raise Exception(f"Failed to verify token: {str(e)}")

def get_token_from_request(request, config_path='config.yaml'):
    """
    Extrae el token JWT del header Authorization.
    
    Args:
        request: Objeto request de Flask
        config_path: Ruta al archivo config.yaml (no usado, pero mantenido para compatibilidad)
    
    Returns:
        str: Token JWT o None si no se encuentra
    """
    try:
        auth_header = request.headers.get('Authorization', '')
        if not auth_header:
            return None
        
        # Formato esperado: "Bearer <token>"
        parts = auth_header.split(' ')
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None
        
        return parts[1]
    except Exception as e:
        logging.error(f"Error extracting token from request: {e}", exc_info=True)
        return None
