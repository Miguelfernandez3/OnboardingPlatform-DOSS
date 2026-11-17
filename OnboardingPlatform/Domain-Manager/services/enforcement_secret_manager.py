"""
Secret encryption/decryption for enforcement credentials.
"""
from __future__ import annotations

import base64
import json
import os
from typing import Dict

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class SecretManagerError(Exception):
    """Base error for secret manager."""


class SecretKeyConfigurationError(SecretManagerError):
    """Raised when encryption keys are not configured properly."""


class EnforcementSecretManager:
    """
    Handles encryption/decryption of enforcement secrets using AES-GCM.

    Keys are provided through environment variables:
    - ENFORCEMENT_KEYS_JSON: JSON object {"v1": "<base64 key>", ...}
    - ENFORCEMENT_ACTIVE_KEY_VERSION: active key version identifier
    """

    def __init__(self):
        self._keys = self._load_keys()
        self._active_key_version = os.getenv('ENFORCEMENT_ACTIVE_KEY_VERSION', '').strip()

    @staticmethod
    def _decode_key_material(raw_value: str) -> bytes:
        try:
            decoded = base64.b64decode(raw_value)
            if decoded:
                return decoded
        except Exception:
            pass
        return raw_value.encode('utf-8')

    def _load_keys(self) -> Dict[str, bytes]:
        raw = os.getenv('ENFORCEMENT_KEYS_JSON', '').strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SecretKeyConfigurationError("ENFORCEMENT_KEYS_JSON is not valid JSON") from exc
        if not isinstance(parsed, dict):
            raise SecretKeyConfigurationError("ENFORCEMENT_KEYS_JSON must be a JSON object")

        keys: Dict[str, bytes] = {}
        for version, material in parsed.items():
            if not isinstance(version, str) or not version.strip():
                raise SecretKeyConfigurationError("Key versions in ENFORCEMENT_KEYS_JSON must be non-empty strings")
            if not isinstance(material, str) or not material.strip():
                raise SecretKeyConfigurationError(f"Key material for version '{version}' must be a non-empty string")
            key_bytes = self._decode_key_material(material.strip())
            if len(key_bytes) not in (16, 24, 32):
                raise SecretKeyConfigurationError(
                    f"Key '{version}' must decode to 16/24/32 bytes for AES-GCM"
                )
            keys[version.strip()] = key_bytes
        return keys

    @property
    def active_key_version(self) -> str:
        return self._active_key_version

    def ensure_ready_for_encryption(self):
        if not self._keys:
            raise SecretKeyConfigurationError("No keys configured (ENFORCEMENT_KEYS_JSON)")
        if not self._active_key_version:
            raise SecretKeyConfigurationError("ENFORCEMENT_ACTIVE_KEY_VERSION is required")
        if self._active_key_version not in self._keys:
            raise SecretKeyConfigurationError(
                f"Active key version '{self._active_key_version}' not found in ENFORCEMENT_KEYS_JSON"
            )

    def encrypt(self, plaintext: str) -> Dict[str, str]:
        self.ensure_ready_for_encryption()
        if not isinstance(plaintext, str) or not plaintext:
            raise SecretManagerError("Secret plaintext must be a non-empty string")

        nonce = os.urandom(12)
        key = self._keys[self._active_key_version]
        cipher = AESGCM(key)
        ciphertext = cipher.encrypt(nonce, plaintext.encode('utf-8'), None)

        return {
            'ciphertext': base64.b64encode(ciphertext).decode('utf-8'),
            'nonce': base64.b64encode(nonce).decode('utf-8'),
            'key_version': self._active_key_version,
        }

    def decrypt(self, *, ciphertext: str, nonce: str, key_version: str) -> str:
        if not key_version or key_version not in self._keys:
            raise SecretManagerError(f"Key version '{key_version}' is not available")
        try:
            ciphertext_bytes = base64.b64decode(ciphertext)
            nonce_bytes = base64.b64decode(nonce)
            plain = AESGCM(self._keys[key_version]).decrypt(nonce_bytes, ciphertext_bytes, None)
            return plain.decode('utf-8')
        except Exception as exc:
            raise SecretManagerError("Unable to decrypt secret") from exc

