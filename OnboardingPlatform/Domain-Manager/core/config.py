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
        return (
            os.getenv('FEAM_SERVER_URL')
            or os.getenv('FEAM_SERVER')
            or self._config['DeviceDomainManager']['FEAM_server']
        )
    
    @property
    def feam_session_id(self) -> str:
        """Session ID for FEAM (env overrides config.yaml; used by docker compose env_file)."""
        return (
            os.getenv('FEAM_SESSION_ID')
            or os.getenv('FEAM_SESSIONID')
            or self._config['DeviceDomainManager']['FEAM_sessionId']
        )
    
    @property
    def threat_mud_manager_url(self) -> str:
        """ThreatMUD Manager URL."""
        return (
            os.getenv('THREAT_MUD_MANAGER_URL')
            or self._config['DeviceDomainManager'].get('ThreatMUDManager_url', 'http://localhost:8889')
        )
    
    @property
    def mud_manager_url(self) -> str:
        """MUD Manager URL."""
        return (
            os.getenv('MUD_MANAGER_URL')
            or self._config['DeviceDomainManager'].get('MUDManager_url', 'http://localhost:8888')
        )
    
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
    def dsp_threat_poll_interval_seconds(self) -> int:
        """Polling interval for DSP threat refresh."""
        raw_value = os.getenv('DSP_THREAT_POLL_INTERVAL_SECONDS')
        if raw_value:
            try:
                return max(1, int(raw_value))
            except ValueError:
                logging.warning(
                    "Invalid DSP_THREAT_POLL_INTERVAL_SECONDS='%s'. Falling back to default 5s.",
                    raw_value,
                )
        return 5

    @property
    def feam_sync_poll_interval_seconds(self) -> int:
        """Polling interval for FEAM read-model synchronization."""
        raw_value = os.getenv('FEAM_SYNC_POLL_INTERVAL_SECONDS')
        if raw_value:
            try:
                return max(10, int(raw_value))
            except ValueError:
                logging.warning(
                    "Invalid FEAM_SYNC_POLL_INTERVAL_SECONDS='%s'. Falling back to default 60s.",
                    raw_value,
                )
        return 60

    @property
    def log_retention_days(self) -> int:
        """Retention window in days for policy execution logs."""
        raw_value = os.getenv('LOG_RETENTION_DAYS')
        if raw_value:
            try:
                return max(0, int(raw_value))
            except ValueError:
                logging.warning(
                    "Invalid LOG_RETENTION_DAYS='%s'. Falling back to default 3.",
                    raw_value,
                )
        return 3

    @property
    def log_retention_interval_seconds(self) -> int:
        """Polling interval for retention loop."""
        raw_value = os.getenv('LOG_RETENTION_INTERVAL_SECONDS')
        if raw_value:
            try:
                return max(60, int(raw_value))
            except ValueError:
                logging.warning(
                    "Invalid LOG_RETENTION_INTERVAL_SECONDS='%s'. Falling back to default 21600s.",
                    raw_value,
                )
        return 21600

    @property
    def log_retention_vacuum_enabled(self) -> bool:
        """Whether SQLite VACUUM is enabled in retention loop."""
        raw_value = os.getenv('LOG_RETENTION_VACUUM_ENABLED')
        if raw_value is None:
            return True
        return raw_value.strip().lower() in {'1', 'true', 'yes', 'on'}

    @property
    def log_retention_vacuum_interval_seconds(self) -> int:
        """Minimum interval between VACUUM runs."""
        raw_value = os.getenv('LOG_RETENTION_VACUUM_INTERVAL_SECONDS')
        if raw_value:
            try:
                return max(300, int(raw_value))
            except ValueError:
                logging.warning(
                    "Invalid LOG_RETENTION_VACUUM_INTERVAL_SECONDS='%s'. Falling back to default 86400s.",
                    raw_value,
                )
        return 86400
