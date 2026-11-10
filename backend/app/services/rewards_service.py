"""Gamification, Rewards, Streaks and Badges Service for SETU.

100% deterministic rules engine managing student XP, Zenith Coins, levels,
Asia/Kolkata calendar streaks, and canonical milestone badges.
Idempotent award operations preventing duplicate credits (Requirement 2 & 11).
"""
from __future__ import annotations

import datetime
import uuid
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session

from app.models.rewards import StudentReward, RewardEvent, Badge, StudentBadge

KOLKATA_TZ = ZoneInfo("Asia/Kolkata")

# Canonical Reward Amounts
XP_PRACTICE = 10
COINS_PRACTICE = 2
XP_DIAGNOSTIC = 50
COINS_DIAGNOSTIC = 10
XP_RESOURCE_COMPLETED = 20
COINS_RESOURCE_COMPLETED = 5
XP_DAILY_LOGIN = 10
COINS_DAILY_LOGIN = 1

CANONICAL_BADGES = [
    {
        "id": "first_step",
        "name": "First Step",
        "description": "Completed your first practice question or diagnostic test in ZENITH.",
        "category": "milestone",
        "icon_url": "/badges/first-step.svg",
        "xp_bonus": 50,
        "criteria_json": {"min_attempts": 1, "min_xp": 10},
    },
    {
        "id": "streak_3",
        "name": "Consistency Star",
        "description": "Maintained a 3-day learning streak in Asia/Kolkata timezone.",
        "category": "streak",
        "icon_url": "/badges/streak-3.svg",
        "xp_bonus": 50,
        "criteria_json": {"min_streak_days": 3},
    },
    {
        "id": "math_whiz",
        "name": "Math Whiz",
        "description": "Solved 10 practice questions correctly in CBSE Class 10 Mathematics.",
        "category": "mastery",
        "icon_url": "/badges/math-whiz.svg",
        "xp_bonus": 100,
        "criteria_json": {"min_correct_attempts": 10},
    },
    {
        "id": "chapter_master",
        "name": "Chapter Master",
        "description": "Completed all resource packages and diagnostic assessment for a chapter.",
        "category": "completion",
        "icon_url": "/badges/chapter-master.svg",
        "xp_bonus": 100,
        "criteria_json": {"completed_chapter": True},
    },
]


def ensure_canonical_badges(db: Session) -> None:
    """Idempotently ensures all 4 canonical badges exist in the database."""
    try:
        existing = {b.id: b for b in db.query(Badge).all()}
        for b_data in CANONICAL_BADGES:
            if b_data["id"] not in existing:
                badge = Badge(
                    id=b_data["id"],
                    name=b_data["name"],
                    description=b_data["description"],
                    icon_url=b_data["icon_url"],
                    category=b_data["category"],
                    criteria_json=b_data["criteria_json"],
                    xp_bonus=b_data["xp_bonus"],
                    created_at=datetime.datetime.utcnow(),
                )
                db.add(badge)
        db.flush()
    except Exception:
        db.rollback()


