# api/enforcement_admin.py
"""
Admin endpoints for enforcement configuration (profiles, mappings, secrets and logs).
"""
from __future__ import annotations

from datetime import datetime
import json
import logging

from flask import Blueprint, jsonify, request

from core.auth.decorators import require_admin
from services.enforcement_secret_manager import SecretManagerError, SecretKeyConfigurationError
from services.enforcement_context import get_bearer_context_key_pair_from_spec_value
from services.policy_enforcement_service import EnforcementPrerequisitesError, EnforcementValidationError
from utils.app_context import get_dadm_instance
from utils.error_handlers import handle_api_errors
from utils.formatters import (
    enforcement_mapping_to_dict,
    enforcement_profile_to_dict,
    enforcement_secret_to_dict,
    policy_execution_log_to_dict,
)


enforcement_admin_bp = Blueprint('enforcement_admin', __name__)
logger = logging.getLogger(__name__)


def _to_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'on'}
    return default


def _normalize_context_spec_value(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=True)
    s = str(value).strip()
    return s or None


def _require_stored_device_bearer_from_context_spec(value) -> bool:
    """
    True si contextSpec JSON incluye options.requireStoredDeviceBearer (token cifrado en dispositivo).
    Acepta dict (request JSON) o str (perfil almacenado).
    """
    if value is None:
        return False
    if isinstance(value, dict):
        data = value
    else:
        s = str(value).strip()
        if not s:
            return False
        try:
            data = json.loads(s)
        except (json.JSONDecodeError, TypeError):
            return False
    if not isinstance(data, dict):
        return False
    opts = data.get("options")
    if not isinstance(opts, dict):
        return False
    return bool(opts.get("requireStoredDeviceBearer"))


def _validate_bearer_context_key_requirement(auth_type, auth_secret_id, context_spec_value) -> str | None:
    """
    Bearer without manager secret must declare exactly one context requirement with bearerForAuth
    and a non-empty key (no implicit token aliases).
    """
    if auth_type != 'bearer' or auth_secret_id is not None:
        return None
    nk, rk = get_bearer_context_key_pair_from_spec_value(context_spec_value)
    if nk is None or rk is None:
        return (
            'Bearer profiles without authSecretId require contextSpec with exactly one requirement '
            'with bearerForAuth true and a non-empty key'
        )
    return None


def _normalize_template(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=True)


def _error(message, code, status, details=None):
    return jsonify({
        'error': message,
        'code': code,
        'details': details or {}
    }), status


def _parse_iso_datetime(raw: str | None):
    if raw is None or not str(raw).strip():
        return None
    try:
        return datetime.fromisoformat(str(raw).strip())
    except ValueError:
        raise ValueError(f"Invalid ISO datetime: {raw}")


@enforcement_admin_bp.route('/api/admin/enforcement/profiles', methods=['GET'])
@handle_api_errors
@require_admin
def list_profiles(current_user):
    dadm = get_dadm_instance()
    include_inactive = _to_bool(request.args.get('include_inactive'), default=True)
    profiles = dadm.db.listEnforcementProfiles(include_inactive=include_inactive)
    return jsonify({
        'profiles': [enforcement_profile_to_dict(profile) for profile in profiles]
    }), 200


