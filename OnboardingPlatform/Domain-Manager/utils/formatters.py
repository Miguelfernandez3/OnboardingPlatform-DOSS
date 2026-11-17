# utils/formatters.py
"""
Functions for formatting device data and other objects
"""
from datetime import datetime, timezone
import json

def user_for_log(current_user) -> str:
    """Returns a compact user identifier suitable for log entries."""
    if isinstance(current_user, dict):
        return str(
            current_user.get('username')
            or current_user.get('email')
            or current_user.get('id')
            or 'unknown'
        )
    return str(
        getattr(current_user, 'username', None)
        or getattr(current_user, 'email', None)
        or getattr(current_user, 'id', None)
        or 'unknown'
    )


def device_to_dict(device):
    """
    Converts a Device SQLAlchemy object to dictionary according to DeviceData interface.
    Maintains exactly the same behavior as the original function.
    """
    # Format dates to ISO 8601 if they exist
    # Use getattr() for compatibility with old devices that don't have these fields
    created_at = None
    updated_at = None
    created_at_val = getattr(device, 'created_at', None)
    updated_at_val = getattr(device, 'updated_at', None)
    
    if created_at_val:
        created_at = created_at_val.isoformat()
    if updated_at_val:
        updated_at = updated_at_val.isoformat()

    enc_ctx = getattr(device, 'enforcement_context', None)
    enc_keys = []
    enc_obj = None
    if enc_ctx and str(enc_ctx).strip():
        try:
            parsed = json.loads(str(enc_ctx))
            if isinstance(parsed, dict):
                enc_keys = list(parsed.keys())
                enc_obj = parsed
        except (json.JSONDecodeError, TypeError, ValueError):
            enc_keys = []

    return {
        'id': device.identifier or str(device.id),
        'name': getattr(device, 'name', None) or device.model or '',
        'type': getattr(device, 'type', None) or '',
        'manufacturer': getattr(device, 'manufacturer', None) or '',
        'model': device.model or '',
        'status': getattr(device, 'status', None) or 'active',
        'createdAt': created_at,
        'updatedAt': updated_at,
        'ip': device.ip,
        'mac': device.mac,
        'identifier': device.identifier,
        'mudurl': device.mudurl,
        'mudfile': device.mudfile,
        'mitigation_actions': device.mitigation_actions,
        'inventory_id': device.dsp_id,
        'idsp_id': device.dsp_id,
        'idspId': device.dsp_id,
        'edk': getattr(device, 'edk', None),
        'pilotId': getattr(device, 'pilot_id', None),
        'hasEnforcementContext': bool(enc_keys),
        'enforcementContextKeys': enc_keys,
        'enforcementContext': enc_obj,
    }

def user_to_dict(user):
    """
    Converts a User SQLAlchemy object to dictionary.
    
    Args:
        user: User SQLAlchemy object
    
    Returns:
        dict: Dictionary representation of the user
    """
    # Format dates to ISO 8601 if they exist
    created_at = None
    updated_at = None
    last_login = None
    
    if user.created_at:
        created_at = user.created_at.isoformat()
    if user.updated_at:
        updated_at = user.updated_at.isoformat()
    if user.last_login:
        last_login = user.last_login.isoformat()
    
    return {
        'id': user.id,
        'email': user.email,
        'role': user.role,
        'is_active': user.is_active,
        'last_login': last_login,
        'created_at': created_at,
        'updated_at': updated_at
    }


def enforcement_profile_to_dict(profile):
    ctx = getattr(profile, 'context_spec', None)
    context_spec = None
    if ctx and str(ctx).strip():
        try:
            context_spec = json.loads(str(ctx))
        except (json.JSONDecodeError, TypeError, ValueError):
            context_spec = str(ctx)
    return {
        'id': profile.id,
        'name': profile.name,
        'mode': profile.mode,
        'method': profile.method,
        'endpointTemplate': profile.endpoint_template,
        'headersTemplate': profile.headers_template,
        'payloadTemplate': profile.payload_template,
        'timeoutSeconds': profile.timeout_seconds,
        'dryRun': bool(profile.dry_run),
        'isDefault': bool(profile.is_default),
        'isActive': bool(profile.is_active),
        'autoEnforceOnRegistration': bool(getattr(profile, 'auto_enforce_on_registration', False)),
        'authType': profile.auth_type,
        'authSecretId': profile.auth_secret_id,
        'allowMsplToken': bool(getattr(profile, 'allow_mspl_token', False)),
        'contextSpec': context_spec,
        'createdBy': getattr(profile, 'created_by', None),
        'createdAt': profile.created_at.isoformat() if getattr(profile, 'created_at', None) else None,
        'updatedAt': profile.updated_at.isoformat() if getattr(profile, 'updated_at', None) else None,
    }


def enforcement_mapping_to_dict(mapping):
    return {
        'id': mapping.id,
        'matchKind': mapping.match_kind,
        'matchValue': mapping.match_value,
        'profileId': mapping.profile_id,
        'priority': mapping.priority,
        'isActive': bool(mapping.is_active),
        'createdBy': getattr(mapping, 'created_by', None),
        'createdAt': mapping.created_at.isoformat() if getattr(mapping, 'created_at', None) else None,
        'updatedAt': mapping.updated_at.isoformat() if getattr(mapping, 'updated_at', None) else None,
    }


def enforcement_secret_to_dict(secret):
    return {
        'id': secret.id,
        'name': secret.name,
        'keyVersion': secret.key_version,
        'createdAt': secret.created_at.isoformat() if getattr(secret, 'created_at', None) else None,
        'updatedAt': secret.updated_at.isoformat() if getattr(secret, 'updated_at', None) else None,
    }


def policy_execution_log_to_dict(log_entry):
    return {
        'id': log_entry.id,
        'deviceId': log_entry.device_id,
        'policyId': log_entry.policy_id,
        'policyName': log_entry.policy_name,
        'profileId': log_entry.profile_id,
        'runMode': log_entry.run_mode,
        'eventType': getattr(log_entry, 'event_type', None),
        'correlationId': getattr(log_entry, 'correlation_id', None),
        'stepName': getattr(log_entry, 'step_name', None),
        'elapsedMs': getattr(log_entry, 'elapsed_ms', None),
        'result': log_entry.result,
        'isTest': bool(log_entry.is_test),
        'requestPreview': log_entry.request_preview,
        'responseStatus': log_entry.response_status,
        'responseExcerpt': log_entry.response_excerpt,
        'errorMessage': log_entry.error_message,
        'requestedBy': log_entry.requested_by,
        'executedAt': log_entry.executed_at.isoformat() if getattr(log_entry, 'executed_at', None) else None,
        'createdAt': log_entry.created_at.isoformat() if getattr(log_entry, 'created_at', None) else None,
    }
