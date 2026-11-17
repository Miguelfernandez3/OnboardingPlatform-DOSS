# api/me_notifications.py
"""Current-user notification settings, Telegram linking, and in-app notification list."""
from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timezone, timedelta

from flask import Blueprint, jsonify, request

from core.auth.decorators import require_auth
from services.notifications.telegram_client import TelegramNotifier
from utils.app_context import get_dadm_instance
from utils.error_handlers import handle_api_errors

logger = logging.getLogger(__name__)

me_notifications_bp = Blueprint('me_notifications', __name__)


def _settings_dict(user):
    return {
        'language': getattr(user, 'language', None) or 'es',
        'telegramEnabled': bool(getattr(user, 'telegram_enabled', False)),
        'telegramLinked': bool(getattr(user, 'telegram_chat_id', None)),
        'inAppNotificationsEnabled': bool(getattr(user, 'in_app_notifications_enabled', True)),
    }


def _notification_dict(n):
    return {
        'id': n.id,
        'message': n.message,
        'notificationType': n.notification_type,
        'status': n.status,
        'language': n.language,
        'deviceId': n.device_id,
        'policyId': n.policy_id,
        'threatId': n.threat_id,
        'mitigationId': n.mitigation_id,
        'threatMudUrl': n.threat_mud_url,
        'deduplicationKey': n.deduplication_key,
        'error': n.error,
        'createdAt': n.created_at.isoformat() if n.created_at else None,
        'sentAt': n.sent_at.isoformat() if n.sent_at else None,
        'readAt': n.read_at.isoformat() if n.read_at else None,
    }


def _bot_username():
    token = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
    if not token:
        return os.getenv('TELEGRAM_BOT_USERNAME', '').strip() or None
    info = TelegramNotifier.get_me(token)
    if info and info.get('username'):
        return info['username']
    return os.getenv('TELEGRAM_BOT_USERNAME', '').strip() or None


@me_notifications_bp.route('/api/users/me/notification-settings', methods=['GET'])
@handle_api_errors
@require_auth
def get_notification_settings(current_user):
    dadm = get_dadm_instance()
    user = dadm.db.getUserById(current_user['id'])
    if not user:
        return jsonify({'error': 'User not found', 'code': 'USER_NOT_FOUND', 'details': {}}), 404
    return jsonify(_settings_dict(user)), 200


@me_notifications_bp.route('/api/users/me/notification-settings', methods=['PUT'])
@handle_api_errors
@require_auth
def put_notification_settings(current_user):
    dadm = get_dadm_instance()
    data = request.get_json(silent=True) or {}
    te = data.get('telegramEnabled')
    ia = data.get('inAppNotificationsEnabled')
    if data.get('language') is not None:
        return jsonify({
            'error': 'Use PUT /api/users/me/settings to update language',
            'code': 'INVALID_REQUEST',
            'details': {},
        }), 400
    kwargs = {}
    if te is not None:
        kwargs['telegram_enabled'] = bool(te)
    if ia is not None:
        kwargs['in_app_notifications_enabled'] = bool(ia)
    if not kwargs:
        return jsonify({'error': 'No valid fields', 'code': 'INVALID_REQUEST', 'details': {}}), 400
    dadm.db.updateUserTelegramAndSettings(current_user['id'], **kwargs)
    user = dadm.db.getUserById(current_user['id'])
    return jsonify(_settings_dict(user)), 200


@me_notifications_bp.route('/api/users/me/telegram/link-token', methods=['POST'])
@handle_api_errors
@require_auth
def post_telegram_link_token(current_user):
    dadm = get_dadm_instance()
    token = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
    if not token:
        return jsonify({
            'error': 'Telegram bot is not configured',
            'code': 'TELEGRAM_NOT_CONFIGURED',
            'details': {},
        }), 503
    username = _bot_username()
    if not username:
        return jsonify({
            'error': 'Could not resolve bot username',
            'code': 'TELEGRAM_BOT_USERNAME_UNKNOWN',
            'details': {},
        }), 503
    raw = 'link_' + secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    dadm.db.createTelegramLinkToken(raw, current_user['id'], expires_at)
    start_url = f'https://t.me/{username}?start={raw}'
    return jsonify({
        'botUsername': username,
        'startUrl': start_url,
        'expiresAt': expires_at.isoformat(),
    }), 200


@me_notifications_bp.route('/api/users/me/telegram', methods=['DELETE'])
@handle_api_errors
@require_auth
def delete_telegram_link(current_user):
    dadm = get_dadm_instance()
    dadm.db.updateUserTelegramAndSettings(current_user['id'], clear_telegram=True)
    return jsonify({'ok': True}), 200


@me_notifications_bp.route('/api/users/me/notifications', methods=['GET'])
@handle_api_errors
@require_auth
def get_my_notifications(current_user):
    dadm = get_dadm_instance()
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
    except ValueError:
        return jsonify({'error': 'Invalid pagination', 'code': 'INVALID_REQUEST', 'details': {}}), 400
    status = request.args.get('status')
    read_state = request.args.get('read_state')
    if read_state is not None and read_state not in ('unread', 'read'):
        return jsonify({'error': 'Invalid read_state', 'code': 'INVALID_REQUEST', 'details': {}}), 400
    rows, total = dadm.db.getNotificationsForUser(
        current_user['id'],
        page=page,
        per_page=per_page,
        status=status,
        read_state=read_state,
    )
    pages = (total + per_page - 1) // per_page if total else 0
    return jsonify({
        'notifications': [_notification_dict(r) for r in rows],
        'pagination': {
            'page': page,
            'perPage': per_page,
            'total': total,
            'pages': pages,
        },
    }), 200


@me_notifications_bp.route('/api/users/me/notifications/unread-count', methods=['GET'])
@handle_api_errors
@require_auth
def get_unread_notifications_count(current_user):
    dadm = get_dadm_instance()
    count = dadm.db.countUnreadNotificationsForUser(current_user['id'])
    return jsonify({'count': count}), 200


@me_notifications_bp.route('/api/users/me/notifications/<int:nid>/read', methods=['POST'])
@handle_api_errors
@require_auth
def mark_notification_read(nid, current_user):
    dadm = get_dadm_instance()
    ok = dadm.db.markNotificationRead(nid, current_user['id'])
    if not ok:
        return jsonify({'error': 'Not found', 'code': 'NOT_FOUND', 'details': {}}), 404
    return jsonify({'ok': True}), 200


@me_notifications_bp.route('/api/users/me/notifications/read-all', methods=['POST'])
@handle_api_errors
@require_auth
def mark_all_notifications_read(current_user):
    dadm = get_dadm_instance()
    updated = dadm.db.markAllNotificationsRead(current_user['id'])
    return jsonify({'ok': True, 'updated': updated}), 200
