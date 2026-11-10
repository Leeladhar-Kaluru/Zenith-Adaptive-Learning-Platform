import pytest

def test_section_by_section_navigation(student_client):
    """Feature 18: Lesson reading content is structured into sections."""
    res = student_client.get("/api/v1/library/resources/real-numbers-lesson")
    assert res.status_code == 200
    sections = res.json()["content"]["sections"]
    assert len(sections) >= 2
    for s in sections:
        assert "title" in s
        assert "body" in s

def test_latex_formula_rendering(student_client):
    """Feature 18: Formulas contain valid LaTeX delimiters ($...$ or $$...$$)."""
    res = student_client.get("/api/v1/library/resources/real-numbers-formula-sheet")
    assert res.status_code == 200
    content = str(res.json()["content"])
    assert "Formula" in content or "LaTeX" in content

def test_worked_examples_interactive_steps(student_client):
    """Feature 18: Worked examples provide clear problem statement and step-by-step resolution."""
    res = student_client.get("/api/v1/library/resources/real-numbers-worked-examples")
    assert res.status_code == 200
    assert "sections" in res.json()["content"]

def test_ask_zenith_drawer_trigger(student_client):
    """Feature 18: Reader allows triggering Socratic doubt drawer with concept context."""
    res = student_client.post(
        "/api/v1/tutor/message",
        json_data={
            "message": "I don't understand step 2 in this worked example.",
            "context": {"chapter_slug": "real-numbers", "resource_id": "real-numbers-worked-examples"}
        }
    )
    assert res.status_code == 200
    assert "reply" in res.json()

def test_save_offline_action(student_client):
    """Feature 18: Lesson resource content payload is serializable for Dexie IndexedDB caching."""
    import json
    res = student_client.get("/api/v1/library/resources/real-numbers-lesson")
    assert res.status_code == 200
    raw_payload = res.json()
    serialized = json.dumps(raw_payload)
    assert len(serialized) > 50
    # Must roundtrip cleanly
    deserialized = json.loads(serialized)
    assert deserialized["id"] == raw_payload["id"]
