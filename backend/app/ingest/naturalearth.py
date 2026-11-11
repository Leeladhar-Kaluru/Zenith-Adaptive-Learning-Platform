"""Natural Earth map layers (public domain): turned into small SVG path sets, so the Atlas needs no map tile server at all."""
from __future__ import annotations

import hashlib
import json
import math
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


def _outer_rings(geom: dict) -> list:
    polys = geom.get("coordinates", []) if geom.get("type") == "MultiPolygon" else [geom.get("coordinates", [])] if geom.get("type") == "Polygon" else []
    return [poly[0] for poly in polys if poly]                 # outer rings only: holes are not worth their bytes here


def _transform(rings_all: list, fit: bool | None):
    """World maps use one fixed equirectangular frame. A map of one region (a country's states) is fitted to its own frame,
    with longitude shrunk by cos(latitude) so shapes look right, and a longer side of 1000 units."""
    lons = [float(p[0]) for r in rings_all for p in r]
    lats = [float(p[1]) for r in rings_all for p in r]
    if not lons:
        return (lambda lon, lat: _xy(lon, lat)), [W, H], 0.0
    span_lon, span_lat = max(lons) - min(lons), max(lats) - min(lats)
    if fit is None:
        fit = span_lon < 120 and span_lat < 120
    if not fit:
        return (lambda lon, lat: _xy(lon, lat)), [W, H], 0.0
    k = math.cos(math.radians((max(lats) + min(lats)) / 2))
    width, height = max(span_lon * k, 1e-6), max(span_lat, 1e-6)
    scale = 1000.0 / max(width, height)
    lon0, lat1 = min(lons), max(lats)
    return (lambda lon, lat: ((lon - lon0) * k * scale, (lat1 - lat) * scale)), [max(1, round(width * scale)), max(1, round(height * scale))], 1.0


def _ring(ring, xy, tol: float) -> str:
    out, last = [], None
    for p in ring:
        x, y = xy(float(p[0]), float(p[1]))
        if last is not None and tol and (x - last[0]) ** 2 + (y - last[1]) ** 2 < tol * tol:
            continue                                      # points closer than a pixel or so add bytes, not shape
        key = (round(x, 1), round(y, 1))
        if key != last:
            out.append(key)
            last = (x, y)
    if len(out) < 3:
        return ""
    return "M" + "L".join(f"{x:g},{y:g}" for x, y in out) + "Z"


def project(geojson: dict, fit: bool | None = None) -> dict:
    """GeoJSON polygons -> {viewBox, features:[{id, name, d}]} (+ optional outline and note).
    A feature marked OUTLINE is not a place: it is a complete boundary drawn underneath, with a plain-language NOTE shown to students."""
    feats, outline_rings, note = [], [], ""
    for f in geojson.get("features", []):
        geom, props = f.get("geometry") or {}, f.get("properties") or {}
        rings = _outer_rings(geom)
        if props.get("OUTLINE"):
            outline_rings = rings
            note = str(props.get("NOTE") or "").strip()[:400]
            continue
        name = str(props.get("NAME") or props.get("ADMIN") or "").strip()
        if rings and name:
            feats.append((name, props, rings))
    if not feats:
        raise GeoError("The map has no countries I can draw.")
    xy, view_box, tol = _transform([r for _, _, rings in feats for r in rings] + outline_rings, fit)
    features, seen = [], set()
    for name, props, rings in feats:
        d = "".join(_ring(r, xy, tol * 0.8) for r in rings)
        if not d:
            continue
        code = str(props.get("CODE") or props.get("ISO_A3") or props.get("ADM0_A3") or name[:3]).strip().upper()
        base, n = code, 2
        while code in seen:                                # many states can share one country code: ids must still be unique
            code, n = f"{base}-{n}", n + 1
        seen.add(code)
        features.append({"id": code, "name": name, "d": d})
    if not features:
        raise GeoError("The map has no countries I can draw.")
    out = {"viewBox": view_box, "features": features}
    outline = "".join(_ring(r, xy, tol * 0.8) for r in outline_rings)
    if outline:
        out["outline"] = outline
        if note:
            out["note"] = note
    return out


def import_geojson(db: Session, geojson: dict, external_id: str, actor_id: uuid.UUID | None, url: str = "https://www.naturalearthdata.com/", fit: bool | None = None) -> SourceAsset:
    decision = evaluate("PDM-1.0")
    if not decision.allowed:                                              # the policy, not this file, decides what is importable
        raise GeoError(decision.reason)
    data = project(geojson, fit)
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
