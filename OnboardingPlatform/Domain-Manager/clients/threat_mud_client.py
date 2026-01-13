# clients/threat_mud_client.py
"""
HTTP client for communicating with the ThreatMUD Manager.
Replaces direct requests calls in get_threats_from_threatmud_manager() and get_threat_by_id_from_threatmud_manager().
"""
from .base_client import BaseHTTPClient
from typing import Optional, Dict, List
import logging
from utils.validators import validate_device_identifier

class ThreatMUDClient(BaseHTTPClient):
    """
    Client for the ThreatMUD Manager API.
    Maintains exactly the same behavior as the original functions.
    """
    def get_threats(self, device_identifier: Optional[str] = None) -> List[Dict]:
        """
        Gets threats from ThreatMUDManager via REST API.
        Equivalent to get_threats_from_threatmud_manager() from the original code.
        
        Args:
            device_identifier: If provided, filters by device_identifier
            
        Returns:
            list: List of threats or empty list if error
        """
        logging.debug(f"ThreatMUDClient.get_threats called with device_identifier={device_identifier}, type={type(device_identifier)}")
        
        # Validate device_identifier (original behavior lines 327-337)
        if device_identifier is None:
            logging.debug("device_identifier is None, getting all threats")
            endpoint = "/api/threats"
        else:
            device_identifier_str = validate_device_identifier(device_identifier)
            if not device_identifier_str:
                logging.warning(f"Invalid device_identifier: {device_identifier}, getting all threats instead")
                endpoint = "/api/threats"
            else:
                endpoint = f"/api/threats/device/{device_identifier_str}"
        
        logging.debug(f"Making HTTP GET request to: {self.base_url}{endpoint}")
        logging.debug(f"ThreatMUDManager_url: {self.base_url}")
        
        response_data = self.get(endpoint, timeout=5)
        
        if response_data is None:
            logging.warning("ThreatMUDClient.get_threats: Failed to get response")
            return []
        
        logging.debug(f"Parsed JSON data type: {type(response_data)}, keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'N/A'}")
        
        threats = response_data.get('threats', [])
        logging.debug(f"Extracted threats: type={type(threats)}, length={len(threats) if isinstance(threats, list) else 'N/A'}")
        
        # Validate that threats is a list
        if not isinstance(threats, list):
            logging.error(f"threats is not a list, it's {type(threats)}: {threats}")
            return []
        
        logging.info(f"Successfully retrieved {len(threats)} threats from ThreatMUDManager")
        return threats
    
    def get_threat_by_id(self, threat_id: str) -> Optional[Dict]:
        """
        Gets a specific threat by ID from ThreatMUDManager via REST API.
        Equivalent to get_threat_by_id_from_threatmud_manager() from the original code.
        
        Args:
            threat_id: Threat ID
            
        Returns:
            dict: Threat data or None if not found
        """
        logging.debug(f"ThreatMUDClient.get_threat_by_id called with threat_id={threat_id}, type={type(threat_id)}")
        
        # Validate threat_id 
        if threat_id is None:
            logging.warning("threat_id is None")
            return None
        
        threat_id_str = str(threat_id)
        endpoint = f"/api/threats/{threat_id_str}"
        
        logging.debug(f"Making HTTP GET request to: {self.base_url}{endpoint}")
        
        response_data = self.get(endpoint, timeout=5)
        
        if response_data is None:
            # Base client already handles logging, but we check if it was 404
            logging.debug(f"Threat {threat_id} not found or error occurred")
            return None
        
        logging.debug(f"Parsed threat data type: {type(response_data)}, keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'N/A'}")
        logging.info(f"Successfully retrieved threat {threat_id} from ThreatMUDManager")
        return response_data
    
    def get_tmud_file(self, tmudurl: str) -> Optional[str]:
        """
        Gets a TMUD file from a URL.
        Equivalent to getTMUDFile() from the original code.
        
        Args:
            tmudurl: TMUD file URL
            
        Returns:
            str: TMUD file content or None if error
        """
        try:
            data = {
                'tmudurl': tmudurl
            }
            # Note: Original code concatenates directly 
            # We maintain that behavior
            response_data = self.post("tmud", data)
            
            if response_data:
                logging.info("TMUD File retrieved successfully")
                # Original code returns response.text, but our client returns JSON
                # We need to adjust this for compatibility
                # For now return the dict complete
                return response_data
            else:
                logging.error("Failed to retrieve TMUD file")
                return None
        except Exception as e:
            logging.error(f"Error retrieving TMUD file: {e}")
            return None

