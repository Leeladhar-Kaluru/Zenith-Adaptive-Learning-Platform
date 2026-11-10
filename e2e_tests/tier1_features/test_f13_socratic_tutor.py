import pytest

def test_tutor_generates_grounded_answer(student_client):
    """Feature 13: Socratic tutor returns explanation grounded with citations."""
    res = student_client.post(
        "/api/v1/tutor/message",
        json_data={"message": "Can you explain Euclid's division lemma?"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert "[1]" in data["reply"]
    assert "citations" in data
    assert len(data["citations"]) >= 1

def test_tutor_citations_reference_curriculum_sources(student_client):
    """Feature 13: Citations identify source title and section."""
    res = student_client.post(
        "/api/v1/tutor/message",
        json_data={"message": "What is the condition for remainders in division?"}
    )
    assert res.status_code == 200
    citations = res.json()["citations"]
    for c in citations:
        assert "ref" in c
        assert "source_title" in c
        assert "section" in c

def test_tutor_empty_message_returns_422(student_client):
    """Feature 13: Submitting empty message returns HTTP 422 Unprocessable Entity."""
    res = student_client.post(
        "/api/v1/tutor/message",
        json_data={"message": "   "}
    )
    assert res.status_code == 422

def test_tutor_daily_message_quota(student_client):
    """Feature 13: Daily message quota enforcement returns 429 when exhausted."""
    # Send messages until quota reached (in simulator quota is 20)
    last_res = None
    for _ in range(25):
        last_res = student_client.post(
            "/api/v1/tutor/message",
            json_data={"message": "How do I calculate prime factors?"}
        )
        if last_res.status_code == 429:
            break
            
    assert last_res is not None
    assert last_res.status_code == 429
    assert "quota" in last_res.json()["detail"].lower()

def test_tutor_provider_offline_returns_honest_503(student_client):
    """Feature 13: Provider offline condition yields honest 503 rather than silent crash."""
    res = student_client.post(
        "/api/v1/tutor/message",
        json_data={"message": "Hello tutor", "simulate_provider_offline": True}
    )
    assert res.status_code == 503
    assert "offline" in res.json()["detail"].lower()
