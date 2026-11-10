"""Home (Today), My Progress, mistake notebook and revision. Every number comes from stored evidence."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from app.core.memo import per_request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.engine import bkt, policy, streaks
from app.models import (Card, Chapter, ChapterConcept, Concept, ConceptState, CurriculumVersion, EvidenceEvent, Item, Lesson, LessonProgress,
                        LessonVersion, LessonVersionItem, Misconception, Profile, Recommendation, RevisionSchedule)
from app.services import assign, engage, library, practice
from app.services import items as item_svc
from app.services import states as st_svc


def _now():
    return datetime.now(timezone.utc)


def _chapters_for(db: Session, profile: Profile) -> list[Chapter]:
    return list(db.scalars(select(Chapter).join(CurriculumVersion, CurriculumVersion.id == Chapter.version_id)
                           .where(Chapter.status == "published", Chapter.grade == profile.grade, CurriculumVersion.board_id == (profile.board_id or "cbse"))
                           .order_by(Chapter.subject_id, Chapter.sort_order, Chapter.number.nulls_last(), Chapter.title)))


@per_request
def due_revision(db: Session, student_id: uuid.UUID) -> list[dict]:
    rows = db.execute(select(RevisionSchedule, Concept).join(Concept, Concept.id == RevisionSchedule.concept_id)
                      .where(RevisionSchedule.student_id == student_id, RevisionSchedule.due_at <= _now()).order_by(RevisionSchedule.due_at)).all()
    return [{"conceptId": c.id, "title": c.title, "dueAt": r.due_at.isoformat(), "reps": r.reps} for r, c in rows]


def next_steps(db: Session, profile: Profile) -> list[dict]:
    """All candidate suggestions with reasons; the first is the top pick."""
    sid = profile.id
    stt = st_svc.states(db, sid)
    cands: list[dict] = []
    now = _now()

    for a in assign.for_student(db, sid):
        if a["complete"]:
            continue
        soon = a["due"] and datetime.fromisoformat(a["due"]) - now <= timedelta(days=3)
        cands.append(policy.step("assigned_due" if soon else "assigned", "assigned", a["title"],
                                 "Your teacher set this" + (f", due {datetime.fromisoformat(a['due']).strftime('%d %b')}" if a["due"] else "") + ".", a["href"], 15, assignment=a["id"]))

    weak = sorted([(c, s) for c, s in stt.items() if s["n"] >= 2 and s["status"] != "secure" and s["p"] < 0.55 and (s["last"] and now - s["last"] < timedelta(days=21))], key=lambda x: x[1]["p"])
    for c, s in weak[:3]:
        gap = st_svc.root_gap(db, sid, [c])
        if gap:
            les = library._lesson_for_concept(db, gap["concept"].id)
            if les:
                tgt = db.get(Concept, c).title
                cands.append(policy.step("prereq", "prereq", gap["concept"].title,
                                         f"You found {tgt} hard ({s['c']} of {s['n']} right). It builds on {gap['concept'].title} (Class {gap['concept'].grade}), so start there.",
                                         f"/lesson/{les['lessonId']}", 6, s["n"], conceptId=gap["concept"].id))
                break
    if weak:
        c, s = weak[0]
        cands.append(policy.step("practice", "practice", f"Practise {db.get(Concept, c).title}", f"{s['c']} of your last {s['n']} answers here were right. A few step-by-step questions will help.",
                                 f"/practice?concept={c}", 8, s["n"], conceptId=c))

    chapters = _chapters_for(db, profile)
    if chapters and not stt:
        ch = chapters[0]
        cands.append(policy.step("probe", "probe", f"Quick check: {ch.title}", "Answer a few questions so ZENITH can see where you are. It is not a graded test.",
                                 f"/tests/new?kind=diagnostic&chapter={ch.slug}", 10, 0))

    due = due_revision(db, sid)
    if due:
        cands.append(policy.step("review", "review", f"Revise {due[0]['title']}" + (f" and {len(due) - 1} more" if len(due) > 1 else ""),
                                 "Spaced revision: you knew this, and a quick refresher keeps it.", "/revision", 5 + 2 * len(due), len(due)))

    prog_rows = library.progress_rows(db, sid)
    cont = next(((lid,) for lid, st in prog_rows if st == "started"), None)
    if cont:
        v = db.scalar(select(LessonVersion).where(LessonVersion.lesson_id == cont[0], LessonVersion.status == "published", LessonVersion.language == "en"))
        if v:
            cands.append(policy.step("continue", "lesson", f"Continue: {v.title}", "You started this lesson.", f"/lesson/{cont[0]}", v.minutes))

    done = {lid for lid, st in prog_rows if st == "completed"}
    for ch in chapters:
        nxt = next(((l, v) for l, v in library._published_lessons(db, ch.id) if l.id not in done), None)
        if nxt:
            l, v = nxt
            cands.append(policy.step("next_lesson", "lesson", v.title, f"Next in {ch.title}.", f"/lesson/{l.id}", v.minutes))
            break

    ids = [c for ch in chapters for c in library.chapter_concept_ids(db, ch.id)]
    if ids and all(stt.get(c, {}).get("status") == "secure" for c in ids):
        cands.append(policy.step("challenge", "challenge", "Try harder questions", "You are secure on everything here, so harder questions will keep you growing.", "/practice?harder=1", 10, len(ids)))
    for e in practice.unlocks(db, profile)["enrichment"][:1]:
        cands.append(policy.step("challenge", "lesson", e["title"], "A new topic opened because you are secure on what it builds on.", f"/lesson/{e['lessonId']}", 10))

    order = {id(c): i for i, c in enumerate(cands)}
    ranked = sorted(cands, key=lambda c: (-policy.PRIORITY[c["rule"]], order[id(c)]))
    return ranked


def today(db: Session, profile: Profile) -> dict:
    sid = profile.id
    steps = next_steps(db, profile)
    top = steps[0] if steps else None
    if top:
        db.add(Recommendation(student_id=sid, kind=top["kind"], concept_id=top.get("conceptId"), payload={"title": top["title"], "href": top["href"]},
                              reason={"text": top["reason"], "evidence": top["evidenceCount"], "rule": top["rule"]}, model_version=policy.MODEL_VERSION))
        # committed once at the end of the request, so the per-request memo stays valid while the page is built
    xp = engage.total_xp(db, sid)
    row = engage.today_row(db, sid)
    q = engage.quests(db, sid)
    recent = library.progress_rows(db, sid)[:3]
    recent_out = []
    for lid, status in recent:
        v = db.scalar(select(LessonVersion).where(LessonVersion.lesson_id == lid, LessonVersion.status == "published"))
        if v:
            les = db.get(Lesson, lid)
            recent_out.append({"lessonId": str(lid), "title": v.title, "chapter": db.get(Chapter, les.chapter_id).title, "status": status})
    result = {"nextStep": {k: v for k, v in top.items() if k != "rule"} if top else None,
            "alternatives": [{k: v for k, v in s.items() if k != "rule"} for s in steps[1:4]],
            "streak": engage.streak_info(db, sid), "xp": streaks.level(xp), "todayXp": row.xp if row else 0,
            "goals": q, "assigned": [a for a in assign.for_student(db, sid) if not a["complete"]],
            "revision": due_revision(db, sid)[:5], "recent": recent_out,
            "badges": [b for b in engage.badge_catalog(db, sid) if b["earned"]][:3],
            "milestones": milestones(db, sid)}
    db.commit()
    return result


def milestones(db: Session, sid: uuid.UUID) -> list[dict]:
    stt = st_svc.states(db, sid)
    secure = sum(1 for s in stt.values() if s["status"] == "secure")
    lessons = sum(1 for _, st in library.progress_rows(db, sid) if st == "completed")
    answers = db.scalar(select(func.count(EvidenceEvent.id)).where(EvidenceEvent.student_id == sid)) or 0
    out = []
    for label, val, steps_ in (("Topics made secure", secure, (1, 3, 5, 10, 25)), ("Lessons finished", lessons, (1, 5, 10, 25, 50)), ("Questions answered", answers, (10, 50, 100, 250, 500))):
        nxt = next((s for s in steps_ if val < s), None)
        out.append({"label": label, "value": val, "next": nxt})
    return out


def overview(db: Session, profile: Profile) -> dict:
    """My Progress: concept understanding, chapters, activity and achievements."""
    sid = profile.id
    stt = st_svc.states(db, sid)
    concepts = []
    for c in db.scalars(select(Concept).where(Concept.id.in_(list(stt)) if stt else Concept.id == "-").order_by(Concept.grade, Concept.title)):
        s = stt[c.id]
        concepts.append({"id": c.id, "title": c.title, "grade": c.grade, "subject": c.subject_id, "band": s["status"], "pKnown": round(s["p"], 3),
                         "evidence": s["n"], "correct": s["c"], "confidence": bkt.uncertainty(s["n"]), "level": bkt.level(s["p"], s["n"]),
                         "lastAt": s["last"].isoformat() if s["last"] else None})
    prog = {lid for lid, st in library.progress_rows(db, sid) if st == "completed"}
    chapters = []
    for ch in _chapters_for(db, profile):
        lessons = library._published_lessons(db, ch.id)
        cids = library.chapter_concept_ids(db, ch.id)
        counts = {}
        for c in cids:
            b = st_svc.band(stt.get(c))
            counts[b] = counts.get(b, 0) + 1
        chapters.append({"slug": ch.slug, "title": ch.title, "subject": ch.subject_id, "lessonsDone": sum(1 for l, _ in lessons if l.id in prog),
                         "lessons": len(lessons), "concepts": counts, "conceptTotal": len(cids)})
    since = _now() - timedelta(days=28)
    from app.models import DailyActivity
    activity = [{"day": r.day.isoformat(), "answers": r.answers, "correct": r.correct, "xp": r.xp}
                for r in sorted(engage.daily_rows(db, sid), key=lambda r: r.day) if r.day >= since.date()]
    return {"concepts": concepts, "chapters": chapters, "activity": activity, "streak": engage.streak_info(db, sid), "xp": streaks.level(engage.total_xp(db, sid)),
            "badges": engage.badge_catalog(db, sid), "mistakes": mistake_count(db, sid), "revisionDue": len(due_revision(db, sid)), "milestones": milestones(db, sid)}


def mistake_count(db: Session, sid: uuid.UUID) -> int:
    return len(mistakes(db, sid, unresolved_only=True))


def mistakes(db: Session, sid: uuid.UUID, unresolved_only: bool = False) -> list[dict]:
    """Mistake notebook: every question the student has missed, with the explanation and whether they have since got it right."""
    evs = list(db.scalars(select(EvidenceEvent).where(EvidenceEvent.student_id == sid).order_by(EvidenceEvent.occurred_at)))
    per: dict[uuid.UUID, dict] = {}
    for e in evs:
        d = per.setdefault(e.item_id, {"missed": 0, "last_missed": None, "resolved": False, "mis": None})
        if e.correct:
            if d["missed"]:
                d["resolved"] = True
        else:
            d["missed"] += 1
            d["last_missed"], d["resolved"], d["mis"] = e.occurred_at, False, e.misconception_id or d["mis"]
    out = []
    for iid, d in per.items():
        if not d["missed"] or (unresolved_only and d["resolved"]):
            continue
        item = db.get(Item, iid)
        mis = db.get(Misconception, d["mis"]) if d["mis"] else None
        cids = [c for c, _ in item_svc.item_concepts(db, iid)]
        out.append({"itemId": str(iid), "stem": item.stem, "explanation": item.explanation, "missedTimes": d["missed"], "resolved": d["resolved"],
                    "lastMissedAt": d["last_missed"].isoformat(), "misconception": mis.description if mis else None, "kind": item.kind, "concepts": cids})
    return sorted(out, key=lambda x: x["lastMissedAt"], reverse=True)


def revision_view(db: Session, profile: Profile) -> dict:
    due = due_revision(db, profile.id)
    cids = [d["conceptId"] for d in due]
    cards = []
    if cids:
        for c in db.scalars(select(Card).join(LessonVersion, LessonVersion.id == Card.lesson_version_id).where(LessonVersion.status == "published", Card.concept_id.in_(cids))):
            cards.append({"id": str(c.id), "conceptId": c.concept_id, "front": c.front, "back": c.back})
    return {"due": due, "cards": cards}


def review_card(db: Session, profile: Profile, card_id: uuid.UUID, remembered: bool) -> dict:
    card = db.get(Card, card_id)
    if card is None:
        raise LookupError("Card not found.")
    row = db.get(RevisionSchedule, (profile.id, card.concept_id))
    now = _now()
    if row is None:
        row = RevisionSchedule(student_id=profile.id, concept_id=card.concept_id, due_at=now, interval_days=1, reps=0)
        db.add(row)
    if remembered:
        row.reps += 1
        row.interval_days = [1, 3, 7, 21, 45][min(row.reps, 4)]
    else:
        row.reps, row.interval_days = 0, 1
    row.due_at, row.last_reviewed_at = now + timedelta(days=row.interval_days), now
    db.commit()
    return {"nextDueInDays": row.interval_days}
