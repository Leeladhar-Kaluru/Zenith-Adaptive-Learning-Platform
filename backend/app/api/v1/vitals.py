from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import reviewer_only
from app.models import Profile
from app.models.ops import VITAL_NAMES
from app.services import vitals

router = APIRouter()


class VitalIn(BaseModel):
    name: str = Field(pattern="^(" + "|".join(VITAL_NAMES) + ")$")
    value: float = Field(ge=0, le=600000)
    route: str = Field(min_length=1, max_length=200)


@router.post("/vitals", status_code=204)
def post_vital(body: VitalIn, db: Session = Depends(get_db)):
    """Anonymous by design: no sign-in needed and nothing about the person is stored."""
    vitals.record(db, body.name, body.value, body.route)
    return Response(status_code=204)


@router.get("/vitals/summary")
def vitals_summary(r: Profile = Depends(reviewer_only), db: Session = Depends(get_db)):
    return {"rows": vitals.summary(db)}
