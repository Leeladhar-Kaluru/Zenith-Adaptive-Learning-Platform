"""Sign-up and sign-in against Supabase Auth, with the network call replaced so every Supabase answer can be tried."""
import asyncio
import uuid

import pytest

from app.core.config import settings
from app.services import accounts
from tests.conftest import make_profile

UID = str(uuid.uuid4())


@pytest.fixture()
def fake(monkeypatch):
    monkeypatch.setattr(accounts, "dev_auth_enabled", lambda: False)
    monkeypatch.setattr(settings, "SUPABASE_SECRET_KEY", "secret-for-test")
    calls = []
    script = {}

    async def call(method, path, body=None, params=None, admin=False):
        calls.append((method, path, admin))
        out = script.get((method, path))
        if callable(out):
            out = out()
        if out is None:
            raise AssertionError(f"unexpected call {method} {path}")
        return out

    monkeypatch.setattr(accounts, "_call", call)
    return script, calls


def run(coro):
    return asyncio.run(coro)


def signup(db, email="new@gmail.com", password="Abcdef12"):
    return run(accounts.signup(db, email=email, password=password, display_name="Asha", role="student", consent=True))


def test_signup_creates_a_confirmed_account_on_the_server_and_signs_in(db, fake):
    script, calls = fake
    script[("POST", "admin/users")] = (200, {"id": UID})
    script[("POST", "token")] = (200, {"access_token": "tok", "user": {"id": UID}})
    out = signup(db)
    assert out["token"] == "tok" and out["profile"]["displayName"] == "Asha"
    assert ("POST", "admin/users", True) in calls and ("POST", "signup", False) not in calls   # never the email-sending path


@pytest.mark.parametrize("answer,needle,status", [
    ((422, {"error_code": "email_exists", "msg": "A user with this email address has already been registered"}), "already exists", 409),
    ((422, {"error_code": "email_address_invalid", "msg": 'Email address "x@y.z" is invalid'}), "real email address", 422),
    ((422, {"error_code": "weak_password", "msg": "Password should contain letters"}), "too easy to guess", 422),
    ((429, {"error_code": "over_email_send_rate_limit", "msg": "email rate limit exceeded"}), "Too many attempts", 429),
    ((500, {"msg": "boom"}), "had a problem", 503),
])
def test_each_signup_failure_says_what_went_wrong(db, fake, answer, needle, status):
    script, _ = fake
    script[("POST", "admin/users")] = answer
    with pytest.raises(accounts.AccountError) as e:
        signup(db)
    assert needle in str(e.value) and e.value.status == status
    assert "Email or password is not correct" not in str(e.value)


def test_signup_password_rules_are_checked_before_calling_supabase(db, fake):
    for bad in ("short1", "abcdefgh", "12345678"):
        with pytest.raises(accounts.AccountError, match="letter and a number"):
            signup(db, password=bad)


def test_login_wrong_password_is_the_only_case_that_says_not_correct(db, fake):
    script, _ = fake
    script[("POST", "token")] = (400, {"error_code": "invalid_credentials", "msg": "Invalid login credentials"})
    with pytest.raises(accounts.AccountError, match="not correct") as e:
        run(accounts.login(db, email="a@gmail.com", password="whatever1"))
    assert e.value.status == 401


def test_login_confirms_an_account_made_while_confirmation_was_on(db, fake):
    script, calls = fake
    p = make_profile(db, "student")
    answers = iter([(400, {"error_code": "email_not_confirmed", "msg": "Email not confirmed"}), (200, {"access_token": "tok", "user": {"id": str(p.id)}})])
    script[("POST", "token")] = lambda: next(answers)
    script[("GET", "admin/users")] = (200, {"users": [{"id": str(p.id), "email": "old@gmail.com"}]})
    script[("PUT", f"admin/users/{p.id}")] = (200, {})
    out = run(accounts.login(db, email="old@gmail.com", password="Abcdef12"))
    assert out["token"] == "tok"
    assert ("PUT", f"admin/users/{p.id}", True) in calls


def test_login_rate_limit_and_outage_have_their_own_messages(db, fake):
    script, _ = fake
    script[("POST", "token")] = (429, {"error_code": "over_request_rate_limit", "msg": "slow down"})
    with pytest.raises(accounts.AccountError, match="Too many attempts"):
        run(accounts.login(db, email="a@gmail.com", password="Abcdef12"))
    script[("POST", "token")] = (503, {})
    with pytest.raises(accounts.AccountError, match="had a problem"):
        run(accounts.login(db, email="a@gmail.com", password="Abcdef12"))
