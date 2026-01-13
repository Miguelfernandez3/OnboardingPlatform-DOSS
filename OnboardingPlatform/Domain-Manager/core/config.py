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

