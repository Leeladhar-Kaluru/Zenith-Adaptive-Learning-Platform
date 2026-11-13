from datetime import timedelta

from sqlalchemy import select

from app import worker
from app.models import IngestJob, Notification, SourceAsset, WorkerHeartbeat
from app.services import coverage
from tests.conftest import auth
from tests.test_api import API, world  # noqa: F401
from tests.test_pipeline import PAGE, open_source, people, site  # noqa: F401  (a made-up vetted source and a topic with no lesson)


def ask(client, who, topic="volcano"):
    return client.post(f"{API}/coverage/request", headers=auth(who), json={"subject": "maths", "topic": topic}).json()["id"]


def test_a_worker_claims_the_most_requested_job_and_two_workers_never_get_the_same_one(client, db, people):
    first = ask(client, people["s7"], "volcano")
    ask(client, people["s7"], "magma")                                    # a second, less requested topic
    ask(client, people["s7b"], "volcano")                                 # demand for the first is now 2
    a = worker.claim(db, "w1")
    b = worker.claim(db, "w2")
    assert str(a.id) == first and a.status == "running" and a.locked_by == "w1" and a.attempts == 1
    assert b is not None and b.id != a.id and worker.claim(db, "w3") is None


def test_a_cycle_runs_a_request_to_the_end_and_records_its_own_history(client, db, people):
    jid = ask(client, people["s7"])
    assert worker.cycle(db, "w1", fetcher=site) == "request"
    j = db.get(IngestJob, jid)
    assert j.status == "done" and j.locked_by is None and j.log[-1]["msg"].startswith("finished") and j.log[0]["msg"].startswith("started by w1")
    assert db.scalar(select(SourceAsset).where(SourceAsset.external_id == PAGE)).status == "pending"
    assert worker.cycle(db, "w1", fetcher=site) is None                    # nothing left: the worker idles instead of inventing work


def test_a_failing_job_is_retried_with_back_off_then_fails_and_tells_reviewers(client, db, people, monkeypatch):
    jid = ask(client, people["s7"])

    def boom(*a, **k):
        raise RuntimeError("the source blew up")
    monkeypatch.setattr(worker.pipeline, "process_request", boom)
    for attempt, wait in ((1, 60), (2, 120)):
        assert worker.cycle(db, "w1") == "failed"
        j = db.get(IngestJob, jid)
        assert j.status == "queued" and j.attempts == attempt and "retry in" in j.log[-1]["msg"] and "blew up" in j.error
        assert 0 < (j.run_after - worker._now()).total_seconds() <= wait + 2
        assert worker.claim(db, "w1") is None                              # not due yet
        j.run_after = worker._now() - timedelta(seconds=1)                 # time passes
        db.commit()
    assert worker.cycle(db, "w1") == "failed"
    j = db.get(IngestJob, jid)
    assert j.status == "failed" and j.attempts == 3 and "gave up" in j.log[-1]["msg"]
    assert db.scalars(select(Notification).where(Notification.user_id == people["reviewer"].id, Notification.dedupe_key == f"jobfail-{jid}")).all()
    assert worker.cycle(db, "w1", fetcher=site) is None                    # a failed job is not picked up again by itself


def test_a_job_whose_worker_vanished_goes_back_in_the_queue_and_a_blocked_request_is_retried_later(client, db, people):
    jid = ask(client, people["s7"])
    j = worker.claim(db, "dead-worker")
    j.locked_at = worker._now() - worker.STALE_LOCK - timedelta(minutes=1)
    db.commit()
    assert worker.reap(db) == 1
    j = db.get(IngestJob, jid)
    assert j.status == "queued" and j.locked_by is None and "stopped responding" in j.log[-1]["msg"]
    j.status, j.updated_at = "blocked", worker._now() - worker.RETRY_BLOCKED_AFTER - timedelta(hours=1)
    db.commit()
    assert worker.requeue_blocked(db) == 1 and db.get(IngestJob, jid).status == "queued" and db.get(IngestJob, jid).attempts == 0


def test_the_pipeline_health_screen_says_whether_a_worker_is_alive_and_a_reviewer_can_retry_a_failed_job(client, db, people):
    h = auth(people["reviewer"])
    assert client.get(f"{API}/pipeline/health", headers=auth(people["s7"])).status_code == 403
    assert client.get(f"{API}/pipeline/health", headers=h).json()["workerAlive"] is False        # no heartbeat yet: say so
    started = worker._now()
    worker.heartbeat(db, "w1", started, {"done": 2})
    live = client.get(f"{API}/pipeline/health", headers=h).json()
    assert live["workerAlive"] is True and live["workers"][0]["stats"] == {"done": 2}
    db.get(WorkerHeartbeat, "w1").last_seen = worker._now() - timedelta(minutes=10)
    db.commit()
    assert client.get(f"{API}/pipeline/health", headers=h).json()["workerAlive"] is False
    jid = ask(client, people["s7"])
    j = db.get(IngestJob, jid)
    j.status, j.attempts = "failed", 3
    db.commit()
    assert client.post(f"{API}/pipeline/jobs/{jid}/retry", headers=h).json()["status"] == "queued"
    assert db.get(IngestJob, jid).attempts == 0 and client.post(f"{API}/pipeline/jobs/{jid}/retry", headers=h).status_code == 404       # only failed or blocked ones
