# api/service_logs.py
"""
Admin endpoint to expose cleaned, redacted stdout logs of platform services
(domain-manager, mud-manager, threat-mud-manager, FDO...) for the demo log panel.

Source = Docker stdout via the docker SDK (the container mounts /var/run/docker.sock
read-only). Lines are filtered (no DEBUG/noise) and redacted (no secrets) server-side,
so nothing sensitive ever reaches the browser.
"""
from __future__ import annotations

import json
import logging
import os
import re

from flask import Blueprint, jsonify, request

from core.auth.decorators import require_admin
from utils.error_handlers import handle_api_errors

service_logs_bp = Blueprint('service_logs', __name__)
logger = logging.getLogger(__name__)

# service key -> (displayName, compose service label). FDO runs in a separate compose,
# so its container name/label can be overridden via LOG_CONTAINERS env (JSON).
# ponytail: static map; add a row per service instead of a discovery endpoint.
_SERVICES = {
    'domain-manager': ('Domain Manager', 'domain-manager'),
    'mud-manager': ('MUD Manager', 'mud-manager'),
    'threat-mud-manager': ('Threat MUD Manager', 'threat-mud-manager'),
    'fdo': ('FDO', 'pri-fdo-aio'),
}

_DEFAULT_TAIL = 200
_MAX_TAIL = 500

# Standard log format used across the Python services: "asctime - name - LEVEL - message"
_LINE_RE = re.compile(
    r'^(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}[.,\d]*)\s*-\s*'
    r'(?P<name>[^-]+?)\s*-\s*'
    r'(?P<level>DEBUG|INFO|WARNING|ERROR|CRITICAL)\s*-\s*'
    r'(?P<msg>.*)$'
)

# Noise to drop entirely (case-insensitive substring match on the raw line).
_NOISE = (
    'waiting for message',
    'leave group and commit',
    'parsing new connexion',
    'GET /health',
    'GET /healthz',
    '/favicon.ico',
)

# Redaction patterns; each match is replaced by ‹redacted›.
# ponytail: fixed regex list; add a pattern if a new secret shape shows up — no DLP engine.
_REDACT = [
    re.compile(r'eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]*'),  # JWT
    re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+'),
    re.compile(r'(?i)\bAuthorization\b\s*[:=]\s*\S+'),
    re.compile(r'(?i)\b(password|passwd|pwd|token|secret|api[_-]?key)\b\s*[:=]\s*\S+'),
    re.compile(r'(?i)\b(JWT_SECRET_KEY|TELEGRAM_BOT_TOKEN|TELEGRAM_WEBHOOK_SECRET)\b\s*[:=]\s*\S+'),
]

_REDACTED = '‹redacted›'


def _container_overrides():
    raw = os.getenv('LOG_CONTAINERS')
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        logger.warning('LOG_CONTAINERS is not valid JSON; ignoring')
        return {}


def _redact(text: str) -> str:
    for pat in _REDACT:
        text = pat.sub(_REDACTED, text)
    return text


def _is_noise(raw: str) -> bool:
    low = raw.lower()
    return any(n.lower() in low for n in _NOISE)


def clean_lines(raw: str) -> list[dict]:
    """Parse -> drop DEBUG/noise -> redact. Pure function so it can be unit-tested."""
    out = []
    for raw_line in raw.splitlines():
        line = raw_line.rstrip()
        if not line or _is_noise(line):
            continue
        m = _LINE_RE.match(line)
        if m:
            if m.group('level') == 'DEBUG':
                continue
            out.append({
                'ts': m.group('ts'),
                'level': m.group('level'),
                'message': _redact(m.group('msg').strip()),
            })
        else:
            out.append({'ts': None, 'level': None, 'message': _redact(line)})
    return out


def _fetch_raw(service_key: str, label: str, tail: int) -> str | None:
    """Return raw stdout of the container for `service_key`, or None if not running /
    docker unavailable. LOG_CONTAINERS[service_key] can override the compose-service label
    with either an exact container name or another compose-service label."""
    import docker  # imported lazily so the app boots even without the SDK/socket

    client = docker.from_env()
    target = _container_overrides().get(service_key, label)
    try:
        # Try exact container name first, then fall back to compose-service label
        # (label is stable across recreations; container names may carry a hash prefix).
        try:
            container = client.containers.get(target)
        except docker.errors.NotFound:
            found = client.containers.list(
                filters={'label': f'com.docker.compose.service={target}'}
            )
            if not found:
                return None
            container = found[0]
        return container.logs(tail=tail, timestamps=False).decode('utf-8', errors='replace')
    except docker.errors.NotFound:
        return None


@service_logs_bp.route('/api/logs/<service>', methods=['GET'])
@handle_api_errors
@require_admin
def get_service_logs(current_user, service):
    entry = _SERVICES.get(service)
    if entry is None:
        return jsonify({
            'error': f'Unknown service: {service}',
            'code': 'SERVICE_NOT_FOUND',
            'details': {'available': list(_SERVICES.keys())},
        }), 404

    display_name, label = entry

    try:
        tail = min(max(int(request.args.get('tail', _DEFAULT_TAIL)), 1), _MAX_TAIL)
    except (TypeError, ValueError):
        tail = _DEFAULT_TAIL

    try:
        raw = _fetch_raw(service, label, tail)
    except Exception as e:  # docker down, socket missing, etc. -> graceful degrade
        logger.warning('Could not read logs for %s: %s', service, e)
        raw = None

    if raw is None:
        return jsonify({
            'service': service,
            'displayName': display_name,
            'available': False,
            'lines': [],
            'truncated': False,
        })

    lines = clean_lines(raw)
    return jsonify({
        'service': service,
        'displayName': display_name,
        'available': True,
        'lines': lines,
        'truncated': len(lines) >= tail,
    })
