# clients/mud_manager_client.py
"""
HTTP client for communicating with the MUD Manager.
Replaces direct requests calls in getMUD().
"""
from .base_client import BaseHTTPClient
from typing import Optional, Dict
import logging

class MUDManagerClient(BaseHTTPClient):
    """
    Client for the MUD Manager API.
    Maintains exactly the same behavior as getMUD() original.
    """
    def get_mud_file(self, mudurl: str, device_identifier: str) -> Optional[Dict[str, str]]:
        """
        Gets the MUD file from MUD Manager via REST API.
        Equivalent to getMUD() from the original code.
        
        Args:
            mudurl: MUD file URL (without .json)
            device_identifier: Device identifier
            
        Returns:
            dict with 'mudurl' and 'mudfile', or None if error
        """
        logging.debug(f"MUDManagerClient.get_mud_file called for device_identifier: {device_identifier}")
        
        # Remove .json if exists 
        mudurl_clean = mudurl.replace(".json", "")
        logging.debug(f"Extracted MUD URL: {mudurl_clean}")
        
        data = {
            'mudurl': mudurl_clean,
            'device_identifier': device_identifier
        }
        
        logging.debug(f"Making HTTP POST request to: {self.base_url}/mud")
        logging.debug(f"MUDManager_url: {self.base_url}")
        logging.debug(f"Request payload: {data}")
        
        response_data = self.post('/mud', data, timeout=10)
        
        if response_data is None:
            logging.error("MUDManagerClient.get_mud_file: Failed to get response")
            return None
        
        logging.debug(f"Response JSON keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'N/A'}")
        
        mudfile = response_data.get('mudfile')
        if not mudfile:
            logging.error("Response JSON does not contain 'mudfile' key")
            return None
        
        result = {
            'mudurl': mudurl_clean,
            'mudfile': mudfile
        }
        
        logging.info(f"Successfully retrieved MUD file for device {device_identifier}")
        return result

