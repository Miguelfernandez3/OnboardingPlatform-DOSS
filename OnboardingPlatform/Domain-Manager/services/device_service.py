# services/device_service.py
"""
Service for handling device-related logic.
Consolidates register_dsp(), printAllDevices() and other device operations.
"""
from typing import List, Dict, Optional
import logging
import json
from Database import DatabaseError
from services.mud_service import MUDService
from services.feam_service import FEAMService

class DeviceService:
    """
    Service for device-related operations.
    """
    def __init__(self, db, mud_service: MUDService, feam_service: FEAMService):
        """
        Args:
            db: Database instance
            mud_service: Service for MUD operations
            feam_service: Service for FEAM operations
        """
        self.db = db
        self.mud_service = mud_service
        self.feam_service = feam_service
    
    def get_dsp(self, dsp_id: str) -> str:
        """
        Gets a DSP from FEAM.
        Equivalent to getDSP() from the original code.
        Maintains the hardcoded fallback if FEAM fails.
        
        Args:
            dsp_id: DSP ID
            
        Returns:
            str: DSP JSON as string
        """
        dsp_response = self.feam_service.get_dsp_from_id(dsp_id)
        logging.warning(f"New DSP File retrieved from DSPP. Updating entry in database.")
        
        if dsp_response:
            # Original code does replace of escaped quotes 
            json_response = json.loads(dsp_response.replace('\"', '"'))
            
            if json_response.get('status') == 'ok':
                dsp_json = json_response.get('responseJson')
                logging.debug(f"DSP JSON: {dsp_json}")
                return dsp_json
        
        # Hardcoded fallback 
        dsp_json = '{"signature":"RYFiVhs5YFNJQ7eR90ki1ryeGWRcI99iD4CSPaUfuPlYXjycjfrpyp/TP0z6Y63ndajAtj6BnuOqzSjHPL4hQvkRaaew/fqI12k3Xl19LK3ZABXmIFjOu7lfi3kHyMIVCgsDCSVJOBmJjDEW/d+Rr9gyoISuCkpPRFiw/6gelIg=","certificate":"MIIBxTCCAS6gAwIBAgIIZ04S/ociQiowDQYJKoZIhvcNAQELBQAwGzEZMBcGA1UEAxMQVGVzdCBDZXJ0aWZpY2F0ZTAeFw0yNTA0MjIxMTM1MDNaFw0yNjA0MjMxMTM1MDNaMBsxGTAXBgNVBAMTEFRlc3QgQ2VydGlmaWNhdGUwgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBAKuCNWExJ/0JBuguUiGYeanS6ieB4N2NhQDOG+w5tXxamuHSLvfAbjHQTJfaZSOBjdOOQbYYD7CUYcb3iOHEPYBVS7vN+lVfE4bAiNg7e440ms8Fv7xc4yMj3BLKMHrTJV3ohvK/+udww3DR5DLJ6tjdIx3myZqKjmcq8FmLTo8PAgMBAAGjEjAQMA4GA1UdDwEB/wQEAwIFoDANBgkqhkiG9w0BAQsFAAOBgQCGL32J9m28yRFZRG57W1Z3lDGpsOy6fOVCOCjO1EcmZboMyggg9oHEFmLwarMXOe2xVys1kT9oBgmNha96eTrFH1n6PuwN3WF6un/y6xNn+dP2XvkNKLHR7Mi/wVk25mW6UFbq8KtKqZ9yQHLKCu6QrqvzkF5RelVZn3A34GgirA==","dspFile":{"doss-dsp":{"uuid":"477ac7cd-c71e-444a-a124-f80c2f47393b","metadata":{"title":"Attacker genDSP","last-modified":"2025-07-09T16:40:00.000000","version":"1.0.0","dsp-model-version":"1.0.0"},"local-definitions":{"components":[{"uuid":"864b7845-54fd-44b4-8c4f-04a5ce648113","type":"this-system","title":"Attacker","description":"Attacker environment for vulnerability scanning and exploitation","links":[{"href":"attacker_sbom.json","rel":"SBOM file","media-type":"application/vnd.cyclonedx+json"},{"href":"http://localhost:8091/attacker_mud.json","rel":"MUD file","media-type":"application/mud+json"}],"status":{"state":"operational"}}]}}}}'
        logging.debug(f"DSP JSON (fallback): {dsp_json}")
        return dsp_json
    
    def register_dsp(self, device) -> bool:
        """
        Registers a device with its DSP.
        Equivalent to register_dsp() from the original code (lines 539-561).
        
        Args:
            device: Device object with dsp_id and identifier
            
        Returns:
            bool: True if registered correctly, False if already exists
        """
        existing_device = self.db.getDevice(device.identifier)
        
        if existing_device is not None:
            logging.info("Device already exists in database.")
            return False
        else:
            logging.warning(f"New device with identifier {device.identifier} joining. Creating entry in database.")
            dsp = self.get_dsp(device.dsp_id)
            device.dsp = dsp
            
            ret = self.mud_service.get_mud(device.dsp, device.identifier)
            if ret is None:
                logging.error(f"Failed to get MUD file for device {device.identifier}. Device registration aborted.")
                return False
            
            device.mudurl = ret['mudurl']
            device.mudfile = ret['mudfile']
            
            self.db.createdevice(device)
            logging.info("Device registered successfully.")
            self.db.printDevice(device)
            return True
    
    def get_all_devices_dict(self) -> List[Dict]:
        """
        Gets all devices as a list of dictionaries.
        Equivalent to printAllDevices() from the original code.
        
        Returns:
            list: List of dictionaries with device information
        """
        devices = self.db.getAllDevices()
        dvcs = []
        for device in devices:
            dvcs.append(self.db.printDevice(device))
        return dvcs

