"""My Classes: the student's view of each class they joined, plus teacher announcements. Every route checks membership."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_profile
from app.models import Profile
from app.services import classes as svc

router = APIRouter()


def _run(fn, *a, **k):
    try:
        return fn(*a, **k)
    except svc.ClassError as e:
        raise HTTPException(e.status, str(e))


class AnnouncementIn(BaseModel):
    # Length and blank checks happen after tags are stripped, so "<b></b>" cannot sneak through as a title.
    title: str
    body: str
    pinned: bool = False


class PinIn(BaseModel):
    pinned: bool


@router.get("/classes")
def my_classes(p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    if p.role != "student":
        raise HTTPException(403, "My Classes is for students. Teachers use the teacher workspace.")
    return svc.listing(db, p)


@router.get("/classes/{class_id}")
def open_class(class_id: uuid.UUID, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.detail, db, p, class_id)


@router.delete("/classes/{class_id}/membership")
def leave_class(class_id: uuid.UUID, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.leave, db, p, class_id)


@router.post("/classes/{class_id}/announcements")
def post_announcement(class_id: uuid.UUID, body: AnnouncementIn, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.announce, db, p, class_id, body.title, body.body, body.pinned)


@router.put("/classes/{class_id}/announcements/{ann_id}/pin")
def pin_announcement(class_id: uuid.UUID, ann_id: uuid.UUID, body: PinIn, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.pin, db, p, class_id, ann_id, body.pinned)


@router.delete("/classes/{class_id}/announcements/{ann_id}")
def delete_announcement(class_id: uuid.UUID, ann_id: uuid.UUID, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.remove, db, p, class_id, ann_id)
