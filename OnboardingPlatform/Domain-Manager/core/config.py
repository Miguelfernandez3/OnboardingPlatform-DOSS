# core/config.py
"""
Centralized configuration management.
Reads and exposes configuration from config.yaml.
"""
import yaml
import os
import logging

class Config:
    """
    Class for managing application configuration.
    """
    def __init__(self, config_path: str = 'config.yaml'):
        """
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self._config = None
        self._load_config()
    
    def _load_config(self):
        """Loads configuration from YAML file."""
        try:
            with open(self.config_path) as f:
                self._config = yaml.load(f, Loader=yaml.FullLoader)
        except FileNotFoundError:
            logging.error(f"Config file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logging.error(f"Error parsing config file: {e}")
            raise
    
    @property
    def broker(self) -> str:
        """Kafka broker."""
        return self._config['DeviceDomainManager']['Broker']
    
    @property
    def feam_server(self) -> str:
        """FEAM server URL."""
        return self._config['DeviceDomainManager']['FEAM_server']
    
    @property
    def feam_session_id(self) -> str:
        """Session ID for FEAM."""
        return self._config['DeviceDomainManager']['FEAM_sessionId']
    
    @property
    def threat_mud_manager_url(self) -> str:
        """ThreatMUD Manager URL."""
        return self._config['DeviceDomainManager'].get('ThreatMUDManager_url', 'http://localhost:8889')
    
    @property
    def mud_manager_url(self) -> str:
        """MUD Manager URL."""
        return self._config['DeviceDomainManager'].get('MUDManager_url', 'http://localhost:8888')
    
    @property
    def topics(self) -> list:
        """List of Kafka topics."""
        return self._config.get('DeviceDomainManager', {}).get('topics', [])

    @property
    def jwt_secret_key(self) -> str:
        """JWT secret key for token signing."""
        # Primero intentar desde variable de entorno
        env_key = os.getenv('JWT_SECRET_KEY')
        if env_key:
            return env_key
        
        # Luego desde config.yaml
        auth_config = self._config.get('Authentication', {})
        secret_key = auth_config.get('jwt_secret_key')
        
        # Si es una referencia a variable de entorno (${JWT_SECRET_KEY})
        if secret_key and secret_key.startswith('${') and secret_key.endswith('}'):
            env_var = secret_key[2:-1]
            env_value = os.getenv(env_var)
            if env_value:
                return env_value
        
        # Si no hay secret key, usar un default (NO RECOMENDADO PARA PRODUCCIÓN)
        if not secret_key:
            logging.warning("JWT_SECRET_KEY not set. Using default (INSECURE). Set JWT_SECRET_KEY environment variable for production.")
            return "CHANGE_THIS_SECRET_KEY_IN_PRODUCTION"
        
        return secret_key
    
    @property
    def jwt_algorithm(self) -> str:
        """JWT algorithm for token signing."""
        auth_config = self._config.get('Authentication', {})
        return auth_config.get('jwt_algorithm', 'HS256')
    
    @property
    def jwt_expiration_hours(self) -> int:
        """JWT access token expiration time in hours."""
        auth_config = self._config.get('Authentication', {})
        return auth_config.get('jwt_expiration_hours', 24)
    
    @property
    def jwt_refresh_expiration_hours(self) -> int:
        """JWT refresh token expiration time in hours."""
        auth_config = self._config.get('Authentication', {})
        return auth_config.get('jwt_refresh_expiration_hours', 168)  # 7 días
    
    @property
    def password_min_length(self) -> int:
        """Minimum password length."""
        auth_config = self._config.get('Authentication', {})
        return auth_config.get('password_min_length', 8)

    @property
    def policy_enforcement_config(self) -> dict:
        """
        Policy enforcement configuration.
        Returns fixed mappings profile->execution and policyType->profile.
        """
        default_config = {
            'default_profile': 'era-default',
            'profiles': {
                'era-default': {
                    'mode': 'era'
                },
                'homeassistant-rest': {
                    'mode': 'rest',
                    'dry_run': True,
                    'endpoint': 'http://localhost:8123/api/services/automation/trigger',
                    'method': 'POST',
                    'timeout_seconds': 10,
                    'headers': {
                        'Content-Type': 'application/json'
                    },
                    'auth': {
                        'type': 'bearer',
                        'token_env': 'HOME_ASSISTANT_TOKEN'
                    },
                    'payload_template': {
                        'entity_id': '{{automation-id}}'
                    }
                }
            },
            'type_mappings': {
                'homeassistant-automation-mspl-type': 'homeassistant-rest',
                'homeassistant-mspl-type': 'homeassistant-rest',
                'boostrapping-mspl-type': 'era-default',
                'bootstrapping-mspl-type': 'era-default',
                'ipv4-mspl-type': 'era-default',
                'ipv6-mspl-type': 'era-default',
                'software-mspl-type': 'era-default'
            }
        }
        return self._config.get('PolicyEnforcement', default_config)