@enforcement_admin_bp.route('/api/admin/enforcement/profiles', methods=['POST'])
@handle_api_errors
@require_admin
def create_profile(current_user):
    dadm = get_dadm_instance()
    data = request.get_json(silent=True) or {}

    name = (data.get('name') or '').strip()
    if not name:
        return _error('name is required', 'INVALID_REQUEST', 400)

    mode = (data.get('mode') or 'rest').strip().lower()
    if mode not in {'rest', 'era'}:
        return _error("mode must be 'rest' or 'era'", 'INVALID_REQUEST', 400)

    method = (data.get('method') or 'POST').strip().upper()
    endpoint_template = data.get('endpointTemplate')
    if mode == 'rest':
        if not endpoint_template:
            return _error('endpointTemplate is required for REST profiles', 'INVALID_REQUEST', 400)
        try:
            dadm.policy_enforcement_service.validate_endpoint_template(str(endpoint_template))
        except EnforcementValidationError as exc:
            return _error(str(exc), 'INVALID_ENDPOINT_TEMPLATE', 400)

    auth_type = (data.get('authType') or 'none').strip().lower()
    if auth_type not in {'none', 'bearer'}:
        return _error("authType must be 'none' or 'bearer'", 'INVALID_REQUEST', 400)

    auth_secret_id = data.get('authSecretId')
    if auth_secret_id is not None:
        try:
            auth_secret_id = int(auth_secret_id)
        except (TypeError, ValueError):
            return _error('authSecretId must be an integer', 'INVALID_REQUEST', 400)
        if dadm.db.getEnforcementSecret(auth_secret_id) is None:
            return _error('authSecretId not found', 'INVALID_REQUEST', 400, {'authSecretId': auth_secret_id})

    require_stored = _require_stored_device_bearer_from_context_spec(data.get('contextSpec'))
    if (
        auth_type == 'bearer'
        and auth_secret_id is None
        and not _to_bool(data.get('allowMsplToken'), False)
        and not require_stored
    ):
        return _error(
            "bearer profiles require authSecretId, allowMsplToken=true, or contextSpec.options.requireStoredDeviceBearer",
            'INVALID_REQUEST',
            400
        )

    key_err = _validate_bearer_context_key_requirement(auth_type, auth_secret_id, data.get('contextSpec'))
    if key_err:
        return _error(key_err, 'INVALID_REQUEST', 400)

    try:
        timeout_seconds = float(data.get('timeoutSeconds', 10))
    except (TypeError, ValueError):
        return _error('timeoutSeconds must be a number', 'INVALID_REQUEST', 400)

    existing = dadm.db.getEnforcementProfileByName(name)
    if existing is not None:
        return _error('Profile name already exists', 'PROFILE_EXISTS', 409)

    context_spec = _normalize_context_spec_value(data.get('contextSpec'))

    profile = dadm.db.createEnforcementProfile(
        name=name,
        mode=mode,
        method=method,
        endpoint_template=str(endpoint_template) if endpoint_template is not None else None,
        headers_template=_normalize_template(data.get('headersTemplate')),
        payload_template=_normalize_template(data.get('payloadTemplate')),
        timeout_seconds=timeout_seconds,
        dry_run=_to_bool(data.get('dryRun'), default=False),
        is_default=_to_bool(data.get('isDefault'), default=False),
        is_active=_to_bool(data.get('isActive'), default=True),
        auto_enforce_on_registration=_to_bool(data.get('autoEnforceOnRegistration'), default=False),
        auth_type=auth_type,
        auth_secret_id=auth_secret_id,
        allow_mspl_token=_to_bool(data.get('allowMsplToken'), default=False),
        context_spec=context_spec,
        created_by=current_user.get('id'),
    )

    if profile.is_default:
        dadm.db.clearDefaultEnforcementProfiles(exclude_profile_id=profile.id)

    return jsonify({'profile': enforcement_profile_to_dict(profile)}), 201


@enforcement_admin_bp.route('/api/admin/enforcement/profiles/<int:profile_id>', methods=['GET'])
@handle_api_errors
@require_admin
def get_profile(current_user, profile_id):
    dadm = get_dadm_instance()
    profile = dadm.db.getEnforcementProfile(profile_id)
    if profile is None:
        return _error(f'Profile with id {profile_id} not found', 'PROFILE_NOT_FOUND', 404)
    return jsonify({'profile': enforcement_profile_to_dict(profile)}), 200


