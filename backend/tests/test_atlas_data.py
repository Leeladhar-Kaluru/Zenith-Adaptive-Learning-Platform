import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.cms.schema import WidgetBlock
from app.ingest import naturalearth
from tests.conftest import auth, make_profile

API = "/api/v1"
REPO = Path(__file__).resolve().parents[2]


def geojson():
    square = [[[10, 10], [20, 10], [20, 20], [10, 20], [10, 10]]]
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"NAME": "Squareland", "ISO_A3": "SQL", "POP_EST": 123456, "secret": "x"}, "geometry": {"type": "Polygon", "coordinates": square}},
        {"type": "Feature", "properties": {"NAME": "Twin Isles", "ISO_A3": "TWN"},
         "geometry": {"type": "MultiPolygon", "coordinates": [[[[-60, -30], [-50, -30], [-50, -20], [-60, -30]]], [[[100, 40], [110, 40], [110, 50], [100, 40]]]]}},
        {"type": "Feature", "properties": {"NAME": "A Point"}, "geometry": {"type": "Point", "coordinates": [0, 0]}},
    ]}


def test_countries_become_svg_paths_inside_the_viewbox_with_only_name_and_code():
    out = naturalearth.project(geojson())
    assert [f["name"] for f in out["features"]] == ["Squareland", "Twin Isles"]            # the point has no area and is skipped
    assert out["viewBox"] == [1000, 500]
    for f in out["features"]:
        assert f["d"].startswith("M") and f["d"].rstrip().endswith("Z") and set(f) == {"id", "name", "d"}
    nums = [float(n) for f in out["features"] for n in __import__("re").findall(r"-?\d+(?:\.\d+)?", f["d"])]
    assert all(0 <= n <= 1000 for n in nums)
    assert "POP_EST" not in json.dumps(out) and "secret" not in json.dumps(out)
    twin = out["features"][1]["d"]
    assert twin.count("M") == 2                                                              # both islands are drawn


def test_import_is_public_domain_credited_and_pending(db):
    a = naturalearth.import_geojson(db, geojson(), "ne_110m_admin_0_countries", make_profile(db, "reviewer").id)
    assert a.kind == "geo" and a.status == "pending" and a.licence_id == "PDM-1.0"
    assert "Natural Earth" in a.attribution_text and a.data["features"][0]["name"] == "Squareland"


def test_a_map_layer_over_the_size_limit_is_refused(db):
    big = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"NAME": f"Country {i}"},
                                                      "geometry": {"type": "Polygon", "coordinates": [[[j % 170 - 80, (j * 7) % 80 - 40] for j in range(400)] + [[-80, -40]]]}} for i in range(120)]}
    with pytest.raises(naturalearth.GeoError, match="too large"):
        naturalearth.import_geojson(db, big, "big", make_profile(db, "reviewer").id)


def test_students_get_only_approved_map_layers(db, client):
    from app.ingest.assets import approve_asset
    rev = make_profile(db, "reviewer")
    a = naturalearth.import_geojson(db, geojson(), "ne_110m_admin_0_countries", rev.id)
    st = make_profile(db, "student")
    assert client.get(f"{API}/datasets/{a.id}", headers=auth(st)).status_code == 404
    approve_asset(db, a.id, rev.id)
    body = client.get(f"{API}/datasets/{a.id}", headers=auth(st)).json()
    assert body["viewBox"] == [1000, 500] and len(body["features"]) == 2 and body["credit"]["licence"] == "PDM-1.0"


def test_atlas_widget_needs_a_dataset_and_a_task():
    WidgetBlock(kind="widget", widget="atlas", config={"dataset": "a1", "find": "Brazil"}, task="Find the country")
    WidgetBlock(kind="widget", widget="atlas", config={"dataset": "a1"}, task="Explore the map")
    with pytest.raises(ValidationError):
        WidgetBlock(kind="widget", widget="atlas", config={}, task="t")
    with pytest.raises(ValidationError):
        WidgetBlock(kind="widget", widget="atlas", config={"dataset": "a1"}, task=" ")


def test_no_code_points_at_the_public_openstreetmap_tile_servers():
    banned = ("tile.openstreetmap.org", "tile.osm.org")
    hits = []
    for root in (REPO / "frontend" / "src", REPO / "backend" / "app"):
        for f in root.rglob("*"):
            if f.is_file() and f.suffix in (".ts", ".tsx", ".py", ".css", ".html", ".js"):
                text = f.read_text(encoding="utf-8", errors="ignore")
                hits += [str(f.relative_to(REPO)) for b in banned if b in text]
    assert hits == []
