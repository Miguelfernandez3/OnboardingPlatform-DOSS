# services/mitigation_service.py
"""
Service for handling mitigation-related logic.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import json
import logging

from utils.xml_parser import parse_mitigation_xml
from services.threat_service import ThreatService
from services.policy_enforcement_service import (
    PolicyEnforcementService,
    EnforcementNotConfiguredError,
)


class MitigationService:
    """
    Service for mitigation-related operations.
    """

    SNAPSHOT_TYPE = "threat-mitigation-snapshot"

    def __init__(
        self,
        db,
        threat_service: ThreatService,
        policy_enforcement: Optional[PolicyEnforcementService] = None,
    ):
        """
        Args:
            db: Database instance
            threat_service: Service for threat operations
            policy_enforcement: Optional; used to precompute missing enforcement context per mitigation
        """
        self.db = db
        self.threat_service = threat_service
        self._policy_enforcement = policy_enforcement

    @classmethod
    def build_applied_snapshot(cls, threat_data: Dict[str, Any], applied_at: Optional[str] = None) -> str:
        if not applied_at:
            applied_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "type": cls.SNAPSHOT_TYPE,
            "threatId": str(threat_data.get("id") or ""),
            "threatMudUrl": threat_data.get("threat_mud_url"),
            "mitigationActions": threat_data.get("mitigation_actions"),
            "name": f"Threat Mitigation {threat_data.get('id')}",
            "appliedAt": applied_at,
        }
        return json.dumps(payload)

    @classmethod
    def parse_applied_snapshot(cls, raw_value: Any) -> Optional[Dict[str, Any]]:
        if not raw_value:
            return None
        if isinstance(raw_value, dict):
            candidate = raw_value
        elif isinstance(raw_value, str):
            try:
                candidate = json.loads(raw_value)
            except json.JSONDecodeError:
                return {
                    "type": "legacy-mitigation-xml",
                    "mitigationActions": raw_value,
                }
        else:
            return None

        if not isinstance(candidate, dict):
            return None
        if candidate.get("type") == cls.SNAPSHOT_TYPE:
            return candidate
        return candidate

    def _build_legacy_mitigation_entry(self, device_id: str, raw_actions: str) -> Optional[Dict[str, Any]]:
        mitigation_data = parse_mitigation_xml(raw_actions)
        if mitigation_data is None:
            return None
        timestamp = datetime.now(timezone.utc).isoformat()
        return {
            "id": f"mitigation-{device_id}",
            "deviceId": device_id,
            "name": "Device Mitigation",
            "description": "Mitigation applied to device",
            "mitigation_actions": raw_actions,
            "is_enforced": True,
            "last_enforced": timestamp,
            "enforcement_timestamp": timestamp,
        }

    @staticmethod
    def _as_mspl_list(mitigation_actions: Any) -> List[str]:
        if isinstance(mitigation_actions, list):
            return [item for item in mitigation_actions if item]
        if isinstance(mitigation_actions, str):
            try:
                parsed = json.loads(mitigation_actions)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                return [item for item in parsed if item]
        if mitigation_actions:
            return [mitigation_actions]
        return []

    @staticmethod
    def _merge_missing_by_key(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """First occurrence wins per `key` (aligns with GUI mergeMissingByKey)."""
        seen: Dict[str, Dict[str, Any]] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            k = item.get("key")
            if k is None:
                continue
            ks = str(k)
            if ks and ks not in seen:
                seen[ks] = item
        return list(seen.values())

    def _enrichment_gaps_for_mitigation(
        self, mitigation_actions: Any, device: Any
    ) -> Dict[str, Any]:
        if self._policy_enforcement is None:
            return {
                "missing": [],
                "warnings": [],
                "ready": True,
            }
        mspls = self._as_mspl_list(mitigation_actions)
        all_missing: List[Dict[str, Any]] = []
        all_warnings: List[str] = []
        for xml in mspls:
            if not xml or not isinstance(xml, str):
                continue
            try:
                g = self._policy_enforcement.compute_enforcement_gaps(xml.strip(), device, None)
                for m in (g.get("missing") or []):
                    if isinstance(m, dict):
                        all_missing.append(m)
                for w in (g.get("warnings") or []):
                    if w:
                        all_warnings.append(str(w))
            except EnforcementNotConfiguredError:
                all_warnings.append("enforcement_not_configured")
            except Exception as exc:  # pylint: disable=broad-except
                logging.warning("compute_enforcement_gaps for mitigation action failed: %s", exc)
                all_warnings.append("enforcement_gaps_unavailable")
        missing_merged = self._merge_missing_by_key(all_missing)
        warnings_dedup = list(dict.fromkeys(all_warnings))  # preserve order, unique
        return {
            "missing": missing_merged,
            "warnings": warnings_dedup,
            "ready": len(missing_merged) == 0,
        }

    def get_device_mitigations(self, device_id: str, device) -> List[Dict]:
        """
        Gets mitigations associated with a device.
        Each mitigation includes enforcementGaps: { missing, warnings, ready } when policy enforcement is available.
        """
        mitigations: List[Dict[str, Any]] = []
        applied_snapshot = self.parse_applied_snapshot(getattr(device, "mitigation_actions", None))
        snapshot_matched = False

        if applied_snapshot and applied_snapshot.get("type") == "legacy-mitigation-xml":
            legacy_entry = self._build_legacy_mitigation_entry(device_id, applied_snapshot.get("mitigationActions"))
            if legacy_entry is not None:
                legacy_entry["enforcementGaps"] = self._enrichment_gaps_for_mitigation(
                    legacy_entry.get("mitigation_actions"), device
                )
                mitigations.append(legacy_entry)

        logging.debug("Getting matching threats for device mitigations: device identifier=%s", device.identifier)
        threats_data = self.threat_service.get_matching_threats(device)
        if not isinstance(threats_data, list):
            logging.error("threats_data is not a list in mitigations: %s", type(threats_data))
            threats_data = []

        for idx, threat_data in enumerate(threats_data):
            try:
                if not isinstance(threat_data, dict):
                    logging.warning("threat_data[%s] is not a dict: %s", idx, type(threat_data))
                    continue

                mitigation_actions = threat_data.get("mitigation_actions")
                if not mitigation_actions:
                    continue

                is_enforced = False
                applied_at = None
                if applied_snapshot and applied_snapshot.get("type") == self.SNAPSHOT_TYPE:
                    applied_threat_id = str(applied_snapshot.get("threatId") or "")
                    applied_threat_url = str(applied_snapshot.get("threatMudUrl") or "").strip()
                    if (
                        applied_threat_id
                        and applied_threat_id == str(threat_data.get("id") or "")
                    ) or (
                        applied_threat_url
                        and applied_threat_url == str(threat_data.get("threat_mud_url") or "").strip()
                    ):
                        is_enforced = True
                        applied_at = applied_snapshot.get("appliedAt")
                        snapshot_matched = True

                entry: Dict[str, Any] = {
                    "id": f'threat-mitigation-{threat_data.get("id")}',
                    "deviceId": device_id,
                    "threatId": threat_data.get("id"),
                    "name": f'Threat Mitigation {threat_data.get("id")}',
                    "description": f'Mitigation for threat {threat_data.get("threat_mud_url")}',
                    "mitigation_actions": mitigation_actions,
                    "is_enforced": is_enforced,
                    "last_enforced": applied_at,
                    "enforcement_timestamp": applied_at,
                }
                entry["enforcementGaps"] = self._enrichment_gaps_for_mitigation(
                    mitigation_actions, device
                )
                mitigations.append(entry)
            except Exception as exc:
                logging.error("Error processing threat_data[%s] for mitigation: %s", idx, exc, exc_info=True)
                continue

        if applied_snapshot and applied_snapshot.get("type") == self.SNAPSHOT_TYPE and not snapshot_matched:
            ma = applied_snapshot.get("mitigationActions")
            extra_entry: Dict[str, Any] = {
                "id": f'mitigation-{device_id}',
                "deviceId": device_id,
                "threatId": applied_snapshot.get("threatId"),
                "name": applied_snapshot.get("name") or "Applied Threat Mitigation",
                "description": "Mitigation applied to device (snapshot)",
                "mitigation_actions": ma,
                "is_enforced": True,
                "last_enforced": applied_snapshot.get("appliedAt"),
                "enforcement_timestamp": applied_snapshot.get("appliedAt"),
            }
            extra_entry["enforcementGaps"] = self._enrichment_gaps_for_mitigation(ma, device)
            mitigations.append(extra_entry)

        return mitigations
