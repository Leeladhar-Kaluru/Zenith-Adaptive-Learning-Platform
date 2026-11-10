"""Imported assets are re-checked on a schedule, so something re-licensed or removed upstream cannot stay live unnoticed."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SourceAsset


def due_for_recheck(db: Session, now: datetime | None = None) -> list[SourceAsset]:
    """Approved assets whose re-check date has passed, oldest first."""
    now = now or datetime.now(timezone.utc)
    return list(db.scalars(select(SourceAsset).where(SourceAsset.status == "approved", SourceAsset.recheck_at <= now).order_by(SourceAsset.recheck_at)))
