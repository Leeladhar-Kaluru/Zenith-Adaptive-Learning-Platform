"""Add India's official outer boundary to a states layer.

Natural Earth's default states layer draws Jammu and Kashmir and Ladakh by present control. Its India-viewpoint country file
follows the boundary published in India's own official maps. This joins the two: the states stay selectable exactly as drawn, and the
complete official outline is added as a decorative layer underneath. We do NOT invent the divisions inside the areas that Pakistan or China
administer: there is no data for them, so they are left as one undivided shape with a plain caption.

An ops tool (needs `shapely`, see requirements-ops.txt). Usage:
    python -m app.ingest.india_outline <states.geojson> <india_viewpoint_countries.geojson> <out.geojson>
A reviewer must still check the result against the Survey of India's published map before approving the layer.
"""
from __future__ import annotations

import json
import sys

NOTE = ("The outline shows India's boundary as published in India's official maps. It includes parts of Jammu and Kashmir and Ladakh "
        "that Pakistan and China administer. The divisions inside those parts are not drawn.")


class OutlineError(ValueError):
    pass


def _is_india(props: dict) -> bool:
    return str(props.get("ADM0_A3") or props.get("adm0_a3") or "").upper() == "IND" or str(props.get("NAME") or props.get("name") or "") == "India"


def build(states: dict, official: dict, tolerance: float = 0.05) -> dict:
    from shapely.geometry import mapping, shape
    from shapely.ops import unary_union

    cands = [f for f in official.get("features", []) if _is_india(f.get("properties") or {})]
    if len(cands) != 1:
        raise OutlineError(f"Expected exactly one India feature in the viewpoint file, found {len(cands)}.")
    outline = shape(cands[0]["geometry"]).buffer(0)
    placed = [f for f in states.get("features", []) if (f.get("geometry") or {}).get("type") in ("Polygon", "MultiPolygon")]
    if not placed:
        raise OutlineError("The states layer has no polygons.")
    union = unary_union([shape(f["geometry"]).buffer(0) for f in placed]).buffer(0)
    stray = union.difference(outline.buffer(tolerance))
    if stray.area > 0.05:
        raise OutlineError(f"The states reach outside the official outline (area {stray.area:.3f}). The two files do not match.")
    feature = {"type": "Feature", "properties": {"NAME": "India (official outline)", "OUTLINE": True, "NOTE": NOTE}, "geometry": mapping(outline)}
    return {"type": "FeatureCollection", "features": [*placed, feature]}


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__)
        return 2
    states, official = (json.load(open(p, encoding="utf-8")) for p in argv[1:3])
    json.dump(build(states, official), open(argv[3], "w", encoding="utf-8"))
    print("wrote", argv[3])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
