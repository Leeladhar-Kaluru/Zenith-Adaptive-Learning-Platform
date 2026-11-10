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


async def _call(method: str, path: str, body: dict | None = None, params: dict | None = None, admin: bool = False) -> tuple[int, dict]:
    """One call to Supabase Auth. `admin` uses the server-side secret key (never sent to the browser)."""
    url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/{path}"
    key = settings.SUPABASE_SECRET_KEY if admin else (settings.SUPABASE_PUBLISHABLE_KEY or settings.SUPABASE_SECRET_KEY)
    headers = {"apikey": key}
    if admin:
        headers["Authorization"] = f"Bearer {key}"
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.request(method, url, json=body, params=params, headers=headers)
    except httpx.HTTPError:
        raise AccountError("ZENITH could not reach the sign-in service. Try again in a moment.", 503)
    try:
        data = r.json() if r.content else {}
    except ValueError:
        data = {}
    return r.status_code, data


def _code(data: dict) -> str:
    return str(data.get("error_code") or data.get("code") or "")


def _message(data: dict) -> str:
    return str(data.get("msg") or data.get("error_description") or data.get("message") or "")


def signup_error(status: int, data: dict) -> AccountError:
    """Say what actually went wrong, instead of one vague message."""
    code, msg = _code(data), _message(data).lower()
    if code in ("user_already_exists", "email_exists") or "already" in msg and "regist" in msg:
        return AccountError("An account with this email already exists. Sign in instead.", 409)
    if code in ("email_address_invalid", "validation_failed") or "email address" in msg and "invalid" in msg:
        return AccountError("That email address was not accepted. Use a real email address, for example one that ends in @gmail.com.", 422)
    if code == "weak_password" or "password" in msg:
        return AccountError("That password is too easy to guess. Use at least 8 characters with letters and numbers, and avoid common passwords.", 422)
    if status == 429 or "rate" in code:
        return AccountError("Too many attempts. Wait a few minutes and try again.", 429)
    if status >= 500:
        return AccountError("The sign-in service had a problem. Try again in a moment.", 503)
    return AccountError("Could not create your account. Check your details and try again.", 422)


async def _login_call(email: str, password: str) -> dict:
    """Password sign-in. An account made while email confirmation was on is confirmed here, but only after the correct password was given."""
    status, data = await _call("POST", "token", {"email": email, "password": password}, {"grant_type": "password"})
    if status < 400:
        return data
    code = _code(data)
    if code == "email_not_confirmed" and settings.SUPABASE_SECRET_KEY:
        # Supabase only reports this after checking the password, so this person knows it.
        st, users = await _call("GET", "admin/users", params={"per_page": 1000}, admin=True)
        found = next((u for u in (users.get("users") or []) if (u.get("email") or "").lower() == email), None)
        if st < 400 and found:
            await _call("PUT", f"admin/users/{found['id']}", {"email_confirm": True}, admin=True)
            status, data = await _call("POST", "token", {"email": email, "password": password}, {"grant_type": "password"})
            if status < 400:
                return data
    if code in ("invalid_credentials", "invalid_grant") or status in (400, 401) and "invalid" in _message(data).lower():
        raise AccountError("Email or password is not correct.", 401)
    if status == 429 or "rate" in code:
        raise AccountError("Too many attempts. Wait a few minutes and try again.", 429)
    if status >= 500:
        raise AccountError("The sign-in service had a problem. Try again in a moment.", 503)
    raise AccountError("Could not sign you in. Check your email and password.", 401)


async def signup(db: Session, *, email: str, password: str, display_name: str, role: str, consent: bool) -> dict:
    email = email.strip().lower()
    if role not in ("student", "teacher"):
        raise AccountError("Choose student or teacher.")
    if not consent:
        raise AccountError("Please confirm the consent statement to continue.")
    if len(password) < 8 or not any(ch.isalpha() for ch in password) or not any(ch.isdigit() for ch in password):
        raise AccountError("Use a password with at least 8 characters, including a letter and a number.")
    if not display_name.strip():
        raise AccountError("Enter your name.")
    if dev_auth_enabled():
        uid, token = uuid.uuid4(), None
        if db.scalar(select(Profile.id).where(Profile.email == email)):
            raise AccountError("An account with this email already exists.", 409)
        token = dev_token(uid)
    else:
        if settings.SUPABASE_SECRET_KEY:
            # Create the account already confirmed, on the server: no confirmation email, no email rate limit. ZENITH sign-in is by password.
            status, data = await _call("POST", "admin/users", {"email": email, "password": password, "email_confirm": True}, admin=True)
            if status >= 400:
                raise signup_error(status, data)
            uid = uuid.UUID(data["id"])
            token = (await _login_call(email, password))["access_token"]
        else:
            status, data = await _call("POST", "signup", {"email": email, "password": password})
            if status >= 400:
                raise signup_error(status, data)
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
    data = await _login_call(email, password)
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
