#!/usr/bin/env python3
"""RQ worker for doss-notifications queue. Run from Domain-Manager directory."""
import os
import sys

# Invoked as `python scripts/run_notification_worker.py`: Python puts `scripts/` first on
# sys.path, so `services` (sibling of scripts/) is not importable unless we add the root.
_DM_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _DM_ROOT not in sys.path:
    sys.path.insert(0, _DM_ROOT)

from redis import from_url
from rq import Worker

from services.notifications.jobs import QUEUE_NAME


def main():
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    conn = from_url(redis_url)
    Worker([QUEUE_NAME], connection=conn).work(with_scheduler=True)


if __name__ == '__main__':
    main()
