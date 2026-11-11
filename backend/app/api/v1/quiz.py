"""1v1 class quiz routes. Every route starts from the class, so the membership check comes first."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_profile
from app.models import Profile
from app.services import quiz as svc
from app.services.classes import ClassError

router = APIRouter()


def _run(fn, *a):
    try:
        return fn(*a)
    except ClassError as e:
        raise HTTPException(e.status, str(e))


class AnswerIn(BaseModel):
    position: int
    response: dict[str, Any]


@router.post("/classes/{class_id}/quiz/join")
def join(class_id: uuid.UUID, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.join, db, p, class_id)


@router.get("/classes/{class_id}/quiz/standings")
def standings(class_id: uuid.UUID, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.standings, db, p, class_id)


@router.get("/quiz/{match_id}")
def state(match_id: uuid.UUID, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.state, db, p, match_id)


@router.post("/quiz/{match_id}/answer")
def answer(match_id: uuid.UUID, body: AnswerIn, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.answer, db, p, match_id, body.position, body.response)


@router.post("/quiz/{match_id}/leave")
def leave(match_id: uuid.UUID, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.leave, db, p, match_id)
