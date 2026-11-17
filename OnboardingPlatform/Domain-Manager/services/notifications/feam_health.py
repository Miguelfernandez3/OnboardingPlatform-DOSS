"""Grace-window coordination for FEAM infrastructure failure notifications."""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import timedelta
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

PENDING_ALERT_KEY = "feam:health:pending"
RECOVERY_ENDPOINTS = {"callResourceServer", "getFunctionsOwn"}
DEFAULT_GRACE_MINUTES = 5.0


def _grace_seconds() -> int:
    raw_value = os.getenv("FEAM_FAILURE_NOTIFY_GRACE_MINUTES")
    if raw_value is None:
        minutes = DEFAULT_GRACE_MINUTES
    else:
        try:
            minutes = max(0.0, float(raw_value))
        except ValueError:
            logger.warning(
                "Invalid FEAM_FAILURE_NOTIFY_GRACE_MINUTES='%s'. Falling back to %s minutes.",
                raw_value,
                DEFAULT_GRACE_MINUTES,
            )
            minutes = DEFAULT_GRACE_MINUTES
    return int(minutes * 60)


def _pending_ttl_seconds(grace_seconds: int) -> int:
    return max(grace_seconds * 2, grace_seconds + 60, 60)


def _redis_client():
    from redis import from_url

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0").strip()
    return from_url(
        redis_url or "redis://localhost:6379/0",
        socket_connect_timeout=1,
        socket_timeout=1,
    )


def _enqueue_pending_alert(delay_seconds: int) -> None:
    from rq import Queue

    from services.notifications.jobs import QUEUE_NAME

    queue = Queue(QUEUE_NAME, connection=_redis_client())
    queue.enqueue_in(
        timedelta(seconds=max(1, int(delay_seconds))),
        "services.notifications.jobs.process_feam_health_alert_job",
        job_timeout=120,
    )


def _notify_feam_unavailable(
    *,
    endpoint: str,
    error_message: str,
    status_code: Optional[int] = None,
    db=None,
) -> None:
    from services.notifications.service import NotificationService

    active_db = db
    if active_db is None:
        from Database import Database

        active_db = Database()
    NotificationService(active_db).notify_feam_unavailable(
        endpoint=endpoint,
        error_message=error_message,
        status_code=status_code,
    )


def _json_dumps(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def _decode_payload(raw_payload: Any) -> Optional[Dict[str, Any]]:
    if raw_payload is None:
        return None
    if isinstance(raw_payload, bytes):
        raw_payload = raw_payload.decode("utf-8")
    if not isinstance(raw_payload, str):
        return None
    try:
        payload = json.loads(raw_payload)
    except (TypeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _coerce_status_code(status_code: Any) -> Optional[int]:
    if status_code is None:
        return None
    try:
        return int(status_code)
    except (TypeError, ValueError):
        return None


def _coerce_first_failure_at(payload: Dict[str, Any], fallback: float) -> float:
    try:
        return float(payload.get("first_failure_at"))
    except (TypeError, ValueError):
        return fallback


def record_infrastructure_failure(
    *,
    endpoint: str,
    error_message: str,
    status_code: Optional[int] = None,
    db=None,
) -> bool:
    """Record a FEAM infrastructure failure and schedule an alert after the grace window.

    Returns True when this call created the pending alert window.
    """
    grace_seconds = _grace_seconds()
    status = _coerce_status_code(status_code)
    message = str(error_message or "unknown error")
    if grace_seconds <= 0:
        _notify_feam_unavailable(
            endpoint=endpoint,
            error_message=message,
            status_code=status,
            db=db,
        )
        return True

    now = time.time()
    ttl_seconds = _pending_ttl_seconds(grace_seconds)
    payload = {
        "first_failure_at": now,
        "last_failure_at": now,
        "endpoint": endpoint,
        "error_message": message,
        "status_code": status,
    }

    try:
        redis_client = _redis_client()
        created = bool(
            redis_client.set(
                PENDING_ALERT_KEY,
                _json_dumps(payload),
                ex=ttl_seconds,
                nx=True,
            )
        )
        if created:
            try:
                _enqueue_pending_alert(grace_seconds)
            except Exception:
                redis_client.delete(PENDING_ALERT_KEY)
                raise
            return True

        existing = _decode_payload(redis_client.get(PENDING_ALERT_KEY))
        if existing is None:
            created = bool(
                redis_client.set(
                    PENDING_ALERT_KEY,
                    _json_dumps(payload),
                    ex=ttl_seconds,
                    nx=True,
                )
            )
            if created:
                try:
                    _enqueue_pending_alert(grace_seconds)
                except Exception:
                    redis_client.delete(PENDING_ALERT_KEY)
                    raise
            return created

        payload["first_failure_at"] = _coerce_first_failure_at(existing, now)
        redis_client.set(PENDING_ALERT_KEY, _json_dumps(payload), ex=ttl_seconds)
        return False
    except Exception as exc:
        logger.warning(
            "Failed to record FEAM infrastructure failure for endpoint=%s: %s",
            endpoint,
            exc,
            exc_info=True,
        )
        return False


def record_infrastructure_success(endpoint: str) -> bool:
    """Clear a pending FEAM health alert after a successful recovery endpoint call."""
    if endpoint not in RECOVERY_ENDPOINTS or _grace_seconds() <= 0:
        return False
    try:
        return bool(_redis_client().delete(PENDING_ALERT_KEY))
    except Exception as exc:
        logger.warning(
            "Failed to clear pending FEAM health alert for endpoint=%s: %s",
            endpoint,
            exc,
            exc_info=True,
        )
        return False


def process_pending_alert(*, db=None) -> bool:
    """Send a pending FEAM unavailable alert if the grace window elapsed."""
    grace_seconds = _grace_seconds()
    try:
        redis_client = _redis_client()
        payload = _decode_payload(redis_client.get(PENDING_ALERT_KEY))
        if payload is None:
            return False

        now = time.time()
        first_failure_at = _coerce_first_failure_at(payload, now)
        elapsed_seconds = now - first_failure_at
        if grace_seconds > 0 and elapsed_seconds < grace_seconds:
            remaining_seconds = max(1, int(grace_seconds - elapsed_seconds))
            _enqueue_pending_alert(remaining_seconds)
            return False

        _notify_feam_unavailable(
            endpoint=str(payload.get("endpoint") or "unknown"),
            error_message=str(payload.get("error_message") or "unknown error"),
            status_code=_coerce_status_code(payload.get("status_code")),
            db=db,
        )
        redis_client.delete(PENDING_ALERT_KEY)
        return True
    except Exception as exc:
        logger.warning("Failed to process pending FEAM health alert: %s", exc, exc_info=True)
        return False


record_failure = record_infrastructure_failure
record_success = record_infrastructure_success
