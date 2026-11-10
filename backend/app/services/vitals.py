"""Real-user speed metrics: stored anonymously, summarised as the 75th percentile per route and metric."""
from __future__ import annotations

import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import WebVital

_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def clean_route(route: str) -> str:
    """Drop query and fragment, replace ids with :id, so a route can never carry a person's identifier."""
    path = route.split("?", 1)[0].split("#", 1)[0]
    path = _UUID.sub(":id", path)
    return path[:80] or "/"


def record(db: Session, name: str, value: float, route: str) -> None:
    db.add(WebVital(name=name, value=value, route=clean_route(route)))
    db.commit()


def summary(db: Session) -> list[dict]:
    rows = db.execute(select(WebVital.route, WebVital.name, func.count(), func.percentile_cont(0.75).within_group(WebVital.value))
                      .group_by(WebVital.route, WebVital.name).order_by(WebVital.route, WebVital.name)).all()
    return [{"route": r, "name": n, "n": c, "p75": round(float(p), 1)} for r, n, c, p in rows]
