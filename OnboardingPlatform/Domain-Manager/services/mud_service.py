# services/mud_service.py
"""
Service for handling MUD file related logic.
Consolidates getMUDUrlFromDSP() and getMUD() from the original code.

Supports IDSP without embedded MUD: follows metadata link rel "Generic DSP"
to fetch genDSP JSON, then extracts rel "MUD file" from genDSP components.
"""
import json
import logging
import os
from typing import Any, Callable, Dict, Iterable, List, Optional
from urllib.parse import urlparse

import requests

from clients.mud_manager_client import MUDManagerClient

# Link rel used in IDSP metadata to point at the generic DSP document
GENERIC_DSP_REL = "Generic DSP"
MUD_FILE_REL = "MUD file"
# Comma-separated list of allowed hostnames for genDSP fetch (SSRF mitigation). Empty = allow all.
GENERIC_DSP_ALLOWED_HOSTS_ENV = "GENERIC_DSP_ALLOWED_HOSTS"
# Timeout for fetching genDSP JSON (seconds)
GENERIC_DSP_FETCH_TIMEOUT = 10
KNOWN_THREAT_MUD_RELS = {
    "threat mud",
    "threat mud file",
    "threat mud url",
}


def _parse_dsp_data(dsp_json: Any) -> Optional[Dict[str, Any]]:
    """Parse DSP input to dict. Returns None on failure."""
    if dsp_json is None:
        return None
    if isinstance(dsp_json, str):
        try:
            return json.loads(dsp_json)
        except json.JSONDecodeError:
            return None
    if isinstance(dsp_json, dict):
        return dsp_json
    return None


