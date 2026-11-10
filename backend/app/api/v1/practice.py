"""Adaptive Practice Arena API Router for SETU.

Exposes smart concept recommendations, question serving with safe student redaction,
and deterministic attempt submission grading with BKT and rewards updates.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.services import practice_service

router = APIRouter()


class PracticeSessionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    chapter_slug: str = Field(alias="chapterSlug")
    concept_id: Optional[str] = Field(default=None, alias="conceptId")
    count: int = Field(default=5, ge=1, le=20)


class PracticeSubmitRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question_id: str = Field(alias="questionId")
    concept_id: str = Field(alias="conceptId")
    response: Any
    hint_level: int = Field(default=0, ge=0, le=10, alias="hintLevel")
    hints_used: Optional[List[str]] = Field(default=None, alias="hintsUsed")
    elapsed_seconds: int = Field(default=0, ge=0, le=3600, alias="elapsedSeconds")
    sync_idempotency_key: Optional[str] = Field(default=None, alias="syncIdempotencyKey")

    @field_validator("hints_used", mode="before")
    @classmethod
    def coerce_hints_used(cls, v: Any) -> Optional[List[str]]:
        if v is None:
            return None
        if isinstance(v, list):
            return [str(x) for x in v]
        if isinstance(v, int):
            return [f"hint_{i + 1}" for i in range(v)] if v > 0 else []
        if isinstance(v, str):
            return [v]
        return []


@router.get("/recommendation")
def get_recommendation(
    chapter_slug: str = Query(..., alias="chapter_slug"),
    student_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Recommends weakest gap or lowest mastery concept for practice."""
    return practice_service.get_practice_recommendation(
        db=db,
        student_id=student_id,
        chapter_slug=chapter_slug,
    )


@router.post("/session")
def create_practice_session(
    req: PracticeSessionRequest,
    student_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Draws calibrated, redacted practice questions for a student session."""
    questions = practice_service.get_practice_questions(
        db=db,
        student_id=student_id,
        chapter_slug=req.chapter_slug,
        concept_id=req.concept_id,
        count=req.count,
    )
    return {
        "chapterSlug": req.chapter_slug,
        "conceptId": req.concept_id,
        "totalQuestions": len(questions),
        "questions": questions,
    }


@router.post("/submit")
def submit_practice_attempt(
    req: PracticeSubmitRequest,
    student_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Grades attempt, updates BKT probability, awards rewards, and returns feedback."""
    return practice_service.submit_practice_attempt(
        db=db,
        student_id=student_id,
        question_id=req.question_id,
        concept_id=req.concept_id,
        response=req.response,
        hint_level=req.hint_level,
        hints_used=req.hints_used,
        elapsed_seconds=req.elapsed_seconds,
        sync_idempotency_key=req.sync_idempotency_key,
    )
