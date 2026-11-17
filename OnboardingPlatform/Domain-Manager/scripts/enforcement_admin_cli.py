#!/usr/bin/env python3
"""
Headless admin CLI for enforcement configuration.
"""
from __future__ import annotations

import argparse
import json
import os
import sys


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, PARENT_DIR)

from Database import Database  # noqa: E402
from services.enforcement_context import get_bearer_context_key_pair_from_spec_value  # noqa: E402
from services.policy_enforcement_service import PolicyEnforcementService  # noqa: E402


def _require_admin_user(db: Database, email: str, password: str):
    user = db.getUser(email)
    if user is None:
        raise RuntimeError("Authentication failed: user not found")
    if not user.is_active:
        raise RuntimeError("Authentication failed: user is inactive")
    if user.role not in ('admin', 'superadmin'):
        raise RuntimeError("Authentication failed: admin role required")
    if not db.verifyPassword(user, password):
        raise RuntimeError("Authentication failed: invalid password")
    return user


def _parse_json_or_none(raw: str | None):
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    return text


def _load_context_spec_arg(raw: str | None):
    if raw is None or not str(raw).strip():
        return None
    text = str(raw).strip()
    if os.path.isfile(text):
        with open(text, 'r', encoding='utf-8') as f:
            return f.read().strip() or None
    return text or None


def _require_stored_device_bearer_cli(context_spec_str: str | None) -> bool:
    if not context_spec_str or not str(context_spec_str).strip():
        return False
    try:
        data = json.loads(str(context_spec_str))
    except (json.JSONDecodeError, TypeError):
        return False
    if not isinstance(data, dict):
        return False
    opts = data.get("options")
    return isinstance(opts, dict) and bool(opts.get("requireStoredDeviceBearer"))


def _cli_validate_bearer_without_secret(
    auth_type: str,
    auth_secret_id: int | None,
    allow_mspl_token: bool,
    context_spec_str: str | None,
) -> None:
    if auth_type != 'bearer' or auth_secret_id is not None:
        return
    if not allow_mspl_token and not _require_stored_device_bearer_cli(context_spec_str):
        raise RuntimeError(
            "Bearer profiles require --auth-secret-id, --allow-mspl-token, "
            "or contextSpec.options.requireStoredDeviceBearer"
        )
    nk, rk = get_bearer_context_key_pair_from_spec_value(context_spec_str)
    if nk is None or rk is None:
        raise RuntimeError(
            "Bearer without auth secret requires contextSpec with exactly one requirement "
            "with bearerForAuth true and a non-empty key"
        )