@enforcement_admin_bp.route('/api/admin/enforcement/profiles/<int:profile_id>', methods=['PUT'])
@handle_api_errors
@require_admin
def update_profile(current_user, profile_id):
    dadm = get_dadm_instance()
    profile = dadm.db.getEnforcementProfile(profile_id)
    if profile is None:
        return _error(f'Profile with id {profile_id} not found', 'PROFILE_NOT_FOUND', 404)

    data = request.get_json(silent=True) or {}
    update_data = {}

    if 'name' in data:
        new_name = (data.get('name') or '').strip()
        if not new_name:
            return _error('name cannot be empty', 'INVALID_REQUEST', 400)
        existing = dadm.db.getEnforcementProfileByName(new_name)
        if existing is not None and existing.id != profile_id:
            return _error('Profile name already exists', 'PROFILE_EXISTS', 409)
        update_data['name'] = new_name

    if 'mode' in data:
        mode = (data.get('mode') or '').strip().lower()
        if mode not in {'rest', 'era'}:
            return _error("mode must be 'rest' or 'era'", 'INVALID_REQUEST', 400)
        update_data['mode'] = mode

    if 'method' in data:
        update_data['method'] = (data.get('method') or 'POST').strip().upper()

    if 'endpointTemplate' in data:
        endpoint = data.get('endpointTemplate')
        if endpoint:
            try:
                dadm.policy_enforcement_service.validate_endpoint_template(str(endpoint))
            except EnforcementValidationError as exc:
                return _error(str(exc), 'INVALID_ENDPOINT_TEMPLATE', 400)
        update_data['endpoint_template'] = str(endpoint) if endpoint is not None else None

    if 'headersTemplate' in data:
        update_data['headers_template'] = _normalize_template(data.get('headersTemplate'))
    if 'payloadTemplate' in data:
        update_data['payload_template'] = _normalize_template(data.get('payloadTemplate'))
    if 'timeoutSeconds' in data:
        try:
            update_data['timeout_seconds'] = float(data.get('timeoutSeconds') or 10)
        except (TypeError, ValueError):
            return _error('timeoutSeconds must be a number', 'INVALID_REQUEST', 400)
    if 'dryRun' in data:
        update_data['dry_run'] = _to_bool(data.get('dryRun'))
    if 'isDefault' in data:
        update_data['is_default'] = _to_bool(data.get('isDefault'))
    if 'isActive' in data:
        update_data['is_active'] = _to_bool(data.get('isActive'))
    if 'autoEnforceOnRegistration' in data:
        update_data['auto_enforce_on_registration'] = _to_bool(data.get('autoEnforceOnRegistration'))
    if 'allowMsplToken' in data:
        update_data['allow_mspl_token'] = _to_bool(data.get('allowMsplToken'))
    if 'contextSpec' in data:
        update_data['context_spec'] = _normalize_context_spec_value(data.get('contextSpec'))

    if 'authType' in data:
        auth_type = (data.get('authType') or '').strip().lower()
        if auth_type not in {'none', 'bearer'}:
            return _error("authType must be 'none' or 'bearer'", 'INVALID_REQUEST', 400)
        update_data['auth_type'] = auth_type

    if 'authSecretId' in data:
        auth_secret_id = data.get('authSecretId')
        if auth_secret_id is None:
            update_data['auth_secret_id'] = None
        else:
            try:
                auth_secret_id = int(auth_secret_id)
            except (TypeError, ValueError):
                return _error('authSecretId must be an integer', 'INVALID_REQUEST', 400)
            if dadm.db.getEnforcementSecret(auth_secret_id) is None:
                return _error('authSecretId not found', 'INVALID_REQUEST', 400, {'authSecretId': auth_secret_id})
            update_data['auth_secret_id'] = auth_secret_id

    final_mode = update_data.get('mode', profile.mode)
    final_endpoint = update_data.get('endpoint_template', profile.endpoint_template)
    if final_mode == 'rest':
        if not final_endpoint:
            return _error('endpointTemplate is required for REST profiles', 'INVALID_REQUEST', 400)
        try:
            dadm.policy_enforcement_service.validate_endpoint_template(str(final_endpoint))
        except EnforcementValidationError as exc:
            return _error(str(exc), 'INVALID_ENDPOINT_TEMPLATE', 400)

    final_auth_type = update_data.get('auth_type', profile.auth_type)
    final_auth_secret_id = update_data.get('auth_secret_id', profile.auth_secret_id)
    final_allow_mspl_token = update_data.get('allow_mspl_token', getattr(profile, 'allow_mspl_token', False))
    final_context_spec = update_data.get('context_spec', getattr(profile, 'context_spec', None))
    require_stored = _require_stored_device_bearer_from_context_spec(final_context_spec)
    if (
        final_auth_type == 'bearer'
        and final_auth_secret_id is None
        and not final_allow_mspl_token
        and not require_stored
    ):
        return _error(
            "bearer profiles require authSecretId, allowMsplToken=true, or contextSpec.options.requireStoredDeviceBearer",
            'INVALID_REQUEST',
            400
        )

    key_err = _validate_bearer_context_key_requirement(
        final_auth_type, final_auth_secret_id, final_context_spec
    )
    if key_err:
        return _error(key_err, 'INVALID_REQUEST', 400)

    updated = dadm.db.updateEnforcementProfile(profile_id, **update_data)
    if updated is None:
        return _error(f'Profile with id {profile_id} not found', 'PROFILE_NOT_FOUND', 404)

    if updated.is_default:
        dadm.db.clearDefaultEnforcementProfiles(exclude_profile_id=updated.id)

    return jsonify({'profile': enforcement_profile_to_dict(updated)}), 200


