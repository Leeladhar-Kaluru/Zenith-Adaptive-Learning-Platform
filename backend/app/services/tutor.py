"""Ask: a text tutor grounded in the student's current lesson. It teaches; it never grades or changes mastery."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.ai_provider import LLMUnavailableError, ai_provider
from app.core.config import settings
from app.models import Chapter, Concept, EvidenceEvent, Lesson, LessonConcept, LessonVersion, Misconception, Profile, TutorMessage, TutorThread

LANG_NAME = {"en": "English", "hi": "Hindi", "te": "Telugu"}


class TutorLimit(Exception):
    pass


def ai_enabled() -> bool:
    if settings.LLM_PROVIDER.lower() == "lmstudio":
        return True
    return bool(settings.ENABLE_REMOTE_AI and settings.GROQ_API_KEY)


def _strip(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


def lesson_text(lv: LessonVersion) -> str:
    parts = [lv.title] + list(lv.objectives)
    for b in lv.blocks:
        k = b["kind"]
        if k in ("text", "callout"):
            parts.append(_strip(b.get("html", "")))
        elif k == "example":
            parts += [b["prompt"]] + list(b["steps"])
        elif k == "summary":
            parts += b["points"]
    return "\n".join(p for p in parts if p)


def _find_lessons(db: Session, profile: Profile, message: str, lesson_id: uuid.UUID | None) -> list[LessonVersion]:
    if lesson_id:
        lv = db.scalar(select(LessonVersion).where(LessonVersion.lesson_id == lesson_id, LessonVersion.status == "published"))
        return [lv] if lv else []
    words = [w for w in re.findall(r"[A-Za-z]{4,}", message.lower())][:6]
    if not words:
        return []
    from sqlalchemy import or_
    q = (select(LessonVersion).join(Lesson, Lesson.id == LessonVersion.lesson_id).join(Chapter, Chapter.id == Lesson.chapter_id)
         .where(LessonVersion.status == "published", Chapter.grade <= (profile.grade or 10), or_(*[LessonVersion.title.ilike(f"%{w}%") for w in words])).limit(2))
    return list(db.scalars(q))


def _relevant_paragraphs(text: str, message: str, n: int = 3) -> list[str]:
    words = {w for w in re.findall(r"[a-z]{4,}", message.lower())}
    paras = [p for p in text.split("\n") if len(p) > 25]
    scored = sorted(paras, key=lambda p: -len(words & set(re.findall(r"[a-z]{4,}", p.lower()))))
    return [p for p in scored[:n] if words & set(re.findall(r"[a-z]{4,}", p.lower()))] or paras[:1]


def _system(profile: Profile, ctx: str, mistakes: list[str], lang: str) -> str:
    lines = [
        f"You are ZENITH, a patient tutor for a Class {profile.grade or 8} student in India.",
        "Teach with short, simple sentences suitable for that class. Use Socratic questions: guide the student to the answer instead of giving it.",
        "Never give the final answer to a practice or test question; give a hint and ask a question back.",
        "Base explanations on the lesson excerpt below. If it does not cover the question, say so and explain carefully from general knowledge.",
        "Do not guess. If you are unsure, say you are unsure and suggest asking the teacher. Keep replies under 120 words.",
        "Write numbers and maths in plain text, with no LaTeX.",
    ]
    if lang != "en":
        lines.append(f"Reply in {LANG_NAME[lang]}. Keep mathematical and scientific terms accurate; you may add the English term in brackets.")
    if mistakes:
        lines.append("Mistakes this student has made on this topic (use them gently): " + "; ".join(mistakes[:3]))
    lines.append("LESSON EXCERPT:\n" + ctx[:3000])
    return "\n".join(lines)


async def ask(db: Session, profile: Profile, message: str, lesson_id: uuid.UUID | None, lang: str, client_id: str | None = None) -> dict:
    if client_id:                                    # the same question sent again (offline retry) returns the stored answer instead of asking twice
        done = db.scalar(select(TutorMessage.meta).join(TutorThread, TutorThread.id == TutorMessage.thread_id)
                         .where(TutorThread.student_id == profile.id, TutorMessage.role == "tutor", TutorMessage.meta["clientId"].astext == client_id))
        if done and done.get("result"):
            return done["result"]
    message = message.strip()
    if not message:
        raise ValueError("Type your question first.")
    if lang not in LANG_NAME:
        lang = "en"
    since = datetime.now(timezone.utc) - timedelta(days=1)
    used = db.scalar(select(func.count(TutorMessage.id)).join(TutorThread, TutorThread.id == TutorMessage.thread_id)
                     .where(TutorThread.student_id == profile.id, TutorMessage.role == "student", TutorMessage.created_at >= since)) or 0
    if used >= settings.TUTOR_DAILY_LIMIT:
        raise TutorLimit()

    thread = db.scalar(select(TutorThread).where(TutorThread.student_id == profile.id, TutorThread.lesson_id == lesson_id, TutorThread.created_at >= since).order_by(TutorThread.created_at.desc()).limit(1))
    if thread is None:
        thread = TutorThread(student_id=profile.id, lesson_id=lesson_id)
        db.add(thread)
        db.flush()
    history = list(db.scalars(select(TutorMessage).where(TutorMessage.thread_id == thread.id).order_by(TutorMessage.created_at.desc()).limit(6)))[::-1]
    db.add(TutorMessage(thread_id=thread.id, role="student", content=message[:1000], language=lang))

    lvs = _find_lessons(db, profile, message, lesson_id)
    ctx = "\n\n".join(lesson_text(lv) for lv in lvs)
    cids = [c for (c,) in db.execute(select(LessonConcept.concept_id).where(LessonConcept.lesson_id.in_([lv.lesson_id for lv in lvs] or [uuid.uuid4()])))]
    mistakes = [m for (m,) in db.execute(select(Misconception.description).join(EvidenceEvent, EvidenceEvent.misconception_id == Misconception.id)
                                         .where(EvidenceEvent.student_id == profile.id, Misconception.concept_id.in_(cids or ["-"])).order_by(EvidenceEvent.occurred_at.desc()).limit(3))]
    citations = [{"title": lv.title, "heading": "Lesson"} for lv in lvs]

    degraded, reply = False, ""
    if ai_enabled():
        msgs = [{"role": "system", "content": _system(profile, ctx, mistakes, lang)}]
        msgs += [{"role": "user" if m.role == "student" else "assistant", "content": m.content} for m in history]
        msgs.append({"role": "user", "content": message})
        try:
            reply = (await ai_provider.generate_chat(messages=msgs, temperature=0.3, max_tokens=700)).strip()
        except (LLMUnavailableError, Exception):  # noqa: BLE001 - any provider failure falls back honestly
            reply = ""
    if not reply:
        degraded = True
        paras = _relevant_paragraphs(ctx, message) if ctx else []
        reply = ("The AI helper is not available right now, so here is what your lesson says:\n" + "\n".join(paras)) if paras else \
            "The AI helper is not available right now, and I could not find this in your lessons. Try the search, or ask your teacher."
    result = {"reply": reply, "citations": citations if lvs else [], "language": lang, "aiTranslated": lang != "en" and not degraded, "degraded": degraded}
    db.add(TutorMessage(thread_id=thread.id, role="tutor", content=reply, language=lang, meta={"degraded": degraded, **({"clientId": client_id, "result": result} if client_id else {})}))
    db.commit()
    return result
