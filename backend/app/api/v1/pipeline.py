"""Notifications, coverage, and the content pipeline (scheduled run and reviewer screens)."""
from __future__ import annotations

import hmac
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.ai_provider import ai_provider
from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_profile, reviewer_only
from app.ingest import assets as asset_svc
from datetime import datetime, timedelta, timezone

from app.models import IngestJob, LessonDraft, Profile, SourceAsset, WorkerHeartbeat
from app.services import coverage, notifications, pipeline
from app.services.tutor import ai_enabled

router = APIRouter()


class ReadIn(BaseModel):
    ids: Optional[list[uuid.UUID]] = None


class RequestIn(BaseModel):
    subject: str = Field(min_length=1, max_length=30)
    topic: Optional[str] = Field(default=None, max_length=coverage.MAX_TOPIC)


@router.get("/notifications")
def my_notifications(p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return notifications.listing(db, p)


@router.post("/notifications/read")
def read_notifications(body: ReadIn, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return {"marked": notifications.mark_read(db, p, body.ids)}


@router.get("/coverage")
def my_coverage(p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    if p.role == "student":
        return coverage.for_student(db, p)
    return {"grade": None, "rows": coverage.table(db)}


@router.post("/coverage/request")
def ask_for_lessons(body: RequestIn, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    try:
        return coverage.request_lessons(db, p, body.subject, body.topic)
    except coverage.CoverageError as e:
        raise HTTPException(e.status, str(e))


async def _generate(**kw) -> str:
    return await ai_provider.generate_chat(**kw)


@router.get("/ingest/run")
async def scheduled_run(authorization: str = Header(default=""), db: Session = Depends(get_db)):
    """Called by the scheduler (Vercel Cron sends the secret as a bearer token). Does a small batch and returns what it did."""
    secret = settings.CRON_SECRET
    if not secret or not hmac.compare_digest(authorization.removeprefix("Bearer ").strip(), secret):
        raise HTTPException(401, "Not allowed.")
    return await pipeline.run_once(db, _generate if ai_enabled() else None)


@router.post("/pipeline/run")
async def run_now(r: Profile = Depends(reviewer_only), db: Session = Depends(get_db)):
    """A reviewer can run one batch by hand from the pipeline screen."""
    return await pipeline.run_once(db, _generate if ai_enabled() else None)


@router.get("/pipeline/overview")
def overview(r: Profile = Depends(reviewer_only), db: Session = Depends(get_db)):
    jobs = db.scalars(select(IngestJob).order_by(IngestJob.created_at.desc()).limit(30)).all()
    pending = db.scalars(select(SourceAsset).where(SourceAsset.kind == "text", SourceAsset.status == "pending").order_by(SourceAsset.retrieved_at.desc()).limit(30)).all()
    drafts = db.scalars(select(LessonDraft).where(LessonDraft.status == "ready").order_by(LessonDraft.created_at.desc()).limit(30)).all()
    return {
        "aiEnabled": ai_enabled(), "cronConfigured": bool(settings.CRON_SECRET), "workerAlive": bool(db.scalar(select(func.count(WorkerHeartbeat.name)).where(WorkerHeartbeat.last_seen > datetime.now(timezone.utc) - timedelta(seconds=ALIVE_S)))),
        "jobs": [{"id": str(j.id), "kind": j.kind, "status": j.status, "grade": j.grade, "subject": j.subject_id, "concept": j.concept_id, "topic": j.topic, "demand": j.demand,
                  "error": j.error, "result": j.result, "attempts": j.attempts, "maxAttempts": j.max_attempts, "log": (j.log or [])[-6:], "at": (j.updated_at or j.created_at).isoformat()} for j in jobs],
        "pages": [{"id": str(a.id), "url": a.url, "title": (a.data or {}).get("title"), "licence": a.licence_id, "credit": a.attribution_text, "sections": len((a.data or {}).get("sections", []))} for a in pending],
        "drafts": [{"id": str(d.id), "title": d.title, "grade": d.grade, "subject": d.subject_id, "score": d.score, "verdict": d.verdict, "at": d.created_at.isoformat()} for d in drafts],
        "queued": db.scalar(select(func.count(IngestJob.id)).where(IngestJob.kind == "request", IngestJob.status == "queued")) or 0,
    }


ALIVE_S = 90


@router.get("/pipeline/health")
def health(r: Profile = Depends(reviewer_only), db: Session = Depends(get_db)):
    """Is the background worker alive, and is the queue moving? Everything comes from the heartbeat rows and the job table."""
    now = datetime.now(timezone.utc)
    workers = [{"name": w.name, "alive": (now - w.last_seen).total_seconds() < ALIVE_S, "lastSeen": w.last_seen.isoformat(), "startedAt": w.started_at.isoformat(), "version": w.version, "stats": w.stats}
               for w in db.scalars(select(WorkerHeartbeat).order_by(WorkerHeartbeat.last_seen.desc()).limit(10))]
    counts = dict(db.execute(select(IngestJob.status, func.count(IngestJob.id)).where(IngestJob.kind == "request").group_by(IngestJob.status)).all())
    oldest = db.scalar(select(func.min(IngestJob.created_at)).where(IngestJob.kind == "request", IngestJob.status == "queued"))
    failed_24h = db.scalar(select(func.count(IngestJob.id)).where(IngestJob.status == "failed", IngestJob.updated_at > now - timedelta(days=1))) or 0
    return {"workerAlive": any(w["alive"] for w in workers), "workers": workers, "queue": counts, "oldestQueuedSeconds": int((now - oldest).total_seconds()) if oldest else None, "failedLast24h": failed_24h}


@router.post("/pipeline/jobs/{job_id}/retry")
def retry_job(job_id: uuid.UUID, r: Profile = Depends(reviewer_only), db: Session = Depends(get_db)):
    j = db.get(IngestJob, job_id)
    if j is None or j.kind != "request" or j.status not in ("failed", "blocked"):
        raise HTTPException(404, "Only a failed or blocked request can be retried.")
    j.status, j.attempts, j.run_after, j.error, j.updated_at = "queued", 0, None, None, datetime.now(timezone.utc)
    db.commit()
    return {"id": str(j.id), "status": j.status}


@router.post("/pipeline/pages/{asset_id}/approve")
def approve_page(asset_id: uuid.UUID, r: Profile = Depends(reviewer_only), db: Session = Depends(get_db)):
    try:
        a = asset_svc.approve_asset(db, asset_id, r.id)
    except Exception as e:  # noqa: BLE001 - the asset service raises its own refusal types with readable text
        raise HTTPException(422, str(e))
    db.commit()
    return {"id": str(a.id), "status": a.status}


@router.get("/pipeline/drafts/{draft_id}")
def draft_detail(draft_id: uuid.UUID, r: Profile = Depends(reviewer_only), db: Session = Depends(get_db)):
    d = db.get(LessonDraft, draft_id)
    if d is None:
        raise HTTPException(404, "Draft not found.")
    import yaml
    return {"id": str(d.id), "title": d.title, "grade": d.grade, "subject": d.subject_id, "scorecard": d.scorecard, "score": d.score, "verdict": d.verdict, "status": d.status,
            "yaml": yaml.safe_dump(d.lesson, allow_unicode=True, sort_keys=False)}


@router.post("/pipeline/drafts/{draft_id}/{action}")
def draft_action(draft_id: uuid.UUID, action: str, r: Profile = Depends(reviewer_only), db: Session = Depends(get_db)):
    """`export` marks the draft as taken into the content tree; `dismiss` throws it away. Neither publishes anything."""
    d = db.get(LessonDraft, draft_id)
    if d is None or action not in ("export", "dismiss"):
        raise HTTPException(404, "Draft not found.")
    d.status = "exported" if action == "export" else "dismissed"
    db.commit()
    return {"id": str(d.id), "status": d.status}
