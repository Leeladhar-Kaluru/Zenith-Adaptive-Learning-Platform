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


def _lines(geom: dict) -> list:
    t, c = geom.get("type"), geom.get("coordinates", [])
    return [c] if t == "LineString" and c else list(c) if t == "MultiLineString" else []


def _point(geom: dict):
    return geom.get("coordinates") if geom.get("type") == "Point" and len(geom.get("coordinates", [])) >= 2 else None


def _frame(points: list, fit: bool | None) -> dict | None:
    """World maps use one fixed equirectangular frame (None). A map of one region is fitted to its own frame, with longitude shrunk by
    cos(latitude) so shapes look right and the longer side 1000 units. The frame is stored with the layer so overlays (rivers, peaks)
    can be drawn in exactly the same place."""
    if not points:
        return None
    lons, lats = [float(p[0]) for p in points], [float(p[1]) for p in points]
    span_lon, span_lat = max(lons) - min(lons), max(lats) - min(lats)
    if fit is None:
        fit = span_lon < 120 and span_lat < 120
    if not fit:
        return None
    k = math.cos(math.radians((max(lats) + min(lats)) / 2))
    width, height = max(span_lon * k, 1e-6), max(span_lat, 1e-6)
    scale = 1000.0 / max(width, height)
    return {"lon0": min(lons), "lat1": max(lats), "k": k, "scale": scale, "w": max(1, round(width * scale)), "h": max(1, round(height * scale))}


def _xy_for(frame: dict | None):
    if frame is None:
        return _xy
    return lambda lon, lat: ((lon - frame["lon0"]) * frame["k"] * frame["scale"], (frame["lat1"] - lat) * frame["scale"])


def _ring(ring, xy, tol: float, close: bool = True) -> str:
    out, last = [], None
    for p in ring:
        x, y = xy(float(p[0]), float(p[1]))
        if last is not None and tol and (x - last[0]) ** 2 + (y - last[1]) ** 2 < tol * tol:
            continue                                      # points closer than a pixel or so add bytes, not shape
        key = (round(x, 1), round(y, 1))
        if key != last:
            out.append(key)
            last = (x, y)
    if len(out) < (3 if close else 2):
        return ""
    return "M" + "L".join(f"{x:g},{y:g}" for x, y in out) + ("Z" if close else "")


def _unique(code: str, seen: set) -> str:
    base, n = code, 2
    while code in seen:                                    # many places can share one code: ids must still be unique
        code, n = f"{base}-{n}", n + 1
    seen.add(code)
    return code


def _slug(name: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in name.upper()).strip("-")[:24] or "X"


def project(geojson: dict, fit: bool | None = None, frame: dict | None = None, label: str | None = None) -> dict:
    """GeoJSON -> {viewBox, features, ...} drawn with SVG paths. Polygons become places; lines (rivers) and points (peaks) become
    `kind: line` / `kind: point` features. A feature marked OUTLINE is not a place but a boundary drawn underneath, with a plain NOTE.
    Pass `frame` (from a base layer) to draw an overlay in exactly the same place as that layer."""
    areas, lines, pts, outline_rings, note = [], {}, [], [], ""
    for f in geojson.get("features", []):
        geom, props = f.get("geometry") or {}, f.get("properties") or {}
        name = str(props.get("NAME") or props.get("ADMIN") or "").strip()
        if props.get("OUTLINE"):
            outline_rings, note = _outer_rings(geom), str(props.get("NOTE") or "").strip()[:400]
            continue
        rings = _outer_rings(geom)
        if rings and name:
            areas.append((name, props, rings))
            continue
        segs = _lines(geom)
        if segs and name:
            lines.setdefault(name, (props, []))[1].extend(segs)
            continue
        pt = _point(geom)
        if pt and name:
            pts.append((name, props, pt))
    if areas:                                   # a layer is one kind of thing: places, or rivers, or peaks. A stray point in a country map is ignored.
        lines, pts = {}, []
    elif lines:
        pts = []
    if not (areas or lines or pts):
        raise GeoError("The map has no countries I can draw.")
    everything = [p for _, _, rings in areas for r in rings for p in r] + [p for r in outline_rings for p in r]
    everything += [p for _, (_, segs) in lines.items() for seg in segs for p in seg] + [pt for _, _, pt in pts]
    use_frame = frame if frame is not None else _frame(everything, fit)
    xy = _xy_for(use_frame)
    tol = 1.0 if use_frame else 0.0
    view_box = [use_frame["w"], use_frame["h"]] if use_frame else [W, H]
    features, seen = [], set()
    for name, props, rings in areas:
        d = "".join(_ring(r, xy, tol * 0.8) for r in rings)
        if d:
            features.append({"id": _unique(str(props.get("CODE") or props.get("ISO_A3") or props.get("ADM0_A3") or name[:3]).strip().upper(), seen), "name": name, "d": d})
    for name, (props, segs) in lines.items():
        d = "".join(_ring(seg, xy, tol * 0.6, close=False) for seg in segs)
        if d:
            features.append({"id": _unique(str(props.get("CODE") or _slug(name)).upper(), seen), "name": name, "kind": "line", "d": d})
    for name, props, pt in pts:
        x, y = xy(float(pt[0]), float(pt[1]))
        feat = {"id": _unique(str(props.get("CODE") or _slug(name)).upper(), seen), "name": name, "kind": "point", "x": round(x, 1), "y": round(y, 1)}
        if props.get("INFO"):
            feat["info"] = str(props["INFO"])[:80]
        features.append(feat)
    if not features:
        raise GeoError("The map has no countries I can draw.")
    out = {"viewBox": view_box, "features": features}
    if use_frame and frame is None:
        out["frame"] = {k: (round(v, 8) if isinstance(v, float) else v) for k, v in use_frame.items()}
    elif frame is not None:
        out["frame"] = frame
    outline = "".join(_ring(r, xy, tol * 0.8) for r in outline_rings)
    if outline:
        out["outline"] = outline
        if note:
            out["note"] = note
    if label:
        out["label"] = label[:40]
    return out


def import_geojson(db: Session, geojson: dict, external_id: str, actor_id: uuid.UUID | None, url: str = "https://www.naturalearthdata.com/", fit: bool | None = None,
                   frame_from: SourceAsset | None = None, label: str | None = None) -> SourceAsset:
    decision = evaluate("PDM-1.0")
    if not decision.allowed:                                              # the policy, not this file, decides what is importable
        raise GeoError(decision.reason)
    frame = None
    if frame_from is not None:
        frame = (frame_from.data or {}).get("frame")
        if not frame:
            raise GeoError("The base map has no stored frame, so an overlay cannot be placed on it. Re-import the base map first.")
    data = project(geojson, fit, frame, label)
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
