"""AI reviewer: reads a lesson like a teacher and raises flags. It never approves, scores or edits anything."""
from __future__ import annotations

import json
import re

from sqlalchemy.orm import Session

from app.core.ai_provider import ai_provider
from app.models import LessonVersion
from app.services import tutor


async def run(db: Session, lv: LessonVersion) -> list[dict]:
    if not tutor.ai_enabled():
        return [{"id": "ai-off", "severity": "info", "text": "The AI reviewer is not available right now. Human review is still required."}]
    text = tutor.lesson_text(lv)[:6000]
    prompt = (
        "You are a careful maths and science teacher reviewing a lesson for school students. List concrete problems only: factual errors, "
        "confusing wording for the stated class, missing common mistakes, or examples a student may not know. Do not praise. "
        'Reply with JSON only: {"flags":[{"severity":"warn|info","text":"..."}]}. Use at most 5 flags; return an empty list if you find nothing.\n\nLESSON:\n' + text)
    try:
        raw = await ai_provider.generate_chat(messages=[{"role": "user", "content": prompt}], temperature=0.1, max_tokens=700)
        data = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
        flags = [{"id": f"ai-{i}", "severity": "warn" if f.get("severity") == "warn" else "info", "text": str(f.get("text", ""))[:300]} for i, f in enumerate(data.get("flags", [])[:5]) if f.get("text")]
        return flags or [{"id": "ai-none", "severity": "info", "text": "The AI reviewer found nothing to flag. This is not approval."}]
    except Exception:  # noqa: BLE001
        return [{"id": "ai-error", "severity": "info", "text": "The AI reviewer could not read this lesson. Human review is still required."}]
