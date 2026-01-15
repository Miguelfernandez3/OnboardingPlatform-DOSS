# services/mitigation_service.py
"""
Service for handling mitigation-related logic.
"""
from typing import List, Dict
from datetime import datetime
import logging
from utils.xml_parser import parse_mitigation_xml
from services.threat_service import ThreatService

class MitigationService:
    """
    Service for mitigation-related operations.
    """
    def __init__(self, db, threat_service: ThreatService):
        """
        Args:
            db: Database instance
            threat_service: Service for threat operations
        """
        self.db = db
        self.threat_service = threat_service
    
    def get_device_mitigations(self, device_id: str, device) -> List[Dict]:
        """
        Gets mitigations associated with a device.
        Equivalent to the logic in get_device_mitigations() endpoint.
        
        Args:
            device_id: Device ID
            device: Device object
            
        Returns:
            list: List of mitigations
        """
        mitigations = []
        
        # If device has mitigation_actions, create a mitigation
        if device.mitigation_actions:
            mitigation_data = parse_mitigation_xml(device.mitigation_actions)
            if mitigation_data:
                mitigations.append({
                    'id': f'mitigation-{device_id}',
                    'deviceId': device_id,
                    'name': 'Device Mitigation',
                    'description': 'Mitigation applied to device',
                    'mitigation_actions': device.mitigation_actions,
                    'is_enforced': True,
                    'last_enforced': datetime.now().isoformat(),
                    'enforcement_timestamp': datetime.now().isoformat()
                })
        
        # Also search for mitigations related to device threats
        logging.debug(f"Getting threats for mitigations, device identifier: {device.identifier}")
        if device.identifier:
            threats_data = self.threat_service.get_threats(device.identifier)
            logging.debug(f"Received threats_data for mitigations: type={type(threats_data)}, length={len(threats_data) if isinstance(threats_data, list) else 'N/A'}")
            
            # Validate that threats_data is a list
            if not isinstance(threats_data, list):
                logging.error(f"threats_data is not a list in mitigations: {type(threats_data)}")
                threats_data = []
            
            for idx, threat_data in enumerate(threats_data):
                try:
                    logging.debug(f"Processing threat {idx} for mitigation: type={type(threat_data)}")
                    if not isinstance(threat_data, dict):
                        logging.warning(f"threat_data[{idx}] is not a dict: {type(threat_data)}")
                        continue
                    
                    mitigation_actions = threat_data.get('mitigation_actions')
                    if mitigation_actions:
                        logging.debug(f"Adding mitigation for threat {threat_data.get('id')}")
                        mitigations.append({
                            'id': f'threat-mitigation-{threat_data.get("id")}',
                            'deviceId': device_id,
                            'threatId': threat_data.get('id'),
                            'name': f'Threat Mitigation {threat_data.get("id")}',
                            'description': f'Mitigation for threat {threat_data.get("threat_mud_url")}',
                            'mitigation_actions': mitigation_actions,
                            'is_enforced': False,
                            'last_enforced': None,
                            'enforcement_timestamp': None
                        })
                except Exception as e:
                    logging.error(f"Error processing threat_data[{idx}] for mitigation: {e}", exc_info=True)
                    continue
        else:
            logging.warning(f"Device {device_id} has no identifier, skipping threat mitigations")
        
        return mitigations