def cmd_profiles(args, db: Database, service: PolicyEnforcementService, user):
    if args.action == 'list':
        profiles = db.listEnforcementProfiles(include_inactive=args.include_inactive)
        print(json.dumps([{
            'id': p.id,
            'name': p.name,
            'mode': p.mode,
            'method': p.method,
            'endpointTemplate': p.endpoint_template,
            'isActive': p.is_active,
            'isDefault': p.is_default,
            'autoEnforceOnRegistration': p.auto_enforce_on_registration,
            'authType': p.auth_type,
            'authSecretId': p.auth_secret_id,
        } for p in profiles], indent=2))
        return

    if args.action == 'create':
        if args.mode == 'rest':
            if not args.endpoint_template:
                raise RuntimeError("REST profiles require --endpoint-template")
            service.validate_endpoint_template(args.endpoint_template)
        ctx_spec = _load_context_spec_arg(getattr(args, 'context_spec', None))
        if args.auth_type == 'bearer' and args.auth_secret_id is None and not args.allow_mspl_token:
            if not _require_stored_device_bearer_cli(ctx_spec):
                raise RuntimeError(
                    "Bearer profiles require --auth-secret-id, --allow-mspl-token, "
                    "or contextSpec.options.requireStoredDeviceBearer"
                )
        _cli_validate_bearer_without_secret(
            args.auth_type, args.auth_secret_id, args.allow_mspl_token, ctx_spec
        )
        if args.auth_secret_id is not None and db.getEnforcementSecret(args.auth_secret_id) is None:
            raise RuntimeError(f"Secret {args.auth_secret_id} not found")
        profile = db.createEnforcementProfile(
            name=args.name,
            mode=args.mode,
            method=args.method.upper(),
            endpoint_template=args.endpoint_template,
            headers_template=_parse_json_or_none(args.headers_template),
            payload_template=_parse_json_or_none(args.payload_template),
            timeout_seconds=args.timeout_seconds,
            dry_run=args.dry_run,
            is_default=args.is_default,
            is_active=not args.inactive,
            auto_enforce_on_registration=args.auto_enforce_on_registration,
            auth_type=args.auth_type,
            auth_secret_id=args.auth_secret_id,
            allow_mspl_token=args.allow_mspl_token,
            context_spec=ctx_spec,
            created_by=user.id,
        )
        if profile.is_default:
            db.clearDefaultEnforcementProfiles(exclude_profile_id=profile.id)
        print(json.dumps({'createdProfileId': profile.id}, indent=2))
        return

    if args.action == 'update':
        profile = db.getEnforcementProfile(args.id)
        if profile is None:
            raise RuntimeError(f"Profile {args.id} not found")

        update_data = {}
        if args.name is not None:
            update_data['name'] = args.name
        if args.mode is not None:
            update_data['mode'] = args.mode
        if args.method is not None:
            update_data['method'] = args.method.upper()
        if args.endpoint_template is not None:
            if args.endpoint_template and (args.mode or profile.mode) == 'rest':
                service.validate_endpoint_template(args.endpoint_template)
            update_data['endpoint_template'] = args.endpoint_template
        if args.headers_template is not None:
            update_data['headers_template'] = _parse_json_or_none(args.headers_template)
        if args.payload_template is not None:
            update_data['payload_template'] = _parse_json_or_none(args.payload_template)
        if args.timeout_seconds is not None:
            update_data['timeout_seconds'] = args.timeout_seconds
        if args.dry_run is not None:
            update_data['dry_run'] = args.dry_run
        if args.is_default is not None:
            update_data['is_default'] = args.is_default
        if args.is_active is not None:
            update_data['is_active'] = args.is_active
        if args.auto_enforce_on_registration is not None:
            update_data['auto_enforce_on_registration'] = args.auto_enforce_on_registration
        if args.auth_type is not None:
            update_data['auth_type'] = args.auth_type
        if args.auth_secret_id is not None:
            if db.getEnforcementSecret(args.auth_secret_id) is None:
                raise RuntimeError(f"Secret {args.auth_secret_id} not found")
            update_data['auth_secret_id'] = args.auth_secret_id
        if args.context_spec is not None:
            update_data['context_spec'] = _load_context_spec_arg(args.context_spec)
        if args.allow_mspl_token is not None:
            update_data['allow_mspl_token'] = args.allow_mspl_token

        final_mode = update_data.get('mode', profile.mode)
        final_endpoint = update_data.get('endpoint_template', profile.endpoint_template)
        if final_mode == 'rest':
            if not final_endpoint:
                raise RuntimeError("REST profiles require endpoint_template")
            service.validate_endpoint_template(final_endpoint)

        final_auth_type = update_data.get('auth_type', profile.auth_type)
        final_auth_secret_id = update_data.get('auth_secret_id', profile.auth_secret_id)
        final_allow_mspl_token = update_data.get('allow_mspl_token', profile.allow_mspl_token)
        final_context_spec = update_data.get('context_spec', getattr(profile, 'context_spec', None))
        if (
            final_auth_type == 'bearer'
            and final_auth_secret_id is None
            and not final_allow_mspl_token
            and not _require_stored_device_bearer_cli(final_context_spec)
        ):
            raise RuntimeError(
                "Bearer profiles require auth_secret_id, allow_mspl_token, "
                "or contextSpec.options.requireStoredDeviceBearer"
            )
        _cli_validate_bearer_without_secret(
            final_auth_type, final_auth_secret_id, final_allow_mspl_token, final_context_spec
        )

        updated = db.updateEnforcementProfile(args.id, **update_data)
        if updated is None:
            raise RuntimeError(f"Profile {args.id} not found")
        if updated.is_default:
            db.clearDefaultEnforcementProfiles(exclude_profile_id=updated.id)
        print(json.dumps({'updatedProfileId': updated.id}, indent=2))
        return

    if args.action == 'test':
        from services.policy_enforcement_service import EnforcementPrerequisitesError  # noqa: E402

        ctx: dict = {}
        if getattr(args, 'context_file', None):
            with open(args.context_file, 'r', encoding='utf-8') as f:
                ctx = json.load(f)
        elif getattr(args, 'context_json', None) and str(args.context_json).strip():
            ctx = json.loads(args.context_json)
        try:
            result = service.test_profile(
                profile_id=args.id,
                run_mode=args.run_mode,
                context=ctx,
                requested_by=f"cli:{user.email}",
            )
        except EnforcementPrerequisitesError as exc:
            print(json.dumps({'code': 'ENFORCEMENT_PREREQUISITES', 'missing': exc.missing}, indent=2))
            sys.exit(2)
        print(json.dumps(result, indent=2, default=str))
        return

    raise RuntimeError(f"Unsupported profiles action: {args.action}")


