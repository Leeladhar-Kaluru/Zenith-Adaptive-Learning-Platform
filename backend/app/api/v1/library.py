"""Curriculum Library API Router for ZENITH.

Exposes catalogue, chapter details, sanitized resource packages,
interactive concept DAG maps, student enrollment, and progress tracking.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.services import library_service

router = APIRouter()


async def get_optional_user_id(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
) -> Optional[uuid.UUID]:
    """Resolves authenticated user ID if present; otherwise returns None."""
    try:
        return await get_current_user_id(authorization=authorization, x_user_id=x_user_id)
    except Exception:
        return None


class EnrollRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    chapter_slug: str = Field(alias="chapterSlug")


class ProgressUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    path_lesson_id: str = Field(alias="pathLessonId")
    status: str = Field(default="completed")
    completion_pct: float = Field(default=100.0, alias="completionPct")
    time_spent_seconds: int = Field(default=0, alias="timeSpentSeconds")
    last_position: Optional[Dict[str, Any]] = Field(default=None, alias="lastPosition")


@router.get("/catalogue")
def get_library_catalogue(
    grade: int = 10,
    subject_id: str = "subject-math",
    user_id: Optional[uuid.UUID] = Depends(get_optional_user_id),
    db: Session = Depends(get_db),
):
    """Returns curriculum library chapters with concepts and resource counts."""
    return library_service.get_catalogue(db, grade=grade, subject_id=subject_id, user_id=user_id)


@router.get("/chapters/{slug}")
def get_chapter_detail(
    slug: str,
    user_id: Optional[uuid.UUID] = Depends(get_optional_user_id),
    db: Session = Depends(get_db),
):
    """Returns full details for a chapter including syllabus concepts and resources."""
    chapter = library_service.get_chapter(db, slug, user_id=user_id)
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chapter '{slug}' not found in curriculum library.",
        )
    return chapter


@router.get("/resources/{resource_id}")
def get_resource_package(
    resource_id: str,
    user_id: Optional[uuid.UUID] = Depends(get_optional_user_id),
    db: Session = Depends(get_db),
):
    """Returns educational resource package with student question redaction."""
    resource = library_service.get_resource(db, resource_id=resource_id, student_id=user_id)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource '{resource_id}' not found.",
        )
    return resource


@router.get("/map/{slug}")
def get_concept_dag_map(
    slug: str,
    user_id: Optional[uuid.UUID] = Depends(get_optional_user_id),
    db: Session = Depends(get_db),
):
    """Returns DAG concepts and directed prerequisite edges for SVG map rendering."""
    return library_service.get_concept_map(db, chapter_slug=slug, student_id=user_id)


@router.post("/enroll")
def enroll_chapter(
    req: EnrollRequest,
    student_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Enrolls the student into a published curriculum chapter."""
    return library_service.enroll_student(db, student_id=student_id, chapter_slug=req.chapter_slug)


@router.get("/my")
def get_my_learning(
    student_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Returns active enrollments and chapter progress counts for current student."""
    return library_service.get_student_learning(db, student_id=student_id)


@router.post("/progress")
def update_progress(
    req: ProgressUpdateRequest,
    student_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Updates progress on a lesson resource, awarding XP and coins upon completion."""
    res = library_service.update_resource_progress(
        db=db,
        student_id=student_id,
        path_lesson_id=req.path_lesson_id,
        status=req.status,
        completion_pct=req.completion_pct,
        time_spent_seconds=req.time_spent_seconds,
        last_position=req.last_position,
    )
    if res is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource '{req.path_lesson_id}' not found or unauthorized.",
        )
    return res
