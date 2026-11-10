"""Per-request memo: load shared data once per request, never across requests or commits.

The memo lives on the SQLAlchemy session (one session per request), and is dropped on commit or rollback, so a view can
safely ask for the same lookup in a loop (one query instead of one per chapter) without ever serving stale data.
"""
from __future__ import annotations

from typing import Callable, TypeVar

from sqlalchemy import event
from sqlalchemy.orm import Session

T = TypeVar("T")
_KEY = "_zenith_memo"


def memo(db: Session, key: object, load: Callable[[], T]) -> T:
    store = db.info.setdefault(_KEY, {})
    if key not in store:
        store[key] = load()
    return store[key]


def _clear(session: Session, *_: object) -> None:
    session.info.pop(_KEY, None)


event.listen(Session, "after_commit", _clear)
event.listen(Session, "after_rollback", _clear)
event.listen(Session, "after_soft_rollback", _clear)


def per_request(fn):
    """Cache a read-only service function for the rest of the request (cleared on commit). Only for functions that never write."""
    import functools

    @functools.wraps(fn)
    def wrapper(db: Session, *args, **kwargs):
        return memo(db, (fn.__module__, fn.__qualname__, args, tuple(sorted(kwargs.items()))), lambda: fn(db, *args, **kwargs))
    return wrapper
