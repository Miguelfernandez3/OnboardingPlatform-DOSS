# clients/base_client.py
"""
Reusable HTTP client base class for all external service communications.
Centralizes HTTP request handling and error handling.
"""
import requests
import logging
from typing import Optional, Dict, Any

class BaseHTTPClient:
    """
    Base HTTP client that provides common methods for all external APIs.
    """
    def __init__(self, base_url: str, timeout: int = 5):
        """
        Args:
            base_url: Base URL of the service (without trailing slash)
            timeout: Timeout in seconds for requests
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Returns default headers for requests.
        Can be overridden by child classes.
        """
        return {
            'Content-Type': 'application/json'
        }
    
    def get(self, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Performs a GET request.
        
        Args:
            endpoint: Relative endpoint (e.g., '/api/threats')
            **kwargs: Additional arguments for requests.get()
            
        Returns:
            Dict with JSON response or None if error
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        # Allow per-request timeout override without duplicating the argument
        timeout = kwargs.pop('timeout', self.timeout)
        try:
            response = requests.get(url, timeout=timeout, **kwargs)
            logging.debug(f"{self.__class__.__name__}.get: {url} -> {response.status_code}")
            
            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError as e:
                    logging.error(f"{self.__class__.__name__}.get: JSON decode error: {e}")
                    return None
            else:
                logging.warning(f"{self.__class__.__name__}.get: Status {response.status_code}, response: {response.text[:200]}")
                return None
        except requests.exceptions.ConnectionError as e:
            logging.warning(f"{self.__class__.__name__}.get: Connection error to {url}: {e}")
            return None
        except requests.exceptions.Timeout as e:
            logging.warning(f"{self.__class__.__name__}.get: Timeout connecting to {url}: {e}")
            return None
        except Exception as e:
            logging.error(f"{self.__class__.__name__}.get: Unexpected error: {e}", exc_info=True)
            return None
    
    def post(self, endpoint: str, data: Dict, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Performs a POST request.
        
        Args:
            endpoint: Relative endpoint (e.g., '/api/threats')
            data: Data to send (will be serialized as JSON)
            **kwargs: Additional arguments for requests.post()
            
        Returns:
            Dict with JSON response or None if error
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {**self._get_headers(), **kwargs.pop('headers', {})}
        # Allow per-request timeout override without duplicating the argument
        timeout = kwargs.pop('timeout', self.timeout)
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=timeout, **kwargs)
            logging.debug(f"{self.__class__.__name__}.post: {url} -> {response.status_code}")
            
            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError as e:
                    logging.error(f"{self.__class__.__name__}.post: JSON decode error: {e}, response: {response.text[:200]}")
                    return None
            else:
                logging.warning(f"{self.__class__.__name__}.post: Status {response.status_code}, response: {response.text[:200]}")
                return None
        except requests.exceptions.ConnectionError as e:
            logging.warning(f"{self.__class__.__name__}.post: Connection error to {url}: {e}")
            return None
        except requests.exceptions.Timeout as e:
            logging.warning(f"{self.__class__.__name__}.post: Timeout connecting to {url}: {e}")
            return None
        except Exception as e:
            logging.error(f"{self.__class__.__name__}.post: Unexpected error: {e}", exc_info=True)
            return None
