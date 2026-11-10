"""Diagnostic Assessment API Router for ZENITH.

Exposes 8-probe diagnostic sessions, submission grading,
BKT mastery updates, prerequisite gap synthesis, and completion rewards.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.services import diagnostic_service

router = APIRouter()


class DiagnosticSessionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    chapter_slug: str = Field(alias="chapterSlug")


class DiagnosticItemResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    item_index: Optional[int] = Field(default=None, alias="itemIndex")
    item_id: Optional[str] = Field(default=None, alias="itemId")
    student_response: Optional[Any] = Field(default=None, alias="studentResponse")
    is_correct: Optional[bool] = Field(default=None, alias="isCorrect")
    hints_used: int = Field(default=0, alias="hintsUsed")


class DiagnosticSubmitRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    session_id: uuid.UUID = Field(alias="sessionId")
    responses: List[DiagnosticItemResponse]


@router.post("/session", status_code=status.HTTP_201_CREATED)
def start_diagnostic_session(
    req: DiagnosticSessionRequest,
    student_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Initializes or resumes an 8-probe diagnostic sitting with redacted questions."""
    if not req.chapter_slug or not req.chapter_slug.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Chapter slug is required.",
        )
    try:
        return diagnostic_service.create_diagnostic_session(
            db=db,
            student_id=student_id,
            chapter_slug=req.chapter_slug.strip(),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get("/session/{session_id}")
def get_session_status(
    session_id: uuid.UUID,
    student_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Fetches details and progress of a diagnostic session."""
    session_data = diagnostic_service.get_diagnostic_session(db, session_id=session_id)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnostic session not found.",
        )
    return session_data


@router.post("/submit")
def submit_diagnostic(
    req: DiagnosticSubmitRequest,
    student_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Evaluates diagnostic responses, updates BKT, synthesizes gap analysis, and awards rewards."""
    try:
        resp_dicts = [
            {
                "itemIndex": r.item_index,
                "item_index": r.item_index,
                "itemId": r.item_id,
                "item_id": r.item_id,
                "studentResponse": r.student_response,
                "is_correct": r.is_correct,
                "hintsUsed": r.hints_used,
            }
            for r in req.responses
        ]
        return diagnostic_service.submit_diagnostic_responses(
            db=db,
            student_id=student_id,
            session_id=req.session_id,
            responses=resp_dicts,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
