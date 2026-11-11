"""Class group chat. One chat per classroom, no private messages, membership checked on every call.

Designed for children: no links, emails or phone numbers (so nobody can be pulled out of the class), no unkind words,
a short list of reactions, teacher-only polls and announcements, reporting, blocking and teacher muting."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models import (ChatBlock, ChatMessage, ChatMute, ChatPollVote, ChatReaction, ChatRead, ChatReport, ClassMember, Profile)
from app.services import chatfiles
from app.services import classes as cls_svc
from app.services.classes import ClassError, plain

MAX_BODY = 1000
BURST = (8, 10)        # at most 8 messages per 10 seconds per person
EMOJI = ("👍", "❤️", "😂", "😮", "😢", "🎉", "👏", "🔥", "💡", "🤔", "✅", "🙏")
URL = re.compile(r"(https?://|www\.|\b[a-z0-9-]+\.(com|net|org|in|io|me|gg|ly|co|app|xyz|tv|link)\b)", re.I)
EMAIL = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
PHONE = re.compile(r"\+?\d[\d\s().-]{8,}\d")
DECIMAL = re.compile(r"\d+\.\d+")
# A deliberately small list of words that have no place in a children's class chat. Teachers can delete and mute for the rest.
BAD = re.compile(r"\b(fuck\w*|shit\w*|bitch\w*|bastard|asshole|cunt|slut|whore|porn\w*|idiot|stupid|dumb|loser|hate you|kill yourself|kys)\b", re.I)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def moderate(text: str) -> None:
    """Raise a kind, specific message when text should not be posted. Applies to everyone except the class teacher."""
    if URL.search(text):
        raise ClassError("Links are not allowed in class chat. Ask your teacher to share it.")
    if EMAIL.search(text) or any(len(re.sub(r"\D", "", m.group())) >= 10 and not DECIMAL.fullmatch(m.group().strip()) for m in PHONE.finditer(text)):
        raise ClassError("Please do not share phone numbers or emails in class chat.")
    if BAD.search(text):
        raise ClassError("Please keep class chat kind. That message was not sent.")


def _is_teacher(p: Profile) -> bool:
    return p.role in ("teacher", "admin")


def _muted(db: Session, c, p: Profile) -> bool:
    m = db.get(ChatMute, (c.id, p.id))
    return bool(m and (m.until is None or m.until > _now()))


def _blocked_ids(db: Session, p: Profile) -> set[uuid.UUID]:
    return {b for (b,) in db.execute(select(ChatBlock.blocked_id).where(ChatBlock.blocker_id == p.id))}


def _author(db: Session, m: ChatMessage, viewer: Profile, cache: dict) -> dict:
    if m.author_id not in cache:
        a = db.get(Profile, m.author_id) if m.author_id else None
        cache[m.author_id] = a
    a = cache[m.author_id]
    if a is None:
        return {"nickname": "Former member", "avatar": None, "teacher": False, "me": False}
    teacher = a.role in ("teacher", "admin")
    return {"nickname": (a.display_name or "Teacher") if teacher else (a.nickname or "Student"), "avatar": a.avatar, "teacher": teacher, "me": a.id == viewer.id}


def _dto(db: Session, m: ChatMessage, viewer: Profile, cache: dict, extras: dict) -> dict:
    gone = m.deleted_at is not None
    reactions = [{"emoji": e, "count": n, "mine": (m.id, e) in extras["mine"]} for (e, n) in extras["reactions"].get(m.id, [])]
    out = {"id": str(m.id), "kind": "text" if gone else m.kind, "body": "This message was removed." if gone else m.body, "removed": gone, "pinned": m.pinned and not gone,
           "createdAt": m.created_at.isoformat(), "author": _author(db, m, viewer, cache), "reactions": [] if gone else reactions,
           "threadCount": extras["threads"].get(m.id, 0), "parentId": str(m.parent_id) if m.parent_id else None, "replyTo": None, "attachment": None, "poll": None}
    if m.reply_to and m.reply_to in extras["replied"]:
        r = extras["replied"][m.reply_to]
        out["replyTo"] = {"id": str(r.id), "nickname": _author(db, r, viewer, cache)["nickname"], "snippet": "Message removed" if r.deleted_at else (r.body or r.kind)[:80]}
    if not gone and m.attachment:
        a = m.attachment
        out["attachment"] = {"name": a.get("name"), "type": a.get("type"), "size": a.get("size")} if "key" in a else {"url": a["url"], "title": a.get("title"), "provider": a.get("provider")}
    if not gone and m.kind == "poll":
        votes = extras["votes"].get(m.id, {})
        opts = m.meta.get("options", [])
        out["poll"] = {"options": [{"text": t, "votes": sum(1 for v in votes.values() if v == i)} for i, t in enumerate(opts)], "total": len(votes), "myVote": votes.get(viewer.id)}
    return out


def _extras(db: Session, rows: list[ChatMessage], viewer: Profile) -> dict:
    ids = [m.id for m in rows]
    if not ids:
        return {"reactions": {}, "mine": set(), "threads": {}, "votes": {}, "replied": {}}
    reactions: dict = {}
    for mid, e, n in db.execute(select(ChatReaction.message_id, ChatReaction.emoji, func.count()).where(ChatReaction.message_id.in_(ids)).group_by(ChatReaction.message_id, ChatReaction.emoji).order_by(func.min(ChatReaction.created_at))):
        reactions.setdefault(mid, []).append((e, n))
    mine = {(mid, e) for mid, e in db.execute(select(ChatReaction.message_id, ChatReaction.emoji).where(ChatReaction.message_id.in_(ids), ChatReaction.user_id == viewer.id))}
    threads = dict(db.execute(select(ChatMessage.parent_id, func.count()).where(ChatMessage.parent_id.in_(ids), ChatMessage.deleted_at.is_(None)).group_by(ChatMessage.parent_id)).all())
    votes: dict = {}
    for mid, uid, opt in db.execute(select(ChatPollVote.message_id, ChatPollVote.user_id, ChatPollVote.option).where(ChatPollVote.message_id.in_(ids))):
        votes.setdefault(mid, {})[uid] = opt
    rids = {m.reply_to for m in rows if m.reply_to}
    replied = {r.id: r for r in db.scalars(select(ChatMessage).where(ChatMessage.id.in_(rids)))} if rids else {}
    return {"reactions": reactions, "mine": mine, "threads": threads, "votes": votes, "replied": replied}


def _present(db: Session, rows: list[ChatMessage], viewer: Profile) -> list[dict]:
    extras, cache = _extras(db, rows, viewer), {}
    return [_dto(db, m, viewer, cache, extras) for m in rows]


def _message(db: Session, c, mid: uuid.UUID) -> ChatMessage:
    m = db.get(ChatMessage, mid)
    if m is None or m.classroom_id != c.id:
        raise ClassError("Message not found.", 404)
    return m


# ---- reading ---------------------------------------------------------------------------------------
def history(db: Session, p: Profile, class_id: uuid.UUID, before: str | None = None, limit: int = 30, q: str | None = None, thread: uuid.UUID | None = None) -> dict:
    c = cls_svc.access(db, p, class_id)
    limit = max(1, min(limit, 50))
    stmt = select(ChatMessage).where(ChatMessage.classroom_id == c.id)
    stmt = stmt.where(ChatMessage.parent_id == thread) if thread else stmt.where(ChatMessage.parent_id.is_(None))
    blocked = _blocked_ids(db, p) if not _is_teacher(p) else set()
    if blocked:
        stmt = stmt.where(or_(ChatMessage.author_id.is_(None), ChatMessage.author_id.not_in(blocked)))
    if q:
        needle = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(ChatMessage.deleted_at.is_(None), ChatMessage.body.ilike(f"%{needle}%", escape="\\"))
    if before:
        try:
            ts = datetime.fromisoformat(before)
        except ValueError:
            raise ClassError("Bad page marker.")
        stmt = stmt.where(ChatMessage.created_at < ts)
    rows = list(db.scalars(stmt.order_by(ChatMessage.created_at.desc()).limit(limit + 1)))
    more = len(rows) > limit
    rows = rows[:limit][::-1]
    pinned = [] if (q or thread) else _present(db, list(db.scalars(select(ChatMessage).where(ChatMessage.classroom_id == c.id, ChatMessage.pinned.is_(True), ChatMessage.deleted_at.is_(None)).order_by(ChatMessage.created_at.desc()).limit(5))), p)
    return {"messages": _present(db, rows, p), "hasMore": more, "next": rows[0].created_at.isoformat() if rows and more else None, "pinned": pinned,
            "muted": _muted(db, c, p), "canModerate": _is_teacher(p)}


def thread(db: Session, p: Profile, class_id: uuid.UUID, root_id: uuid.UUID) -> dict:
    c = cls_svc.access(db, p, class_id)
    root = _message(db, c, root_id)
    out = history(db, p, class_id, limit=50, thread=root.id)
    out["root"] = _present(db, [root], p)[0]
    return out


def unread(db: Session, p: Profile, class_id: uuid.UUID) -> int:
    r = db.get(ChatRead, (class_id, p.id))
    stmt = select(func.count()).select_from(ChatMessage).where(ChatMessage.classroom_id == class_id, ChatMessage.deleted_at.is_(None), ChatMessage.author_id != p.id)
    if r:
        stmt = stmt.where(ChatMessage.created_at > r.last_read_at)
    return db.scalar(stmt) or 0


def mark_read(db: Session, p: Profile, class_id: uuid.UUID) -> dict:
    cls_svc.access(db, p, class_id)
    r = db.get(ChatRead, (class_id, p.id))
    if r is None:
        db.add(ChatRead(classroom_id=class_id, user_id=p.id, last_read_at=_now()))
    else:
        r.last_read_at = _now()
    db.commit()
    return {"unread": 0}


# ---- writing ---------------------------------------------------------------------------------------
def _post(db: Session, p: Profile, class_id: uuid.UUID, kind: str, body: str = "", reply_to: uuid.UUID | None = None, thread_id: uuid.UUID | None = None,
          attachment: dict | None = None, meta: dict | None = None) -> ChatMessage:
    c = cls_svc.access(db, p, class_id)
    teacher = _is_teacher(p)
    if not teacher and _muted(db, c, p):
        raise ClassError("Your teacher has paused your chat for now.", 403)
    recent = db.scalar(select(func.count()).select_from(ChatMessage).where(ChatMessage.author_id == p.id, ChatMessage.created_at > _now() - timedelta(seconds=BURST[1])))
    if (recent or 0) >= BURST[0]:
        raise ClassError("You are sending messages very fast. Wait a few seconds.", 429)
    parent = None
    if reply_to:
        target = _message(db, c, reply_to)
        parent = target.parent_id or target.id          # a reply inside a thread stays in that thread
        if target.deleted_at:
            raise ClassError("You cannot reply to a removed message.")
    if thread_id:
        root = _message(db, c, thread_id)
        parent = root.parent_id or root.id
    m = ChatMessage(classroom_id=c.id, author_id=p.id, kind=kind, body=body, reply_to=reply_to, parent_id=parent, attachment=attachment, meta=meta or {})
    db.add(m)
    db.commit()
    return m


def send_text(db: Session, p: Profile, class_id: uuid.UUID, text: str, reply_to: uuid.UUID | None = None, thread_id: uuid.UUID | None = None, announcement: bool = False) -> dict:
    body = plain(text)
    if not body:
        raise ClassError("Write a message first.")
    if len(body) > MAX_BODY:
        raise ClassError(f"Keep messages under {MAX_BODY} characters.")
    if announcement and not _is_teacher(p):
        raise ClassError("Only the teacher can post announcements.", 403)
    if not _is_teacher(p):
        moderate(body)
    m = _post(db, p, class_id, "announcement" if announcement else "text", body, reply_to, thread_id)
    return _present(db, [m], p)[0]


def send_poll(db: Session, p: Profile, class_id: uuid.UUID, question: str, options: list[str]) -> dict:
    if not _is_teacher(p):
        raise ClassError("Only the teacher can start a poll.", 403)
    q, opts = plain(question), [plain(o) for o in options if plain(o)]
    if not q or len(q) > 200 or not 2 <= len(opts) <= 6 or any(len(o) > 80 for o in opts):
        raise ClassError("A poll needs a question and 2 to 6 short options.")
    return _present(db, [_post(db, p, class_id, "poll", q, meta={"options": opts})], p)[0]


def send_gif(db: Session, p: Profile, class_id: uuid.UUID, url: str, title: str, thread_id: uuid.UUID | None = None) -> dict:
    if not chatfiles.gif_url_ok(url):
        raise ClassError("That GIF cannot be used.")
    return _present(db, [_post(db, p, class_id, "gif", plain(title)[:80], thread_id=thread_id, attachment={"url": url, "title": plain(title)[:80], "provider": "giphy"})], p)[0]


def send_file(db: Session, p: Profile, class_id: uuid.UUID, filename: str, data: bytes, caption: str = "", thread_id: uuid.UUID | None = None) -> dict:
    c = cls_svc.access(db, p, class_id)
    if not _is_teacher(p) and _muted(db, c, p):
        raise ClassError("Your teacher has paused your chat for now.", 403)
    try:
        info = chatfiles.validate(filename, data)
        cap = plain(caption)[:200]
        if cap and not _is_teacher(p):
            moderate(cap)
        key = chatfiles.new_key(c.id, info["ext"])
        chatfiles.put(key, data, info["type"])
    except chatfiles.FileError as e:
        raise ClassError(str(e), e.status)
    m = _post(db, p, class_id, info["kind"], cap, thread_id=thread_id, attachment={"key": key, "name": info["name"], "type": info["type"], "size": info["size"]})
    return _present(db, [m], p)[0]


def file_link(db: Session, p: Profile, class_id: uuid.UUID, mid: uuid.UUID) -> dict:
    c = cls_svc.access(db, p, class_id)
    m = _message(db, c, mid)
    if m.deleted_at or not m.attachment or "key" not in m.attachment:
        raise ClassError("File not found.", 404)
    if m.author_id in _blocked_ids(db, p) and not _is_teacher(p):
        raise ClassError("File not found.", 404)
    try:
        return {"url": chatfiles.signed_url(m.attachment["key"]), "name": m.attachment["name"], "type": m.attachment["type"], "expiresIn": chatfiles.LINK_SECONDS}
    except chatfiles.FileError as e:
        raise ClassError(str(e), e.status)


def react(db: Session, p: Profile, class_id: uuid.UUID, mid: uuid.UUID, emoji: str) -> dict:
    c = cls_svc.access(db, p, class_id)
    m = _message(db, c, mid)
    if emoji not in EMOJI:
        raise ClassError("Pick a reaction from the list.")
    if m.deleted_at:
        raise ClassError("That message was removed.")
    row = db.get(ChatReaction, (m.id, p.id, emoji))
    if row:
        db.delete(row)
    else:
        db.add(ChatReaction(message_id=m.id, user_id=p.id, emoji=emoji))
    db.commit()
    return _present(db, [m], p)[0]


def vote(db: Session, p: Profile, class_id: uuid.UUID, mid: uuid.UUID, option: int) -> dict:
    c = cls_svc.access(db, p, class_id)
    m = _message(db, c, mid)
    if m.kind != "poll" or m.deleted_at:
        raise ClassError("That is not an open poll.")
    if not 0 <= option < len(m.meta.get("options", [])):
        raise ClassError("Choose one of the options.")
    row = db.get(ChatPollVote, (m.id, p.id))
    if row:
        row.option = option
    else:
        db.add(ChatPollVote(message_id=m.id, user_id=p.id, option=option))
    db.commit()
    return _present(db, [m], p)[0]


def pin(db: Session, p: Profile, class_id: uuid.UUID, mid: uuid.UUID, pinned: bool) -> dict:
    c = cls_svc.owner_only(db, p, class_id)
    m = _message(db, c, mid)
    m.pinned = pinned and m.deleted_at is None
    db.commit()
    return {"pinned": m.pinned}


def remove(db: Session, p: Profile, class_id: uuid.UUID, mid: uuid.UUID) -> dict:
    c = cls_svc.access(db, p, class_id)
    m = _message(db, c, mid)
    if m.author_id != p.id and not _is_teacher(p):
        raise ClassError("You can only remove your own messages.", 403)
    m.deleted_at, m.pinned = _now(), False
    db.commit()
    return {"removed": True}


# ---- safety ----------------------------------------------------------------------------------------
def report(db: Session, p: Profile, class_id: uuid.UUID, mid: uuid.UUID, reason: str) -> dict:
    c = cls_svc.access(db, p, class_id)
    m = _message(db, c, mid)
    if m.author_id == p.id:
        raise ClassError("You cannot report your own message.")
    why = plain(reason)[:300]
    if not why:
        raise ClassError("Tell your teacher what is wrong.")
    if db.scalar(select(ChatReport.id).where(ChatReport.message_id == m.id, ChatReport.reporter_id == p.id)) is None:
        db.add(ChatReport(classroom_id=c.id, message_id=m.id, reporter_id=p.id, reason=why))
        db.commit()
    return {"reported": True}


def reports(db: Session, p: Profile, class_id: uuid.UUID) -> list[dict]:
    c = cls_svc.owner_only(db, p, class_id)
    out = []
    for r in db.scalars(select(ChatReport).where(ChatReport.classroom_id == c.id, ChatReport.status == "open").order_by(ChatReport.created_at)):
        m, cache = db.get(ChatMessage, r.message_id), {}
        out.append({"id": str(r.id), "reason": r.reason, "createdAt": r.created_at.isoformat(), "message": _present(db, [m], p)[0] if m else None})
    return out


def resolve_report(db: Session, p: Profile, class_id: uuid.UUID, rid: uuid.UUID, delete_message: bool = False, mute_minutes: int = 0) -> dict:
    c = cls_svc.owner_only(db, p, class_id)
    r = db.get(ChatReport, rid)
    if r is None or r.classroom_id != c.id:
        raise ClassError("Report not found.", 404)
    m = db.get(ChatMessage, r.message_id)
    if m and delete_message:
        m.deleted_at, m.pinned = _now(), False
    if m and mute_minutes and m.author_id:
        mute(db, p, class_id, m.author_id, mute_minutes, commit=False)
    for same in db.scalars(select(ChatReport).where(ChatReport.message_id == r.message_id)):
        same.status = "closed"
    db.commit()
    return {"closed": True}


def mute(db: Session, p: Profile, class_id: uuid.UUID, user_id: uuid.UUID, minutes: int, commit: bool = True) -> dict:
    c = cls_svc.owner_only(db, p, class_id)
    target = db.get(ClassMember, (c.id, user_id))
    if target is None:
        raise ClassError("That student is not in this class.", 404)
    until = _now() + timedelta(minutes=minutes) if minutes > 0 else None
    row = db.get(ChatMute, (c.id, user_id))
    if row:
        row.until, row.set_by = until, p.id
    else:
        db.add(ChatMute(classroom_id=c.id, user_id=user_id, until=until, set_by=p.id))
    if commit:
        db.commit()
    return {"muted": True}


def mute_author(db: Session, p: Profile, class_id: uuid.UUID, mid: uuid.UUID, minutes: int) -> dict:
    c = cls_svc.owner_only(db, p, class_id)
    m = _message(db, c, mid)
    if not m.author_id:
        raise ClassError("That member has left.", 404)
    return mute(db, p, class_id, m.author_id, minutes)


def unmute_author(db: Session, p: Profile, class_id: uuid.UUID, mid: uuid.UUID) -> dict:
    c = cls_svc.owner_only(db, p, class_id)
    m = _message(db, c, mid)
    row = db.get(ChatMute, (c.id, m.author_id)) if m.author_id else None
    if row:
        db.delete(row)
        db.commit()
    return {"muted": False}


def block_author(db: Session, p: Profile, class_id: uuid.UUID, mid: uuid.UUID) -> dict:
    c = cls_svc.access(db, p, class_id)
    m = _message(db, c, mid)
    if m.author_id is None or m.author_id == p.id:
        raise ClassError("You cannot block that.")
    target = db.get(Profile, m.author_id)
    if target is not None and target.role != "student":
        raise ClassError("You cannot block your teacher. Tell them if something is wrong.")
    if db.scalar(select(ChatBlock.id).where(ChatBlock.blocker_id == p.id, ChatBlock.blocked_id == m.author_id)) is None:
        db.add(ChatBlock(blocker_id=p.id, blocked_id=m.author_id))
        db.commit()
    return {"blocked": True}


def blocks(db: Session, p: Profile) -> list[dict]:
    out = []
    for b in db.scalars(select(ChatBlock).where(ChatBlock.blocker_id == p.id).order_by(ChatBlock.created_at)):
        t = db.get(Profile, b.blocked_id)
        out.append({"id": str(b.id), "nickname": (t.nickname if t else None) or "A classmate", "avatar": t.avatar if t else None})
    return out


def unblock(db: Session, p: Profile, block_id: uuid.UUID) -> dict:
    b = db.get(ChatBlock, block_id)
    if b is None or b.blocker_id != p.id:
        raise ClassError("Not found.", 404)
    db.delete(b)
    db.commit()
    return {"blocked": False}
