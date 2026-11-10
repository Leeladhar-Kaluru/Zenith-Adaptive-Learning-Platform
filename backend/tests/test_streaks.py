from datetime import date, timedelta

from app.engine import streaks

T = date(2026, 11, 10)


def days(*offsets):
    return {T - timedelta(days=o) for o in offsets}


def test_streak_counts_consecutive_days_including_today():
    assert streaks.streak(days(0, 1, 2), T)["days"] == 3


def test_streak_alive_until_today_ends():
    r = streaks.streak(days(1, 2, 3), T)
    assert r["days"] == 3 and not r["activeToday"]


def test_one_missed_day_is_forgiven_once_per_week():
    r = streaks.streak(days(0, 1, 3, 4), T)   # missed day 2
    assert r["days"] == 4 and not r["restDayAvailable"]


def test_two_missed_days_break_the_streak():
    assert streaks.streak(days(0, 1, 4, 5), T)["days"] == 2


def test_no_activity_means_no_streak():
    assert streaks.streak(set(), T)["days"] == 0


def test_two_rests_inside_a_week_break_it():
    assert streaks.streak(days(0, 2, 4), T)["days"] == 1 + 1  # rest on day 1 allowed, day 3 rest not allowed within 7 days


def test_level_grows_with_xp_and_reports_progress():
    assert streaks.level(0)["level"] == 1
    assert streaks.level(50)["level"] == 2
    lv = streaks.level(120)
    assert lv["level"] == 2 and 0 < lv["progress"] < 100


def test_max_correct_run():
    assert streaks.max_correct_run([True, True, False, True, True, True]) == 3
    assert streaks.max_correct_run([]) == 0