@enforcement_admin_bp.route('/api/admin/enforcement/profiles/<int:profile_id>', methods=['DELETE'])
@handle_api_errors
@require_admin
def delete_profile(current_user, profile_id):
    dadm = get_dadm_instance()
    mappings = dadm.db.listEnforcementMappings(include_inactive=True)
    if any(mapping.profile_id == profile_id for mapping in mappings):
        return _error(
            'Profile is used by one or more mappings',
            'PROFILE_IN_USE',
            409,
            {'profileId': profile_id}
        )
    deleted = dadm.db.deleteEnforcementProfile(profile_id)
    if not deleted:
        return _error(f'Profile with id {profile_id} not found', 'PROFILE_NOT_FOUND', 404)
    return jsonify({}), 200


@enforcement_admin_bp.route('/api/admin/enforcement/mappings', methods=['GET'])
@handle_api_errors
@require_admin
def list_mappings(current_user):
    dadm = get_dadm_instance()
    include_inactive = _to_bool(request.args.get('include_inactive'), default=True)
    mappings = dadm.db.listEnforcementMappings(include_inactive=include_inactive)
    return jsonify({
        'mappings': [enforcement_mapping_to_dict(mapping) for mapping in mappings]
    }), 200


@enforcement_admin_bp.route('/api/admin/enforcement/mappings', methods=['POST'])
@handle_api_errors
@require_admin
def create_mapping(current_user):
    dadm = get_dadm_instance()
    data = request.get_json(silent=True) or {}

    match_kind = (data.get('matchKind') or '').strip()
    if match_kind not in {'explicitProfile', 'policyType', 'capability'}:
        return _error(
            "matchKind must be one of explicitProfile|policyType|capability",
            'INVALID_REQUEST',
            400
        )

    raw_match_value = (data.get('matchValue') or '').strip()
    if not raw_match_value:
        return _error('matchValue is required', 'INVALID_REQUEST', 400)
    match_value = dadm.policy_enforcement_service.normalize_key(raw_match_value)

    try:
        profile_id = int(data.get('profileId'))
    except (TypeError, ValueError):
        return _error('profileId must be an integer', 'INVALID_REQUEST', 400)

    profile = dadm.db.getEnforcementProfile(profile_id)
    if profile is None:
        return _error(f'Profile with id {profile_id} not found', 'PROFILE_NOT_FOUND', 404)

    try:
        priority = int(data.get('priority', 100))
    except (TypeError, ValueError):
        return _error('priority must be an integer', 'INVALID_REQUEST', 400)

    mapping = dadm.db.createEnforcementMapping(
        match_kind=match_kind,
        match_value=match_value,
        profile_id=profile_id,
        priority=priority,
        is_active=_to_bool(data.get('isActive'), default=True),
        created_by=current_user.get('id'),
    )
    return jsonify({'mapping': enforcement_mapping_to_dict(mapping)}), 201


