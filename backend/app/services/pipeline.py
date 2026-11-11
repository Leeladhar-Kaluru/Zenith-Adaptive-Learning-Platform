"""The content pipeline runner. It is called on a schedule (Vercel Cron) and does a small amount of work per call, so it fits a serverless function.

  request  -> find topics of that class and subject that have no published lesson
  import   -> look through vetted open-licence sources for a page on each topic, check the licence, store it as a pending credited asset
  (a person approves the source page)
  draft    -> turn an approved page into a simple lesson draft, evaluate it, and queue it for review

Nothing here publishes. Students only ever see lessons a named reviewer approved. Every step records what it did in ingest_jobs."""
from __future__ import annotations

import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingest import textsource, webtext
from app.ingest.commons import user_agent
from app.ingest.fetch import fetch
from app.models import Concept, IngestJob, LessonDraft, SourceAsset
from app.services import coverage, notifications

RETRY_BLOCKED_AFTER = timedelta(days=3)
PER_REQUEST_TOPICS = 3
MIN_LINK_HITS = 1


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _keywords(c: Concept) -> list[str]:
    words = [k for k in (c.keywords or []) if k] or re.findall(r"[A-Za-z]{4,}", c.title)
    return [w.lower() for w in words][:8]


def discover(db: Session, keywords: list[str], fetcher: Callable[..., bytes]) -> list[tuple[str, str, str]]:
    """(source key, url, link text) candidates from every vetted source's index pages, best match first. Pages already stored are skipped."""
    have = {u for (u,) in db.execute(select(SourceAsset.external_id).where(SourceAsset.kind == "text"))}
    found: list[tuple[int, str, str, str]] = []
    for key, src in textsource.SOURCES.items():
        for idx in src.index_urls:
            try:
                html = fetcher(idx, user_agent=user_agent()).decode("utf-8", errors="replace")
            except Exception:                                   # an index that is down or refuses us is skipped, never crashes the run
                continue
            for url, text in webtext.links(html, idx):
                try:
                    textsource._source_for(url, key)
                except textsource.TextSourceError:
                    continue
                hits = webtext.relevance(text + " " + url.rsplit("/", 1)[-1].replace("-", " ").replace("_", " "), keywords)
                if url != idx and url not in have and hits >= MIN_LINK_HITS:
                    found.append((hits, key, url, text))
    found.sort(key=lambda t: (-t[0], t[2]))
    return [(k, u, t) for _, k, u, t in found]


def _topic_concepts(db: Session, job: IngestJob) -> list[Concept]:
    cs = coverage.missing_concepts(db, job.grade, job.subject_id)
    if job.topic:
        t = job.topic.lower()
        cs = [c for c in cs if t in c.title.lower() or any(t in (k or "").lower() for k in (c.keywords or []))] or cs
    return cs[:PER_REQUEST_TOPICS]


def run_requests(db: Session, fetcher: Callable[..., bytes] = fetch, budget_s: float = 20.0) -> dict:
    """Work through the most requested topics first. Returns counts for the log."""
    start = time.monotonic()
    out = {"requests": 0, "pages": 0, "nothing": 0}
    stale = _now() - RETRY_BLOCKED_AFTER
    jobs = db.scalars(select(IngestJob).where(IngestJob.kind == "request", ((IngestJob.status == "queued") | ((IngestJob.status == "blocked") & (IngestJob.updated_at < stale))))
                      .order_by(IngestJob.demand.desc(), IngestJob.created_at)).all()
    for job in jobs:
        if time.monotonic() - start > budget_s:
            break
        job.status, job.attempts, job.updated_at = "running", job.attempts + 1, _now()
        db.commit()
        made, missed = [], []
        for c in _topic_concepts(db, job):
            if time.monotonic() - start > budget_s:
                break
            cands = discover(db, _keywords(c), fetcher)
            done = False
            for key, url, text in cands[:3]:
                try:
                    a = textsource.import_page(db, url, key, None, keywords=_keywords(c), fetcher=fetcher)
                except (textsource.TextSourceError, ValueError, OSError) as e:
                    missed.append({"concept": c.id, "url": url, "why": str(e)[:160]})
                    continue
                db.add(IngestJob(kind="import", status="done", grade=job.grade, subject_id=job.subject_id, concept_id=c.id, asset_id=a.id,
                                 result={"url": url, "title": text[:120]}, updated_at=_now()))
                made.append({"concept": c.id, "asset": str(a.id), "url": url})
                done = True
                break
            if not done and not any(m["concept"] == c.id for m in missed):
                missed.append({"concept": c.id, "why": "No page about this topic was found in the vetted open-licence sources."})
        job.result = {"imported": made, "missed": missed}
        job.status = "done" if made else "blocked"
        job.error = None if made else "No open-licence source page could be found yet. It will be tried again."
        job.updated_at = _now()
        db.commit()
        out["requests"] += 1
        out["pages"] += len(made)
        out["nothing"] += int(not made)
    if out["pages"]:
        notifications.notify_role(db, ("reviewer", "admin"), "pipeline", f"{out['pages']} new source page{'s' if out['pages'] != 1 else ''} to approve",
                                  "Open the pipeline to check the licence and approve them.", "/review/pipeline", f"pages-{_now().date()}")
        db.commit()
    return out


