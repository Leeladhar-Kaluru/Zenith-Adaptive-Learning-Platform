"""Read access to previously generated coach notes.

The background generation pipeline that produced these notes was removed with
the document stack; new personalised feedback will come from the rebuilt
learner model. Existing ready notes remain readable.
"""
import uuid
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.learning import CoachNote


def latest_ready_note(db: Session, *, owner_id: uuid.UUID, concept_id: str) -> Optional[Dict[str, Any]]:
    note = (
        db.query(CoachNote)
        .filter(
            CoachNote.owner_id == owner_id,
            CoachNote.concept_id == concept_id,
            CoachNote.status == "ready",
        )
        .order_by(CoachNote.completed_at.desc())
        .first()
    )
    if note is None:
        return None
    return {
        "id": str(note.id),
        "conceptId": note.concept_id,
        "content": note.content_json,
        "completedAt": note.completed_at.isoformat() if note.completed_at else None,
    }
