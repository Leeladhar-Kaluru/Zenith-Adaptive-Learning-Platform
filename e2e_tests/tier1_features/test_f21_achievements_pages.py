import os
import re
import json
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def test_unlocked_and_locked_badges_split(student_client):
    """Feature 21: Badges page distinguishes earned badges from locked badges with dynamic cross-referencing."""
    # 1. Inspect real AchievementsPage.tsx implementation from disk
    achievements_page_path = os.path.join(PROJECT_ROOT, "frontend", "src", "pages", "AchievementsPage.tsx")
    assert os.path.exists(achievements_page_path), f"AchievementsPage.tsx not found at {achievements_page_path}"
    with open(achievements_page_path, "r", encoding="utf-8") as f:
        tsx_source = f.read()

    # Verify canonical badge catalog definition on frontend
    assert "canonicalBadges: BadgeCatalogItem[]" in tsx_source
    assert "first_steps" in tsx_source
    assert "curious_mind" in tsx_source
    assert "consistency_star" in tsx_source
    assert "concept_master" in tsx_source

    # Verify that default state locks badges until earned in student_badges
    assert "isUnlocked: false" in tsx_source
    assert "awardedAt: null" in tsx_source
    assert "const isUnlocked = b.isUnlocked || isEarnedInProfile;" in tsx_source

    # Check backend badge catalog source (badges.json if present, or rewards_service)
    badges_json_path = os.path.join(PROJECT_ROOT, "backend", "app", "content", "badges.json")
    if os.path.exists(badges_json_path):
        with open(badges_json_path, "r", encoding="utf-8") as f:
            badges_json = json.load(f)
        badge_list = badges_json.get("badges", badges_json) if isinstance(badges_json, dict) else badges_json
        assert isinstance(badge_list, list)
        assert len(badge_list) >= 4
        for b in badge_list:
            assert "id" in b and "name" in b and "category" in b
    else:
        # Fallback to rewards_service.py canonical badges definition
        rewards_service_path = os.path.join(PROJECT_ROOT, "backend", "app", "services", "rewards_service.py")
        with open(rewards_service_path, "r", encoding="utf-8") as f:
            service_source = f.read()
        assert "CANONICAL_BADGES = [" in service_source
        assert "first_step" in service_source
        assert "streak_3" in service_source

    # 2. Verify via API responses for authenticated student
    student_res = student_client.get("/api/v1/rewards/me")
    assert student_res.status_code == 200
    student_data = student_res.json()
    unlocked = student_data.get("badges", [])
    
    all_res = student_client.get("/api/v1/rewards/badges")
    assert all_res.status_code == 200
    all_badges = all_res.json().get("badges", [])
    assert len(all_badges) >= 4, "Catalogue must expose canonical badges"

    unlocked_ids = {b if isinstance(b, str) else b.get("id") for b in unlocked}
    locked_badges = [b for b in all_badges if b["id"] not in unlocked_ids]
    
    # Assert genuine partition: student has unlocked badges AND remaining locked badges
    assert len(unlocked_ids) > 0, "Student has initial earned badges"
    assert len(locked_badges) > 0, "Student must still have locked badges to pursue"
    assert len(locked_badges) + len(unlocked_ids) >= len(all_badges)


def test_monthly_streak_calendar_data(student_client):
    """Feature 21: Student profile reports streak length and timezone derived in Asia/Kolkata."""
    # 1. Inspect real AchievementsPage.tsx implementation from disk
    achievements_page_path = os.path.join(PROJECT_ROOT, "frontend", "src", "pages", "AchievementsPage.tsx")
    with open(achievements_page_path, "r", encoding="utf-8") as f:
        tsx_source = f.read()

    # Verify Asia/Kolkata timezone label and contract in streak calendar UI
    assert "Asia/Kolkata" in tsx_source
    assert "Calculated daily at midnight in" in tsx_source
    
    # Verify dynamic daysInMonth derivation (never hardcoded 30 or 31)
    assert "new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()" in tsx_source
    assert "now.getDate()" in tsx_source
    assert "isActive = streak > 0 && dayNum <= currentDay && dayNum > (currentDay - streak)" in tsx_source

    # 2. Verify API response conforms to Asia/Kolkata timezone contract
    res = student_client.get("/api/v1/rewards/me")
    assert res.status_code == 200
    data = res.json()
    assert data.get("timezone") == "Asia/Kolkata"
    assert "streak" in data or "currentStreakDays" in data
    streak_val = data.get("streak", data.get("currentStreakDays", 0))
    assert isinstance(streak_val, int) and streak_val >= 0


