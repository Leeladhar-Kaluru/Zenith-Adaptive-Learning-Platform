import pytest

def test_empty_diagnostic_submission_payload(student_client):
    """Tier 2: Empty JSON payload returns HTTP 422 Unprocessable Entity."""
    res = student_client.post("/api/v1/diagnostics/submit", json_data={})
    assert res.status_code == 422

def test_zero_responses_submitted_in_quiz(student_client):
    """Tier 2: Submitting empty list of responses returns HTTP 422."""
    res = student_client.post("/api/v1/diagnostics/submit", json_data={
        "session_id": "test-session",
        "responses": []
    })
    assert res.status_code == 422

def test_extremely_large_payload_handling(student_client):
    """Tier 2: Extremely large text payload does not trigger internal 500 error."""
    huge_text = "What is math? " * 5000  # ~75 KB
    res = student_client.post(
        "/api/v1/tutor/message",
        json_data={"message": huge_text}
    )
    # Must be handled cleanly (422, 413, or 200/429)
    assert res.status_code in (200, 413, 422, 429, 503)

def test_whitespace_only_tutor_question(student_client):
    """Tier 2: Message composed exclusively of whitespace returns HTTP 422."""
    res = student_client.post(
        "/api/v1/tutor/message",
        json_data={"message": "   \n\t  \r  "}
    )
    assert res.status_code == 422

def test_missing_required_fields_in_session_init(student_client):
    """Tier 2: Omission of chapter_slug in session creation returns HTTP 422."""
    res = student_client.post(
        "/api/v1/diagnostics/session",
        json_data={"unrelated_key": "some_value"}
    )
    assert res.status_code == 422
