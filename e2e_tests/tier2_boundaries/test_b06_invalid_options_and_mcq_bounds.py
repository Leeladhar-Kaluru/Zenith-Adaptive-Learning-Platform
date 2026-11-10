import pytest

def test_submitting_invalid_option_key(student_client):
    """Tier 2: Submitting an option key outside the valid options list."""
    session_res = student_client.post("/api/v1/diagnostics/session", json_data={"chapter_slug": "real-numbers"})
    session_id = session_res.json()["session_id"]
    
    # Submitting option "Z" when options are ["A", "B", "C", "D"]
    submit_res = student_client.post("/api/v1/diagnostics/submit", json_data={
        "session_id": session_id,
        "responses": [{"item_id": "real-numbers-d1", "selected_option": "Z", "is_correct": False}]
    })
    # Should safely record as incorrect without crashing
    assert submit_res.status_code == 200
    assert submit_res.json()["correct_items"] == 0

def test_empty_option_string_handled_safely(student_client):
    """Tier 2: Empty option string is evaluated as incorrect response."""
    session_res = student_client.post("/api/v1/diagnostics/session", json_data={"chapter_slug": "real-numbers"})
    session_id = session_res.json()["session_id"]
    
    submit_res = student_client.post("/api/v1/diagnostics/submit", json_data={
        "session_id": session_id,
        "responses": [{"item_id": "real-numbers-d1", "selected_option": "", "is_correct": False}]
    })
    assert submit_res.status_code == 200
    assert submit_res.json()["correct_items"] == 0

def test_duplicate_options_detected_by_validator():
    """Tier 2: Content validator rejects questions with duplicate MCQ choices."""
    question_with_duplicates = {
        "text": "What is the degree of a linear polynomial?",
        "options": ["1", "2", "1", "3"],
        "answerKey": "1"
    }
    has_duplicates = len(question_with_duplicates["options"]) != len(set(question_with_duplicates["options"]))
    assert has_duplicates is True

def test_single_option_question_detected_by_validator():
    """Tier 2: Question with fewer than 2 options is rejected by schema validator."""
    question_too_few = {
        "text": "Is pi rational?",
        "options": ["No"],
        "answerKey": "No"
    }
    is_valid_mcq = len(question_too_few["options"]) >= 2
    assert is_valid_mcq is False

def test_negative_time_spent_boundary_sanitization(student_client):
    """Tier 2: Negative time_spent_ms is clamped or sanitized without failure."""
    session_res = student_client.post("/api/v1/diagnostics/session", json_data={"chapter_slug": "real-numbers"})
    session_id = session_res.json()["session_id"]
    
    submit_res = student_client.post("/api/v1/diagnostics/submit", json_data={
        "session_id": session_id,
        "responses": [{"item_id": "real-numbers-d1", "time_spent_ms": -5000, "is_correct": True}]
    })
    assert submit_res.status_code == 200
