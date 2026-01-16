# core/auth/jwt_service.py
"""
JWT token generation and verification service.
"""
import jwt
import logging
from typing import Optional
from datetime import datetime, timedelta, timezone
from flask import request
from core.config import Config
from core.auth.exceptions import AuthenticationError, TokenExpiredError

# Instancia global de configuración (se inicializará al importar)
_config = None

def _get_config():
    """Obtiene la instancia de configuración"""
    global _config
    if _config is None:
        _config = Config()
    return _config

def generate_access_token(user_id: int, email: str, role: str) -> str:
    """
    Genera un token JWT de acceso.
    
    Args:
        user_id: ID del usuario
        email: Email del usuario
        role: Rol del usuario ('user' o 'admin')
    
    Returns:
        str: Token JWT codificado
    """
    try:
        config = _get_config()
        secret_key = config.jwt_secret_key
        algorithm = config.jwt_algorithm
        expiration_hours = config.jwt_expiration_hours
        
        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=expiration_hours)
        
        payload = {
            'user_id': user_id,
            'email': email,
            'role': role,
            'type': 'access',
            'iat': int(now.timestamp()),
            'exp': int(exp.timestamp())
        }
        
        token = jwt.encode(payload, secret_key, algorithm=algorithm)
        return token
    except Exception as e:
        logging.error(f"Error generating access token: {e}", exc_info=True)
        raise AuthenticationError("Failed to generate access token", e)

def generate_refresh_token(user_id: int, email: str, role: str) -> str:
    """
    Genera un token JWT de refresh.
    
    Args:
        user_id: ID del usuario
        email: Email del usuario
        role: Rol del usuario ('user' o 'admin')
    
    Returns:
        str: Token JWT codificado
    """
    try:
        config = _get_config()
        secret_key = config.jwt_secret_key
        algorithm = config.jwt_algorithm
        expiration_hours = config.jwt_refresh_expiration_hours
        
        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=expiration_hours)
        
        payload = {
            'user_id': user_id,
            'email': email,
            'role': role,
            'type': 'refresh',
            'iat': int(now.timestamp()),
            'exp': int(exp.timestamp())
        }
        
        token = jwt.encode(payload, secret_key, algorithm=algorithm)
        return token
    except Exception as e:
        logging.error(f"Error generating refresh token: {e}", exc_info=True)
        raise AuthenticationError("Failed to generate refresh token", e)

def verify_token(token: str) -> dict:
    """
    Verifica y decodifica un token JWT.
    
    Args:
        token: Token JWT a verificar
    
    Returns:
        dict: Payload decodificado del token
    
    Raises:
        AuthenticationError: Si el token es inválido
        TokenExpiredError: Si el token ha expirado
    """
    try:
        config = _get_config()
        secret_key = config.jwt_secret_key
        algorithm = config.jwt_algorithm
        
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise AuthenticationError("Invalid token", e)
    except Exception as e:
        logging.error(f"Error verifying token: {e}", exc_info=True)
        raise AuthenticationError("Failed to verify token", e)

def get_token_from_request(request) -> Optional[str]:
    """
    Extrae el token JWT del header Authorization.
    
    Args:
        request: Objeto request de Flask
    
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
