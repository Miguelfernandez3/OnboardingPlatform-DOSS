# services/policy_service.py
"""
Service for handling policy-related logic.
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
import logging
import json
import hashlib
import re
from Policy_Translator import mudtranslator

class PolicyService:
    """
    Service for MSPL policy-related operations.
    """
    UUID_PATTERN = re.compile(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        re.IGNORECASE,
    )
    PLACEHOLDER_RULE_PATTERN = re.compile(
        r"(mud-abstraction-[A-Za-z0-9_\-]+-)[0-9a-f]{8}\b",
        re.IGNORECASE,
    )

    def __init__(self, db, policy_enforcement_service=None):
        """
        Args:
            db: Database instance
            policy_enforcement_service: Optional PolicyEnforcementService instance
        """
        self.db = db
        self.policy_enforcement_service = policy_enforcement_service

    @staticmethod
    def _normalize_mspl_for_hash(mspl_xml: str) -> str:
        normalized = (mspl_xml or "").strip()
        normalized = PolicyService.UUID_PATTERN.sub("<uuid>", normalized)
        normalized = PolicyService.PLACEHOLDER_RULE_PATTERN.sub(r"\1<id>", normalized)
        normalized = re.sub(r">\s+<", "><", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    @staticmethod
    def _hash_mspl(mspl_xml: str) -> str:
        """Returns a stable hash for MSPL XML content."""
        normalized = PolicyService._normalize_mspl_for_hash(mspl_xml).encode("utf-8")
        return hashlib.sha256(normalized).hexdigest()

    @staticmethod
    def _policy_rank(policy) -> tuple[int, int]:
        enforcement_status = str(getattr(policy, 'enforcement_status', '') or '').strip().lower()
        status_priority = {
            'completed': 3,
            'active': 2,
            'pending': 1,
            'deferred': 1,
            'failed': 0,
            'superseded': -1,
        }.get(enforcement_status, 0)
        return status_priority, int(getattr(policy, 'id', 0) or 0)

    def _dedupe_persisted_policies(self, persisted_policies: List[Any]) -> List[Any]:
        deduped: List[Any] = []
        mud_candidates: Dict[str, Any] = {}

        for policy in persisted_policies:
            source_value = (getattr(policy, 'source', None) or '').strip().lower()
            if source_value not in {'mud', 'mud_file'}:
                deduped.append(policy)
                continue

            policy_hash = self._hash_mspl(getattr(policy, 'mspl_xml', None))
            current_best = mud_candidates.get(policy_hash)
            if current_best is None or self._policy_rank(policy) > self._policy_rank(current_best):
                mud_candidates[policy_hash] = policy

        deduped.extend(
            sorted(
                mud_candidates.values(),
                key=lambda policy: int(getattr(policy, 'id', 0) or 0),
            )
        )
        return deduped

    def _find_existing_mud_policy(self, device_id: str, mspl_xml: str):
        try:
            persisted_policies = self.db.getPoliciesByDevice(device_id)
        except Exception as exc:
            logging.error("Error retrieving policies for MUD match on device %s: %s", device_id, exc, exc_info=True)
            return None

        target_hash = self._hash_mspl(mspl_xml)
        candidates = []
        for policy in persisted_policies or []:
            source_value = (getattr(policy, 'source', None) or '').strip().lower()
            if source_value not in {'mud', 'mud_file'}:
                continue
            state_values = {
                str(getattr(policy, 'status', '') or '').strip().lower(),
                str(getattr(policy, 'enforcement_status', '') or '').strip().lower(),
            }
            if 'superseded' in state_values:
                continue
            if self._hash_mspl(getattr(policy, 'mspl_xml', None)) == target_hash:
                candidates.append(policy)

        if not candidates:
            return None
        return max(candidates, key=self._policy_rank)

    def _extract_policy_metadata(self, mspl_xml: str) -> Dict[str, Optional[str]]:
        """Extracts metadata from MSPL XML for UI and mapping."""
        if self.policy_enforcement_service is None:
            return {
                'policyType': None,
                'capability': None,
                'enforcementProfile': None
            }
        return self.policy_enforcement_service.extract_policy_metadata(mspl_xml)

    def _build_policy_payload(
        self,
        *,
        policy_id: str,
        device_id: str,
        name: str,
        mspl_xml: str,
        status: str,
        applied_at: Optional[datetime],
        enforcement_status: str,
        source: Optional[str],
        policy_type: Optional[str],
        can_enforce: bool = True,
        enforcement_blockers: Optional[str] = None,
    ) -> Dict[str, Any]:
        metadata = self._extract_policy_metadata(mspl_xml)
        final_policy_type = policy_type or metadata.get('policyType')
        blockers = None
        if enforcement_blockers and str(enforcement_blockers).strip():
            try:
                blockers = json.loads(str(enforcement_blockers))
            except (json.JSONDecodeError, TypeError, ValueError):
                blockers = None
        is_superseded = (
            str(status or '').strip().lower() == 'superseded'
            or str(enforcement_status or '').strip().lower() == 'superseded'
        )

        return {
            'id': policy_id,
            'deviceId': device_id,
            'name': name,
            'msplXml': mspl_xml,
            'status': status,
            'appliedAt': applied_at.isoformat() if applied_at else None,
            'enforcementStatus': enforcement_status,
            'enforcementBlockers': blockers,
            'source': source,
            'policyType': final_policy_type,
            'canEnforce': bool(can_enforce) and not is_superseded,
        }
    
    def get_device_policies(self, device_id: str, device) -> List[Dict]:
        """
        Gets all policies applied to a device.
        Includes MUD policies (derived dynamically) and persistent policies.
        Equivalent to the logic in get_device_policies() endpoint.
        
        Args:
            device_id: Device ID
            device: Device object
            
        Returns:
            list: List of policies
        """
        policies: List[Dict[str, Any]] = []
        persisted_policies = []

        # 1. Persistent policies: Read from Policy table
        try:
            persisted_policies = self.db.getPoliciesByDevice(device_id)
            persisted_policies = self._dedupe_persisted_policies(persisted_policies or [])
        except Exception as e:
            logging.error(f"Error retrieving persisted policies for device {device_id}: {e}", exc_info=True)

        persisted_mud_hashes = set()
        for policy in persisted_policies:
            source_value = (policy.source or '').strip().lower()
            state_values = {
                str(getattr(policy, 'status', '') or '').strip().lower(),
                str(getattr(policy, 'enforcement_status', '') or '').strip().lower(),
            }
            if source_value in {'mud', 'mud_file'} and 'superseded' not in state_values:
                persisted_mud_hashes.add(self._hash_mspl(policy.mspl_xml))

        # 2. MUD Policies: Derived dynamically from mudfile (not persisted)
        if device.mudfile:
            try:
                mud_json = json.loads(device.mudfile)
                mspl_list = mudtranslator.translate(mud_json)

                for idx, mspl_xml in enumerate(mspl_list):
                    if self._hash_mspl(mspl_xml) in persisted_mud_hashes:
                        # Skip duplicates already persisted after prior enforce.
                        continue

                    policies.append(self._build_policy_payload(
                        policy_id=f'mud-policy-{idx}',
                        device_id=device_id,
                        name=f'MUD Policy {idx + 1}',
                        mspl_xml=mspl_xml,
                        status='pending',
                        applied_at=None,
                        enforcement_status='pending',
                        source='mud_file',
                        policy_type=None,
                        can_enforce=True
                    ))
            except Exception as e:
                logging.error(f"Error translating MUD to MSPL: {e}", exc_info=True)

        # 3. Add persisted policies
        for policy in persisted_policies:
            policies.append(self._build_policy_payload(
                policy_id=str(policy.id),
                device_id=device_id,
                name=policy.name,
                mspl_xml=policy.mspl_xml,
                status=policy.status or 'pending',
                applied_at=policy.applied_at,
                enforcement_status=policy.enforcement_status or 'pending',
                source=policy.source,
                policy_type=policy.policy_type,
                can_enforce=(
                    str(policy.status or '').strip().lower() != 'superseded'
                    and str(policy.enforcement_status or '').strip().lower() != 'superseded'
                ),
                enforcement_blockers=getattr(policy, 'enforcement_blockers', None),
            ))

        return policies

    def translate_mud_json_to_policies(self, mud_json: Dict[str, Any], device_id: str = 'preview') -> List[Dict[str, Any]]:
        """
        Translates a full MUD JSON into policy entries (MSPL + metadata).
        """
        policies: List[Dict[str, Any]] = []
        mspl_list = mudtranslator.translate(mud_json)

        for idx, mspl_xml in enumerate(mspl_list):
            policy_payload = self._build_policy_payload(
                policy_id=f'mud-policy-{idx}',
                device_id=device_id,
                name=f'MUD Policy {idx + 1}',
                mspl_xml=mspl_xml,
                status='pending',
                applied_at=None,
                enforcement_status='pending',
                source='mud_file',
                policy_type=None,
                can_enforce=True
            )

            if self.policy_enforcement_service is not None:
                try:
                    resolution = self.policy_enforcement_service.resolve_enforcement_profile(mspl_xml)
                    policy_payload['profileId'] = resolution.get('profileId')
                    policy_payload['enforcementMode'] = resolution.get('mode')
                except Exception as exc:
                    logging.warning(f"Could not resolve enforcement profile for preview policy {idx}: {exc}")

            policies.append(policy_payload)

        return policies

    def get_policy_for_enforcement(self, device_id: str, policy_id: str, device) -> Optional[Dict[str, Any]]:
        """
        Resolves a policy (persisted or dynamic MUD-derived) to enforce.

        Returns:
            dict with policy data or None if not found/invalid.
        """
        if policy_id.startswith('mud-policy-'):
            if not device.mudfile:
                return None

            try:
                idx = int(policy_id.replace('mud-policy-', ''))
            except ValueError:
                return None

            try:
                mud_json = json.loads(device.mudfile)
                mspl_list = mudtranslator.translate(mud_json)
            except Exception as e:
                logging.error(f"Error translating MUD for policy '{policy_id}': {e}", exc_info=True)
                return None

            if idx < 0 or idx >= len(mspl_list):
                return None

            mspl_xml = mspl_list[idx]
            metadata = self._extract_policy_metadata(mspl_xml)
            existing_policy = self._find_existing_mud_policy(device_id, mspl_xml)
            if existing_policy is not None:
                return {
                    'id': str(existing_policy.id),
                    'deviceId': device_id,
                    'name': existing_policy.name or f'MUD Policy {idx + 1}',
                    'msplXml': existing_policy.mspl_xml,
                    'source': existing_policy.source or 'mud_file',
                    'policyType': existing_policy.policy_type or metadata.get('policyType'),
                    'isPersisted': True,
                    'policyModel': existing_policy,
                }
            return {
                'id': policy_id,
                'deviceId': device_id,
                'name': f'MUD Policy {idx + 1}',
                'msplXml': mspl_xml,
                'source': 'mud_file',
                'policyType': metadata.get('policyType'),
                'isPersisted': False,
                'policyModel': None,
            }

        # Persisted policy by numeric/string id
        lookup_id = int(policy_id) if str(policy_id).isdigit() else policy_id
        policy = self.db.getPolicy(lookup_id)
        if policy is None:
            return None
        if policy.device_id != device_id:
            return None

        metadata = self._extract_policy_metadata(policy.mspl_xml)
        return {
            'id': str(policy.id),
            'deviceId': device_id,
            'name': policy.name,
            'msplXml': policy.mspl_xml,
            'source': policy.source or 'user',
            'policyType': policy.policy_type or metadata.get('policyType'),
            'status': policy.status,
            'enforcementStatus': policy.enforcement_status,
            'isPersisted': True,
            'policyModel': policy,
        }
    
    def get_enforcement_status(self, device_id: str, device) -> Dict:
        """
        Gets the enforcement status of a device based on real policies.
        Equivalent to the logic in get_enforcement_status() endpoint.
        
        Args:
            device_id: Device ID
            device: Device object
            
        Returns:
            dict: Enforcement status with details
        """
        logging.debug(f"Getting enforcement status for device {device_id}")
        
        # Get all persistent policies for the device
        try:
            persisted_policies = self.db.getPoliciesByDevice(device_id)
            logging.debug(f"Found {len(persisted_policies)} persisted policies for device {device_id}")
        except Exception as e:
            logging.error(f"Error retrieving persisted policies for enforcement status: {e}", exc_info=True)
            persisted_policies = []
        
        # Analyze enforcement states
        active_policies = [
            policy for policy in persisted_policies
            if str(policy.status or '').strip().lower() != 'superseded'
            and str(policy.enforcement_status or '').strip().lower() != 'superseded'
        ]
        total_policies = len(active_policies)
        completed = 0
        pending = 0
        failed = 0
        unknown = 0
        deferred = 0
        superseded = len(persisted_policies) - total_policies
        
        policy_details = []
        
        for policy in persisted_policies:
            enforcement_status = policy.enforcement_status or 'unknown'
            status_value = str(policy.status or '').strip().lower()
            enforcement_value = str(enforcement_status or '').strip().lower()

            if status_value == 'superseded' or enforcement_value == 'superseded':
                pass
            elif enforcement_status == 'completed':
                completed += 1
            elif enforcement_status == 'failed':
                failed += 1
            elif enforcement_status == 'pending':
                pending += 1
            elif enforcement_status == 'deferred':
                deferred += 1
            else:
                unknown += 1
            
            policy_details.append({
                'id': str(policy.id),
                'name': policy.name,
                'enforcementStatus': enforcement_status,
                'status': policy.status
            })
        
        logging.debug(f"Enforcement status breakdown: completed={completed}, pending={pending}, failed={failed}, unknown={unknown}")
        
        # Determine overall status
        if total_policies == 0:
            # No persistent policies, check if has MUD
            has_mud = bool(device.mudfile)
            overall_status = 'pending'
            message = 'No policies applied' if not has_mud else 'Only MUD policies (pending manual enforcement)'
        elif failed > 0:
            overall_status = 'failed'
            message = f'{failed} policy(ies) failed enforcement'
        elif pending > 0 or unknown > 0 or deferred > 0:
            overall_status = 'pending'
            message = f'{pending + unknown + deferred} policy(ies) pending or awaiting context'
        else:
            overall_status = 'completed'
            message = 'All policies are enforced'
        
        logging.info(f"Enforcement status for device {device_id}: {overall_status} - {message}")
        
        return {
            'status': overall_status,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'details': {
                'totalPolicies': total_policies,
                'completed': completed,
                'pending': pending,
                'deferred': deferred,
                'failed': failed,
                'unknown': unknown,
                'superseded': superseded,
                'policies': policy_details
            }
        }
