"""Grounded Socratic AI Tutor API Router for ZENITH.

Exposes conversational AI tutoring grounded in curriculum content,
with citation extraction, daily quota enforcement, and graceful degradation.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.services import tutor_service

router = APIRouter()


class TutorMessageRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    message: str
    thread_id: Optional[uuid.UUID] = Field(default=None, alias="threadId")
    chapter_slug: Optional[str] = Field(default=None, alias="chapterSlug")
    resource_key: Optional[str] = Field(default=None, alias="resourceKey")
    concept_id: Optional[str] = Field(default=None, alias="conceptId")
    simulate_provider_offline: Optional[bool] = Field(default=False, alias="simulate_provider_offline")


@router.post("/message")
async def post_tutor_message(
    req: TutorMessageRequest,
    student_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Processes student query using Socratic dialogue grounded in curriculum snippets."""
    if not req.message or not req.message.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message content cannot be empty.",
        )

    if req.simulate_provider_offline:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI provider is offline. Your learning progress is safe.",
        )

    res = await tutor_service.process_tutor_message(
        db=db,
        student_id=student_id,
        user_message=req.message.strip(),
        thread_id=req.thread_id,
        chapter_slug=req.chapter_slug,
        resource_key=req.resource_key,
        concept_id=req.concept_id,
    )
    if res.get("quotaExceeded"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily message quota reached. Great job studying today!",
        )
    return res


@router.get("/threads")
def list_threads(
    student_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Lists tutor conversation threads for the current student."""
    return tutor_service.get_student_threads(db, student_id=student_id)


@router.get("/threads/{thread_id}/messages")
def get_thread_history(
    thread_id: uuid.UUID,
    student_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Fetches full conversation message history for a specific tutor thread."""
    messages = tutor_service.get_thread_messages(db, student_id=student_id, thread_id=thread_id)
    if messages is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tutor thread not found.",
        )
    return messages
