import asyncio
import json
import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.core import security
from app.core.config import settings

KID = "test-kid"
KEY = ec.generate_private_key(ec.SECP256R1())
OTHER = ec.generate_private_key(ec.SECP256R1())
UID = str(uuid.uuid4())


def jwks():
    pub = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(KEY.public_key()))
    return {"keys": [{**pub, "kid": KID, "alg": "ES256", "use": "sig"}]}


def token(key=KEY, **over):
    claims = {"sub": UID, "aud": "authenticated", "iss": f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1", "exp": int(time.time()) + 600, **over}
    return jwt.encode(claims, key, algorithm="ES256", headers={"kid": KID})


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://example.supabase.co")
    security._jwks_cache.update(at=0.0, keys={}, tried=0.0)
    security._token_cache.clear()
    calls = {"network": 0, "jwks": 0}

    async def fetch_jwks():
        calls["jwks"] += 1
        return jwks()

    async def network(tok):
        calls["network"] += 1
        return {"id": UID}

    monkeypatch.setattr(security, "_fetch_jwks", fetch_jwks)
    monkeypatch.setattr(security, "_fetch_supabase_user", network)
    return calls


def run(t):
    return asyncio.run(security.verify_supabase_token(t))


def test_valid_token_verifies_without_network(setup):
    assert run(token()) == {"id": UID}
    assert setup["network"] == 0 and setup["jwks"] == 1
    run(token())                                    # keys are cached
    assert setup["jwks"] == 1


def test_expired_wrong_signature_and_wrong_audience_are_rejected_without_fallback(setup):
    assert run(token(exp=int(time.time()) - 10)) is None
    assert run(token(key=OTHER)) is None
    assert run(token(aud="anon")) is None
    assert run(token(iss="https://evil.example/auth/v1")) is None
    assert setup["network"] == 0                     # a definite "no" is never retried over the network


def test_falls_back_to_network_when_keys_unavailable(monkeypatch, setup):
    async def broken():
        raise RuntimeError("jwks down")
    monkeypatch.setattr(security, "_fetch_jwks", broken)
    assert run(token()) == {"id": UID}
    assert setup["network"] == 1


def test_legacy_or_unsigned_tokens_use_the_network_check(setup):
    legacy = jwt.encode({"sub": UID, "exp": int(time.time()) + 600}, "x" * 40, algorithm="HS256")
    run(legacy)
    assert setup["network"] == 1
    security._token_cache.clear()
    none_alg = "e30." + "e30" + "."                 # alg none style token
    run(none_alg)
    assert setup["network"] == 2                     # Supabase itself is the authority for anything we cannot verify
