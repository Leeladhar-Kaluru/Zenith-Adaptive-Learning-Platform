import pytest

def test_catalogue_listing(client):
    """Feature 9: GET /api/v1/library/catalogue returns list of chapters and metadata."""
    res = client.get("/api/v1/library/catalogue")
    assert res.status_code == 200
    data = res.json()
    assert "chapters" in data
    assert "subjects" in data
    assert "boards" in data
    assert "cbse" in data["boards"]

def test_chapter_detail_lookup(client):
    """Feature 9: GET /api/v1/library/chapters/{slug} returns resources."""
    res = client.get("/api/v1/library/chapters/real-numbers")
    assert res.status_code == 200
    data = res.json()
    assert "chapter" in data
    assert "resources" in data
    assert data["chapter"]["slug"] == "real-numbers"

def test_chapter_not_found_returns_404(client):
    """Feature 9: Requesting an unknown chapter slug returns HTTP 404."""
    res = client.get("/api/v1/library/chapters/unknown-astronomy-ch99")
    assert res.status_code == 404
    assert "detail" in res.json()

def test_published_library_paths_readable(student_client):
    """Feature 9: Authenticated student can access published library resources."""
    res = student_client.get("/api/v1/library/resources/real-numbers-lesson")
    assert res.status_code == 200
    assert "id" in res.json()

def test_concept_map_endpoint(client):
    """Feature 9: GET /api/v1/library/map/{slug} returns concept DAG nodes and edges."""
    res = client.get("/api/v1/library/map/real-numbers")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) >= 2
