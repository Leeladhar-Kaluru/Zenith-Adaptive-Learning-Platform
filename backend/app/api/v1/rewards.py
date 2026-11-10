"""Gamification and Rewards API Router for SETU.

Exposes student XP, Zenith Coins, level progress, Asia/Kolkata calendar streaks,
and milestone badges.
"""
from __future__ import annotations

import datetime
import uuid
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.rewards import Badge, StudentBadge
from app.services import rewards_service

router = APIRouter()
KOLKATA_TZ = ZoneInfo("Asia/Kolkata")


@router.get("/me")
def get_my_rewards(
    student_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Returns gamification profile including XP, coins, streak, and badges."""
    return rewards_service.get_student_rewards_summary(db, student_id=student_id)


@router.get("/badges")
def get_all_badges(
    student_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Returns all canonical badges with unlocked status for current student."""
    rewards_service.ensure_canonical_badges(db)
    all_badges = db.query(Badge).all()
    unlocked_badges = {
        sb.badge_id: sb.awarded_at
        for sb in db.query(StudentBadge).filter(StudentBadge.student_id == student_id).all()
    }

    result = []
    for b in all_badges:
        is_unlocked = b.id in unlocked_badges
        result.append({
            "id": b.id,
            "name": b.name,
            "description": b.description,
            "category": b.category,
            "iconUrl": b.icon_url,
            "xpBonus": b.xp_bonus,
            "isUnlocked": is_unlocked,
            "awardedAt": unlocked_badges[b.id].isoformat() if is_unlocked and unlocked_badges[b.id] else None,
        })
    return {"badges": result}


@router.post("/claim-daily")
def claim_daily_bonus(
    idempotency_key_header: Optional[str] = Header(None, alias="Idempotency-Key"),
    student_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Claims daily login streak bonus (+10 XP, +1 Coin) in Asia/Kolkata timezone."""
    today_kolkata = datetime.datetime.now(KOLKATA_TZ).date().isoformat()
    idempotency_key = idempotency_key_header or f"daily:{student_id}:{today_kolkata}"

    res = rewards_service.award_activity_rewards(
        db=db,
        student_id=student_id,
        event_type="daily_login",
        idempotency_key=idempotency_key,
        xp_amount=10,
        coins_amount=1,
    )
    return {
        "success": True,
        "idempotent": not res["awarded"],
        "xp_awarded": res["xpAwarded"],
        "streak": res["currentStreak"],
        **res,
    }
