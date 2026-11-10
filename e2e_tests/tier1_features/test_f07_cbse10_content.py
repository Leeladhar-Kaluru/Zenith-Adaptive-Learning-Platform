import pytest
from e2e_tests.test_config import FLAGSHIP_CHAPTERS, EXPECTED_RESOURCE_TYPES

def test_all_4_flagship_chapters_present(client):
    """Feature 7: Real Numbers, Polynomials, Linear Equations, Quadratic Equations."""
    res = client.get("/api/v1/library/catalogue")
    assert res.status_code == 200
    data = res.json()
    chapter_slugs = [c["slug"] for c in data["chapters"]]
    for slug in FLAGSHIP_CHAPTERS:
        assert slug in chapter_slugs

def test_20_resource_packages_structure(client):
    """Feature 7: 5 resource packages per chapter across all 4 chapters (total 20)."""
    total_resources = 0
    for slug in FLAGSHIP_CHAPTERS:
        res = client.get(f"/api/v1/library/chapters/{slug}")
        assert res.status_code == 200
        resources = res.json()["resources"]
        assert len(resources) == len(EXPECTED_RESOURCE_TYPES)
        total_resources += len(resources)
    assert total_resources == 20

def test_4_diagnostic_banks_present(client):
    """Feature 7: Each chapter provides an active diagnostic bank."""
    for slug in FLAGSHIP_CHAPTERS:
        res = client.post("/api/v1/diagnostics/session", json_data={"chapter_slug": slug})
        assert res.status_code == 201
        data = res.json()
        assert len(data["items"]) >= 6

def test_worked_examples_step_by_step(client):
    """Feature 7: Worked examples package includes structured sections and equations."""
    res = client.get("/api/v1/library/resources/real-numbers-worked-examples")
    assert res.status_code == 200
    data = res.json()
    assert "content" in data
    assert "sections" in data["content"]
    assert len(data["content"]["sections"]) >= 2

def test_content_rights_declared_as_original(client):
    """Feature 7: All curriculum packages have rights set to 'original'."""
    res = client.get("/api/v1/library/chapters/real-numbers")
    assert res.status_code == 200
    resources = res.json()["resources"]
    for r in resources:
        assert r.get("rights") == "original"
