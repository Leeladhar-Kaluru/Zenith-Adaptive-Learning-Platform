"""Every request costs database round trips; this keeps the heaviest student pages from growing back."""
import pytest
from sqlalchemy import event, select

from app.core.database import engine
from app.models import ItemConcept, Lesson
from tests.conftest import auth, make_profile
from tests.test_api import publish_all

API = "/api/v1"


@pytest.fixture()
def student(db, client, tmp_path):
    reviewer = make_profile(db, "reviewer")
    publish_all(db, tmp_path, reviewer)
    return make_profile(db, "student", grade=7)


def count_queries(client, path, headers):
    n = {"n": 0}

    def hit(*_):
        n["n"] += 1
    event.listen(engine, "before_cursor_execute", hit)
    try:
        r = client.get(path, headers=headers)
    finally:
        event.remove(engine, "before_cursor_execute", hit)
    assert r.status_code == 200 and r.json() is not None, (path, r.status_code)
    return n["n"]


@pytest.mark.parametrize("path_fn,limit", [
    (lambda db: "/today", 16),
    (lambda db: f"/library/lessons/{db.scalar(select(Lesson.id).limit(1))}", 10),
    (lambda db: f"/practice/next?concept={db.scalar(select(ItemConcept.concept_id).limit(1))}", 15),
    (lambda db: "/library/chapters?grade=7", 6),
    (lambda db: "/progress/overview", 13),
])
def test_query_budget(db, client, student, path_fn, limit):
    h = auth(student)
    path = API + path_fn(db)
    count_queries(client, path, h)                    # warm: imports, first-use caches
    got = count_queries(client, path, h)
    assert got <= limit, f"{path} used {got} queries, budget is {limit}"
