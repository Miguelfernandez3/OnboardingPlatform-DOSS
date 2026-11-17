#!/usr/bin/env python3
"""
Seed Home Assistant enforcement secrets and REST profiles in Domain-Manager.

Reads JWT tokens from environment (never commit tokens to the repo):
  HA_MAIN_BEARER  — shared token for block-all, thermometer, thermostat
  HA_LAMP_BEARER  — token for smart lamp webhook

Usage (from Domain-Manager directory, with ENFORCEMENT_KEYS_JSON configured):
  export HA_MAIN_BEARER='eyJ...'
  export HA_LAMP_BEARER='eyJ...'
  python3 scripts/seed_ha_enforcement.py
"""
from __future__ import annotations

import json
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, PARENT_DIR)

from Database import Database  # noqa: E402
from services.enforcement_secret_manager import EnforcementSecretManager  # noqa: E402
from services.policy_enforcement_service import PolicyEnforcementService  # noqa: E402

CONTEXT_SPEC = json.dumps(
    {
        "requirements": [
            {
                "key": "ha_ip",
                "label": "IP del hub Home Assistant",
                "source": "operator",
            }
        ]
    }
)

PROFILES = [
    (
        "ha-block-all-doss-devices",
        "http://{{ha_ip}}:8123/api/webhook/-MkjxeD7BPZQhpzf6Wrn-xH6H",
        "ha-main-bearer",
    ),
    (
        "ha-block-smart-lamp",
        "http://{{ha_ip}}:8123/api/webhook/-nyXcg5w6Hfzmg0yz514OZygS",
        "ha-lamp-bearer",
    ),
    (
        "ha-turn-off-thermometer",
        "http://{{ha_ip}}:6001/turn_off_thermometer",
        "ha-main-bearer",
    ),
    (
        "ha-turn-off-thermostat",
        "http://{{ha_ip}}:7001/turn_off_thermostat",
        "ha-main-bearer",
    ),
]


def _get_or_create_secret(db: Database, sm: EnforcementSecretManager, name: str, value: str) -> int:
    existing = db.getEnforcementSecretByName(name)
    if existing is not None:
        print(f"  secret '{name}' already exists (id={existing.id})")
        return existing.id
    encrypted = sm.encrypt(value)
    secret = db.createEnforcementSecret(
        name=name,
        ciphertext=encrypted["ciphertext"],
        nonce=encrypted["nonce"],
        key_version=encrypted["key_version"],
    )
    print(f"  created secret '{name}' (id={secret.id})")
    return secret.id


def _get_or_create_profile(
    db: Database,
    service: PolicyEnforcementService,
    name: str,
    endpoint: str,
    secret_id: int,
) -> int:
    existing = db.getEnforcementProfileByName(name)
    if existing is not None:
        print(f"  profile '{name}' already exists (id={existing.id})")
        return existing.id
    service.validate_endpoint_template(endpoint.replace("{{ha_ip}}", "160.40.54.46"))
    profile = db.createEnforcementProfile(
        name=name,
        mode="rest",
        method="POST",
        endpoint_template=endpoint,
        headers_template=None,
        payload_template=None,
        timeout_seconds=10.0,
        dry_run=False,
        is_default=False,
        is_active=True,
        auto_enforce_on_registration=False,
        auth_type="bearer",
        auth_secret_id=secret_id,
        allow_mspl_token=False,
        context_spec=CONTEXT_SPEC,
        created_by=None,
    )
    print(f"  created profile '{name}' (id={profile.id})")
    return profile.id


def main() -> int:
    main_token = (os.getenv("HA_MAIN_BEARER") or "").strip()
    lamp_token = (os.getenv("HA_LAMP_BEARER") or "").strip()
    if not main_token or not lamp_token:
        print("Set HA_MAIN_BEARER and HA_LAMP_BEARER environment variables.", file=sys.stderr)
        return 1

    db = Database()
    sm = EnforcementSecretManager()
    service = PolicyEnforcementService(db, legacy_enforcer=lambda *_: None)

    print("Creating enforcement secrets...")
    main_id = _get_or_create_secret(db, sm, "ha-main-bearer", main_token)
    lamp_id = _get_or_create_secret(db, sm, "ha-lamp-bearer", lamp_token)
    secret_by_name = {"ha-main-bearer": main_id, "ha-lamp-bearer": lamp_id}

    print("Creating enforcement profiles...")
    for name, endpoint, secret_name in PROFILES:
        _get_or_create_profile(db, service, name, endpoint, secret_by_name[secret_name])

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