@enforcement_admin_bp.route('/api/admin/enforcement/mappings/<int:mapping_id>', methods=['PUT'])
@handle_api_errors
@require_admin
def update_mapping(current_user, mapping_id):
    dadm = get_dadm_instance()
    mapping = dadm.db.getEnforcementMapping(mapping_id)
    if mapping is None:
        return _error(f'Mapping with id {mapping_id} not found', 'MAPPING_NOT_FOUND', 404)

    data = request.get_json(silent=True) or {}
    update_data = {}

    if 'matchKind' in data:
        match_kind = (data.get('matchKind') or '').strip()
        if match_kind not in {'explicitProfile', 'policyType', 'capability'}:
            return _error(
                "matchKind must be one of explicitProfile|policyType|capability",
                'INVALID_REQUEST',
                400
            )
        update_data['match_kind'] = match_kind
    if 'matchValue' in data:
        match_value = (data.get('matchValue') or '').strip()
        if not match_value:
            return _error('matchValue cannot be empty', 'INVALID_REQUEST', 400)
        update_data['match_value'] = dadm.policy_enforcement_service.normalize_key(match_value)
    if 'profileId' in data:
        try:
            profile_id = int(data.get('profileId'))
        except (TypeError, ValueError):
            return _error('profileId must be an integer', 'INVALID_REQUEST', 400)
        if dadm.db.getEnforcementProfile(profile_id) is None:
            return _error(f'Profile with id {profile_id} not found', 'PROFILE_NOT_FOUND', 404)
        update_data['profile_id'] = profile_id
    if 'priority' in data:
        try:
            update_data['priority'] = int(data.get('priority'))
        except (TypeError, ValueError):
            return _error('priority must be an integer', 'INVALID_REQUEST', 400)
    if 'isActive' in data:
        update_data['is_active'] = _to_bool(data.get('isActive'))

    updated = dadm.db.updateEnforcementMapping(mapping_id, **update_data)
    if updated is None:
        return _error(f'Mapping with id {mapping_id} not found', 'MAPPING_NOT_FOUND', 404)
    return jsonify({'mapping': enforcement_mapping_to_dict(updated)}), 200


@enforcement_admin_bp.route('/api/admin/enforcement/mappings/<int:mapping_id>', methods=['GET'])
@handle_api_errors
@require_admin
def get_mapping(current_user, mapping_id):
    dadm = get_dadm_instance()
    mapping = dadm.db.getEnforcementMapping(mapping_id)
    if mapping is None:
        return _error(f'Mapping with id {mapping_id} not found', 'MAPPING_NOT_FOUND', 404)
    return jsonify({'mapping': enforcement_mapping_to_dict(mapping)}), 200


@enforcement_admin_bp.route('/api/admin/enforcement/mappings/<int:mapping_id>', methods=['DELETE'])
@handle_api_errors
@require_admin
def delete_mapping(current_user, mapping_id):
    dadm = get_dadm_instance()
    deleted = dadm.db.deleteEnforcementMapping(mapping_id)
    if not deleted:
        return _error(f'Mapping with id {mapping_id} not found', 'MAPPING_NOT_FOUND', 404)
    return jsonify({}), 200