def calculate_level_info(total_xp: int) -> Tuple[int, int, int]:
    """Computes (level, progress_xp_in_level, xp_to_next_level).
    
    Formula: level = max(1, (total_xp // 100) + 1)
    """
    level = max(1, (total_xp // 100) + 1)
    current_level_progress_xp = total_xp % 100
    xp_to_next_level = 100 - current_level_progress_xp
    return level, current_level_progress_xp, xp_to_next_level


def get_or_create_student_reward(db: Session, student_id: uuid.UUID) -> StudentReward:
    """Retrieves student reward profile or initializes starting values."""
    reward = db.query(StudentReward).filter(StudentReward.student_id == student_id).first()
    if reward is not None:
        return reward

    reward = StudentReward(
        id=uuid.uuid4(),
        student_id=student_id,
        total_xp=0,
        zenith_coins=0,
        current_level=1,
        current_streak_days=0,
        longest_streak_days=0,
        last_active_date=None,
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow(),
    )
    db.add(reward)
    db.flush()
    return reward


def update_streak_kolkata(reward: StudentReward) -> Tuple[int, bool]:
    """Updates student streak based on calendar days in Asia/Kolkata timezone.
    
    Returns:
        (current_streak_days, is_streak_incremented)
    """
    today_kolkata = datetime.datetime.now(KOLKATA_TZ).date()
    yesterday_kolkata = today_kolkata - datetime.timedelta(days=1)

    if reward.last_active_date is None:
        reward.current_streak_days = 1
        reward.longest_streak_days = max(reward.longest_streak_days, 1)
        reward.last_active_date = today_kolkata
        return reward.current_streak_days, True

    if reward.last_active_date == today_kolkata:
        # Already active today; streak maintained
        return reward.current_streak_days, False

    if reward.last_active_date == yesterday_kolkata:
        # Consecutive day!
        reward.current_streak_days += 1
        reward.longest_streak_days = max(reward.longest_streak_days, reward.current_streak_days)
        reward.last_active_date = today_kolkata
        return reward.current_streak_days, True

    # Missed yesterday -> streak resets to 1
    reward.current_streak_days = 1
    reward.last_active_date = today_kolkata
    return reward.current_streak_days, False


def check_and_award_badges(
    db: Session,
    student_id: uuid.UUID,
    reward: StudentReward,
    extra_criteria: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Evaluates badge eligibility and awards newly unlocked badges with bonus XP."""
    ensure_canonical_badges(db)
    awarded_badges: List[Dict[str, Any]] = []

    existing_badge_ids = {
        sb.badge_id
        for sb in db.query(StudentBadge).filter(StudentBadge.student_id == student_id).all()
    }

    all_badges = {b.id: b for b in db.query(Badge).all()}
    criteria = extra_criteria or {}

    for badge_id, badge in all_badges.items():
        if badge_id in existing_badge_ids:
            continue

        eligible = False
        if badge_id == "first_step":
            if reward.total_xp >= 10 or criteria.get("completed_attempt", False):
                eligible = True
        elif badge_id == "streak_3":
            if reward.current_streak_days >= 3:
                eligible = True
        elif badge_id == "math_whiz":
            correct_count = criteria.get("correct_count", 0)
            if correct_count >= 10 or criteria.get("score_pct", 0) >= 80.0:
                eligible = True
        elif badge_id == "chapter_master":
            if criteria.get("chapter_completed", False) or criteria.get("score_pct", 0) >= 80.0:
                eligible = True

        if eligible:
            idempotency_key = f"badge:{student_id}:{badge_id}"
            sb = StudentBadge(
                id=uuid.uuid4(),
                student_id=student_id,
                badge_id=badge_id,
                awarded_at=datetime.datetime.utcnow(),
                idempotency_key=idempotency_key,
            )
            db.add(sb)

            # Award bonus XP for unlocking badge
            reward.total_xp += badge.xp_bonus
            reward.zenith_coins += 5  # Bonus coins
            awarded_badges.append({
                "id": badge.id,
                "name": badge.name,
                "description": badge.description,
                "iconUrl": badge.icon_url,
                "xpBonus": badge.xp_bonus,
            })

    if awarded_badges:
        lvl, _, _ = calculate_level_info(reward.total_xp)
        reward.current_level = lvl
        db.flush()

    return awarded_badges


def award_activity_rewards(
    db: Session,
    student_id: uuid.UUID,
    event_type: str,
    idempotency_key: str,
    xp_amount: Optional[int] = None,
    coins_amount: Optional[int] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Idempotently awards XP and Zenith Coins to a student and updates streaks/badges.
    
    If idempotency_key has already been awarded, returns current state with awarded=0.
    """
    reward = get_or_create_student_reward(db, student_id)

    # Check idempotency
    existing_event = (
        db.query(RewardEvent)
        .filter(RewardEvent.idempotency_key == idempotency_key)
        .first()
    )
    if existing_event is not None:
        level, progress_xp, xp_needed = calculate_level_info(reward.total_xp)
        return {
            "awarded": False,
            "xpAwarded": 0,
            "coinsAwarded": 0,
            "totalXp": reward.total_xp,
            "coins": reward.zenith_coins,
            "zenithCoins": reward.zenith_coins,
            "currentLevel": level,
            "currentStreak": reward.current_streak_days,
            "unlockedBadges": [],
        }

    # Determine reward values
    if xp_amount is None or coins_amount is None:
        if event_type == "practice":
            is_correct = (meta or {}).get("is_correct", False)
            xp_to_add = XP_PRACTICE if is_correct else 5
            coins_to_add = COINS_PRACTICE if is_correct else 1
        elif event_type == "diagnostic":
            xp_to_add = XP_DIAGNOSTIC
            coins_to_add = COINS_DIAGNOSTIC
        elif event_type == "resource_completed":
            xp_to_add = XP_RESOURCE_COMPLETED
            coins_to_add = COINS_RESOURCE_COMPLETED
        elif event_type == "daily_login":
            xp_to_add = XP_DAILY_LOGIN
            coins_to_add = COINS_DAILY_LOGIN
        else:
            xp_to_add = 10
            coins_to_add = 2
    else:
        xp_to_add = xp_amount
        coins_to_add = coins_amount

    # Apply rewards
    reward.total_xp += xp_to_add
    reward.zenith_coins += coins_to_add
    update_streak_kolkata(reward)
    level, progress_xp, xp_needed = calculate_level_info(reward.total_xp)
    reward.current_level = level
    reward.updated_at = datetime.datetime.utcnow()

    # Create immutable RewardEvent
    event = RewardEvent(
        id=uuid.uuid4(),
        student_id=student_id,
        event_type=event_type,
        xp_awarded=xp_to_add,
        coins_awarded=coins_to_add,
        idempotency_key=idempotency_key,
        meta_json=meta,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(event)
    db.flush()

    # Check for newly unlocked badges
    unlocked = check_and_award_badges(
        db=db,
        student_id=student_id,
        reward=reward,
        extra_criteria=meta,
    )

    return {
        "awarded": True,
        "xpAwarded": xp_to_add,
        "coinsAwarded": coins_to_add,
        "totalXp": reward.total_xp,
        "coins": reward.zenith_coins,
        "zenithCoins": reward.zenith_coins,
        "currentLevel": reward.current_level,
        "currentStreak": reward.current_streak_days,
        "unlockedBadges": unlocked,
    }


def get_student_rewards_summary(db: Session, student_id: uuid.UUID) -> Dict[str, Any]:
    """Generates a full gamification summary for GET /api/v1/rewards/me."""
    ensure_canonical_badges(db)
    reward = get_or_create_student_reward(db, student_id)

    today_kolkata = datetime.datetime.now(KOLKATA_TZ).date()
    yesterday_kolkata = today_kolkata - datetime.timedelta(days=1)

    streak_active_today = (reward.last_active_date == today_kolkata)
    
    # Calculate effective display streak: if student missed yesterday and hasn't studied today, display 0
    display_streak = reward.current_streak_days
    if reward.last_active_date and reward.last_active_date < yesterday_kolkata:
        display_streak = 0

    level, progress_xp, xp_needed = calculate_level_info(reward.total_xp)

    # Fetch unlocked badges
    badges_awarded = (
        db.query(StudentBadge, Badge)
        .join(Badge, StudentBadge.badge_id == Badge.id)
        .filter(StudentBadge.student_id == student_id)
        .order_by(StudentBadge.awarded_at.desc())
        .all()
    )

    badge_list = [
        {
            "id": b.id,
            "name": b.name,
            "description": b.description,
            "category": b.category,
            "iconUrl": b.icon_url,
            "awardedAt": sb.awarded_at.isoformat() if sb.awarded_at else None,
        }
        for sb, b in badges_awarded
    ]

    # Fetch recent reward events
    recent_events = (
        db.query(RewardEvent)
        .filter(RewardEvent.student_id == student_id)
        .order_by(RewardEvent.created_at.desc())
        .limit(10)
        .all()
    )

    event_list = [
        {
            "eventType": e.event_type,
            "xpAwarded": e.xp_awarded,
            "coinsAwarded": e.coins_awarded,
            "createdAt": e.created_at.isoformat() if e.created_at else None,
        }
        for e in recent_events
    ]

    return {
        "studentId": str(student_id),
        "totalXp": reward.total_xp,
        "xp": reward.total_xp,
        "coins": reward.zenith_coins,
        "zenithCoins": reward.zenith_coins,
        "currentLevel": level,
        "currentLevelProgressXp": progress_xp,
        "xpToNextLevel": xp_needed,
        "currentStreakDays": display_streak,
        "streak": display_streak,
        "longestStreakDays": reward.longest_streak_days,
        "lastActiveDate": reward.last_active_date.isoformat() if reward.last_active_date else None,
        "streakActiveToday": streak_active_today,
        "timezone": "Asia/Kolkata",
        "badges": badge_list,
        "recentEvents": event_list,
    }
