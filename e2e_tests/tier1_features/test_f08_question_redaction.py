import pytest

def test_student_resource_payload_redacts_answer_key(student_client):
    """Feature 8: answerKey is stripped from student payloads."""
    res = student_client.get("/api/v1/library/resources/real-numbers-practice-set")
    assert res.status_code == 200
    questions = res.json()["content"]["questions"]
    for q in questions:
        assert "answerKey" not in q, "answerKey must be redacted for student role"

def test_student_resource_payload_redacts_explanation(student_client):
    """Feature 8: Private explanation is stripped from student payloads."""
    res = student_client.get("/api/v1/library/resources/real-numbers-practice-set")
    assert res.status_code == 200
    questions = res.json()["content"]["questions"]
    for q in questions:
        assert "explanation" not in q, "explanation must be redacted for student role"

def test_teacher_resource_payload_preserves_answer_key(teacher_client):
    """Feature 8: Teachers retain access to answerKey for classroom review."""
    res = teacher_client.get("/api/v1/library/resources/real-numbers-practice-set")
    assert res.status_code == 200
    questions = res.json()["content"]["questions"]
    for q in questions:
        assert "answerKey" in q, "answerKey should be accessible to teachers"

def test_redaction_does_not_mutate_question_options(student_client):
    """Feature 8: Question text and options list remain intact after redaction."""
    res = student_client.get("/api/v1/library/resources/real-numbers-practice-set")
    assert res.status_code == 200
    questions = res.json()["content"]["questions"]
    for q in questions:
        assert "question_id" in q
        assert "text" in q
        assert "options" in q
        assert len(q["options"]) >= 2

def test_diagnostic_items_redacted_for_students(student_client):
    """Feature 8: Diagnostic session items do not leak correct answers."""
    res = student_client.post("/api/v1/diagnostics/session", json_data={"chapter_slug": "real-numbers"})
    assert res.status_code == 201
    items = res.json()["items"]
    for item in items:
        assert "answer" not in item
        assert "correct" not in item
        assert "answerKey" not in item
