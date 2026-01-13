# clients/feam_client.py
"""
HTTP client for communicating with the FEAM server.
Replaces direct requests calls in prepareFEAM(), FEAMcheckPIN() and FEAMgetDSPfromID().
"""
from .base_client import BaseHTTPClient
from typing import Optional, Dict
import logging
import json
import requests

class FEAMClient(BaseHTTPClient):
    """
    Client for the FEAM API.
    Maintains exactly the same behavior as the original functions.
    """
    def __init__(self, base_url: str, session_id: str, timeout: int = 5):
        """
        Args:
            base_url: Base URL of the FEAM server
            session_id: Session ID for requests
            timeout: Timeout in seconds
        """
        super().__init__(base_url, timeout)
        self.session_id = session_id
    
    def _get_feam_headers(self) -> Dict[str, str]:
        """
        FEAM-specific headers (original behavior lines 98-101, etc.)
        """
        return {
            'user-agent': "vscode-restclient",
            'content-type': "application/json"
        }
    
    def _make_feam_request(self, endpoint: str, payload_dict: Dict) -> Optional[Dict]:
        """
        Makes a POST request to FEAM with the specific format required.
        
        Args:
            endpoint: Relative endpoint (e.g., '/init')
            payload_dict: Dictionary with payload data
            
        Returns:
            Dict with response or None if error
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_feam_headers()
        
        # FEAM requires payload as JSON string (original behavior)
        payload_str = json.dumps(payload_dict)
        
        logging.debug(f"FEAMClient._make_feam_request: {url}")
        logging.debug(f"Payload: {payload_str}")
        
        try:
            response = requests.post(url, data=payload_str, headers=headers, timeout=self.timeout)
            logging.debug(f"FEAMClient response status: {response.status_code}")
            logging.debug(f"FEAMClient response text: {response.text}")
            
            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError:
                    # If not JSON, return text
                    return {'text': response.text}
            else:
                logging.warning(f"FEAM server returned status {response.status_code}: {response.text}")
                return None
        except requests.exceptions.ConnectionError as e:
            logging.warning(f"FEAM server is not available at {self.base_url}: {e}")
            return None
        except requests.exceptions.Timeout as e:
            logging.warning(f"Timeout connecting to FEAM server at {self.base_url}: {e}")
            return None
        except Exception as e:
            logging.error(f"Error in FEAM request: {e}", exc_info=True)
            return None
    
    def init(self) -> bool:
        """
        Initializes the FEAM server.
        Equivalent to the first part of prepareFEAM() (lines 95-119).
        
        Returns:
            bool: True if initialized correctly, False otherwise
        """
        logging.info("Initializing FEAM server")
        
        payload = {"sessionId": self.session_id}
        response = self._make_feam_request("/init", payload)
        
        if response:
            logging.info("FEAM server is prepared")
            return True
        else:
            logging.warning("FEAM server is not prepared")
            logging.warning("Continuing without FEAM server initialization (DEVELOPMENT MODE)")
            return False
    
    def stop_forget_pin_timer(self) -> bool:
        """
        Stops the forget PIN timer in FEAM.
        Equivalent to the second part of prepareFEAM() (lines 121-142).
        
        Returns:
            bool: True if stopped correctly, False otherwise
        """
        logging.info("Stopping Forget Pin Timer")
        
        payload = {"sessionId": self.session_id}
        response = self._make_feam_request("/stopForgetPinTimer", payload)
        
        if response:
            logging.info("FEAM Forget Pin Timer is stopped")
            return True
        else:
            logging.warning("FEAM Forget Pin Timer is not stopped")
            return False
    
    def check_pin(self, pin: int = 1234) -> Optional[Dict]:
        """
        Checks a PIN in FEAM.
        Equivalent to FEAMcheckPIN() (lines 146-155).
        
        Args:
            pin: PIN to check (default: 1234)
            
        Returns:
            Dict with response or None if error
        """
        payload = {
            "sessionId": self.session_id,
            "pinCode": str(pin)
        }
        
        response = self._make_feam_request("/checkPin", payload)
        if response:
            logging.debug(f"FEAM checkPin response: {response}")
        return response
    
    def get_dsp_from_id(self, dsp_id: str) -> Optional[str]:
        """
        Gets a DSP from FEAM using its ID.
        Equivalent to FEAMgetDSPfromID() (lines 157-169).
        
        Args:
            dsp_id: DSP ID
            
        Returns:
            str: FEAM response as text or None if error
        """
        # First check PIN (original behavior line 158)
        self.check_pin()
        
        payload = {
            "sessionId": self.session_id,
            "functionId": "0bfae6a6-9281-4d38-ad18-b851ef9b86a0",
            "operationId": "0bfae6a6-4637-487c-a71a-9cba257304af",
            "extraValues": [json.dumps({"id": dsp_id, "version": "1.0.0"})]
        }
        
        response = self._make_feam_request("/callResourceServer", payload)
        
        if response:
            # Original code returns response.text directly
            # We need to return the text of the response
            if isinstance(response, dict) and 'text' in response:
                return response['text']
            else:
                return json.dumps(response)
        return None

