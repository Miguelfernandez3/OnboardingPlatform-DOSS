# services/feam_service.py
"""
Service for handling FEAM-related logic.
Consolidates prepareFEAM(), FEAMcheckPIN() and FEAMgetDSPfromID().
"""
from typing import Optional
from clients.feam_client import FEAMClient
import logging
import json

class FEAMService:
    """
    Service for FEAM-related operations.
    """
    def __init__(self, feam_client: FEAMClient):
        """
        Args:
            feam_client: Client for communicating with FEAM
        """
        self.feam_client = feam_client
    
    def prepare(self) -> None:
        """
        Prepares the FEAM server (initialization and stop PIN timer).
        Equivalent to prepareFEAM() from the original code.
        Maintains behavior of continuing even if it fails (DEVELOPMENT MODE).
        """
        # Initialize FEAM
        init_success = self.feam_client.init()
        
        # Stop PIN timer
        timer_success = self.feam_client.stop_forget_pin_timer()
        
        logging.info("FEAM initialization completed (may have failed if server is not available - DEVELOPMENT MODE)")
    
    def check_pin(self, pin: int = 1234) -> Optional[dict]:
        """
        Checks a PIN in FEAM.
        Equivalent to FEAMcheckPIN() from the original code.
        
        Args:
            pin: PIN to check (default: 1234)
            
        Returns:
            dict with response or None if error
        """
        return self.feam_client.check_pin(pin)
    
    def get_dsp_from_id(self, dsp_id: str) -> Optional[str]:
        """
        Gets a DSP from FEAM using its ID.
        Equivalent to FEAMgetDSPfromID() from the original code.
        
        Args:
            dsp_id: DSP ID
            
        Returns:
            str: FEAM response as text or None if error
        """
        return self.feam_client.get_dsp_from_id(dsp_id)

