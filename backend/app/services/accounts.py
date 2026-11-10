"""Sign-up, sign-in and profile. Supabase Auth is the identity authority; dev auth is local/test only."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import dev_auth_enabled, dev_token
from app.models import Board, ConsentEvent, Profile, Subject

AVATARS = {"fox", "panda", "owl", "turtle", "rocket", "cat", "bear", "rabbit", "penguin", "lion", "whale", "robot"}
GOALS = {"concept_mastery", "board_exam_prep", "homework_help", "fast_track", "fill_gaps"}


class AccountError(ValueError):
    def __init__(self, msg: str, status: int = 422):
        super().__init__(msg)
        self.status = status


def profile_view(db: Session, p: Profile) -> dict:
    from app.models import ClassMember
    classes = [str(c) for (c,) in db.execute(select(ClassMember.classroom_id).where(ClassMember.student_id == p.id, ClassMember.status == "active"))]
    return {"id": str(p.id), "displayName": p.display_name, "nickname": p.nickname or "", "avatar": p.avatar or "fox", "role": p.role, "grade": p.grade,
            "boardId": p.board_id, "language": p.language, "goals": p.goals or [], "subjects": p.subjects or [], "onboardingCompleted": p.onboarding_completed,
            "consentStatus": p.consent_status, "classroomIds": classes, "leagueOptOut": p.league_opt_out}


async def _supabase(path: str, body: dict, params: dict | None = None) -> dict:
    url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/{path}"
    key = settings.SUPABASE_PUBLISHABLE_KEY or settings.SUPABASE_SECRET_KEY
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(url, json=body, params=params, headers={"apikey": key})
    except httpx.HTTPError:
        raise AccountError("ZENITH could not reach the sign-in service. Try again in a moment.", 503)
    data = r.json() if r.content else {}
    if r.status_code >= 400:
        msg = data.get("msg") or data.get("error_description") or data.get("message") or "Sign-in failed."
        raise AccountError("Email or password is not correct." if r.status_code in (400, 401) and "invalid" in msg.lower() else msg, 400 if r.status_code < 500 else 503)
    return data


async def signup(db: Session, *, email: str, password: str, display_name: str, role: str, consent: bool) -> dict:
    email = email.strip().lower()
    if role not in ("student", "teacher"):
        raise AccountError("Choose student or teacher.")
    if not consent:
        raise AccountError("Please confirm the consent statement to continue.")
    if len(password) < 8:
        raise AccountError("Use a password with at least 8 characters.")
    if not display_name.strip():
        raise AccountError("Enter your name.")
    if dev_auth_enabled():
        uid, token = uuid.uuid4(), None
        if db.scalar(select(Profile.id).where(Profile.email == email)):
            raise AccountError("An account with this email already exists.", 409)
        token = dev_token(uid)
    else:
        data = await _supabase("signup", {"email": email, "password": password})
        user = data.get("user") or data
        uid = uuid.UUID(user["id"])
        token = data.get("access_token")
    p = db.get(Profile, uid) or Profile(id=uid, email=email, role=role, display_name=display_name.strip()[:120], language="en", consent_status="granted",
                                        consent_at=datetime.now(timezone.utc), board_id=db.scalar(select(Board.id).where(Board.active.is_(True)).order_by(Board.id).limit(1)))
    db.add(p)
    db.flush()
    db.add(ConsentEvent(student_id=uid, status="granted", method="self_declared"))
    db.commit()
    if not token:
        return {"needsEmailConfirmation": True}
    return {"token": token, "profile": profile_view(db, p)}


async def login(db: Session, *, email: str, password: str) -> dict:
    email = email.strip().lower()
    if dev_auth_enabled():
        p = db.scalar(select(Profile).where(Profile.email == email))
        if p is None:
            raise AccountError("Email or password is not correct.", 401)
        return {"token": dev_token(p.id), "profile": profile_view(db, p)}
    data = await _supabase("token", {"email": email, "password": password}, {"grant_type": "password"})
    uid = uuid.UUID(data["user"]["id"])
    p = db.get(Profile, uid)
    if p is None:
        raise AccountError("Finish creating your ZENITH profile first. Sign up with this email.", 403)
    return {"token": data["access_token"], "profile": profile_view(db, p)}


def update_profile(db: Session, p: Profile, patch: dict) -> Profile:
    if "nickname" in patch and patch["nickname"] is not None:
        n = str(patch["nickname"]).strip()
        if not 2 <= len(n) <= 16:
            raise AccountError("Nickname must be 2 to 16 characters.")
        p.nickname = n
    if "avatar" in patch and patch["avatar"] is not None:
        if patch["avatar"] not in AVATARS:
            raise AccountError("Choose a character from the list.")
        p.avatar = patch["avatar"]
    if "grade" in patch and patch["grade"] is not None:
        if p.role == "student" and not 6 <= int(patch["grade"]) <= 10:
            raise AccountError("Class must be between 6 and 10.")
        p.grade = int(patch["grade"]) if p.role == "student" else None
    if patch.get("boardId"):
        b = db.get(Board, patch["boardId"])
        if b is None or not b.active:
            raise AccountError("Choose a board from the list.")
        p.board_id = b.id
    if patch.get("language"):
        if patch["language"] not in ("en", "hi", "te"):
            raise AccountError("Choose English, Hindi or Telugu.")
        p.language = patch["language"]
    if patch.get("goals") is not None:
        if any(g not in GOALS for g in patch["goals"]):
            raise AccountError("Unknown learning goal.")
        p.goals = list(patch["goals"])[:5]
    if patch.get("subjects") is not None:
        known = {s for (s,) in db.execute(select(Subject.id))}
        if any(s not in known for s in patch["subjects"]):
            raise AccountError("Unknown subject.")
        p.subjects = list(patch["subjects"])
    if patch.get("leagueOptOut") is not None:
        p.league_opt_out = bool(patch["leagueOptOut"])
    if patch.get("onboardingCompleted"):
        if not p.nickname:
            raise AccountError("Choose a nickname first.")
        if p.role == "student" and not p.grade:
            raise AccountError("Choose your class first.")
        p.onboarding_completed = True
    db.commit()
    return p
