"""Create prerequisite notifications for all eligible users and enqueue Telegram delivery."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from services.notifications import templates
from services.notifications.jobs import enqueue_notification_delivery

logger = logging.getLogger(__name__)


def _env_flag(name: str, default: bool = True) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {'1', 'true', 'yes', 'on'}


def _feam_dedup_bucket() -> int:
    hours = 12
    raw = os.getenv('FEAM_FAILURE_NOTIFY_DEDUP_HOURS')
    if raw is not None:
        try:
            hours = max(1, int(raw))
        except ValueError:
            pass
    return int(time.time()) // (hours * 3600)


def _truncate_error_message(message: str, max_len: int = 200) -> str:
    text = (message or '').strip() or '(unknown)'
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + '…'


def _missing_fingerprint(missing: List[Any]) -> str:
    try:
        blob = json.dumps(missing, sort_keys=True, default=str)
    except TypeError:
        blob = str(missing)
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()[:24]


def _missing_fields_human(missing: List[Any]) -> str:
    """Usa la etiqueta humana del requisito si existe; la clave técnica solo como respaldo."""
    parts = []
    for item in missing or []:
        if isinstance(item, dict):
            label = item.get("label")
            key = item.get("key")
            if label is not None and str(label).strip():
                parts.append(str(label).strip())
            elif key is not None and str(key).strip():
                parts.append(str(key).strip())
            else:
                parts.append(str(item))
        else:
            parts.append(str(item))
    return ", ".join(parts) if parts else "(unknown)"


def _device_display_name(device, device_id: str) -> str:
    """Nombre legible: nombre > fabricante+modelo > sufijo corto del id (evita UUID completo)."""
    did = (device_id or "").strip()
    name = getattr(device, "name", None)
    if name and str(name).strip():
        return str(name).strip()
    chunks: List[str] = []
    for attr in ("manufacturer", "model"):
        v = getattr(device, attr, None)
        if v and str(v).strip():
            chunks.append(str(v).strip())
    if chunks:
        return " ".join(chunks)
    if len(did) >= 14:
        return f"…{did[-10:]}"
    return did or "—"


class NotificationService:
    """Domain service: prerequisites blocked → per-user notification rows + queue."""

    def __init__(self, db):
        self.db = db

    def notify_policy_prerequisites(
        self,
        *,
        device,
        policy_id: str,
        policy_name: str,
        missing: List[Any],
    ) -> None:
        if not _env_flag('NOTIFICATIONS_ENABLED', True):
            logger.warning(
                'notify_policy_prerequisites: NOTIFICATIONS_ENABLED is false; skipping policy=%s',
                policy_id,
            )
            return
        device_id = getattr(device, 'identifier', None) or str(getattr(device, 'id', ''))
        device_name = _device_display_name(device, device_id)
        mf = _missing_fingerprint(missing)
        human = _missing_fields_human(missing)
        ntype = 'missing_enforcement_context'
        for user in self.db.getUsersEligibleForPrerequisiteNotifications():
            dedup = f'{user.id}:{device_id}:policy:{policy_id}:{mf}:{ntype}'
            if self.db.getNotificationByDedupKey(dedup):
                continue
            lang = getattr(user, 'language', None) or 'es'
            body = templates.render_template(
                lang,
                'missing_policy_context',
                {
                    'device_name': device_name,
                    'missing_fields': human,
                    'policy_name': policy_name or policy_id,
                    'policy_id': str(policy_id),
                },
            )
            row = self.db.createNotification(
                user_id=user.id,
                device_id=device_id,
                notification_type=ntype,
                language=lang,
                message=body,
                deduplication_key=dedup,
                policy_id=str(policy_id),
                threat_id=None,
                mitigation_id=None,
                threat_mud_url=None,
            )
            if row:
                if not enqueue_notification_delivery(row.id):
                    logger.warning('Notification %s created but not enqueued (Redis/RQ)', row.id)

    def notify_mitigation_prerequisites(
        self,
        *,
        device,
        threat_id: str,
        mitigation_id: str,
        threat_mud_url: Optional[str],
        mitigation_name: str,
        missing: List[Any],
        mspl_index: int = 0,
    ) -> None:
        if not _env_flag('NOTIFICATIONS_ENABLED', True):
            logger.warning(
                'notify_mitigation_prerequisites: NOTIFICATIONS_ENABLED is false; skipping threat=%s mitigation=%s',
                threat_id,
                mitigation_id,
            )
            return
        device_id = getattr(device, 'identifier', None) or str(getattr(device, 'id', ''))
        device_name = _device_display_name(device, device_id)
        mf = _missing_fingerprint(missing)
        human = _missing_fields_human(missing)
        ntype = 'missing_mitigation_fields'
        users = self.db.getUsersEligibleForPrerequisiteNotifications()
        if not users:
            logger.warning(
                'notify_mitigation_prerequisites: no eligible users (enable in-app notifications in '
                'Settings or link Telegram); device=%s threat=%s mitigation=%s',
                device_id,
                threat_id,
                mitigation_id,
            )
            return
        created = 0
        for user in users:
            dedup = f'{user.id}:{device_id}:threat:{threat_id}:mit:{mitigation_id}:i{mspl_index}:{mf}:{ntype}'
            if self.db.getNotificationByDedupKey(dedup):
                continue
            lang = getattr(user, 'language', None) or 'es'
            body = templates.render_template(
                lang,
                'missing_mitigation_fields',
                {
                    'device_name': device_name,
                    'missing_fields': human,
                    'mitigation_name': mitigation_name,
                },
            )
            row = self.db.createNotification(
                user_id=user.id,
                device_id=device_id,
                notification_type=ntype,
                language=lang,
                message=body,
                deduplication_key=dedup,
                policy_id=None,
                threat_id=str(threat_id),
                mitigation_id=str(mitigation_id),
                threat_mud_url=threat_mud_url,
            )
            if row:
                created += 1
                if not enqueue_notification_delivery(row.id):
                    logger.warning('Notification %s created but not enqueued (Redis/RQ)', row.id)
        logger.info(
            'notify_mitigation_prerequisites: eligible_users=%s rows_created=%s device=%s threat=%s mitigation=%s',
            len(users),
            created,
            device_id,
            threat_id,
            mitigation_id,
        )
        if created == 0:
            logger.warning(
                'notify_mitigation_prerequisites: no new rows (dedup already existed for all users, or '
                'createNotification returned None); device=%s',
                device_id,
            )

    def notify_feam_unavailable(
        self,
        *,
        endpoint: str,
        error_message: str,
        status_code: Optional[int] = None,
    ) -> None:
        if not _env_flag('NOTIFICATIONS_ENABLED', True):
            logger.warning(
                'notify_feam_unavailable: NOTIFICATIONS_ENABLED is false; skipping endpoint=%s',
                endpoint,
            )
            return
        users = self.db.getUsersEligibleForAdminNotifications()
        if not users:
            logger.warning(
                'notify_feam_unavailable: no eligible admin users; endpoint=%s',
                endpoint,
            )
            return
        bucket = _feam_dedup_bucket()
        ntype = 'feam_unavailable'
        truncated_error = _truncate_error_message(error_message)
        status_label = str(status_code) if status_code is not None else 'N/A'
        created = 0
        for user in users:
            dedup = f'{user.id}:feam_unavailable:b{bucket}'
            if self.db.getNotificationByDedupKey(dedup):
                continue
            lang = getattr(user, 'language', None) or 'es'
            body = templates.render_template(
                lang,
                'feam_unavailable',
                {
                    'endpoint': endpoint or 'unknown',
                    'status_code': status_label,
                    'error_message': truncated_error,
                },
            )
            row = self.db.createNotification(
                user_id=user.id,
                device_id=None,
                notification_type=ntype,
                language=lang,
                message=body,
                deduplication_key=dedup,
                policy_id=None,
                threat_id=None,
                mitigation_id=None,
                threat_mud_url=None,
            )
            if row:
                created += 1
                if not enqueue_notification_delivery(row.id):
                    logger.warning('Notification %s created but not enqueued (Redis/RQ)', row.id)
        logger.info(
            'notify_feam_unavailable: eligible_admins=%s rows_created=%s endpoint=%s bucket=%s',
            len(users),
            created,
            endpoint,
            bucket,
        )
