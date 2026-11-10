"""Natural Earth map layers (public domain): turned into small SVG path sets, so the Atlas needs no map tile server at all."""
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

W, H = 1000, 500                  # equirectangular: longitude -180..180 -> 0..1000, latitude 90..-90 -> 0..500
MAX_BYTES = 300 * 1024
ATTRIBUTION = "Made with Natural Earth. Free vector and raster map data at naturalearthdata.com."
RECHECK_DAYS = 365


class GeoError(ValueError):
    pass


def _xy(lon: float, lat: float) -> tuple[float, float]:
    return (lon + 180.0) / 360.0 * W, (90.0 - lat) / 180.0 * H


def _ring(ring) -> str:
    pts = [_xy(float(p[0]), float(p[1])) for p in ring]
    out, last = [], None
    for x, y in pts:                      # one decimal is plenty at this scale; drop repeated points to keep the layer small
        key = (round(x, 1), round(y, 1))
        if key != last:
            out.append(key)
            last = key
    if len(out) < 3:
        return ""
    return "M" + "L".join(f"{x:g},{y:g}" for x, y in out) + "Z"


def project(geojson: dict) -> dict:
    """GeoJSON countries -> {viewBox, features:[{id, name, d}]}. Only the name and a three-letter code are kept; points and lines are skipped."""
    features = []
    for f in geojson.get("features", []):
        geom, props = f.get("geometry") or {}, f.get("properties") or {}
        polys = geom.get("coordinates", []) if geom.get("type") == "MultiPolygon" else [geom.get("coordinates", [])] if geom.get("type") == "Polygon" else []
        d = "".join(_ring(r) for poly in polys for r in poly[:1])        # outer rings only: holes are not worth their bytes here
        name = str(props.get("NAME") or props.get("ADMIN") or "").strip()
        if not d or not name:
            continue
        code = str(props.get("ISO_A3") or props.get("ADM0_A3") or name[:3]).strip().upper()
        features.append({"id": code, "name": name, "d": d})
    if not features:
        raise GeoError("The map has no countries I can draw.")
    return {"viewBox": [W, H], "features": features}


def import_geojson(db: Session, geojson: dict, external_id: str, actor_id: uuid.UUID | None, url: str = "https://www.naturalearthdata.com/") -> SourceAsset:
    decision = evaluate("PDM-1.0")
    if not decision.allowed:                                              # the policy, not this file, decides what is importable
        raise GeoError(decision.reason)
    data = project(geojson)
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
    if len(blob) > MAX_BYTES:
        raise GeoError(f"The map layer is too large ({len(blob) // 1024} kB; limit {MAX_BYTES // 1024} kB). Use a coarser scale.")
    source = get_source(db, "Natural Earth", "https://www.naturalearthdata.com/", "https://www.naturalearthdata.com/about/terms-of-use/")
    existing = db.scalar(select(SourceAsset).where(SourceAsset.source_id == source.id, SourceAsset.external_id == external_id))
    if existing:
        return existing
    now = datetime.now(timezone.utc)
    a = SourceAsset(source_id=source.id, external_id=external_id, url=url, kind="geo", licence_id="PDM-1.0", attribution_text=ATTRIBUTION, author="Natural Earth",
                    sha256=hashlib.sha256(blob).hexdigest(), bytes=len(blob), data=data, status="pending", retrieved_at=now, recheck_at=now + timedelta(days=RECHECK_DAYS))
    db.add(a)
    db.commit()
    return a
