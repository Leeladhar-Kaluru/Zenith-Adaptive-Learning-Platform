"""Real-user speed metrics: stored anonymously, summarised as the 75th percentile per route and metric."""
from __future__ import annotations

import random
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import WebVital

_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


DAILY_CAP = 20_000        # rows per day; beyond this an anonymous caller is ignored, so the table cannot fill the database
PRUNE_EVERY = 500         # on average one insert in this many also deletes rows older than RETAIN_DAYS
RETAIN_DAYS = 30
_SEGMENT = re.compile(r"^[A-Za-z0-9_:-]{1,30}$")


def clean_route(route: str) -> str:
    """Drop query and fragment, replace ids with :id, keep at most three tidy segments, so a route can never carry a person's identifier or free text."""
    path = _UUID.sub(":id", route.split("?", 1)[0].split("#", 1)[0])
    segments = [s if _SEGMENT.match(s) else ":x" for s in path.strip("/").split("/") if s][:3]
    return "/" + "/".join(segments)


def record(db: Session, name: str, value: float, route: str) -> None:
    now = datetime.now(timezone.utc)
    if (db.scalar(select(func.count(WebVital.id)).where(WebVital.at >= now.replace(hour=0, minute=0, second=0, microsecond=0))) or 0) >= DAILY_CAP:
        return
    db.add(WebVital(name=name, value=value, route=clean_route(route)))
    if random.randrange(PRUNE_EVERY) == 0:
        db.query(WebVital).filter(WebVital.at < now - timedelta(days=RETAIN_DAYS)).delete()
    db.commit()


def summary(db: Session) -> list[dict]:
    rows = db.execute(select(WebVital.route, WebVital.name, func.count(), func.percentile_cont(0.75).within_group(WebVital.value))
                      .group_by(WebVital.route, WebVital.name).order_by(WebVital.route, WebVital.name)).all()
    return [{"route": r, "name": n, "n": c, "p75": round(float(p), 1)} for r, n, c, p in rows]
