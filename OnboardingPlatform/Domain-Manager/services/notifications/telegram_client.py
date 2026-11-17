"""Thin Telegram Bot API client (send only)."""

import logging
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token

    def send_message(self, chat_id: str, text: str, parse_mode: str = 'HTML') -> Dict[str, Any]:
        url = f'https://api.telegram.org/bot{self.bot_token}/sendMessage'
        response = requests.post(
            url,
            json={
                'chat_id': chat_id,
                'text': text,
                'parse_mode': parse_mode,
            },
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def get_me(bot_token: str) -> Optional[Dict[str, Any]]:
        try:
            r = requests.get(
                f'https://api.telegram.org/bot{bot_token}/getMe',
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            if data.get('ok') and data.get('result'):
                return data['result']
        except Exception as exc:
            logger.warning('Telegram getMe failed: %s', exc)
        return None
