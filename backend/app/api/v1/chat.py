"""Class chat routes. Everything is under /classes/{id}/chat so the class membership check is the first thing each call does."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_profile
from app.models import Profile
from app.services import chat as svc
from app.services import chatfiles
from app.services.classes import ClassError

router = APIRouter()


def _run(fn, *a, **k):
    try:
        return fn(*a, **k)
    except ClassError as e:
        raise HTTPException(e.status, str(e))
    except chatfiles.FileError as e:
        raise HTTPException(e.status, str(e))


class TextIn(BaseModel):
    text: str = ""
    replyTo: Optional[uuid.UUID] = None
    threadId: Optional[uuid.UUID] = None
    announcement: bool = False


class PollIn(BaseModel):
    question: str
    options: list[str] = Field(max_length=6)


class GifIn(BaseModel):
    url: str
    title: str = "GIF"
    threadId: Optional[uuid.UUID] = None


class EmojiIn(BaseModel):
    emoji: str


class VoteIn(BaseModel):
    option: int


class PinIn(BaseModel):
    pinned: bool


class ReportIn(BaseModel):
    reason: str


class ResolveIn(BaseModel):
    deleteMessage: bool = False
    muteMinutes: int = Field(0, ge=0, le=7 * 24 * 60)


class MuteIn(BaseModel):
    minutes: int = Field(60, ge=0, le=7 * 24 * 60)     # 0 = until a teacher lifts it


@router.get("/classes/{class_id}/chat")
def history(class_id: uuid.UUID, before: Optional[str] = None, limit: int = Query(30, ge=1, le=50), q: Optional[str] = Query(None, max_length=60),
            p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.history, db, p, class_id, before, limit, q)


@router.get("/classes/{class_id}/chat/unread")
def unread(class_id: uuid.UUID, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    _run(svc.cls_svc.access, db, p, class_id)
    return {"unread": svc.unread(db, p, class_id)}


@router.post("/classes/{class_id}/chat/read")
def read(class_id: uuid.UUID, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.mark_read, db, p, class_id)


@router.post("/classes/{class_id}/chat/messages")
def send(class_id: uuid.UUID, body: TextIn, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.send_text, db, p, class_id, body.text, body.replyTo, body.threadId, body.announcement)


@router.get("/classes/{class_id}/chat/messages/{mid}/thread")
def thread(class_id: uuid.UUID, mid: uuid.UUID, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.thread, db, p, class_id, mid)


@router.post("/classes/{class_id}/chat/polls")
def poll(class_id: uuid.UUID, body: PollIn, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.send_poll, db, p, class_id, body.question, body.options)


@router.post("/classes/{class_id}/chat/gifs")
def send_gif(class_id: uuid.UUID, body: GifIn, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.send_gif, db, p, class_id, body.url, body.title, body.threadId)


@router.get("/classes/{class_id}/chat/gifs")
def gifs(class_id: uuid.UUID, q: str = Query("", max_length=60), p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    _run(svc.cls_svc.access, db, p, class_id)
    return {"gifs": _run(chatfiles.gif_search, q), "credit": "Powered by GIPHY"}


@router.post("/classes/{class_id}/chat/upload")
async def upload(class_id: uuid.UUID, request: Request, name: str = Query("file", max_length=120), caption: str = Query("", max_length=200),
                 threadId: Optional[uuid.UUID] = None, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    """The file is the request body (no multipart), so the browser can show real upload progress. Size is checked before reading it."""
    _run(svc.cls_svc.access, db, p, class_id)
    try:
        declared = int(request.headers.get("content-length", "0"))
    except ValueError:
        declared = 0
    if declared > chatfiles.MAX_BYTES:
        raise HTTPException(413, "That file is too big. The limit is 4 MB.")
    data = await request.body()
    return _run(svc.send_file, db, p, class_id, name, data, caption, threadId)


@router.get("/classes/{class_id}/chat/messages/{mid}/file")
def file(class_id: uuid.UUID, mid: uuid.UUID, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.file_link, db, p, class_id, mid)


@router.put("/classes/{class_id}/chat/messages/{mid}/reaction")
def react(class_id: uuid.UUID, mid: uuid.UUID, body: EmojiIn, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.react, db, p, class_id, mid, body.emoji)


@router.put("/classes/{class_id}/chat/messages/{mid}/vote")
def vote(class_id: uuid.UUID, mid: uuid.UUID, body: VoteIn, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.vote, db, p, class_id, mid, body.option)


@router.put("/classes/{class_id}/chat/messages/{mid}/pin")
def pin(class_id: uuid.UUID, mid: uuid.UUID, body: PinIn, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.pin, db, p, class_id, mid, body.pinned)


@router.delete("/classes/{class_id}/chat/messages/{mid}")
def remove(class_id: uuid.UUID, mid: uuid.UUID, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.remove, db, p, class_id, mid)


@router.post("/classes/{class_id}/chat/messages/{mid}/report")
def report(class_id: uuid.UUID, mid: uuid.UUID, body: ReportIn, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.report, db, p, class_id, mid, body.reason)


@router.post("/classes/{class_id}/chat/messages/{mid}/block")
def block(class_id: uuid.UUID, mid: uuid.UUID, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.block_author, db, p, class_id, mid)


@router.post("/classes/{class_id}/chat/messages/{mid}/mute")
def mute(class_id: uuid.UUID, mid: uuid.UUID, body: MuteIn, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.mute_author, db, p, class_id, mid, body.minutes)


@router.delete("/classes/{class_id}/chat/messages/{mid}/mute")
def unmute(class_id: uuid.UUID, mid: uuid.UUID, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.unmute_author, db, p, class_id, mid)


@router.get("/classes/{class_id}/chat/reports")
def reports(class_id: uuid.UUID, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.reports, db, p, class_id)


@router.post("/classes/{class_id}/chat/reports/{rid}/resolve")
def resolve(class_id: uuid.UUID, rid: uuid.UUID, body: ResolveIn, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.resolve_report, db, p, class_id, rid, body.deleteMessage, body.muteMinutes)


@router.get("/chat/blocks")
def my_blocks(p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return svc.blocks(db, p)


@router.delete("/chat/blocks/{block_id}")
def unblock(block_id: uuid.UUID, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _run(svc.unblock, db, p, block_id)