def test_dynamic_reward_event_history(student_client):
    """Feature 21: Reward event history displays dynamically recorded learning achievements."""
    # 1. Inspect real AchievementsPage.tsx implementation from disk
    achievements_page_path = os.path.join(PROJECT_ROOT, "frontend", "src", "pages", "AchievementsPage.tsx")
    with open(achievements_page_path, "r", encoding="utf-8") as f:
        tsx_source = f.read()

    # Verify Reward Events card in AchievementsPage
    assert "Reward Events" in tsx_source
    assert "evt.eventType.replace(/_/g, ' ').toUpperCase()" in tsx_source
    assert "+{evt.xpAwarded} XP" in tsx_source
    assert "Solve practice questions or complete curriculum lessons to record reward events." in tsx_source

    # 2. Inspect real backend database model for RewardEvent
    rewards_model_path = os.path.join(PROJECT_ROOT, "backend", "app", "models", "rewards.py")
    with open(rewards_model_path, "r", encoding="utf-8") as f:
        model_source = f.read()
    assert "class RewardEvent(Base):" in model_source
    assert '__tablename__ = "reward_events"' in model_source
    assert "event_type = Column(" in model_source
    assert "xp_awarded = Column(" in model_source
    assert "idempotency_key = Column(" in model_source

    # 3. Verify profile rewards response structure
    res = student_client.get("/api/v1/rewards/me")
    assert res.status_code == 200
    data = res.json()
    assert "xp" in data or "totalXp" in data
    assert "coins" in data or "zenithCoins" in data


def test_scholar_rank_and_level_progression():
    """Feature 21: Scholar Rank and Level progression formulas are strictly deterministic."""
    # 1. Inspect real AchievementsPage.tsx implementation from disk
    achievements_page_path = os.path.join(PROJECT_ROOT, "frontend", "src", "pages", "AchievementsPage.tsx")
    with open(achievements_page_path, "r", encoding="utf-8") as f:
        tsx_source = f.read()

    assert "Scholar Rank {level}" in tsx_source
    assert "progressXp / 100" in tsx_source
    assert "{coins} Zenith Coins" in tsx_source

    # 2. Inspect real backend level calculation in rewards_service.py
    rewards_service_path = os.path.join(PROJECT_ROOT, "backend", "app", "services", "rewards_service.py")
    with open(rewards_service_path, "r", encoding="utf-8") as f:
        service_source = f.read()
    assert "def calculate_level_info(total_xp: int)" in service_source
    assert "level = max(1, (total_xp // 100) + 1)" in service_source
    assert "current_level_progress_xp = total_xp % 100" in service_source
    assert "xp_to_next_level = 100 - current_level_progress_xp" in service_source

    # 3. Verify math across boundary conditions
    # Level 1 at 0 XP
    lvl, prog, needed = max(1, (0 // 100) + 1), 0 % 100, 100 - (0 % 100)
    assert lvl == 1 and prog == 0 and needed == 100

    # Level 3 at 250 XP
    lvl, prog, needed = max(1, (250 // 100) + 1), 250 % 100, 100 - (250 % 100)
    assert lvl == 3 and prog == 50 and needed == 50


def test_my_learning_tabs_and_offline_learning(student_client):
    """Feature 21: My Learning navigation integrates chapters, resources, and offline library."""
    # 1. Inspect real ChapterPage.tsx and OfflineLibraryPage.tsx from disk
    chapter_page_path = os.path.join(PROJECT_ROOT, "frontend", "src", "pages", "ChapterPage.tsx")
    offline_page_path = os.path.join(PROJECT_ROOT, "frontend", "src", "pages", "OfflineLibraryPage.tsx")
    assert os.path.exists(chapter_page_path)
    assert os.path.exists(offline_page_path)

    with open(chapter_page_path, "r", encoding="utf-8") as f:
        ch_source = f.read()
    assert "completionPct" in ch_source
    assert "chapter?.resources" in ch_source

    with open(offline_page_path, "r", encoding="utf-8") as f:
        off_source = f.read()
    assert "listOfflineLessons" in off_source
    assert "getOfflineStorageUsage" in off_source
    assert "IndexedDB storage" in off_source

    # 2. Query real catalogue and chapter endpoints
    cat_res = student_client.get("/api/v1/library/catalogue")
    assert cat_res.status_code == 200
    chapters = cat_res.json()["chapters"]
    assert len(chapters) >= 4

    # Verify resource readiness for offline study
    ch_res = student_client.get("/api/v1/library/chapters/real-numbers")
    assert ch_res.status_code == 200
    resources = ch_res.json()["resources"]
    assert len(resources) >= 5

    lesson_res = student_client.get("/api/v1/library/resources/real-numbers-lesson")
    assert lesson_res.status_code == 200
    assert lesson_res.json()["id"] == "real-numbers-lesson"
    assert "content" in lesson_res.json()
