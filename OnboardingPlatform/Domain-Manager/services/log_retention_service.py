"""
Service for app-native log retention jobs.
"""
import logging
import threading
import time


class LogRetentionService:
    """
    Executes periodic retention for policy execution logs and SQLite vacuum.
    """

    def __init__(self, db, *, db_factory=None):
        self.db = db
        self.db_factory = db_factory
        self._retention_days = 3
        self._interval_seconds = 21600
        self._vacuum_enabled = True
        self._vacuum_interval_seconds = 86400
        self._last_vacuum_ts = 0.0
        self._stop_event = threading.Event()
        self._thread = None

    def configure(
        self,
        *,
        retention_days=3,
        interval_seconds=21600,
        vacuum_enabled=True,
        vacuum_interval_seconds=86400,
    ):
        self._retention_days = max(0, int(retention_days or 0))
        self._interval_seconds = max(60, int(interval_seconds or 21600))
        self._vacuum_enabled = bool(vacuum_enabled)
        self._vacuum_interval_seconds = max(300, int(vacuum_interval_seconds or 86400))

    def run_once(self, *, db_override=None):
        active_db = db_override or self.db
        deleted_rows = active_db.purgePolicyExecutionLogsOlderThanDays(self._retention_days)
        logging.info(
            "[log-retention] Purged %s rows older than %s day(s)",
            deleted_rows,
            self._retention_days,
        )

        now_ts = time.time()
        should_vacuum = self._vacuum_enabled and (
            self._last_vacuum_ts == 0.0
            or (now_ts - self._last_vacuum_ts) >= self._vacuum_interval_seconds
        )
        if should_vacuum:
            did_vacuum = active_db.vacuumSqlite()
            if did_vacuum:
                self._last_vacuum_ts = now_ts
                logging.info("[log-retention] SQLite VACUUM completed")

    def _run_loop(self):
        retention_db = self.db_factory() if self.db_factory is not None else self.db
        while not self._stop_event.is_set():
            try:
                self.run_once(db_override=retention_db)
            except Exception as exc:
                logging.warning("[log-retention] Iteration failed: %s", exc, exc_info=True)
            self._stop_event.wait(self._interval_seconds)

    def start_retention_jobs(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="log-retention",
            daemon=True,
        )
        self._thread.start()

    def stop_retention_jobs(self):
        self._stop_event.set()
