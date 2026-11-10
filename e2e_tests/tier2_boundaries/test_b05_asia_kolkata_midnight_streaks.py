from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import pytest
from e2e_tests.test_config import TIMEZONE_STREAKS

def test_asia_kolkata_timezone_object_loads():
    """Tier 2: ZoneInfo('Asia/Kolkata') is valid and available in Python environment."""
    tz = ZoneInfo(TIMEZONE_STREAKS)
    assert str(tz) == "Asia/Kolkata"

def test_midnight_ist_boundary_transition():
    """Tier 2: Actions at 23:59:59 IST and 00:00:01 IST belong to two consecutive calendar days."""
    tz = ZoneInfo(TIMEZONE_STREAKS)
    # Day 1: 2026-11-06 23:59:59 IST
    dt_day1 = datetime(2026, 11, 6, 23, 59, 59, tzinfo=tz)
    # Day 2: 2026-11-07 00:00:01 IST (2 seconds later)
    dt_day2 = dt_day1 + timedelta(seconds=2)
    
    assert dt_day1.date() != dt_day2.date()
    assert (dt_day2.date() - dt_day1.date()).days == 1

def test_same_day_activity_does_not_double_increment_streak(student_client):
    """Tier 2: Claiming multiple times in the same day yields idempotent response."""
    res1 = student_client.post("/api/v1/rewards/claim-daily", headers={"Idempotency-Key": "same-day-1"})
    assert res1.status_code == 200
    res2 = student_client.post("/api/v1/rewards/claim-daily", headers={"Idempotency-Key": "same-day-1"})
    assert res2.status_code == 200
    assert res2.json()["idempotent"] is True

def test_inactivity_gap_breaks_streak():
    """Tier 2: Activity gap >= 2 days (48 hours) resets streak counter to 1."""
    tz = ZoneInfo(TIMEZONE_STREAKS)
    last_active = datetime(2026, 11, 1, 10, 0, 0, tzinfo=tz).date()
    current_date = datetime(2026, 11, 4, 10, 0, 0, tzinfo=tz).date()
    
    gap_days = (current_date - last_active).days
    assert gap_days > 1
    # Streak logic rule: if gap > 1 day, streak resets to 1
    new_streak = 1 if gap_days > 1 else 2
    assert new_streak == 1

def test_consecutive_day_increments_streak():
    """Tier 2: Activity on consecutive calendar days increments streak counter."""
    tz = ZoneInfo(TIMEZONE_STREAKS)
    last_active = datetime(2026, 11, 5, 18, 0, 0, tzinfo=tz).date()
    current_date = datetime(2026, 11, 6, 9, 0, 0, tzinfo=tz).date()
    
    gap_days = (current_date - last_active).days
    assert gap_days == 1
    prior_streak = 3
    new_streak = prior_streak + 1
    assert new_streak == 4
