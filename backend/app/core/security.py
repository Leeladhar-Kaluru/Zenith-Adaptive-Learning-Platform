import asyncio
import base64
import hashlib
import json
import logging
import time
import uuid
from typing import Optional, Dict, Any

import httpx
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.identity import Profile

logger = logging.getLogger(__name__)

# Supabase Auth is the authority. Verifying each request with a fresh HTTPS call
# made every page load depend on an external round trip and caused intermittent
# 401s when several dashboard requests arrived together. Cache successful
# verifications briefly and collapse concurrent checks of the same token into a
# single upstream request.
_TOKEN_CACHE_TTL_SECONDS = 60.0
_TOKEN_CACHE_MAX_ENTRIES = 512
_token_cache: Dict[str, tuple[float, Dict[str, Any]]] = {}
_inflight_checks: Dict[str, asyncio.Task] = {}
_http_client: Optional[httpx.AsyncClient] = None


class AuthUpstreamError(Exception):
    """Supabase Auth could not answer; this is not proof of an invalid token."""


def _decode_claims(token: str) -> Dict[str, Any]:
    try:
        payload = token.split(".")[1]
        padded = payload + "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        return claims if isinstance(claims, dict) else {}
    except Exception:
        return {}


def _token_expiry(token: str) -> Optional[float]:
    exp = _decode_claims(token).get("exp")
    return float(exp) if isinstance(exp, (int, float)) else None


