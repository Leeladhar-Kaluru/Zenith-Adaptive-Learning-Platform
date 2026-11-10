import pytest

def test_zero_score_submission_edge(student_client):
    """Tier 2: Student answering 0 questions correctly receives score = 0."""
    session_res = student_client.post("/api/v1/diagnostics/session", json_data={"chapter_slug": "real-numbers"})
    session_id = session_res.json()["session_id"]
    
    submit_res = student_client.post("/api/v1/diagnostics/submit", json_data={
        "session_id": session_id,
        "responses": [
            {"item_id": "real-numbers-d1", "is_correct": False},
            {"item_id": "real-numbers-d2", "is_correct": False},
            {"item_id": "real-numbers-d3", "is_correct": False},
        ]
    })
    assert submit_res.status_code == 200
    data = submit_res.json()
    assert data["score"] == 0
    assert data["correct_items"] == 0
    assert data["gap_status"] == "confirmed_gap"

def test_perfect_score_submission_edge(student_client):
    """Tier 2: Student answering all questions correctly receives score = 100."""
    session_res = student_client.post("/api/v1/diagnostics/session", json_data={"chapter_slug": "real-numbers"})
    session_id = session_res.json()["session_id"]
    
    submit_res = student_client.post("/api/v1/diagnostics/submit", json_data={
        "session_id": session_id,
        "responses": [
            {"item_id": "real-numbers-d1", "is_correct": True},
            {"item_id": "real-numbers-d2", "is_correct": True},
        ]
    })
    assert submit_res.status_code == 200
    data = submit_res.json()
    assert data["score"] == 100
    assert data["correct_items"] == 2

def test_bkt_mastery_probability_floor(bkt_oracle):
    """Tier 2: Repeated errors do not drop probability below numerical floor (0.0001)."""
    p_l = 0.25
    for _ in range(50):
        p_l = bkt_oracle.update(p_l, correct=False)
    assert p_l >= 0.0001

def test_bkt_mastery_probability_ceiling(bkt_oracle):
    """Tier 2: Repeated correct answers do not exceed probability ceiling (0.9999)."""
    p_l = 0.25
    for _ in range(50):
        p_l = bkt_oracle.update(p_l, correct=True)
    assert p_l <= 0.9999

def test_bkt_alternating_responses_oscillation(bkt_oracle):
    """Tier 2: Alternating correct and incorrect answers remain stable without divergent oscillations."""
    history = bkt_oracle.sequence_update(initial_p_l=0.50, observations=[True, False, True, False, True, False])
    for val in history:
        assert 0.10 <= val <= 0.90
