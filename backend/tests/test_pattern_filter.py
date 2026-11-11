from types import SimpleNamespace as I

from app.services.items import PATTERNS, item_pattern
from tests.conftest import auth  # noqa: F401
from tests.test_api import API, world  # noqa: F401  (the published sample content)


def test_questions_are_classified_by_how_they_are_asked():
    assert item_pattern(I(kind="numeric", stem="How many?")) == "numeric"
    assert item_pattern(I(kind="mcq", stem="Assertion (A): x. Reason (R): y.")) == "assertion"
    assert item_pattern(I(kind="mcq", stem="  Assertion (A): leading space")) == "assertion"
    assert item_pattern(I(kind="mcq", stem="Which is bigger?")) == "mcq"
    assert item_pattern(I(kind="mcq", stem="Read this. A boy...", payload={"pattern": "case"})) == "case"       # only the explicit tag makes a case-based question
    assert item_pattern(I(kind="mcq", stem="Read this. A boy...", payload={})) == "mcq"
    assert item_pattern(I(kind="match", stem="Match them")) == "other"
    assert set(PATTERNS) == {"mcq", "assertion", "numeric", "case"}


def test_practice_can_be_limited_to_one_question_type(client, world):
    h = world["h"]
    got = client.get(f"{API}/practice/next?concept=number-line&pattern=mcq", headers=h)
    assert got.status_code == 200 and got.json()["item"]["kind"] == "mcq" and not got.json().get("generated")
    none = client.get(f"{API}/practice/next?concept=number-line&pattern=assertion", headers=h)
    assert none.status_code == 409 and "assertion and reason" in none.json()["detail"].lower()
    assert client.get(f"{API}/practice/next?concept=number-line&pattern=essay", headers=h).status_code == 422
    assert client.get(f"{API}/practice/next?concept=number-line", headers=h).status_code == 200            # no filter still works
