"""RQ jobs for notification delivery and deferred notification checks."""

import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

QUEUE_NAME = 'doss-notifications'


def _env_flag(name: str, default: bool = True) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {'1', 'true', 'yes', 'on'}


def process_notification_job(notification_id: int) -> None:
    from Database import Database
    from services.notifications.telegram_client import TelegramNotifier

    if not _env_flag('NOTIFICATIONS_ENABLED', True):
        return

    db = Database()
    notif = db.getNotificationById(notification_id)
    if not notif or notif.status != 'pending':
        return

    user = db.getUserById(notif.user_id)
    if not user or not user.is_active:
        db.updateNotificationFields(
            notification_id,
            status='skipped',
            error='user inactive or missing',
            sent_at=datetime.now(timezone.utc),
        )
        return

    if not _env_flag('TELEGRAM_NOTIFICATIONS_ENABLED', True):
        db.updateNotificationFields(
            notification_id,
            status='skipped',
            error='telegram notifications disabled',
            sent_at=datetime.now(timezone.utc),
        )
        return

    token = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
    if not token:
        db.updateNotificationFields(
            notification_id,
            status='skipped',
            error='TELEGRAM_BOT_TOKEN not configured',
            sent_at=datetime.now(timezone.utc),
        )
        return

    if not user.telegram_enabled or not user.telegram_chat_id:
        db.updateNotificationFields(
            notification_id,
            status='skipped',
            sent_at=datetime.now(timezone.utc),
        )
        return

    notifier = TelegramNotifier(token)
    try:
        notifier.send_message(str(user.telegram_chat_id), notif.message)
        db.updateNotificationFields(
            notification_id,
            status='sent',
            error=None,
            sent_at=datetime.now(timezone.utc),
        )
    except Exception as exc:
        logger.warning('Telegram send failed for notification %s: %s', notification_id, exc)
        db.updateNotificationFields(
            notification_id,
            status='failed',
            error=str(exc)[:2000],
            sent_at=datetime.now(timezone.utc),
        )


def process_feam_health_alert_job() -> None:
    from services.notifications.feam_health import process_pending_alert

    process_pending_alert()


def enqueue_notification_delivery(notification_id: int) -> bool:
    """Push job to RQ. Returns False if enqueue was skipped or failed."""
    if not _env_flag('NOTIFICATIONS_ENABLED', True):
        return False
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0').strip()
    try:
        from redis import from_url
        from rq import Queue

        conn = from_url(redis_url)
        q = Queue(QUEUE_NAME, connection=conn)
        q.enqueue(
            'services.notifications.jobs.process_notification_job',
            notification_id,
            job_timeout=120,
        )
        return True
    except Exception as exc:
        logger.error('RQ enqueue failed for notification %s: %s', notification_id, exc)
        return False
