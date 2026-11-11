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


def _state(name, code, x, y, w=4, pts=3):
    # a wavy square: `pts` points per side so simplification has something to remove
    ring = [[x + w * i / pts, y] for i in range(pts)] + [[x + w, y + w * i / pts] for i in range(pts)] + [[x + w - w * i / pts, y + w] for i in range(pts)] + [[x, y + w - w * i / pts] for i in range(pts)]
    return {"type": "Feature", "properties": {"NAME": name, "ADMIN": "Testland", "ISO_A3": "TST", "CODE": code}, "geometry": {"type": "Polygon", "coordinates": [ring + [ring[0]]]}}


def test_a_regional_map_is_fitted_to_its_own_frame_and_keeps_every_place_distinct():
    gj = {"type": "FeatureCollection", "features": [_state("North", "TL-N", 70, 20), _state("South", "TL-S", 70, 10), _state("East", "TL-E", 78, 14)]}
    out = naturalearth.project(gj)
    w, h = out["viewBox"]
    assert max(w, h) == 1000 and w != 1000 or h != 500                         # fitted, not the world frame
    assert w < h * 1.5 and h < w * 1.5                                          # roughly square, because the region is
    assert [f["id"] for f in out["features"]] == ["TL-N", "TL-S", "TL-E"]
    nums = [float(n) for f in out["features"] for n in __import__("re").findall(r"-?\d+(?:\.\d+)?", f["d"])]
    assert min(nums) >= 0 and max(nums) <= 1000


def test_places_sharing_a_country_code_still_get_unique_ids():
    gj = {"type": "FeatureCollection", "features": [{**_state("A", "", 70, 10), "properties": {"NAME": "A", "ISO_A3": "IND"}}, {**_state("B", "", 76, 10), "properties": {"NAME": "B", "ISO_A3": "IND"}}]}
    ids = [f["id"] for f in naturalearth.project(gj)["features"]]
    assert len(set(ids)) == 2 and ids[0] == "IND"


def test_fitting_can_be_forced_off_and_a_world_sized_map_never_fits_by_accident():
    gj = {"type": "FeatureCollection", "features": [_state("North", "TL-N", 70, 20), _state("South", "TL-S", 70, 10)]}
    assert naturalearth.project(gj, fit=False)["viewBox"] == [1000, 500]
    world = {"type": "FeatureCollection", "features": [_state("W", "W", -170, 10), _state("E", "E", 100, 10)]}
    assert naturalearth.project(world)["viewBox"] == [1000, 500]


def test_a_very_detailed_boundary_is_simplified_so_it_fits_the_size_limit():
    dense = _state("Dense", "TL-D", 70, 10, w=10, pts=3000)
    gj = {"type": "FeatureCollection", "features": [dense, _state("Other", "TL-O", 80, 10)]}
    big = len(json.dumps(naturalearth.project(gj, fit=False)))
    fitted = naturalearth.project(gj)
    assert len(fitted["features"][0]["d"]) < len(dense["geometry"]["coordinates"][0]) * 8          # far fewer points than the source
    assert big > 0


def _outlined():
    states = [_state("North", "TL-N", 70, 20), _state("South", "TL-S", 70, 10)]
    outline = {"type": "Feature", "properties": {"NAME": "Testland (official outline)", "OUTLINE": True, "NOTE": "Includes areas that others administer."},
               "geometry": {"type": "Polygon", "coordinates": [[[68, 8], [76, 8], [76, 26], [68, 26], [68, 8]]]}}
    return {"type": "FeatureCollection", "features": [*states, outline]}


def test_an_outline_is_drawn_underneath_widens_the_frame_and_is_never_a_place():
    out = naturalearth.project(_outlined())
    assert [f["id"] for f in out["features"]] == ["TL-N", "TL-S"]            # the outline cannot be tapped or found
    assert out["outline"].startswith("M") and out["note"] == "Includes areas that others administer."
    plain = naturalearth.project({"type": "FeatureCollection", "features": _outlined()["features"][:2]})
    assert out["viewBox"] != plain["viewBox"]                                  # the frame now has room for the whole outline
    nums = [float(n) for n in __import__("re").findall(r"-?\d+(?:\.\d+)?", out["outline"] + "".join(f["d"] for f in out["features"]))]
    assert min(nums) >= 0 and max(nums) <= 1000
    assert "outline" not in plain and "note" not in plain


def test_students_receive_the_outline_and_note_for_an_approved_layer(client, db):
    from app.ingest.assets import approve_asset
    rev, st = make_profile(db, "reviewer"), make_profile(db, "student")
    a = naturalearth.import_geojson(db, _outlined(), "outlined-test", rev.id)
    approve_asset(db, a.id, rev.id)
    body = client.get(f"{API}/datasets/{a.id}", headers=auth(st)).json()
    assert body["outline"].startswith("M") and "administer" in body["note"] and len(body["features"]) == 2


def test_the_india_outline_builder_joins_states_and_the_official_boundary_and_refuses_a_mismatch():
    pytest.importorskip("shapely")
    from app.ingest import india_outline
    states = {"type": "FeatureCollection", "features": [_state("North", "TL-N", 70, 20), _state("South", "TL-S", 70, 10)]}
    official = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"NAME": "India", "ADM0_A3": "IND"}, "geometry": {"type": "Polygon", "coordinates": [[[68, 8], [76, 8], [76, 26], [68, 26], [68, 8]]]}},
        {"type": "Feature", "properties": {"NAME": "Elsewhere", "ADM0_A3": "ELS"}, "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}}]}
    joined = india_outline.build(states, official)
    assert len(joined["features"]) == 3 and joined["features"][-1]["properties"]["OUTLINE"] is True
    assert "not drawn" in joined["features"][-1]["properties"]["NOTE"]
    assert len(naturalearth.project(joined)["features"]) == 2
    far = {"type": "FeatureCollection", "features": [_state("Far", "TL-F", 10, 50)]}
    with pytest.raises(india_outline.OutlineError, match="outside the official outline"):
        india_outline.build(far, official)
    with pytest.raises(india_outline.OutlineError, match="exactly one India"):
        india_outline.build(states, {"type": "FeatureCollection", "features": []})
