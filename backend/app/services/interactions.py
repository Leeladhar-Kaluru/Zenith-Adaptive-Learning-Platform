"""Store the moves a student makes while learning. Bounded per request and per day; idempotent per client event id."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from sqlalchemy.orm import Session

from app.models import InteractionEvent
from app.models.learning import INTERACTION_KINDS

MAX_PER_REQUEST = 200
MAX_PER_DAY = 2000
MAX_VALUE_BYTES = 600
MAX_MS = 3_600_000


def store(db: Session, student_id: uuid.UUID, events: list[dict]) -> dict:
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    used = db.scalar(select(func.count(InteractionEvent.id)).where(InteractionEvent.student_id == student_id, InteractionEvent.received_at >= day_start)) or 0
    room = max(0, MAX_PER_DAY - used)
    rows = []
    for e in events[:room]:
        if e["kind"] not in INTERACTION_KINDS:
            continue
        value = e.get("value") or {}
        if not isinstance(value, dict) or len(str(value)) > MAX_VALUE_BYTES:
            value = {}
        at = e.get("occurredAt") or now
        if at > now:
            at = now
        rows.append({"student_id": student_id, "client_event_id": e["clientEventId"][:64], "kind": e["kind"], "target_type": e["targetType"][:16],
                     "target_id": e["targetId"][:120], "value": value, "ms": max(0, min(int(e.get("ms") or 0), MAX_MS)), "occurred_at": at})
    stored = 0
    if rows:
        res = db.execute(insert(InteractionEvent).values(rows).on_conflict_do_nothing(constraint="uq_interaction_client_event")
                         .returning(InteractionEvent.id))
        stored = len(res.fetchall())
        db.commit()
    return {"received": len(events), "stored": stored, "ignored": len(events) - stored, "dailyLimitReached": room == 0 or len(events) > room}
