# clients/feam_client.py
"""
HTTP client for communicating with the FEAM server.
Replaces direct requests calls in prepareFEAM(), FEAMcheckPIN() and FEAMgetDSPfromID().
"""
from .base_client import BaseHTTPClient
from typing import Optional, Dict, Any, List
import logging
import json
import os
import time
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
        self.max_attempts = max(1, int(os.getenv("FEAM_HTTP_MAX_ATTEMPTS", "3")))
        self.retry_backoff_seconds = max(0.0, float(os.getenv("FEAM_HTTP_RETRY_BACKOFF_SECONDS", "0.2")))
    
    def _get_feam_headers(self) -> Dict[str, str]:
        """
        FEAM-specific headers (original behavior lines 98-101, etc.)
        """
        return {
            'user-agent': "vscode-restclient",
            'content-type': "application/json"
        }
    
    def _normalize_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Normalizes FEAM HTTP responses into a consistent shape.
        """
        parsed_body: Any = None
        parse_error: Optional[str] = None
        try:
            parsed_body = response.json()
        except ValueError as exc:
            parse_error = str(exc)
            parsed_body = response.text

        return {
            "ok": response.status_code == 200,
            "status_code": response.status_code,
            "body": parsed_body,
            "raw_text": response.text,
            "error": None if response.status_code == 200 else response.text,
            "json_parse_error": parse_error,
        }

    def post_raw(self, endpoint: str, payload_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends a raw FEAM POST request and returns a normalized response.
        """
        endpoint_name = endpoint.lstrip("/")
        forbidden_endpoints = {"init", "register", "activate"}
        if endpoint_name in forbidden_endpoints:
            return {
                "ok": False,
                "status_code": None,
                "body": None,
                "raw_text": "",
                "error": f"Forbidden FEAM endpoint: {endpoint_name}",
                "json_parse_error": None,
                "attempts": [],
            }

        url = f"{self.base_url}/{endpoint_name}"
        headers = self._get_feam_headers()
        payload_str = json.dumps(payload_dict)

        logging.debug("FEAMClient.post_raw: %s", url)
        logging.debug("FEAMClient.post_raw payload: %s", payload_str)
        attempts: List[Dict[str, Any]] = []
        last_error = "request_failed"
        for attempt_idx in range(1, self.max_attempts + 1):
            start = time.perf_counter()
            retryable_http_error = False
            try:
                response = requests.post(url, data=payload_str, headers=headers, timeout=self.timeout)
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                normalized = self._normalize_response(response)
                status_code = normalized.get("status_code")
                retryable_http_error = status_code in (408, 425, 429, 500, 502, 503, 504)
                attempts.append(
                    {
                        "attempt": attempt_idx,
                        "elapsed_ms": elapsed_ms,
                        "status_code": status_code,
                        "ok": bool(normalized.get("ok")),
                        "error": normalized.get("error"),
                    }
                )
                normalized["attempts"] = attempts
                logging.debug("FEAMClient.post_raw status=%s attempt=%s", status_code, attempt_idx)
                if normalized.get("ok") or not retryable_http_error or attempt_idx == self.max_attempts:
                    return normalized
                time.sleep(self.retry_backoff_seconds * attempt_idx)
                continue
            except requests.exceptions.ConnectionError as e:
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                last_error = f"connection_error: {e}"
                attempts.append(
                    {
                        "attempt": attempt_idx,
                        "elapsed_ms": elapsed_ms,
                        "status_code": None,
                        "ok": False,
                        "error": last_error,
                    }
                )
                logging.warning("FEAM server is not available at %s (attempt %s/%s): %s", self.base_url, attempt_idx, self.max_attempts, e)
            except requests.exceptions.Timeout as e:
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                last_error = f"timeout: {e}"
                attempts.append(
                    {
                        "attempt": attempt_idx,
                        "elapsed_ms": elapsed_ms,
                        "status_code": None,
                        "ok": False,
                        "error": last_error,
                    }
                )
                logging.warning("Timeout connecting to FEAM server at %s (attempt %s/%s): %s", self.base_url, attempt_idx, self.max_attempts, e)
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                last_error = f"unexpected_error: {e}"
                attempts.append(
                    {
                        "attempt": attempt_idx,
                        "elapsed_ms": elapsed_ms,
                        "status_code": None,
                        "ok": False,
                        "error": last_error,
                    }
                )
                logging.error("Error in FEAM request (attempt %s/%s): %s", attempt_idx, self.max_attempts, e, exc_info=True)

            if attempt_idx < self.max_attempts:
                time.sleep(self.retry_backoff_seconds * attempt_idx)

        return {
            "ok": False,
            "status_code": None,
            "body": None,
            "raw_text": "",
            "error": last_error,
            "json_parse_error": None,
            "attempts": attempts,
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
        normalized = self.post_raw(endpoint, payload_dict)
        if not normalized.get("ok"):
            logging.warning(
                "FEAM server returned non-OK response for %s: %s",
                endpoint,
                normalized.get("error"),
            )
            return None
        body = normalized.get("body")
        if isinstance(body, dict):
            return body
        return {"text": normalized.get("raw_text", "")}
    
    def init(self) -> bool:
        """
        Initializes the FEAM server.
        Equivalent to the first part of prepareFEAM() (lines 95-119).
        
        Returns:
            bool: True if initialized correctly, False otherwise
        """
        logging.info("Initializing FEAM server")
        
        logging.warning("FEAM init endpoint is forbidden by policy and will be skipped.")
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

    def get_functions_own(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Gets delegated functions from FEAM for the current user/session.
        """
        payload = {"sessionId": session_id or self.session_id}
        return self.post_raw("/getFunctionsOwn", payload)

    def call_resource_server(
        self,
        function_id: str,
        operation_id: str,
        extra_values: Optional[List[str]] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calls FEAM callResourceServer endpoint with operation identifiers.
        """
        payload: Dict[str, Any] = {
            "sessionId": session_id or self.session_id,
            "functionId": function_id,
            "operationId": operation_id,
        }
        if extra_values is not None:
            payload["extraValues"] = extra_values
        return self.post_raw("/callResourceServer", payload)

