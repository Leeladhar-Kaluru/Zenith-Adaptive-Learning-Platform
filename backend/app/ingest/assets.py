"""Shared asset steps: find or create a source, and approve an asset (the only way an asset becomes usable in a lesson)."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingest.policy import evaluate
from app.models import Source, SourceAsset


class AssetError(ValueError):
    pass


def get_source(db: Session, name: str, homepage: str, licence_terms_url: str = "", api_terms_url: str = "") -> Source:
    s = db.scalar(select(Source).where(Source.name == name))
    if s is None:
        s = Source(name=name, homepage=homepage, licence_terms_url=licence_terms_url, api_terms_url=api_terms_url, robots_ok=True)
        db.add(s)
        db.flush()
    return s


def approve_asset(db: Session, asset_id: uuid.UUID, reviewer_id: uuid.UUID) -> SourceAsset:
    """A person approves an asset. The licence is checked again here, so a policy change cannot be bypassed by an old import."""
    a = db.get(SourceAsset, asset_id)
    if a is None:
        raise AssetError("Asset not found.")
    if a.status in ("rejected", "retired"):
        raise AssetError(f"This asset is {a.status}. Import it again if it should be reconsidered.")
    decision = evaluate(a.licence_id)
    if not decision.allowed:
        raise AssetError(decision.reason)
    if not a.attribution_text.strip():
        raise AssetError("An asset needs attribution text before it can be approved.")
    a.status, a.reviewer_id = "approved", reviewer_id
    db.commit()
    return a


def retire_asset(db: Session, asset_id: uuid.UUID, reviewer_id: uuid.UUID, reason: str) -> SourceAsset:
    """Take an asset out of use (for example its licence changed upstream). Students stop seeing it at once; lessons that use it fail their gate on the next import."""
    a = db.get(SourceAsset, asset_id)
    if a is None:
        raise AssetError("Asset not found.")
    a.status, a.reviewer_id = "retired", reviewer_id
    db.commit()
    return a
