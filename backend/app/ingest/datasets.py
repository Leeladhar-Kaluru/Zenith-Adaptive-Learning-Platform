"""Import a small, aggregated dataset with its licence and credit, so a lesson can chart real data."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingest.assets import get_source
from app.ingest.policy import evaluate
from app.models import SourceAsset

MAX_BYTES = 200 * 1024
MAX_ROWS = 2000
RECHECK_DAYS = 180


class DatasetError(ValueError):
    pass


def import_dataset(db: Session, spec: dict, actor_id: uuid.UUID | None) -> SourceAsset:
    """spec: source_name, source_homepage, external_id, title, url, licence, attribution, fields, rows. Left pending for a reviewer."""
    decision = evaluate(spec.get("licence"))
    if not decision.allowed:
        raise DatasetError(decision.reason)
    if not str(spec.get("attribution", "")).strip():
        raise DatasetError("A dataset needs attribution text.")
    fields, rows = list(spec.get("fields", [])), list(spec.get("rows", []))
    if not fields or not rows:
        raise DatasetError("A dataset needs fields and rows.")
    if len(rows) > MAX_ROWS:
        raise DatasetError(f"Too many rows ({len(rows)}); at most {MAX_ROWS}. Aggregate it first.")
    if any(set(r) != set(fields) for r in rows):
        raise DatasetError("Every row must have exactly the declared fields.")
    blob = json.dumps({"fields": fields, "rows": rows}, ensure_ascii=False, separators=(",", ":")).encode()
    if len(blob) > MAX_BYTES:
        raise DatasetError(f"The dataset is too large ({len(blob) // 1024} kB; limit {MAX_BYTES // 1024} kB). Aggregate it first.")
    source = get_source(db, spec["source_name"], spec["source_homepage"])
    existing = db.scalar(select(SourceAsset).where(SourceAsset.source_id == source.id, SourceAsset.external_id == spec["external_id"]))
    if existing:
        return existing
    now = datetime.now(timezone.utc)
    a = SourceAsset(source_id=source.id, external_id=spec["external_id"], url=spec["url"], kind="dataset", licence_id=spec["licence"], attribution_text=spec["attribution"],
                    author=spec["source_name"], sha256=hashlib.sha256(blob).hexdigest(), bytes=len(blob), data={"fields": fields, "rows": rows},
                    status="pending", retrieved_at=now, recheck_at=now + timedelta(days=RECHECK_DAYS))
    db.add(a)
    db.commit()
    return a
