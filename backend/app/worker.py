"""The background worker: a long-running process (Render Background Worker, or any machine) that works through the content pipeline queue.

    python -m app.worker

The queue is the `ingest_jobs` table in the same Postgres the API uses, so there is no broker to run. Workers claim a job with
SELECT ... FOR UPDATE SKIP LOCKED, so several can run side by side without taking the same job. A job that raises is retried with
exponential back-off up to its max_attempts, then marked failed and reviewers are told. A worker that dies mid-job leaves a stale lock; the
reaper puts such jobs back. Every loop writes a heartbeat row so the API can show whether the worker is alive. Logs are one JSON object per
line on stdout, which Render (and any log shipper) can read."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import socket
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from app.core.ai_provider import ai_provider
from app.core.database import SessionLocal
from app.ingest.fetch import fetch
from app.models import IngestJob, WorkerHeartbeat
from app.services import notifications, pipeline
from app.services.tutor import ai_enabled

VERSION = "worker-1"
STALE_LOCK = timedelta(minutes=15)           # a job running longer than this has lost its worker
RETRY_BLOCKED_AFTER = pipeline.RETRY_BLOCKED_AFTER
LOG_KEEP = 20
DRAFT_LOCK = 70001                          # advisory lock so two workers never draft from the same page at once
log = logging.getLogger("zenith.worker")


def _now() -> datetime:
    return datetime.now(timezone.utc)


class JsonFormatter(logging.Formatter):
    def format(self, r: logging.LogRecord) -> str:
        d = {"t": _now().isoformat(timespec="seconds"), "level": r.levelname.lower(), "msg": r.getMessage(), "worker": getattr(r, "worker", None)}
        for k in ("job", "kind", "attempt", "ms"):
            if hasattr(r, k):
                d[k] = getattr(r, k)
        if r.exc_info:
            d["error"] = self.formatException(r.exc_info)[-600:]
        return json.dumps(d, ensure_ascii=False)


def note(job: IngestJob, level: str, msg: str) -> None:
    """Add a line to the job's own history (kept short), so a reviewer can see what happened without server logs."""
    job.log = [*(job.log or []), {"at": _now().isoformat(timespec="seconds"), "level": level, "msg": msg[:200]}][-LOG_KEEP:]


def claim(db: Session, worker: str) -> IngestJob | None:
    """Take the most requested queued job that is due. Safe to call from several workers at once."""
    now = _now()
    job = db.scalar(select(IngestJob).where(IngestJob.kind == "request", IngestJob.status == "queued", or_(IngestJob.run_after.is_(None), IngestJob.run_after <= now))
                    .order_by(IngestJob.demand.desc(), IngestJob.created_at).limit(1).with_for_update(skip_locked=True))
    if job is None:
        return None
    job.status, job.locked_by, job.locked_at, job.attempts, job.updated_at = "running", worker, now, job.attempts + 1, now
    note(job, "info", f"started by {worker}, attempt {job.attempts} of {job.max_attempts}")
    db.commit()
    return job


def fail(db: Session, job: IngestJob, exc: BaseException) -> str:
    """A job raised. Retry later with back-off, or give up and tell the reviewers."""
    db.rollback()
    job = db.get(IngestJob, job.id)
    msg = f"{type(exc).__name__}: {exc}"[:250]
    job.locked_by = job.locked_at = None
    job.updated_at = _now()
    job.error = msg[:300]
    if job.attempts < job.max_attempts:
        wait = min(3600, 60 * 2 ** (job.attempts - 1))
        job.status, job.run_after = "queued", _now() + timedelta(seconds=wait)
        note(job, "warn", f"failed ({msg}); retry in {wait} s")
        outcome = "retry"
    else:
        job.status = "failed"
        note(job, "error", f"gave up after {job.attempts} attempts ({msg})")
        notifications.notify_role(db, ("reviewer", "admin"), "pipeline", "A pipeline job failed", f"{job.subject_id or ''} Class {job.grade or ''}: {msg}"[:300],
                                  "/review/pipeline", f"jobfail-{job.id}")
        outcome = "failed"
    db.commit()
    return outcome


