"""The worker for Render's FREE tier.

Render has no free background worker, and a free web service goes to sleep after 15 minutes without incoming HTTP. So the worker is wrapped in a small web
service that works like this, with no keep-alive pings:

  * Any incoming request wakes the instance. On start-up it drains the queue straight away, so even a request that timed out while the instance was waking
    still gets the work done.
  * POST /run (with the shared secret) starts a drain if one is not already running. The API calls it when a student asks for lessons, and the daily cron calls it.
  * A drain runs jobs until the queue is idle or about 13 minutes have passed (before the 15-minute sleep), then stops and the instance sleeps. Anything left,
    or any job cut off by a sleep, is picked up on the next wake (stale locks are recovered by the same worker code).

Start command on Render:  uvicorn app.worker_web:app --host 0.0.0.0 --port $PORT
Moving to a paid Background Worker later needs no code change: run `python -m app.worker` instead."""
from __future__ import annotations

import hmac
import logging
import os
import socket
import sys
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException

from app import worker
from app.core.ai_provider import ai_provider  # noqa: F401  (imported so a bad AI configuration fails at start-up, not mid-job)
from app.core.config import settings
from app.core.database import SessionLocal
from app.services.tutor import ai_enabled

MAX_DRAIN_S = 13 * 60
NAME = os.environ.get("WORKER_NAME") or f"render-{socket.gethostname()}"
log = logging.getLogger("zenith.worker")
state: dict = {"thread": None, "started_at": None, "finished_at": None, "done": 0, "failed": 0, "drafts": 0, "last_error": None}
_lock = threading.Lock()


def _drain() -> None:
    gen = worker._generate if ai_enabled() else None
    began = time.monotonic()
    started = datetime.now(timezone.utc)
    log.info("drain started", extra={"worker": NAME})
    try:
        while time.monotonic() - began < MAX_DRAIN_S:
            with SessionLocal() as db:
                what = worker.cycle(db, NAME, generate=gen)
                if what:
                    state["done" if what == "request" else "failed" if what == "failed" else "drafts"] += 1
                worker.heartbeat(db, NAME, started, {"done": state["done"], "failed": state["failed"], "drafts": state["drafts"], "ai": gen is not None, "mode": "free-web"})
            if not what:
                break                                   # idle: stop, and the instance can sleep
    except Exception as e:  # noqa: BLE001 - recorded; the next wake tries again
        state["last_error"] = f"{type(e).__name__}: {e}"[:200]
        log.error("drain error", extra={"worker": NAME}, exc_info=True)
    finally:
        state["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        log.info("drain finished", extra={"worker": NAME})


def start_drain() -> bool:
    """Start a drain unless one is running. Returns True if a new one started."""
    with _lock:
        t = state["thread"]
        if t is not None and t.is_alive():
            return False
        state["started_at"], state["last_error"] = datetime.now(timezone.utc).isoformat(timespec="seconds"), None
        state["thread"] = threading.Thread(target=_drain, name="drain", daemon=True)
        state["thread"].start()
        return True


@asynccontextmanager
async def lifespan(_: FastAPI):
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(worker.JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[h], force=True)
    if os.environ.get("WORKER_DRAIN_ON_START", "1") == "1":
        start_drain()
    yield


app = FastAPI(title="ZENITH worker", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)


def _auth(authorization: str) -> None:
    secret = settings.WORKER_SECRET
    if not secret:
        raise HTTPException(503, "WORKER_SECRET is not set.")
    if not hmac.compare_digest(authorization.removeprefix("Bearer ").strip(), secret):
        raise HTTPException(401, "Not allowed.")


@app.get("/")
def root():
    return {"service": "zenith-worker"}


@app.post("/run", status_code=202)
def run(authorization: str = Header(default="")):
    _auth(authorization)
    return {"started": start_drain()}


@app.get("/status")
def status(authorization: str = Header(default="")):
    _auth(authorization)
    t = state["thread"]
    return {"running": bool(t and t.is_alive()), **{k: state[k] for k in ("started_at", "finished_at", "done", "failed", "drafts", "last_error")}, "ai": ai_enabled()}
