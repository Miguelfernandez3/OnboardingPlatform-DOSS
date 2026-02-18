# services/policy_service.py
"""
Service for handling policy-related logic.
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
import logging
import json
import hashlib
from Policy_Translator import mudtranslator

class PolicyService:
    """
    Service for MSPL policy-related operations.
    """
    def __init__(self, db, policy_enforcement_service=None):
        """
        Args:
            db: Database instance
            policy_enforcement_service: Optional PolicyEnforcementService instance
        """
        self.db = db
        self.policy_enforcement_service = policy_enforcement_service

    @staticmethod
    def _hash_mspl(mspl_xml: str) -> str:
        """Returns a stable hash for MSPL XML content."""
        normalized = (mspl_xml or "").strip().encode("utf-8")
        return hashlib.sha256(normalized).hexdigest()

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
        can_enforce: bool = True
    ) -> Dict[str, Any]:
        metadata = self._extract_policy_metadata(mspl_xml)
        final_policy_type = policy_type or metadata.get('policyType')

        return {
            'id': policy_id,
            'deviceId': device_id,
            'name': name,
            'msplXml': mspl_xml,
            'status': status,
            'appliedAt': applied_at.isoformat() if applied_at else None,
            'enforcementStatus': enforcement_status,
            'source': source,
            'policyType': final_policy_type,
            'canEnforce': can_enforce,
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
        except Exception as e:
            logging.error(f"Error retrieving persisted policies for device {device_id}: {e}", exc_info=True)

        persisted_mud_hashes = set()
        for policy in persisted_policies:
            source_value = (policy.source or '').strip().lower()
            if source_value in {'mud', 'mud_file'}:
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
                can_enforce=True
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
        total_policies = len(persisted_policies)
        completed = 0
        pending = 0
        failed = 0
        unknown = 0
        
        policy_details = []
        
        for policy in persisted_policies:
            enforcement_status = policy.enforcement_status or 'unknown'
            
            if enforcement_status == 'completed':
                completed += 1
            elif enforcement_status == 'failed':
                failed += 1
            elif enforcement_status == 'pending':
                pending += 1
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
        elif pending > 0 or unknown > 0:
            overall_status = 'pending'
            message = f'{pending + unknown} policy(ies) pending enforcement'
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
                'failed': failed,
                'unknown': unknown,
                'policies': policy_details
            }
        }