def _get_doss_dsp(dsp_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract doss-dsp node from FEAM envelope or raw doss-dsp root.
    Supports:
    - { "dspFile": { "doss-dsp": { ... } } }
    - { "doss-dsp": { ... } } at root
    - Raw genDSP JSON whose root is already the inner doss-dsp content
    """
    if not isinstance(dsp_data, dict):
        return None
    dsp_file = dsp_data.get("dspFile")
    if isinstance(dsp_file, dict):
        doss = dsp_file.get("doss-dsp")
        if isinstance(doss, dict):
            return doss
    doss = dsp_data.get("doss-dsp")
    if isinstance(doss, dict):
        return doss
    # Response body may be the inner object only (local-definitions at top level)
    if "local-definitions" in dsp_data and "metadata" in dsp_data:
        return dsp_data
    return None


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", " ").replace("-", " ")


def _iter_dsp_links(doss_dsp: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    """Yields metadata links first and then component links."""
    if not doss_dsp or not isinstance(doss_dsp, dict):
        return

    metadata = doss_dsp.get("metadata") or {}
    for link in metadata.get("links", []) or []:
        if isinstance(link, dict):
            yield link

    components = doss_dsp.get("local-definitions", {}).get("components", []) or []
    for component in components:
        if not isinstance(component, dict):
            continue
        for link in component.get("links", []) or []:
            if isinstance(link, dict):
                yield link


def _find_link_hrefs(
    doss_dsp: Dict[str, Any],
    matcher: Callable[[Dict[str, Any]], bool],
) -> List[str]:
    hrefs: List[str] = []
    for link in _iter_dsp_links(doss_dsp):
        href = str(link.get("href") or "").strip()
        if not href:
            continue
        if matcher(link):
            hrefs.append(href)
    return hrefs


def _generic_dsp_rels() -> List[str]:
    """Rels that identify link to genDSP document. Configurable via env (comma-separated)."""
    raw = os.getenv("GENERIC_DSP_REL", GENERIC_DSP_REL).strip()
    if not raw:
        return [GENERIC_DSP_REL]
    return [r.strip() for r in raw.split(",") if r.strip()]


def _is_generic_dsp_link(link: Dict[str, Any]) -> bool:
    rel = str(link.get("rel") or "").strip()
    return rel in set(_generic_dsp_rels())


def _is_mud_link(link: Dict[str, Any]) -> bool:
    return str(link.get("rel") or "").strip() == MUD_FILE_REL


def _is_provisional_threat_mud_link(link: Dict[str, Any]) -> bool:
    """
    Heuristic matcher for Threat MUD links inside DSP/genDSP.

    TODO: tighten this logic when we receive a real DSP/genDSP sample from Ilias.
    For now we intentionally accept several rel variants and use media-type only as
    a soft signal so the parser survives temporary contract mismatches.
    """
    rel_normalized = _normalize_text(link.get("rel"))
    media_type_normalized = _normalize_text(link.get("media-type"))

    if rel_normalized in KNOWN_THREAT_MUD_RELS:
        return True

    if "threat" in rel_normalized and "mud" in rel_normalized:
        return True

    if (
        "threat" in media_type_normalized
        and "mud" in media_type_normalized
        and ("mud" in rel_normalized or "policy" in rel_normalized or not rel_normalized)
    ):
        return True

    return False


def _host_allowed_for_generic_dsp(href: str) -> bool:
    allowed = os.getenv(GENERIC_DSP_ALLOWED_HOSTS_ENV, "").strip()
    if not allowed:
        return True
    try:
        parsed = urlparse(href)
        host = (parsed.hostname or "").lower()
        if not host:
            return False
        allowed_hosts = {h.strip().lower() for h in allowed.split(",") if h.strip()}
        return host in allowed_hosts
    except Exception:
        return False


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

    def _fetch_generic_dsp(self, generic_href: str) -> Optional[Dict[str, Any]]:
        if not _host_allowed_for_generic_dsp(generic_href):
            logging.error(
                "generic_dsp_fetch_failed: host not allowed for href=%s (set %s)",
                generic_href,
                GENERIC_DSP_ALLOWED_HOSTS_ENV,
            )
            return None

        try:
            resp = requests.get(generic_href, timeout=GENERIC_DSP_FETCH_TIMEOUT)
        except requests.RequestException as exc:
            logging.error("generic_dsp_fetch_failed: GET %s: %s", generic_href, exc)
            return None

        if resp.status_code != 200:
            logging.error(
                "generic_dsp_fetch_failed: status=%s url=%s",
                resp.status_code,
                generic_href,
            )
            return None

        try:
            next_data = resp.json()
        except json.JSONDecodeError as exc:
            logging.error("generic_dsp_fetch_failed: invalid JSON from %s: %s", generic_href, exc)
            return None

        next_doss = _get_doss_dsp(next_data)
        if next_doss is None:
            logging.error("generic_dsp_fetch_failed: no doss-dsp in response from %s", generic_href)
            return None

        return next_doss

    def _resolve_dsp_chain(self, dsp_json: Any) -> List[Dict[str, Any]]:
        """
        Resolves the DSP plus a single optional genDSP hop.
        """
        dsp_data = _parse_dsp_data(dsp_json)
        if dsp_data is None:
            logging.error("invalid DSP JSON received")
            return []

        doss_dsp = _get_doss_dsp(dsp_data)
        if doss_dsp is None:
            logging.warning("no doss-dsp node found")
            return []

        chain = [doss_dsp]
        generic_candidates = _find_link_hrefs(doss_dsp, _is_generic_dsp_link)
        if not generic_candidates:
            return chain

        next_doss = self._fetch_generic_dsp(generic_candidates[0])
        if next_doss is not None:
            chain.append(next_doss)
        return chain

    def get_mud_url_from_dsp(self, dsp_json) -> Optional[str]:
        """
        Extract MUD file URL from DSP JSON.
        1) Looks in doss-dsp links for rel "MUD file".
        2) If missing, follows metadata link rel "Generic DSP" (configurable), GETs JSON,
           then searches again (IDSP -> genDSP chain).

        Args:
            dsp_json: The DSP JSON object (either string or dict)

        Returns:
            str: The href URL of the MUD file, or None if not found
        """
        for doss_dsp in self._resolve_dsp_chain(dsp_json):
            mud_hrefs = _find_link_hrefs(doss_dsp, _is_mud_link)
            if mud_hrefs:
                return mud_hrefs[0]

        logging.warning("No MUD file link found in DSP/genDSP chain")
        return None

    def get_threat_mud_urls_from_dsp(self, dsp_json) -> List[str]:
        """
        Extracts Threat MUD URLs from DSP or genDSP.

        TODO: revisit rel/media-type matching once we have a real DSP/genDSP sample.
        """
        discovered: List[str] = []
        for doss_dsp in self._resolve_dsp_chain(dsp_json):
            for href in _find_link_hrefs(doss_dsp, _is_provisional_threat_mud_link):
                if href not in discovered:
                    discovered.append(href)
        return discovered

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
        logging.debug("MUDService.get_mud called for device_identifier: %s", device_identifier)

        mudurl = self.get_mud_url_from_dsp(dsp)
        if not mudurl:
            logging.error("No MUD URL found in DSP")
            return None

        return self.mud_manager_client.get_mud_file(mudurl, device_identifier)
