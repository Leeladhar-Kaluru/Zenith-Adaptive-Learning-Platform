"""My Classes: the student's view of each class they joined, plus teacher announcements. Every route checks membership."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_profile
from app.models import Profile
from app.services import chatfiles
from app.services import classes as svc
from app.services import resources as res_svc

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


class LinkIn(BaseModel):
    title: str
    url: str
    note: str = ""


@router.post("/classes/{class_id}/resources/link")
def add_link(class_id: uuid.UUID, body: LinkIn, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(res_svc.add_link, db, p, class_id, body.title, body.url, body.note)


@router.post("/classes/{class_id}/resources/upload")
async def add_file(class_id: uuid.UUID, request: Request, name: str = Query("file", max_length=120), title: str = Query("", max_length=200), note: str = Query("", max_length=600),
                   p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    """The file is the request body (no multipart). Ownership and size are checked before the body is read."""
    _run(svc.owner_only, db, p, class_id)
    try:
        declared = int(request.headers.get("content-length", "0"))
    except ValueError:
        declared = 0
    if declared > chatfiles.MAX_BYTES:
        raise HTTPException(413, "That file is too big. The limit is 4 MB.")
    return _run(res_svc.add_file, db, p, class_id, name, await request.body(), title, note)


@router.get("/classes/{class_id}/resources/{rid}/file")
def resource_file(class_id: uuid.UUID, rid: uuid.UUID, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(res_svc.file_link, db, p, class_id, rid)


@router.delete("/classes/{class_id}/resources/{rid}")
def delete_resource(class_id: uuid.UUID, rid: uuid.UUID, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(res_svc.remove, db, p, class_id, rid)
