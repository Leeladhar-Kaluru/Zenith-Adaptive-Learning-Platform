"""Read-only access to a student's existing learning paths.

Path creation from uploaded documents was removed with the document stack.
The curriculum Learn library replaces it; these endpoints keep previously
created paths readable until the legacy data is archived.
"""
import copy
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.learning import LearningPath, PathLesson, LessonVersion
from app.services.text_sanitize import sanitize_tree

router = APIRouter()


def _redact_answer_keys(package: dict) -> dict:
    sanitized = copy.deepcopy(package)
    for section in ("practice", "checkpointTest"):
        for question in sanitized.get(section, []) or []:
            question.pop("answerKey", None)
    return sanitized


@router.get("")
def list_learning_paths(
    owner_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    paths = (
        db.query(LearningPath)
        .filter(
            LearningPath.owner_id == owner_id,
            LearningPath.status != "archived",
        )
        .order_by(LearningPath.created_at.desc())
        .all()
    )
    results = []
    for p in paths:
        lessons = db.query(PathLesson).filter(PathLesson.path_id == p.id).order_by(PathLesson.sequence.asc()).all()
        ready_count = sum(1 for l in lessons if l.status == "ready")
        first_l = lessons[0] if lessons else None
        results.append({
            "id": str(p.id),
            "title": p.outline_json.get("title", f"Class {p.grade} {p.subject_id}"),
            "grade": p.grade,
            "subjectId": p.subject_id,
            "status": p.status,
            "totalLessons": len(lessons),
            "readyLessons": ready_count,
            "progressPercent": int(round(100 * ready_count / len(lessons))) if lessons else 0,
            "firstLessonId": str(first_l.id) if first_l else None,
            "lessons": [
                {
                    "id": str(lesson.id),
                    "title": lesson.title,
                    "status": lesson.status,
                    "sequence": lesson.sequence,
                }
                for lesson in lessons
            ],
            "createdAt": p.created_at.isoformat()
        })
    return results

@router.get("/{path_id}")
def get_learning_path_detail(
    path_id: uuid.UUID,
    owner_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    path = db.query(LearningPath).filter(LearningPath.id == path_id, LearningPath.owner_id == owner_id).first()
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")

    lessons = db.query(PathLesson).filter(PathLesson.path_id == path.id).order_by(PathLesson.sequence.asc()).all()
    return {
        "id": str(path.id),
        "title": path.outline_json.get("title", f"Class {path.grade} {path.subject_id}"),
        "grade": path.grade,
        "subjectId": path.subject_id,
        "goal": path.goal,
        "outline": path.outline_json,
        "status": path.status,
        "lessons": [
            {
                "id": str(l.id),
                "sequence": l.sequence,
                "lessonKey": l.lesson_key,
                "title": l.title,
                "status": l.status
            }
            for l in lessons
        ]
    }

@router.get("/lessons/{lesson_id}")
def get_lesson_package(
    lesson_id: str,
    pathId: Optional[str] = None,
    owner_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns full lesson package JSON. Supports lookup by UUID or lesson_key.
    Only the learning path owner can read the lesson; any other caller gets 404
    so the response never confirms that the lesson exists.
    """
    lesson = None
    try:
        l_uuid = uuid.UUID(lesson_id)
        lesson = (
            db.query(PathLesson)
            .join(LearningPath, LearningPath.id == PathLesson.path_id)
            .filter(PathLesson.id == l_uuid, LearningPath.owner_id == owner_id)
            .first()
        )
    except Exception:
        # Lookup by lesson_key
        q = (
            db.query(PathLesson)
            .join(LearningPath, LearningPath.id == PathLesson.path_id)
            .filter(PathLesson.lesson_key == lesson_id, LearningPath.owner_id == owner_id)
        )
        if pathId:
            try:
                p_uuid = uuid.UUID(pathId)
                q = q.filter(PathLesson.path_id == p_uuid)
            except Exception:
                pass
        lesson = q.first()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    version = db.query(LessonVersion).filter(LessonVersion.path_lesson_id == lesson.id).order_by(LessonVersion.version_number.desc()).first()
    if not version or not version.lesson_package_json:
        raise HTTPException(status_code=404, detail="Lesson package content not ready")

    package = _redact_answer_keys(dict(version.lesson_package_json))
    # Existing packages were generated before the plain-text policy; sanitize
    # LaTeX/markdown artifacts at read time so stored lessons render cleanly.
    package = sanitize_tree(package)
    package["lessonVersionId"] = str(version.id)
    return package
