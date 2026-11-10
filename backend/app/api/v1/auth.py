from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_profile
from app.models import Profile
from app.services import accounts, teacher as teacher_svc

router = APIRouter()


def _raise(e: Exception):
    raise HTTPException(status_code=getattr(e, "status", 422), detail=str(e))


class SignupIn(BaseModel):
    email: str
    password: str
    displayName: str
    role: str = "student"
    consent: bool = False


class LoginIn(BaseModel):
    email: str
    password: str


class ProfileIn(BaseModel):
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    grade: Optional[int] = None
    boardId: Optional[str] = None
    language: Optional[str] = None
    goals: Optional[list[str]] = None
    subjects: Optional[list[str]] = None
    leagueOptOut: Optional[bool] = None
    onboardingCompleted: Optional[bool] = None
    classCode: Optional[str] = Field(None, max_length=12)


@router.post("/auth/signup")
async def signup(body: SignupIn, db: Session = Depends(get_db)):
    try:
        return await accounts.signup(db, email=body.email, password=body.password, display_name=body.displayName, role=body.role, consent=body.consent)
    except accounts.AccountError as e:
        _raise(e)


@router.post("/auth/login")
async def login(body: LoginIn, db: Session = Depends(get_db)):
    try:
        return await accounts.login(db, email=body.email, password=body.password)
    except accounts.AccountError as e:
        _raise(e)


@router.get("/profile")
def get_my_profile(p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return accounts.profile_view(db, p)


@router.put("/profile")
def put_my_profile(body: ProfileIn, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    try:
        patch = body.model_dump(exclude_unset=True)
        code = patch.pop("classCode", None)
        accounts.update_profile(db, p, patch)
        if code:
            if p.role != "student":
                raise accounts.AccountError("Only students join a class with a code.")
            teacher_svc.join(db, p, code)
        return accounts.profile_view(db, p)
    except (accounts.AccountError, teacher_svc.TeacherError) as e:
        _raise(e)