def cmd_mappings(args, db: Database, service: PolicyEnforcementService, user):
    if args.action == 'list':
        mappings = db.listEnforcementMappings(include_inactive=args.include_inactive)
        print(json.dumps([{
            'id': m.id,
            'matchKind': m.match_kind,
            'matchValue': m.match_value,
            'profileId': m.profile_id,
            'priority': m.priority,
            'isActive': m.is_active,
        } for m in mappings], indent=2))
        return

    if args.action == 'create':
        if db.getEnforcementProfile(args.profile_id) is None:
            raise RuntimeError(f"Profile {args.profile_id} not found")
        mapping = db.createEnforcementMapping(
            match_kind=args.match_kind,
            match_value=service.normalize_key(args.match_value),
            profile_id=args.profile_id,
            priority=args.priority,
            is_active=not args.inactive,
            created_by=user.id,
        )
        print(json.dumps({'createdMappingId': mapping.id}, indent=2))
        return

    if args.action == 'update':
        mapping = db.getEnforcementMapping(args.id)
        if mapping is None:
            raise RuntimeError(f"Mapping {args.id} not found")
        update_data = {}
        if args.match_kind is not None:
            update_data['match_kind'] = args.match_kind
        if args.match_value is not None:
            update_data['match_value'] = service.normalize_key(args.match_value)
        if args.profile_id is not None:
            if db.getEnforcementProfile(args.profile_id) is None:
                raise RuntimeError(f"Profile {args.profile_id} not found")
            update_data['profile_id'] = args.profile_id
        if args.priority is not None:
            update_data['priority'] = args.priority
        if args.is_active is not None:
            update_data['is_active'] = args.is_active
        updated = db.updateEnforcementMapping(args.id, **update_data)
        print(json.dumps({'updatedMappingId': updated.id}, indent=2))
        return

    raise RuntimeError(f"Unsupported mappings action: {args.action}")


def cmd_secrets(args, db: Database, service: PolicyEnforcementService):
    if args.action == 'create':
        encrypted = service.secret_manager.encrypt(args.value)
        secret = db.createEnforcementSecret(
            name=args.name,
            ciphertext=encrypted['ciphertext'],
            nonce=encrypted['nonce'],
            key_version=encrypted['key_version'],
        )
        print(json.dumps({'createdSecretId': secret.id}, indent=2))
        return

    if args.action == 'rotate':
        secret = db.getEnforcementSecret(args.id)
        if secret is None:
            raise RuntimeError(f"Secret {args.id} not found")
        encrypted = service.secret_manager.encrypt(args.value)
        db.updateEnforcementSecret(
            args.id,
            ciphertext=encrypted['ciphertext'],
            nonce=encrypted['nonce'],
            key_version=encrypted['key_version'],
        )
        print(json.dumps({'rotatedSecretId': args.id}, indent=2))
        return

    raise RuntimeError(f"Unsupported secrets action: {args.action}")