def _cache_key(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _auth_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(6.0, connect=3.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            headers={
                "apikey": settings.SUPABASE_PUBLISHABLE_KEY or settings.SUPABASE_SECRET_KEY,
            },
        )
    return _http_client


async def _fetch_supabase_user(token: str) -> Optional[Dict[str, Any]]:
    url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/user"
    headers = {"Authorization": f"Bearer {token}"}
    last_error: Optional[Exception] = None

    for attempt in range(2):
        try:
            resp = await _auth_client().get(url, headers=headers)
        except httpx.HTTPError as exc:
            last_error = exc
        else:
            if resp.status_code == 200:
                try:
                    body = resp.json()
                except ValueError as exc:
                    last_error = exc
                else:
                    return body if isinstance(body, dict) else None
            if resp.status_code in (401, 403):
                return None
            last_error = RuntimeError(f"Supabase Auth returned {resp.status_code}")
        if attempt == 0:
            await asyncio.sleep(0.15)

    raise AuthUpstreamError(str(last_error) if last_error else "Supabase Auth unavailable")


async def _fetch_and_cache(token: str, key: str) -> Optional[Dict[str, Any]]:
    try:
        user_info = await _fetch_supabase_user(token)
        if user_info:
            now = time.time()
            expires_at = _token_expiry(token)
            ttl = min(_TOKEN_CACHE_TTL_SECONDS, (expires_at - now) if expires_at else _TOKEN_CACHE_TTL_SECONDS)
            if ttl > 0:
                if len(_token_cache) >= _TOKEN_CACHE_MAX_ENTRIES:
                    for stale in [k for k, (until, _) in _token_cache.items() if until <= now]:
                        _token_cache.pop(stale, None)
                _token_cache[key] = (now + ttl, user_info)
        return user_info
    finally:
        _inflight_checks.pop(key, None)


# ---- local verification --------------------------------------------------------------------------
# Supabase signs access tokens with an asymmetric key (ES256) and publishes the public keys. Checking the signature here
# costs microseconds instead of a network round trip to Supabase on every cold instance. Anything we cannot verify locally
# (legacy tokens, keys unreachable) still goes to Supabase, which stays the authority.
_JWKS_TTL = 3600.0
_JWKS_RETRY_AFTER = 60.0
_jwks_cache: Dict[str, Any] = {"at": 0.0, "keys": {}, "tried": 0.0}


class _LocalUnavailable(Exception):
    """This token cannot be judged locally; ask Supabase."""


async def _fetch_jwks() -> Dict[str, Any]:
    resp = await _auth_client().get(f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json")
    resp.raise_for_status()
    return resp.json()


async def _signing_key(kid: str):
    import jwt
    now = time.time()
    keys = _jwks_cache["keys"]
    stale = now - _jwks_cache["at"] > _JWKS_TTL
    if (kid not in keys or stale) and now - _jwks_cache["tried"] > _JWKS_RETRY_AFTER:
        _jwks_cache["tried"] = now
        try:
            fetched = await _fetch_jwks()
            keys = {k["kid"]: jwt.algorithms.ECAlgorithm.from_jwk(json.dumps(k)) for k in fetched.get("keys", []) if k.get("kty") == "EC" and k.get("kid")}
            _jwks_cache.update(at=now, keys=keys)
        except Exception as exc:  # noqa: BLE001 - keys unreachable: fall back to the network check
            logger.warning("could not refresh Supabase signing keys: %s", exc)
    if kid not in keys:
        raise _LocalUnavailable()
    return keys[kid]


async def _verify_local(token: str) -> Optional[Dict[str, Any]]:
    """Return {"id": ...} for a valid token, None for a definitely invalid one, raise _LocalUnavailable when unsure."""
    try:
        import jwt
        header = jwt.get_unverified_header(token)
    except Exception:  # noqa: BLE001
        raise _LocalUnavailable()
    if header.get("alg") != "ES256" or not header.get("kid"):
        raise _LocalUnavailable()
    key = await _signing_key(header["kid"])
    try:
        claims = jwt.decode(token, key, algorithms=["ES256"], audience="authenticated",
                            issuer=f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1", options={"require": ["exp", "sub"]})
    except jwt.PyJWTError:
        return None
    return {"id": claims["sub"]}


async def verify_supabase_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify a Supabase Bearer token: locally when possible, else through Supabase, with a short cache and single-flight."""
    if not settings.SUPABASE_URL or not token:
        return None
    try:
        return await _verify_local(token)
    except _LocalUnavailable:
        pass

    expires_at = _token_expiry(token)
    now = time.time()
    if expires_at is not None and expires_at <= now:
        return None

    key = _cache_key(token)
    cached = _token_cache.get(key)
    if cached and cached[0] > now:
        return cached[1]
    if cached:
        _token_cache.pop(key, None)

    task = _inflight_checks.get(key)
    if task is None:
        task = asyncio.create_task(_fetch_and_cache(token, key))
        _inflight_checks[key] = task
    return await task


def dev_auth_enabled() -> bool:
    """Local development and tests only: tokens of the form `dev:<uuid>` stand in for Supabase sessions.

    Real database, real logic, real permissions. Refused in any other environment.
    """
    return settings.ZENITH_DEV_AUTH is True and settings.APP_ENV in ("local", "test")


def dev_token(user_id: uuid.UUID) -> str:
    return f"dev:{user_id}"


async def get_current_user_id(authorization: Optional[str] = Header(None)) -> uuid.UUID:
    """Resolve the authenticated user id from a Bearer token (Supabase JWT, or `dev:<uuid>` in dev/test)."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()
        if token.startswith("dev:") and dev_auth_enabled():
            try:
                return uuid.UUID(token[4:])
            except ValueError:
                pass
        else:
            try:
                user_info = await verify_supabase_token(token)
            except AuthUpstreamError:
                logger.warning("Supabase auth verification unavailable")
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                    detail="ZENITH could not verify your session right now. Please retry in a moment.",
                                    headers={"Retry-After": "2"})
            if user_info and "id" in user_info:
                try:
                    return uuid.UUID(user_info["id"])
                except ValueError:
                    pass
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Please sign in to continue.",
                        headers={"WWW-Authenticate": "Bearer"})


def get_profile(user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)) -> Profile:
    profile = db.get(Profile, user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finish creating your ZENITH profile first.")
    return profile


def require_roles(*roles: str):
    """Dependency factory: the caller must have one of the roles. Admin passes every role check."""
    def dep(profile: Profile = Depends(get_profile)) -> Profile:
        if profile.role != "admin" and profile.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this.")
        return profile
    return dep


student_only = require_roles("student")
teacher_only = require_roles("teacher")
reviewer_only = require_roles("reviewer")   # only an explicitly promoted reviewer (or admin) can approve content
