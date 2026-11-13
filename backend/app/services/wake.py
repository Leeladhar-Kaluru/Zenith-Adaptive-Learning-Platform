"""Wake the free-tier worker. A request to the Render service wakes it; on start-up it drains the queue, so even a call that times out while the instance is
waking still gets the work started. Best effort by design: if the worker is not configured or unreachable nothing breaks, the job stays queued and the next
wake (the daily cron, or another request) picks it up."""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings

log = logging.getLogger("zenith.wake")


def configured() -> bool:
    return bool(settings.WORKER_URL and settings.WORKER_SECRET)


def wake_worker() -> bool:
    """Tell the worker there is work. Returns True if it answered."""
    if not configured():
        return False
    try:
        r = httpx.post(settings.WORKER_URL.rstrip("/") + "/run", headers={"Authorization": f"Bearer {settings.WORKER_SECRET}"}, timeout=8.0)
        return r.status_code < 300
    except httpx.HTTPError:
        log.info("worker did not answer in time; it will start on its own when it wakes")
        return False
