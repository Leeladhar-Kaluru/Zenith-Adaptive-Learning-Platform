"""XP, streaks, daily quests, badges and classroom leagues, all derived from stored learning activity."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.engine import streaks
from app.models import (Chapter, ClassMember, Classroom, ConceptState, DailyActivity, EvidenceEvent, Lesson, LessonProgress, LessonVersion,
                        LeagueMembership, Profile, StudentBadge, XpEvent)

TIERS = ["foothill", "ridge", "summit", "zenith"]
BADGES = {
    "first_step": ("First step", "Answer your first question", "flag"),
    "sharp_shooter": ("Sharp shooter", "Get 5 answers right in a row", "target"),
    "comeback": ("Comeback", "Get one right after three misses on the same topic", "arrowUp"),
    "first_secure": ("Rock solid", "Make your first topic secure", "shield"),
    "chapter_climber": ("Chapter climber", "Finish every lesson in a chapter", "peak"),
    "streak_7": ("Seven-day summit", "Keep a 7-day streak", "flame"),
}


def _today() -> date:
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=30))).date()   # India Standard Time


def total_xp(db: Session, student_id: uuid.UUID) -> int:
    return int(db.scalar(select(func.coalesce(func.sum(XpEvent.amount), 0)).where(XpEvent.student_id == student_id)) or 0)


def streak_info(db: Session, student_id: uuid.UUID) -> dict:
    days = {d for (d,) in db.execute(select(DailyActivity.day).where(DailyActivity.student_id == student_id, (DailyActivity.answers > 0) | (DailyActivity.lessons > 0)))}
    return streaks.streak(days, _today())


def today_row(db: Session, student_id: uuid.UUID) -> DailyActivity | None:
    return db.get(DailyActivity, (student_id, _today()))


def quests(db: Session, student_id: uuid.UUID) -> list[dict]:
    row = today_row(db, student_id)
    answers, lessons = (row.answers, row.lessons) if row else (0, 0)
    start = datetime.combine(_today(), datetime.min.time(), tzinfo=timezone(timedelta(hours=5, minutes=30)))
    flags = [c for (c,) in db.execute(select(EvidenceEvent.correct).where(EvidenceEvent.student_id == student_id, EvidenceEvent.occurred_at >= start).order_by(EvidenceEvent.occurred_at))]
    run = streaks.max_correct_run(flags)
    return [{"id": "answers", "title": "Answer 5 questions", "icon": "target", "done": min(5, answers), "total": 5},
            {"id": "run", "title": "Get 3 right in a row", "icon": "link", "done": min(3, run), "total": 3},
            {"id": "lesson", "title": "Finish a lesson", "icon": "book", "done": min(1, lessons), "total": 1}]


def check_badges(db: Session, student_id: uuid.UUID) -> list[str]:
    have = {c for (c,) in db.execute(select(StudentBadge.code).where(StudentBadge.student_id == student_id))}
    new: list[str] = []

    def grant(code: str):
        if code not in have:
            db.add(StudentBadge(student_id=student_id, code=code))
            new.append(code)

    n = db.scalar(select(func.count(EvidenceEvent.id)).where(EvidenceEvent.student_id == student_id)) or 0
    if n >= 1:
        grant("first_step")
    recent = [(c, cs) for c, cs in db.execute(select(EvidenceEvent.correct, EvidenceEvent.concepts).where(EvidenceEvent.student_id == student_id).order_by(EvidenceEvent.occurred_at.desc()).limit(60))][::-1]
    if streaks.max_correct_run([c for c, _ in recent]) >= 5:
        grant("sharp_shooter")
    miss: dict[str, int] = {}
    for c, cs in recent:
        for ref in cs:
            if c and miss.get(ref["id"], 0) >= 3:
                grant("comeback")
            miss[ref["id"]] = 0 if c else miss.get(ref["id"], 0) + 1
    if db.scalar(select(func.count(ConceptState.concept_id)).where(ConceptState.student_id == student_id, ConceptState.status == "secure")):
        grant("first_secure")
    if streak_info(db, student_id)["days"] >= 7:
        grant("streak_7")
    done = {l for (l,) in db.execute(select(LessonProgress.lesson_id).where(LessonProgress.student_id == student_id, LessonProgress.status == "completed"))}
    for ch in db.scalars(select(Chapter).where(Chapter.status == "published")):
        ids = {l for (l,) in db.execute(select(Lesson.id).where(Lesson.chapter_id == ch.id))}
        if ids and ids <= done:
            grant("chapter_climber")
    db.flush()
    return new


def badge_catalog(db: Session, student_id: uuid.UUID) -> list[dict]:
    got = {c: t for c, t in db.execute(select(StudentBadge.code, StudentBadge.earned_at).where(StudentBadge.student_id == student_id))}
    return [{"id": code, "title": t, "hint": h, "icon": ic, "earned": code in got, "earnedAt": got[code].isoformat() if code in got else None}
            for code, (t, h, ic) in BADGES.items()]


# ---- classroom league ---------------------------------------------------------------------------
def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _week_xp(db: Session, student_ids: list[uuid.UUID], start: date) -> dict[uuid.UUID, int]:
    s = datetime.combine(start, datetime.min.time(), tzinfo=timezone(timedelta(hours=5, minutes=30)))
    e = s + timedelta(days=7)
    rows = db.execute(select(XpEvent.student_id, func.sum(XpEvent.amount)).where(XpEvent.student_id.in_(student_ids), XpEvent.created_at >= s, XpEvent.created_at < e).group_by(XpEvent.student_id))
    out = {i: 0 for i in student_ids}
    out.update({sid: int(x) for sid, x in rows})
    return out


def _members(db: Session, classroom: Classroom) -> list[Profile]:
    return list(db.scalars(select(Profile).join(ClassMember, ClassMember.student_id == Profile.id)
                           .where(ClassMember.classroom_id == classroom.id, ClassMember.status == "active", Profile.league_opt_out.is_(False)).order_by(Profile.id)))


def settle(db: Session, classroom: Classroom) -> None:
    """Apply last week's promotions and demotions once per new week. Needs at least 5 players to mean anything."""
    this = _week_start(_today())
    prev = this - timedelta(days=7)
    members = _members(db, classroom)
    rows = {m.id: db.get(LeagueMembership, (m.id, classroom.id)) or LeagueMembership(student_id=m.id, classroom_id=classroom.id, tier="foothill") for m in members}
    for r in rows.values():
        db.add(r) if r not in db else None
    pending = [m for m in members if rows[m.id].last_week is None or rows[m.id].last_week < this]
    if pending and len(members) >= 5:
        xp = _week_xp(db, [m.id for m in members], prev)
        by_tier: dict[str, list[Profile]] = {}
        for m in members:
            by_tier.setdefault(rows[m.id].tier, []).append(m)
        for tier, group in by_tier.items():
            ranked = sorted(group, key=lambda m: (-xp[m.id], str(m.id)))
            k = max(1, len(ranked) // 4)
            for m in ranked[:k]:
                if xp[m.id] > 0 and TIERS.index(tier) < len(TIERS) - 1:
                    rows[m.id].tier = TIERS[TIERS.index(tier) + 1]
            for m in ranked[-k:]:
                if xp[m.id] == 0 and TIERS.index(tier) > 0 and m not in ranked[:k]:
                    rows[m.id].tier = TIERS[TIERS.index(tier) - 1]
    for r in rows.values():
        r.last_week = this
    db.flush()


def league_view(db: Session, profile: Profile) -> dict:
    """The student's league inside the classroom they belong to. Explains why when there is none."""
    if profile.league_opt_out:
        return {"league": None, "reason": "opted_out"}
    cls = db.scalar(select(Classroom).join(ClassMember, ClassMember.classroom_id == Classroom.id).where(ClassMember.student_id == profile.id, ClassMember.status == "active").order_by(ClassMember.joined_at).limit(1))
    if cls is None:
        return {"league": None, "reason": "no_classroom"}
    if not cls.leagues_enabled:
        return {"league": None, "reason": "teacher_off"}
    settle(db, cls)
    members = _members(db, cls)
    if len(members) < 2:
        return {"league": None, "reason": "too_few"}
    this = _week_start(_today())
    xp = _week_xp(db, [m.id for m in members], this)
    tiers = {m.id: (db.get(LeagueMembership, (m.id, cls.id)).tier) for m in members}
    mine = tiers.get(profile.id, "foothill")
    group = sorted([m for m in members if tiers[m.id] == mine][:20], key=lambda m: (-xp[m.id], str(m.id)))
    k = max(1, len(group) // 4)
    rows = []
    for i, m in enumerate(group):
        zone = "up" if (i < k and len(members) >= 5) else "down" if (i >= len(group) - k and len(group) >= 5 and i >= k) else "stay"
        rows.append({"rank": i + 1, "nickname": m.nickname or "Learner", "avatar": m.avatar, "xp": xp[m.id], "me": m.id == profile.id, "zone": zone})
    end = datetime.combine(this + timedelta(days=7), datetime.min.time(), tzinfo=timezone(timedelta(hours=5, minutes=30)))
    return {"league": {"tier": mine, "endsAt": end.isoformat(), "rows": rows, "classroom": cls.name}, "reason": None}
