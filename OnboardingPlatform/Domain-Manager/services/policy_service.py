# services/policy_service.py
"""
Service for handling policy-related logic.
"""
from typing import List, Dict, Optional
from datetime import datetime, timezone
import logging
import json
from Policy_Translator import mudtranslator

class PolicyService:
    """
    Service for MSPL policy-related operations.
    """
    def __init__(self, db):
        """
        Args:
            db: Database instance
        """
        self.db = db
    
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
        policies = []
        
        # 1. MUD Policies: Derived dynamically from mudfile (not persisted)
        if device.mudfile:
            try:
                mud_json = json.loads(device.mudfile)
                mspl_list = mudtranslator.translate(mud_json)
                
                for idx, mspl_xml in enumerate(mspl_list):
                    policies.append({
                        'id': f'mud-policy-{idx}',
                        'deviceId': device_id,
                        'name': f'MUD Policy {idx + 1}',
                        'msplXml': mspl_xml,
                        'status': 'active',
                        'appliedAt': None,
                        'enforcementStatus': 'completed'
                    })
            except Exception as e:
                logging.error(f"Error translating MUD to MSPL: {e}")
        
        # 2. Persistent policies: Read from Policy table
        try:
            persisted_policies = self.db.getPoliciesByDevice(device_id)
            for policy in persisted_policies:
                policies.append({
                    'id': str(policy.id),
                    'deviceId': device_id,
                    'name': policy.name,
                    'msplXml': policy.mspl_xml,
                    'status': policy.status,
                    'appliedAt': policy.applied_at.isoformat() if policy.applied_at else None,
                    'enforcementStatus': policy.enforcement_status
                })
        except Exception as e:
            logging.error(f"Error retrieving persisted policies for device {device_id}: {e}", exc_info=True)
        
        return policies
    
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
            message = 'No policies applied' if not has_mud else 'Only MUD policies (status unknown)'
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

