import json

import pytest
from pydantic import ValidationError

from app.cms import gates
from app.cms.schema import WidgetBlock
from app.ingest import datasets, worldbank
from app.models import SourceAsset
from tests.conftest import auth, make_profile

API = "/api/v1"

SPEC = dict(source_name="World Bank Open Data", source_homepage="https://data.worldbank.org", external_id="SP.POP.TOTL:IN", title="India population",
            url="https://data.worldbank.org/indicator/SP.POP.TOTL?locations=IN", licence="CC-BY-4.0", attribution="World Bank, Population total (SP.POP.TOTL), India, CC BY 4.0",
            fields=["year", "value"], rows=[{"year": 2000 + i, "value": 1_000_000_000 + i * 15_000_000} for i in range(20)])


def test_open_dataset_imports_pending_with_its_data_and_credit(db):
    actor = make_profile(db, "reviewer")
    a = datasets.import_dataset(db, dict(SPEC), actor.id)
    assert a.status == "pending" and a.kind == "dataset" and a.licence_id == "CC-BY-4.0"
    assert a.data["fields"] == ["year", "value"] and len(a.data["rows"]) == 20
    assert a.recheck_at > a.retrieved_at


@pytest.mark.parametrize("licence", ["CC-BY-NC-4.0", "", "all rights reserved"])
def test_datasets_with_refused_licences_are_not_imported(db, licence):
    with pytest.raises(datasets.DatasetError):
        datasets.import_dataset(db, {**SPEC, "licence": licence}, make_profile(db, "reviewer").id)


def test_size_and_shape_limits(db):
    actor = make_profile(db, "reviewer")
    with pytest.raises(datasets.DatasetError, match="too large"):
        datasets.import_dataset(db, {**SPEC, "rows": [{"year": i, "value": "x" * 200} for i in range(1500)]}, actor.id)
    with pytest.raises(datasets.DatasetError, match="rows"):
        datasets.import_dataset(db, {**SPEC, "rows": [{"year": i, "value": i} for i in range(2001)]}, actor.id)
    with pytest.raises(datasets.DatasetError, match="field"):
        datasets.import_dataset(db, {**SPEC, "rows": [{"year": 1, "other": 2}]}, actor.id)
    with pytest.raises(datasets.DatasetError, match="attribution"):
        datasets.import_dataset(db, {**SPEC, "attribution": " "}, actor.id)


def test_students_get_only_approved_datasets_with_their_credit(db, client):
    from app.ingest.assets import approve_asset
    rev = make_profile(db, "reviewer")
    a = datasets.import_dataset(db, dict(SPEC), rev.id)
    st = make_profile(db, "student")
    assert client.get(f"{API}/datasets/{a.id}").status_code == 401
    assert client.get(f"{API}/datasets/{a.id}", headers=auth(st)).status_code == 404            # still pending
    approve_asset(db, a.id, rev.id)
    body = client.get(f"{API}/datasets/{a.id}", headers=auth(st)).json()
    assert body["fields"] == ["year", "value"] and len(body["rows"]) == 20
    assert body["credit"] == {"text": SPEC["attribution"], "url": SPEC["url"], "licence": "CC-BY-4.0"}
    assert client.get(f"{API}/datasets/not-a-uuid", headers=auth(st)).status_code == 404


def test_world_bank_adapter_builds_a_dataset_from_the_api_response(db, monkeypatch):
    payload = [{"page": 1, "pages": 1, "total": 3}, [{"date": "2022", "value": 1417173173}, {"date": "2021", "value": 1414203896}, {"date": "2020", "value": None}]]
    seen = []

    def fake(url, *, user_agent, client=None):
        seen.append(url)
        return json.dumps(payload).encode()

    monkeypatch.setattr(worldbank, "fetch", fake)
    a = worldbank.import_indicator(db, "SP.POP.TOTL", "IN", "Population, total", make_profile(db, "reviewer").id)
    assert "api.worldbank.org" in seen[0] and a.licence_id == "CC-BY-4.0"
    assert [r["year"] for r in a.data["rows"]] == [2021, 2022]                       # sorted, empty years dropped
    assert "SP.POP.TOTL" in a.attribution_text and "World Bank" in a.attribution_text


def test_chart_widget_needs_dataset_fields_and_a_task():
    WidgetBlock(kind="widget", widget="data_chart", config={"dataset": "a1", "x": "year", "y": "value", "chart": "line"}, task="Describe the trend")
    for cfg, task in (({"x": "year", "y": "value"}, "t"), ({"dataset": "a1", "y": "value"}, "t"), ({"dataset": "a1", "x": "year", "y": "value", "chart": "pie"}, "t"),
                      ({"dataset": "a1", "x": "year", "y": "value"}, " ")):
        with pytest.raises(ValidationError):
            WidgetBlock(kind="widget", widget="data_chart", config=cfg, task=task)


def test_a_chart_dataset_must_be_listed_credited_and_approved():
    def gate(sources, assets):
        blocks = [{"kind": "widget", "widget": "data_chart", "config": {"dataset": "d1", "x": "year", "y": "value"}, "task": "t"}]
        return next(g for g in gates.lesson_gates(title="t", grade=6, objectives=["o"], blocks=blocks, items=[], concept_ids=set(), known_concepts=set(), graph_error=None,
                                                   curriculum_verified=True, misconception_codes=set(), sources=sources, assets=assets) if g.name == "Imported assets are credited")
    ok = {"d1": {"status": "approved", "attribution": "World Bank, CC BY 4.0"}}
    assert gate(["d1"], ok).passed
    assert not gate([], ok).passed
    assert not gate(["d1"], {"d1": {"status": "pending", "attribution": "x"}}).passed
