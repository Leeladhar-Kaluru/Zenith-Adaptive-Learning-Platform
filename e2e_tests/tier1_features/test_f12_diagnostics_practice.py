import pytest

def test_create_diagnostic_session(student_client):
    """Feature 12: Starting diagnostic session returns session_id and items."""
    res = student_client.post("/api/v1/diagnostics/session", json_data={"chapter_slug": "real-numbers"})
    assert res.status_code == 201
    data = res.json()
    assert "session_id" in data
    assert "items" in data
    assert len(data["items"]) >= 6

def test_submit_diagnostic_computes_score(student_client):
    """Feature 12: Submitting responses computes aggregate score and totals."""
    # 1. Start session
    session_res = student_client.post("/api/v1/diagnostics/session", json_data={"chapter_slug": "real-numbers"})
    session_id = session_res.json()["session_id"]
    
    # 2. Submit responses: 4 correct, 2 incorrect
    responses = [
        {"item_id": "real-numbers-d1", "is_correct": True},
        {"item_id": "real-numbers-d2", "is_correct": True},
        {"item_id": "real-numbers-d3", "is_correct": True},
        {"item_id": "real-numbers-d4", "is_correct": True},
        {"item_id": "real-numbers-d5", "is_correct": False},
        {"item_id": "real-numbers-d6", "is_correct": False},
    ]
    submit_res = student_client.post("/api/v1/diagnostics/submit", json_data={
        "session_id": session_id,
        "responses": responses
    })
    assert submit_res.status_code == 200
    data = submit_res.json()
    assert data["total_items"] == 6
    assert data["correct_items"] == 4
    assert data["score"] == 66  # 4/6 * 100

def test_diagnostic_submission_updates_bkt_probability(student_client):
    """Feature 12: Submission updates Bayesian Knowledge Tracing probability."""
    session_res = student_client.post("/api/v1/diagnostics/session", json_data={"chapter_slug": "real-numbers"})
    session_id = session_res.json()["session_id"]
    
    submit_res = student_client.post("/api/v1/diagnostics/submit", json_data={
        "session_id": session_id,
        "responses": [{"item_id": "real-numbers-d1", "is_correct": True}]
    })
    assert submit_res.status_code == 200
    assert "mastery_probability" in submit_res.json()
    assert 0.0 < submit_res.json()["mastery_probability"] < 1.0

def test_weakest_prerequisite_gap_recommendation(student_client):
    """Feature 12: Diagnostic yields recommended practice targeting confirmed gap."""
    session_res = student_client.post("/api/v1/diagnostics/session", json_data={"chapter_slug": "real-numbers"})
    session_id = session_res.json()["session_id"]
    
    # 2 errors -> confirmed gap
    submit_res = student_client.post("/api/v1/diagnostics/submit", json_data={
        "session_id": session_id,
        "responses": [
            {"item_id": "real-numbers-d1", "is_correct": False},
            {"item_id": "real-numbers-d2", "is_correct": False},
        ]
    })
    assert submit_res.status_code == 200
    data = submit_res.json()
    assert data["gap_status"] == "confirmed_gap"
    assert "recommended_practice" in data
    assert "concept_id" in data["recommended_practice"]

def test_diagnostic_invalid_chapter_returns_422(student_client):
    """Feature 12: Invalid or missing chapter slug returns HTTP 422."""
    res = student_client.post("/api/v1/diagnostics/session", json_data={"chapter_slug": ""})
    assert res.status_code == 422
