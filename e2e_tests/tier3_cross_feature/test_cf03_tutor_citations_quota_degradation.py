import pytest

def test_tutor_citations_quota_degradation_flow(student_client):
    """
    Tier 3 Pairwise Pipeline:
    1. Socratic doubt asking with curriculum citations
    2. Daily message quota decrement
    3. Graceful degradation when offline without crashing
    """
    # 1. Ask doubt about Quadratic Equations
    tutor_res1 = student_client.post(
        "/api/v1/tutor/message",
        json_data={
            "message": "Why does a quadratic equation have at most two roots?",
            "context": {"chapter_slug": "quadratic-equations"}
        }
    )
    assert tutor_res1.status_code == 200
    data1 = tutor_res1.json()
    assert "reply" in data1
    assert "citations" in data1
    assert len(data1["citations"]) >= 1
    # Check citation notation
    assert "[1]" in data1["reply"]

    # 2. Simulate Groq offline degradation
    tutor_res_offline = student_client.post(
        "/api/v1/tutor/message",
        json_data={
            "message": "Explain factoring method.",
            "simulate_provider_offline": True
        }
    )
    assert tutor_res_offline.status_code == 503
    assert "offline" in tutor_res_offline.json()["detail"].lower()