def build_parser():
    parser = argparse.ArgumentParser(description='Enforcement admin CLI')
    parser.add_argument('--email', required=True, help='Admin email')
    parser.add_argument('--password', required=True, help='Admin password')

    subparsers = parser.add_subparsers(dest='resource', required=True)

    profiles = subparsers.add_parser('profiles', help='Manage enforcement profiles')
    profiles_sub = profiles.add_subparsers(dest='action', required=True)
    profiles_list = profiles_sub.add_parser('list')
    profiles_list.add_argument('--include-inactive', action='store_true')

    profiles_create = profiles_sub.add_parser('create')
    profiles_create.add_argument('--name', required=True)
    profiles_create.add_argument('--mode', choices=['rest', 'era'], default='rest')
    profiles_create.add_argument('--method', default='POST')
    profiles_create.add_argument('--endpoint-template')
    profiles_create.add_argument('--headers-template')
    profiles_create.add_argument('--payload-template')
    profiles_create.add_argument('--timeout-seconds', type=float, default=10.0)
    profiles_create.add_argument('--dry-run', action='store_true')
    profiles_create.add_argument('--is-default', action='store_true')
    profiles_create.add_argument('--inactive', action='store_true')
    profiles_create.add_argument('--auto-enforce-on-registration', action='store_true')
    profiles_create.add_argument('--auth-type', choices=['none', 'bearer'], default='none')
    profiles_create.add_argument('--auth-secret-id', type=int)
    profiles_create.add_argument('--allow-mspl-token', action='store_true')
    profiles_create.add_argument(
        '--context-spec',
        help='JSON string or path to file: enforcement context spec (requirements list)',
    )

    profiles_test = profiles_sub.add_parser('test', help='Dry-run a REST profile with template context')
    profiles_test.add_argument('--id', type=int, required=True, help='Profile id')
    profiles_test.add_argument(
        '--run-mode',
        choices=['preview', 'execute'],
        default='preview',
    )
    profiles_test.add_argument(
        '--context-json',
        help='JSON object for placeholders (e.g. device_ip, token). Optional if profile needs no context.',
    )
    profiles_test.add_argument('--context-file', help='Path to JSON file with the same keys as --context-json')

    profiles_update = profiles_sub.add_parser('update')
    profiles_update.add_argument('--id', type=int, required=True)
    profiles_update.add_argument('--name')
    profiles_update.add_argument('--mode', choices=['rest', 'era'])
    profiles_update.add_argument('--method')
    profiles_update.add_argument('--endpoint-template')
    profiles_update.add_argument('--headers-template')
    profiles_update.add_argument('--payload-template')
    profiles_update.add_argument('--timeout-seconds', type=float)
    profiles_update.add_argument('--dry-run', type=lambda x: x.lower() == 'true')
    profiles_update.add_argument('--is-default', type=lambda x: x.lower() == 'true')
    profiles_update.add_argument('--is-active', type=lambda x: x.lower() == 'true')
    profiles_update.add_argument('--auto-enforce-on-registration', type=lambda x: x.lower() == 'true')
    profiles_update.add_argument('--auth-type', choices=['none', 'bearer'])
    profiles_update.add_argument('--auth-secret-id', type=int)
    profiles_update.add_argument('--allow-mspl-token', type=lambda x: x.lower() == 'true')
    profiles_update.add_argument(
        '--context-spec',
        help='JSON string or path to file: enforcement context spec',
    )

    mappings = subparsers.add_parser('mappings', help='Manage enforcement mappings')
    mappings_sub = mappings.add_subparsers(dest='action', required=True)
    mappings_list = mappings_sub.add_parser('list')
    mappings_list.add_argument('--include-inactive', action='store_true')

    mappings_create = mappings_sub.add_parser('create')
    mappings_create.add_argument('--match-kind', choices=['explicitProfile', 'policyType', 'capability'], required=True)
    mappings_create.add_argument('--match-value', required=True)
    mappings_create.add_argument('--profile-id', type=int, required=True)
    mappings_create.add_argument('--priority', type=int, default=100)
    mappings_create.add_argument('--inactive', action='store_true')

    mappings_update = mappings_sub.add_parser('update')
    mappings_update.add_argument('--id', type=int, required=True)
    mappings_update.add_argument('--match-kind', choices=['explicitProfile', 'policyType', 'capability'])
    mappings_update.add_argument('--match-value')
    mappings_update.add_argument('--profile-id', type=int)
    mappings_update.add_argument('--priority', type=int)
    mappings_update.add_argument('--is-active', type=lambda x: x.lower() == 'true')

    secrets = subparsers.add_parser('secrets', help='Manage enforcement secrets')
    secrets_sub = secrets.add_subparsers(dest='action', required=True)
    secrets_create = secrets_sub.add_parser('create')
    secrets_create.add_argument('--name', required=True)
    secrets_create.add_argument('--value', required=True)

    secrets_rotate = secrets_sub.add_parser('rotate')
    secrets_rotate.add_argument('--id', type=int, required=True)
    secrets_rotate.add_argument('--value', required=True)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    db = Database()
    service = PolicyEnforcementService(db, legacy_enforcer=lambda _mspl_xml, _device: None)
    user = _require_admin_user(db, args.email, args.password)

    if args.resource == 'profiles':
        cmd_profiles(args, db, service, user)
    elif args.resource == 'mappings':
        cmd_mappings(args, db, service, user)
    elif args.resource == 'secrets':
        cmd_secrets(args, db, service)
    else:
        raise RuntimeError(f"Unsupported resource: {args.resource}")


if __name__ == '__main__':
    main()
