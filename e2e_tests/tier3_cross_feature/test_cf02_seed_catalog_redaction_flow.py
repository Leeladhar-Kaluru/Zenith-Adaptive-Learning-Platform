import pytest

def test_seed_catalog_redaction_cross_flow(client, student_client, teacher_client):
    """
    Tier 3 Pairwise Pipeline:
    1. Query curriculum catalogue
    2. Query chapter details and resources
    3. Verify student gets redacted question payload
    4. Verify teacher gets full payload with answerKey
    """
    # 1. Query catalogue
    cat_res = client.get("/api/v1/library/catalogue")
    assert cat_res.status_code == 200
    chapters = cat_res.json()["chapters"]
    poly_ch = next(c for c in chapters if c["slug"] == "polynomials")
    assert poly_ch["resource_count"] == 5

    # 2. Query chapter details
    ch_res = client.get("/api/v1/library/chapters/polynomials")
    assert ch_res.status_code == 200
    resources = ch_res.json()["resources"]
    assert len(resources) == 5

    # 3. Query practice resource as student -> must be redacted
    student_res = student_client.get("/api/v1/library/resources/polynomials-practice-set")
    assert student_res.status_code == 200
    student_questions = student_res.json()["content"]["questions"]
    for q in student_questions:
        assert "answerKey" not in q, "Security leak: answerKey present in student view!"
        assert "explanation" not in q, "Security leak: explanation present in student view!"

    # 4. Query same resource as teacher -> answerKey must be accessible
    teacher_res = teacher_client.get("/api/v1/library/resources/polynomials-practice-set")
    assert teacher_res.status_code == 200
    teacher_questions = teacher_res.json()["content"]["questions"]
    for q in teacher_questions:
        assert "answerKey" in q
