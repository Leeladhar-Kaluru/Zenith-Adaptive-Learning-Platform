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


def test_practice_can_be_limited_to_one_subject_and_only_lists_subjects_with_real_questions(client, world):
    h = world["h"]
    listed = client.get(f"{API}/practice/subjects", headers=h).json()
    assert listed and all(x["questions"] > 0 for x in listed) and "maths" in [x["id"] for x in listed]
    assert client.get(f"{API}/practice/next?concept=number-line&subject=maths", headers=h).status_code == 200
    assert client.get(f"{API}/practice/next?concept=number-line&subject=nonsense", headers=h).status_code == 422
    other = next((x for x in client.get(f"{API}/library/boards").json()["subjects"] if x["id"] not in [y["id"] for y in listed]), None)
    if other:                                                       # a real subject with nothing published for this class says so plainly
        r = client.get(f"{API}/practice/next?subject={other['id']}", headers=h)
        assert r.status_code == 409 and "No" in r.json()["detail"]
