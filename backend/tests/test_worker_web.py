import threading
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from app import worker, worker_web
from app.core.config import settings
from app.services import wake
from tests.conftest import auth
from tests.test_api import API, world  # noqa: F401
from tests.test_pipeline import people  # noqa: F401


@pytest.fixture()
def web(monkeypatch):
    monkeypatch.setattr(settings, "WORKER_SECRET", "w-secret-for-tests")
    monkeypatch.setenv("WORKER_DRAIN_ON_START", "0")
    worker_web.state.update(thread=None, done=0, failed=0, drafts=0, last_error=None)
    with TestClient(worker_web.app) as c:
        yield c


H = {"Authorization": "Bearer w-secret-for-tests"}


def test_the_worker_service_needs_its_secret_and_says_nothing_without_it(web, monkeypatch):
    assert web.get("/").json() == {"service": "zenith-worker"}
    assert web.post("/run").status_code == 401 and web.post("/run", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert web.get("/status").status_code == 401
    monkeypatch.setattr(settings, "WORKER_SECRET", "")
    assert web.post("/run", headers=H).status_code == 503                      # unset secret: refuse everything, never accept an empty one


def test_a_run_drains_the_queue_then_stops_and_a_second_run_while_busy_does_not_start_another(web, monkeypatch):
    gate = threading.Event()
    calls = []

    def fake_cycle(db, name, fetcher=None, generate=None):
        calls.append(1)
        gate.wait(5)
        return "request" if len(calls) <= 2 else None                           # two jobs, then idle
    monkeypatch.setattr(worker, "cycle", fake_cycle)
    monkeypatch.setattr(worker, "heartbeat", lambda *a, **k: None)
    r = web.post("/run", headers=H)
    assert r.status_code == 202 and r.json() == {"started": True}
    time.sleep(0.2)
    assert web.post("/run", headers=H).json() == {"started": False}              # already draining
    assert web.get("/status", headers=H).json()["running"] is True
    gate.set()
    for _ in range(50):
        if not web.get("/status", headers=H).json()["running"]:
            break
        time.sleep(0.1)
    st = web.get("/status", headers=H).json()
    assert st["running"] is False and st["done"] == 2 and len(calls) == 3 and st["finished_at"]
    assert web.post("/run", headers=H).json() == {"started": True}               # idle again: a new wake starts a new drain


def test_a_drain_that_hits_an_error_records_it_and_ends_instead_of_dying(web, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("database blinked")
    monkeypatch.setattr(worker, "cycle", boom)
    web.post("/run", headers=H)
    for _ in range(50):
        if not web.get("/status", headers=H).json()["running"]:
            break
        time.sleep(0.1)
    assert "database blinked" in web.get("/status", headers=H).json()["last_error"]


def test_waking_the_worker_is_best_effort_and_sends_the_secret(monkeypatch):
    assert wake.wake_worker() is False                                           # not configured: nothing happens, nothing breaks
    monkeypatch.setattr(settings, "WORKER_URL", "https://worker.example.test/")
    monkeypatch.setattr(settings, "WORKER_SECRET", "s")
    seen = {}

    def ok(url, headers, timeout):
        seen.update(url=url, auth=headers["Authorization"])
        return httpx.Response(202)
    monkeypatch.setattr(wake.httpx, "post", ok)
    assert wake.wake_worker() is True and seen == {"url": "https://worker.example.test/run", "auth": "Bearer s"}
    monkeypatch.setattr(wake.httpx, "post", lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectTimeout("asleep")))
    assert wake.wake_worker() is False                                           # a worker that is still waking is not an error


def test_asking_for_lessons_wakes_the_worker_and_the_cron_hands_over_to_it(client, db, people, monkeypatch):
    woke = []
    monkeypatch.setattr(wake, "wake_worker", lambda: woke.append(1) or True)
    r = client.post(f"{API}/coverage/request", headers=auth(people["s7"]), json={"subject": "maths"})
    assert r.status_code == 200 and woke == [1]
    monkeypatch.setattr(settings, "CRON_SECRET", "c")
    monkeypatch.setattr(settings, "WORKER_URL", "https://worker.example.test")
    monkeypatch.setattr(settings, "WORKER_SECRET", "s")
    out = client.get(f"{API}/ingest/run", headers={"Authorization": "Bearer c"}).json()
    assert out == {"mode": "worker", "woke": True} and woke == [1, 1]            # handed to the worker, not run inside the API
    assert client.get(f"{API}/pipeline/overview", headers=auth(people["reviewer"])).json()["workerConfigured"] is True
