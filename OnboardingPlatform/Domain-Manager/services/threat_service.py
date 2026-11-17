# services/threat_service.py
"""
Service for handling threat-related logic.
Consolidates get_threats_from_threatmud_manager() and get_threat_by_id_from_threatmud_manager().
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from clients.threat_mud_client import ThreatMUDClient


logger = logging.getLogger(__name__)


class ThreatService:
    """
    Service for threat-related operations.
    """

    def __init__(self, threat_mud_client: ThreatMUDClient, db=None):
        """
        Args:
            threat_mud_client: Client for communicating with ThreatMUD Manager
            db: Optional DB instance used for local device-aware filtering
        """
        self.threat_mud_client = threat_mud_client
        self.db = db

    @staticmethod
    def _normalize_url(value: Any) -> str:
        """Canonical form for TMUD URL comparison (tolerant to trailing slash)."""
        return str(value or "").strip().rstrip("/")

    def _get_discovered_threat_urls(self, device) -> List[str]:
        raw_value = getattr(device, "discovered_threat_mud_urls", None)
        if not raw_value:
            return []
        if isinstance(raw_value, list):
            return [str(item).strip() for item in raw_value if str(item).strip()]
        if isinstance(raw_value, str):
            try:
                parsed = json.loads(raw_value)
            except json.JSONDecodeError:
                logger.warning(
                    "Could not parse discovered_threat_mud_urls for device '%s'",
                    getattr(device, "identifier", None),
                )
                return []
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        return []

    def get_threats(self, device_identifier: Optional[str] = None) -> List[Dict]:
        """
        Gets threats from ThreatMUDManager via REST API.
        Equivalent to get_threats_from_threatmud_manager() from the original code.
        """
        return self.threat_mud_client.get_threats(device_identifier)

    def get_threat_by_id(self, threat_id: str) -> Optional[Dict]:
        """
        Gets a specific threat by ID from ThreatMUDManager via REST API.
        Equivalent to get_threat_by_id_from_threatmud_manager().
        """
        return self.threat_mud_client.get_threat_by_id(threat_id)

    def get_tmud_file(self, tmudurl: str) -> Optional[str]:
        """
        Gets a TMUD file from a URL.
        Equivalent to getTMUDFile() from the original code.
        """
        return self.threat_mud_client.get_tmud_file(tmudurl)

    def _ensure_discovered_urls_imported(self, discovered_urls: List[str], threats: List[Dict]) -> List[Dict]:
        if not discovered_urls:
            return threats

        known_urls = {
            str(threat.get("threat_mud_url") or "").strip()
            for threat in threats
            if isinstance(threat, dict)
        }
        missing_urls = [url for url in discovered_urls if url and url not in known_urls]
        if not missing_urls:
            return threats

        for url in missing_urls:
            try:
                logger.info("Importing newly discovered Threat MUD into ThreatMUDManager: %s", url)
                self.get_tmud_file(url)
            except Exception as exc:
                logger.warning("Could not import discovered Threat MUD '%s': %s", url, exc, exc_info=True)

        return self.get_threats()

    def _matches_device(self, threat_data: Dict[str, Any], device, discovered_urls: List[str]) -> bool:
        """
        A threat applies to a device only if the device's DSP (or its genDSP hop)
        declares the threat's TMUD URL. Detection is strictly DSP-driven: no DSP
        TMUD link means no threat/mitigation; adding one to the DSP makes it appear.
        """
        threat_url = self._normalize_url(threat_data.get("threat_mud_url"))
        if not threat_url:
            return False
        return threat_url in {self._normalize_url(url) for url in discovered_urls}

    def get_matching_threats(self, device) -> List[Dict]:
        """
        Retrieves all threats from ThreatMUDManager and filters them locally.
        """
        if device is None:
            return []

        discovered_urls = self._get_discovered_threat_urls(device)
        threats = self.get_threats()
        if not isinstance(threats, list):
            logger.warning("ThreatMUDManager returned non-list threats payload: %s", type(threats))
            threats = []

        threats = self._ensure_discovered_urls_imported(discovered_urls, threats)
        matches: List[Dict] = []
        for threat_data in threats:
            if not isinstance(threat_data, dict):
                continue
            if self._matches_device(threat_data, device, discovered_urls):
                matches.append(threat_data)
        return matches

    def get_matching_threat_by_id(self, device, threat_id: str) -> Optional[Dict]:
        for threat_data in self.get_matching_threats(device):
            if str(threat_data.get("id")) == str(threat_id):
                return threat_data
        return None
