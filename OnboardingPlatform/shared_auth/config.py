# shared_auth/config.py
"""
Configuration for shared authentication module.
"""
import os
import yaml
import logging

def get_jwt_secret_key(config_path='config.yaml'):
    """
    Obtiene el JWT secret key desde variable de entorno o config.yaml.
    
    Args:
        config_path: Ruta al archivo config.yaml
    
    Returns:
        str: JWT secret key
    """
    # Primero intentar desde variable de entorno
    env_key = os.getenv('JWT_SECRET_KEY')
    if env_key:
        return env_key
    
    # Luego desde config.yaml
    try:
        with open(config_path) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
            auth_config = config.get('Authentication', {})
            secret_key = auth_config.get('jwt_secret_key')
            
            # Si es una referencia a variable de entorno (${JWT_SECRET_KEY})
            if secret_key and secret_key.startswith('${') and secret_key.endswith('}'):
                env_var = secret_key[2:-1]
                env_value = os.getenv(env_var)
                if env_value:
                    return env_value
            
            if secret_key:
                return secret_key
    except FileNotFoundError:
        logging.warning(f"Config file not found: {config_path}")
    except Exception as e:
        logging.warning(f"Error reading config file: {e}")
    
    # Si no hay secret key, usar un default (NO RECOMENDADO PARA PRODUCCIÓN)
    logging.warning("JWT_SECRET_KEY not set. Using default (INSECURE). Set JWT_SECRET_KEY environment variable for production.")
    return "CHANGE_THIS_SECRET_KEY_IN_PRODUCTION"

def get_jwt_algorithm(config_path='config.yaml'):
    """
    Obtiene el algoritmo JWT desde config.yaml.
    
    Args:
        config_path: Ruta al archivo config.yaml
    
    Returns:
        str: JWT algorithm (default: HS256)
    """
    try:
        with open(config_path) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
            auth_config = config.get('Authentication', {})
            return auth_config.get('jwt_algorithm', 'HS256')
    except Exception:
        return 'HS256'