@enforcement_admin_bp.route('/api/admin/enforcement/secrets', methods=['GET'])
@handle_api_errors
@require_admin
def list_secrets(current_user):
    dadm = get_dadm_instance()
    secrets = dadm.db.listEnforcementSecrets()
    return jsonify({
        'secrets': [enforcement_secret_to_dict(secret) for secret in secrets]
    }), 200


@enforcement_admin_bp.route('/api/admin/enforcement/secrets', methods=['POST'])
@handle_api_errors
@require_admin
def create_secret(current_user):
    dadm = get_dadm_instance()
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    value = data.get('value')

    if not name:
        return _error('name is required', 'INVALID_REQUEST', 400)
    if not isinstance(value, str) or not value:
        return _error('value is required', 'INVALID_REQUEST', 400)
    if dadm.db.getEnforcementSecretByName(name) is not None:
        return _error('Secret name already exists', 'SECRET_EXISTS', 409)

    try:
        encrypted = dadm.policy_enforcement_service.secret_manager.encrypt(value)
    except SecretKeyConfigurationError as exc:
        return _error(str(exc), 'SECRET_KEYS_NOT_CONFIGURED', 500)
    except SecretManagerError as exc:
        return _error(str(exc), 'SECRET_ENCRYPTION_FAILED', 500)

    secret = dadm.db.createEnforcementSecret(
        name=name,
        ciphertext=encrypted['ciphertext'],
        nonce=encrypted['nonce'],
        key_version=encrypted['key_version'],
    )
    return jsonify({'secret': enforcement_secret_to_dict(secret)}), 201


@enforcement_admin_bp.route('/api/admin/enforcement/secrets/<int:secret_id>', methods=['PUT'])
@handle_api_errors
@require_admin
def update_secret(current_user, secret_id):
    dadm = get_dadm_instance()
    secret = dadm.db.getEnforcementSecret(secret_id)
    if secret is None:
        return _error(f'Secret with id {secret_id} not found', 'SECRET_NOT_FOUND', 404)

    data = request.get_json(silent=True) or {}
    update_data = {}

    if 'name' in data:
        name = (data.get('name') or '').strip()
        if not name:
            return _error('name cannot be empty', 'INVALID_REQUEST', 400)
        existing = dadm.db.getEnforcementSecretByName(name)
        if existing is not None and existing.id != secret_id:
            return _error('Secret name already exists', 'SECRET_EXISTS', 409)
        update_data['name'] = name

    if 'value' in data:
        value = data.get('value')
        if not isinstance(value, str) or not value:
            return _error('value cannot be empty', 'INVALID_REQUEST', 400)
        try:
            encrypted = dadm.policy_enforcement_service.secret_manager.encrypt(value)
        except SecretKeyConfigurationError as exc:
            return _error(str(exc), 'SECRET_KEYS_NOT_CONFIGURED', 500)
        except SecretManagerError as exc:
            return _error(str(exc), 'SECRET_ENCRYPTION_FAILED', 500)
        update_data['ciphertext'] = encrypted['ciphertext']
        update_data['nonce'] = encrypted['nonce']
        update_data['key_version'] = encrypted['key_version']

    if not update_data:
        return _error('Nothing to update', 'INVALID_REQUEST', 400)

    updated = dadm.db.updateEnforcementSecret(secret_id, **update_data)
    return jsonify({'secret': enforcement_secret_to_dict(updated)}), 200


@enforcement_admin_bp.route('/api/admin/enforcement/secrets/<int:secret_id>', methods=['GET'])
@handle_api_errors
@require_admin
def get_secret(current_user, secret_id):
    dadm = get_dadm_instance()
    secret = dadm.db.getEnforcementSecret(secret_id)
    if secret is None:
        return _error(f'Secret with id {secret_id} not found', 'SECRET_NOT_FOUND', 404)
    return jsonify({'secret': enforcement_secret_to_dict(secret)}), 200


