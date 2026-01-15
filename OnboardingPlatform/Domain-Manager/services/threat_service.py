# services/threat_service.py
"""
Service for handling threat-related logic.
Consolidates get_threats_from_threatmud_manager() and get_threat_by_id_from_threatmud_manager().
"""
from typing import Optional, List, Dict
from clients.threat_mud_client import ThreatMUDClient
import logging

class ThreatService:
    """
    Service for threat-related operations.
    """
    def __init__(self, threat_mud_client: ThreatMUDClient):
        """
        Args:
            threat_mud_client: Client for communicating with ThreatMUD Manager
        """
        self.threat_mud_client = threat_mud_client
    
    def get_threats(self, device_identifier: Optional[str] = None) -> List[Dict]:
        """
        Gets threats from ThreatMUDManager via REST API.
        Equivalent to get_threats_from_threatmud_manager() from the original code.
        
        Args:
            device_identifier: If provided, filters by device_identifier
        
        Returns:
            list: List of threats or empty list if error
        """
        return self.threat_mud_client.get_threats(device_identifier)
    
    def get_threat_by_id(self, threat_id: str) -> Optional[Dict]:
        """
        Gets a specific threat by ID from ThreatMUDManager via REST API.
        Equivalent to get_threat_by_id_from_threatmud_manager() from the original code.
        
        Args:
            threat_id: Threat ID
        
        Returns:
            dict: Threat data or None if not found
        """
        return self.threat_mud_client.get_threat_by_id(threat_id)
    
    def get_tmud_file(self, tmudurl: str) -> Optional[str]:
        """
        Gets a TMUD file from a URL.
        Equivalent to getTMUDFile() from the original code.
        
        Args:
            tmudurl: TMUD file URL
        
        Returns:
            str: TMUD file content or None if error
        """
        return self.threat_mud_client.get_tmud_file(tmudurl)

