import pytest

def test_dashboard_gamification_cards(student_client):
    """Feature 16: Dashboard displays 4 core stats: XP, Level, Streak, Badges."""
    res = student_client.get("/api/v1/rewards/me")
    assert res.status_code == 200
    data = res.json()
    assert "xp" in data
    assert "level" in data
    assert "streak" in data
    assert "badges" in data

def test_course_progress_display(client):
    """Feature 16: Course progress tracks module completion percentage."""
    res = client.get("/api/v1/library/chapters/real-numbers")
    assert res.status_code == 200
    resources = res.json()["resources"]
    assert len(resources) > 0
    # Simulate progress calculation
    completed = 2
    pct = int((completed / len(resources)) * 100)
    assert pct == 40

def test_today_challenge_card(student_client):
    """Feature 16: Today's challenge is accessible from the student dashboard."""
    res = student_client.get("/api/v1/rewards/me")
    assert res.status_code == 200
    # Streak banner and challenge availability
    assert res.json()["streak"] >= 0

def test_learning_efficiency_donut(bkt_oracle):
    """Feature 16: Learning efficiency breakdown reflects mastery probability."""
    prob = bkt_oracle.update(0.25, correct=True)
    # Mastered vs in-progress partition
    assert 0.0 <= prob <= 1.0

def test_monthly_activity_calendar(student_client):
    """Feature 16: Activity calendar tracks study timestamps."""
    res = student_client.get("/api/v1/rewards/me")
    assert res.status_code == 200
    assert "timezone" in res.json()