@enforcement_admin_bp.route('/api/admin/enforcement/secrets/<int:secret_id>', methods=['DELETE'])
@handle_api_errors
@require_admin
def delete_secret(current_user, secret_id):
    dadm = get_dadm_instance()
    profiles = dadm.db.listEnforcementProfiles(include_inactive=True)
    if any(profile.auth_secret_id == secret_id for profile in profiles):
        return _error(
            'Secret is used by one or more profiles',
            'SECRET_IN_USE',
            409,
            {'secretId': secret_id}
        )

    deleted = dadm.db.deleteEnforcementSecret(secret_id)
    if not deleted:
        return _error(f'Secret with id {secret_id} not found', 'SECRET_NOT_FOUND', 404)
    return jsonify({}), 200


@enforcement_admin_bp.route('/api/admin/enforcement/test', methods=['POST'])
@handle_api_errors
@require_admin
def test_enforcement(current_user):
    dadm = get_dadm_instance()
    data = request.get_json(silent=True) or {}

    run_mode = (data.get('runMode') or '').strip().lower()
    if run_mode not in {'preview', 'execute'}:
        return _error("runMode must be 'preview' or 'execute'", 'INVALID_REQUEST', 400)

    try:
        profile_id = int(data.get('profileId'))
    except (TypeError, ValueError):
        return _error('profileId must be an integer', 'INVALID_REQUEST', 400)

    context = data.get('context') if isinstance(data.get('context'), dict) else {}

    try:
        result = dadm.policy_enforcement_service.test_profile(
            profile_id=profile_id,
            run_mode=run_mode,
            context=context,
            requested_by=current_user.get('email'),
        )
    except EnforcementPrerequisitesError as exc:
        return jsonify({
            'error': 'Enforcement prerequisites not satisfied',
            'code': 'ENFORCEMENT_PREREQUISITES',
            'missing': exc.missing,
        }), 409
    except ValueError as exc:
        msg = str(exc)
        if 'inactive' in msg.lower():
            return _error(msg, 'PROFILE_INACTIVE', 400)
        if 'not found' in msg.lower():
            return _error(msg, 'PROFILE_NOT_FOUND', 404)
        if 'only rest' in msg.lower() or 'runmode' in msg.lower():
            return _error(msg, 'INVALID_REQUEST', 400)
        return _error(msg, 'INVALID_REQUEST', 400)

    return jsonify(result), 200


@enforcement_admin_bp.route('/api/admin/enforcement/executions', methods=['GET'])
@handle_api_errors
@require_admin
def list_executions(current_user):
    dadm = get_dadm_instance()

    raw_from = request.args.get('from')
    raw_to = request.args.get('to')
    try:
        from_date = _parse_iso_datetime(raw_from)
        to_date = _parse_iso_datetime(raw_to)
    except ValueError as exc:
        return _error(str(exc), 'INVALID_REQUEST', 400)

    result = request.args.get('result')
    device_id = request.args.get('deviceId')
    is_test = request.args.get('isTest')
    profile_id = request.args.get('profileId')
    limit = request.args.get('limit', '200')

    is_test_filter = None
    if is_test is not None:
        is_test_filter = _to_bool(is_test, default=False)

    profile_id_filter = None
    if profile_id is not None and str(profile_id).strip():
        try:
            profile_id_filter = int(profile_id)
        except (TypeError, ValueError):
            return _error('profileId must be an integer', 'INVALID_REQUEST', 400)

    try:
        limit_value = int(limit)
    except ValueError:
        limit_value = 200

    logs = dadm.db.listPolicyExecutionLogs(
        from_date=from_date,
        to_date=to_date,
        result=result,
        device_id=device_id,
        is_test=is_test_filter,
        profile_id=profile_id_filter,
        limit=limit_value,
    )
    return jsonify({
        'executions': [policy_execution_log_to_dict(log_entry) for log_entry in logs]
    }), 200
