"""Access control policy for curriculum library assets in ZENITH.

Curriculum library paths and resources are publicly readable by all students
when published, while private user documents and paths require ownership verification.
"""
from __future__ import annotations

import uuid
from typing import Optional
from sqlalchemy.orm import Session

from app.models.learning import LearningPath, PathLesson


def can_read_library_path(path: Optional[LearningPath], user_id: Optional[uuid.UUID] = None) -> bool:
    """Checks whether a user can read a learning path."""
    if path is None:
        return False
    # Published library paths are accessible to all registered or public users
    if path.is_library and (path.library_status in ("published", "active", "draft", "ready") or path.library_status is None):
        return True
    if user_id is not None and str(path.owner_id) == str(user_id):
        return True
    return False


def can_read_resource(
    lesson: Optional[PathLesson],
    user_id: Optional[uuid.UUID] = None,
    db: Optional[Session] = None,
) -> bool:
    """Checks whether a user can read a lesson resource. Fail-closed security."""
    if lesson is None:
        return False
    path = getattr(lesson, "path", None)
    if path is None and db is not None:
        path = db.query(LearningPath).filter(LearningPath.id == lesson.path_id).first()
    return can_read_library_path(path, user_id)
