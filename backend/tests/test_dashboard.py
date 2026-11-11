import uuid

from sqlalchemy import select

from app.models import Item
from tests.test_api import API, world  # noqa: F401  (the published sample content)


def answer_item(client, db, h, item, right, ms=4000):
    spec = item.answer_spec
    resp = {"choice": spec["correct"] if right else next(o["key"] for o in item.payload["options"] if o["key"] != spec["correct"])}
    r = client.post(f"{API}/evidence", json={"itemId": str(item.id), "response": resp, "hintsUsed": 0, "ms": ms, "context": "solve", "clientEventId": uuid.uuid4().hex}, headers=h)
    assert r.status_code == 200, r.text


def test_a_new_student_gets_an_honest_empty_dashboard(client, world):
    d = client.get(f"{API}/profile/dashboard", headers=world["h"]).json()
    assert d["today"]["answers"] == 0 and d["subjects"] == [] and d["focus"] == [] and d["pace"]["answers30d"] == 0 and d["pace"]["medianMsRight"] is None
    assert d["battles"]["games"] == 0 and len(d["days"]) == 14


def test_the_dashboard_numbers_come_from_the_students_own_answers(client, db, world):
    h = world["h"]
    items = [i for i in db.scalars(select(Item).where(Item.status == "published", Item.kind == "mcq").order_by(Item.key)).all()][:5]
    for n, it in enumerate(items):
        answer_item(client, db, h, it, right=n != 0, ms=1000 if n == 0 else 5000)       # one fast wrong answer (a likely guess), four right
    d = client.get(f"{API}/profile/dashboard", headers=h).json()
    assert d["today"]["answers"] == 5 and d["today"]["correct"] == 4
    assert d["pace"]["answers30d"] == 5 and d["pace"]["medianMsRight"] == 5000 and d["pace"]["medianMsWrong"] == 1000
    assert d["pace"]["guessRate"] == 0.2 and d["pace"]["hintRate"] == 0.0
    assert sum(x["total"] for x in d["pace"]["byDifficulty"]) == 5 and sum(x["right"] for x in d["pace"]["byDifficulty"]) == 4
    assert d["subjects"] and d["subjects"][0]["answers"] >= 5 and 0 <= d["subjects"][0]["understanding"] <= 1
    assert sum(x["answers"] for x in d["days"]) == 5
    other = client.get(f"{API}/profile/dashboard", headers=__import__("tests.conftest", fromlist=["x"]).auth(world["reviewer"]))
    assert other.status_code in (401, 403)                                                 # only students have a learner dashboard
