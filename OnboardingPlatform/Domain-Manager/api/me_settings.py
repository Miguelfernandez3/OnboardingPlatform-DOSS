# api/me_settings.py
"""Preferencias generales del usuario autenticado (idioma de la UI, etc.)."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from core.auth.decorators import require_auth
from utils.app_context import get_dadm_instance
from utils.error_handlers import handle_api_errors

me_settings_bp = Blueprint('me_settings', __name__)


@me_settings_bp.route('/api/users/me/settings', methods=['GET'])
@handle_api_errors
@require_auth
def get_me_settings(current_user):
    dadm = get_dadm_instance()
    user = dadm.db.getUserById(current_user['id'])
    if not user:
        return jsonify({'error': 'User not found', 'code': 'USER_NOT_FOUND', 'details': {}}), 404
    lang = getattr(user, 'language', None) or 'es'
    return jsonify({'language': str(lang).lower().split('-')[0]}), 200


@me_settings_bp.route('/api/users/me/settings', methods=['PUT'])
@handle_api_errors
@require_auth
def put_me_settings(current_user):
    dadm = get_dadm_instance()
    data = request.get_json(silent=True) or {}
    lang = data.get('language')
    if lang is None:
        return jsonify({'error': 'language is required', 'code': 'INVALID_REQUEST', 'details': {}}), 400
    normalized = str(lang).lower().split('-')[0]
    if normalized not in {'es', 'en'}:
        return jsonify({
            'error': 'language must be es or en',
            'code': 'INVALID_REQUEST',
            'details': {},
        }), 400
    dadm.db.updateUserTelegramAndSettings(current_user['id'], language=normalized)
    return jsonify({'language': normalized}), 200
