# api/telegram_webhook.py
"""Telegram Bot webhook: link accounts via /start <token>."""
from __future__ import annotations

import logging
import os

from flask import Blueprint, jsonify, request

from services.notifications.telegram_client import TelegramNotifier
from utils.app_context import get_dadm_instance

logger = logging.getLogger(__name__)

telegram_webhook_bp = Blueprint('telegram_webhook', __name__)


def _confirm_message(language: str) -> str:
    lang = (language or 'en').lower().split('-')[0]
    if lang == 'es':
        return 'Notificaciones de Telegram activadas correctamente para tu cuenta.'
    return 'Telegram notifications have been enabled successfully for your account.'


def _invalid_token_message(language: str) -> str:
    lang = (language or 'en').lower().split('-')[0]
    if lang == 'es':
        return 'Código inválido o caducado. Genera uno nuevo desde la aplicación.'
    return 'Invalid or expired linking code. Generate a new one from the app.'


@telegram_webhook_bp.route('/webhooks/telegram', methods=['POST'])
def telegram_webhook():
    secret = os.getenv('TELEGRAM_WEBHOOK_SECRET', '').strip()
    incoming = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
    if secret and incoming != secret:
        return jsonify({'ok': False}), 403

    dadm = get_dadm_instance()
    if dadm is None:
        return jsonify({'ok': False}), 503

    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
    if not bot_token:
        return jsonify({'ok': False}), 503

    update = request.get_json(silent=True) or {}
    message = update.get('message') or {}
    chat = message.get('chat') or {}
    chat_id = chat.get('id')
    text = (message.get('text') or '').strip()

    if chat_id is None or not text:
        return jsonify({'ok': True})

    if not text.startswith('/start'):
        return jsonify({'ok': True})

    parts = text.split(maxsplit=1)
    link_token = parts[1].strip() if len(parts) > 1 else ''

    notifier = TelegramNotifier(bot_token)

    def reply(msg: str):
        try:
            notifier.send_message(str(chat_id), msg, parse_mode='HTML')
        except Exception as exc:
            logger.warning('Telegram reply failed: %s', exc)

    if not link_token:
        reply('DOSS: use the link from the app (Connect Telegram) to pair this chat.')
        return jsonify({'ok': True})

    row = dadm.db.getValidTelegramLinkToken(link_token)
    if not row:
        reply(_invalid_token_message('en'))
        return jsonify({'ok': True})

    user = dadm.db.getUserById(row.user_id)
    lang = (getattr(user, 'language', None) or 'en') if user else 'en'
    if not user or not user.is_active:
        reply(_invalid_token_message(lang))
        return jsonify({'ok': True})

    dadm.db.updateUserTelegramAndSettings(
        user.id,
        telegram_chat_id=str(chat_id),
        telegram_enabled=True,
    )
    dadm.db.markTelegramLinkTokenUsed(row.id)
    reply(_confirm_message(getattr(user, 'language', None) or 'es'))
    return jsonify({'ok': True})
