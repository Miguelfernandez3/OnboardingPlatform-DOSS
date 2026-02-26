# core/auth/password_service.py
"""
Password hashing and verification service.
"""
from typing import Tuple
import bcrypt
import logging

# Límite máximo de bcrypt en bytes
BCRYPT_MAX_PASSWORD_LENGTH = 72

# Número de rounds para bcrypt
BCRYPT_ROUNDS = 12

def hash_password(password: str) -> str:
    """
    Genera un hash del password usando bcrypt.
    
    Args:
        password: Password en texto plano
    
    Returns:
        str: Password hasheado (como string)
    
    Note:
        Bcrypt limita los passwords a 72 bytes. Si el password es más largo,
        se truncará automáticamente a 72 bytes.
    """
    try:
        # Convertir a bytes para verificar longitud
        password_bytes = password.encode('utf-8')
        
        # Bcrypt tiene una limitación de 72 bytes
        if len(password_bytes) > BCRYPT_MAX_PASSWORD_LENGTH:
            logging.warning(f"Password exceeds {BCRYPT_MAX_PASSWORD_LENGTH} bytes, truncating")
            password_bytes = password_bytes[:BCRYPT_MAX_PASSWORD_LENGTH]
        
        # Generar salt y hash usando bcrypt directamente
        salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password_bytes, salt)
        
        # Devolver como string (bcrypt devuelve bytes)
        return hashed.decode('utf-8')
    except Exception as e:
        logging.error(f"Error hashing password: {e}", exc_info=True)
        raise

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica un password contra su hash.
    
    Args:
        plain_password: Password en texto plano
        hashed_password: Password hasheado almacenado
    
    Returns:
        bool: True si el password es correcto, False en caso contrario
    """
    try:
        # Convertir a bytes
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        
        # Truncar si es necesario para verificación
        if len(password_bytes) > BCRYPT_MAX_PASSWORD_LENGTH:
            password_bytes = password_bytes[:BCRYPT_MAX_PASSWORD_LENGTH]
        
        # Verificar usando bcrypt directamente
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logging.error(f"Error verifying password: {e}", exc_info=True)
        return False

def validate_password_strength(password: str, min_length: int = 8) -> Tuple[bool, str]:
    """
    Valida la fortaleza del password.
    
    Args:
        password: Password a validar
        min_length: Longitud mínima requerida
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not password:
        return False, "Password cannot be empty"
    
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters long"
    
    # Validar longitud máxima (bcrypt limita a 72 bytes)
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > BCRYPT_MAX_PASSWORD_LENGTH:
        return False, f"Password cannot be longer than {BCRYPT_MAX_PASSWORD_LENGTH} bytes (approximately {BCRYPT_MAX_PASSWORD_LENGTH} characters for ASCII)"
    
    return True, ""