def reap(db: Session) -> int:
    """Jobs whose worker vanished (stale lock) go back to the queue, or fail if they have used all their attempts."""
    n = 0
    for job in db.scalars(select(IngestJob).where(IngestJob.status == "running", IngestJob.locked_at < _now() - STALE_LOCK).with_for_update(skip_locked=True)):
        job.locked_by = job.locked_at = None
        job.updated_at = _now()
        if job.attempts < job.max_attempts:
            job.status = "queued"
            note(job, "warn", "worker stopped responding; put back in the queue")
        else:
            job.status, job.error = "failed", "The worker stopped responding too many times."
            note(job, "error", job.error)
        n += 1
    db.commit()
    return n


def requeue_blocked(db: Session) -> int:
    """A request that found nothing is tried again after a few days, because sources and topics change."""
    n = 0
    for job in db.scalars(select(IngestJob).where(IngestJob.kind == "request", IngestJob.status == "blocked", IngestJob.updated_at < _now() - RETRY_BLOCKED_AFTER).with_for_update(skip_locked=True)):
        job.status, job.attempts, job.run_after = "queued", 0, None
        note(job, "info", "retrying a request that found nothing earlier")
        n += 1
    db.commit()
    return n


def heartbeat(db: Session, name: str, started: datetime, stats: dict) -> None:
    row = db.get(WorkerHeartbeat, name)
    if row is None:
        row = WorkerHeartbeat(name=name, started_at=started, last_seen=_now(), version=VERSION, stats=stats)
        db.add(row)
    else:
        row.last_seen, row.stats, row.version = _now(), stats, VERSION
    db.commit()


async def _generate(**kw) -> str:
    return await ai_provider.generate_chat(**kw)


def cycle(db: Session, name: str, fetcher: Callable[..., bytes] = fetch, generate=None) -> str | None:
    """One pass: housekeeping, then one request job, otherwise one draft. Returns what was done, or None when idle."""
    reap(db)
    requeue_blocked(db)
    job = claim(db, name)
    if job is not None:
        t0 = time.monotonic()
        try:
            r = pipeline.process_request(db, job, fetcher)
            job = db.get(IngestJob, job.id)
            job.locked_by = job.locked_at = None
            note(job, "info", f"finished: {r['pages']} page(s) stored")
            db.commit()
            log.info("request done", extra={"worker": name, "job": str(job.id), "kind": "request", "attempt": job.attempts, "ms": int((time.monotonic() - t0) * 1000)})
            return "request"
        except Exception as e:  # noqa: BLE001 - any failure is retried or recorded, never crashes the worker
            log.error("request failed", extra={"worker": name, "job": str(job.id), "kind": "request", "attempt": job.attempts}, exc_info=True)
            fail(db, job, e)
            return "failed"
    if generate is not None:
        if db.execute(text("select pg_try_advisory_lock(:k)"), {"k": DRAFT_LOCK}).scalar():
            try:
                out = asyncio.run(pipeline.run_drafts(db, generate, limit=1))
                if out.get("drafted") or out.get("rejected"):
                    log.info("draft made", extra={"worker": name, "kind": "draft"})
                    return "draft"
            finally:
                db.rollback()
                db.execute(text("select pg_advisory_unlock(:k)"), {"k": DRAFT_LOCK})
                db.commit()
    return None


def main() -> None:
    name = os.environ.get("WORKER_NAME") or f"{socket.gethostname()}-{os.getpid()}"
    poll = float(os.environ.get("WORKER_POLL_SECONDS", "5"))
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[h], force=True)
    stop = {"now": False}
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.__setitem__("now", True))         # finish the current job, then exit cleanly
    started = _now()
    stats = {"done": 0, "failed": 0, "drafts": 0}
    gen = _generate if ai_enabled() else None
    log.info("worker started", extra={"worker": name})
    while not stop["now"]:
        try:
            with SessionLocal() as db:
                what = cycle(db, name, generate=gen)
                if what:
                    stats["done" if what == "request" else "failed" if what == "failed" else "drafts"] += 1
                heartbeat(db, name, started, {**stats, "ai": gen is not None})
        except Exception:  # noqa: BLE001 - e.g. the database blinked: log it and keep going
            log.error("loop error", extra={"worker": name}, exc_info=True)
            what = None
        if not what:
            for _ in range(int(poll * 2)):                                 # sleep in short steps so a stop request is honoured quickly
                if stop["now"]:
                    break
                time.sleep(0.5)
    log.info("worker stopped", extra={"worker": name})


if __name__ == "__main__":
    main()