async def run_drafts(db: Session, generate: Callable[..., Awaitable[str]] | None, limit: int = 1, budget_s: float = 20.0) -> dict:
    """Draft a lesson from each approved text page that has none yet. Needs the AI helper; without it nothing is drafted and that is reported."""
    from app.cms import autodraft, evaluator          # needs PyYAML, so loaded only when drafting is on
    out = {"drafted": 0, "rejected": 0, "skipped": ""}
    if generate is None:
        out["skipped"] = "The AI helper is switched off, so no drafts were made."
        return out
    start = time.monotonic()
    done_assets = {a for (a,) in db.execute(select(LessonDraft.asset_id)) if a}
    imports = db.scalars(select(IngestJob).where(IngestJob.kind == "import", IngestJob.asset_id.isnot(None)).order_by(IngestJob.created_at)).all()
    for imp in imports:
        if out["drafted"] + out["rejected"] >= limit or time.monotonic() - start > budget_s:
            break
        a = db.get(SourceAsset, imp.asset_id)
        c = db.get(Concept, imp.concept_id) if imp.concept_id else None
        if a is None or c is None or a.status != "approved" or a.kind != "text" or a.id in done_assets:
            continue
        slug = f"auto-{c.id}"[:60]
        try:
            lesson = await autodraft.draft(a, grade=c.grade, subject=c.subject_id, slug=slug, title=c.title, concept_id=c.id, concept_title=c.title, generate=generate)
        except autodraft.AutoDraftError as e:
            db.add(IngestJob(kind="draft", status="failed", grade=c.grade, subject_id=c.subject_id, concept_id=c.id, asset_id=a.id, error=str(e)[:300], updated_at=_now()))
            db.commit()
            continue
        source_text = " ".join(s["text"] for s in a.data["sections"])
        card = evaluator.evaluate(lesson, source_text, c.grade)
        job = IngestJob(kind="draft", status="done", grade=c.grade, subject_id=c.subject_id, concept_id=c.id, asset_id=a.id, updated_at=_now(),
                        result={"score": card["score"], "verdict": card["verdict"]})
        db.add(job)
        db.flush()
        db.add(LessonDraft(job_id=job.id, asset_id=a.id, grade=c.grade, subject_id=c.subject_id, concept_id=c.id, slug=slug, title=c.title, lesson=lesson,
                           scorecard=card, score=card["score"], verdict=card["verdict"], status="ready", model="ai_assisted"))
        db.commit()
        out["rejected" if card["verdict"] == "rejected" else "drafted"] += 1
    if out["drafted"]:
        notifications.notify_role(db, ("reviewer", "admin"), "pipeline", f"{out['drafted']} lesson draft{'s' if out['drafted'] != 1 else ''} ready to review",
                                  "Each draft comes with its evaluator scorecard.", "/review/pipeline", f"drafts-{_now().date()}-{uuid.uuid4().hex[:6]}")
        db.commit()
    return out


async def run_once(db: Session, generate: Callable[..., Awaitable[str]] | None, fetcher: Callable[..., bytes] = fetch) -> dict:
    """One scheduled call: find sources for requested topics, then draft from approved pages."""
    a = run_requests(db, fetcher)
    b = await run_drafts(db, generate)
    return {**a, **b, "at": _now().isoformat()}
