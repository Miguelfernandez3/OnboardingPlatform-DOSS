# services/mud_service.py
"""
Service for handling MUD file related logic.
Consolidates getMUDUrlFromDSP() and getMUD() from the original code.
"""
import json
import logging
from typing import Optional, Dict
from clients.mud_manager_client import MUDManagerClient

class MUDService:
    """
    Service for MUD file operations.
    """
    def __init__(self, mud_manager_client: MUDManagerClient):
        """
        Args:
            mud_manager_client: Client for communicating with MUD Manager
        """
        self.mud_manager_client = mud_manager_client
    
    def get_mud_url_from_dsp(self, dsp_json) -> Optional[str]:
        """
        Extract MUD file URL from DSP JSON by looking for links with rel="MUD file".
        Equivalent to getMUDUrlFromDSP() from the original code.
        
        Args:
            dsp_json: The DSP JSON object (either string or dict)
        
        Returns:
            str: The href URL of the MUD file, or None if not found
        """
        try:
            # If dsp_json is a string, parse it
            if isinstance(dsp_json, str):
                dsp_data = json.loads(dsp_json)
            else:
                dsp_data = dsp_json
            
            # Navigate to components in the DSP structure
            components = dsp_data.get('dspFile', {}).get('doss-dsp', {}).get('local-definitions', {}).get('components', [])
            
            # Iterate through components to find MUD file links
            for component in components:
                links = component.get('links', [])
                for link in links:
                    # Check if this link is a MUD file
                    if link.get('rel') == 'MUD file':
                        return link.get('href')
            
            # If no MUD file found
            logging.warning("No MUD file link found in DSP")
            return None
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logging.error(f"Error parsing DSP JSON for MUD URL: {e}")
            return None
    
    def get_mud(self, dsp, device_identifier: str) -> Optional[Dict[str, str]]:
        """
        Gets the MUD file from MUD Manager via REST API.
        Equivalent to getMUD() from the original code.
        
        Args:
            dsp: Digital Service Passport (JSON)
            device_identifier: Device identifier
        
        Returns:
            dict: Dictionary with 'mudurl' and 'mudfile', or None if error
        """
        logging.debug(f"MUDService.get_mud called for device_identifier: {device_identifier}")
        
        mudurl = self.get_mud_url_from_dsp(dsp)
        if not mudurl:
            logging.error("No MUD URL found in DSP")
            return None
        
        return self.mud_manager_client.get_mud_file(mudurl, device_identifier)

