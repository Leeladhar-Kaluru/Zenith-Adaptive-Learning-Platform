import pytest
from e2e_tests.test_config import FLAGSHIP_CHAPTERS

def test_explore_filters(client):
    """Feature 17: Explore page provides filtering by board, class, and subject."""
    res = client.get("/api/v1/library/catalogue")
    assert res.status_code == 200
    data = res.json()
    assert "cbse" in data["boards"]
    assert "10" in data["classes"]
    assert "mathematics" in data["subjects"]

def test_chapter_cards_show_syllabus_and_resources(client):
    """Feature 17: Each chapter card reports resource counts and titles."""
    res = client.get("/api/v1/library/catalogue")
    chapters = res.json()["chapters"]
    for ch in chapters:
        assert "title" in ch
        assert "resource_count" in ch
        assert ch["resource_count"] == 5

def test_chapter_page_displays_5_resource_packages(client):
    """Feature 17: Navigating to a chapter page displays all 5 educational packages."""
    for slug in FLAGSHIP_CHAPTERS:
        res = client.get(f"/api/v1/library/chapters/{slug}")
        assert res.status_code == 200
        assert len(res.json()["resources"]) == 5

def test_chapter_prerequisites_indicator(client):
    """Feature 17: Chapter dependencies and prerequisites are readable."""
    res = client.get("/api/v1/library/map/real-numbers")
    assert res.status_code == 200
    assert "edges" in res.json()

def test_diagnostic_cta_button(student_client):
    """Feature 17: Chapter page contains active CTA to begin diagnostic challenge."""
    res = student_client.post("/api/v1/diagnostics/session", json_data={"chapter_slug": "real-numbers"})
    assert res.status_code == 201
    assert "session_id" in res.json()
