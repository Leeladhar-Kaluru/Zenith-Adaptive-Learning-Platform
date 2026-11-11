"""Class chat attachments and GIF search.

Files are checked here (size, real type from the first bytes, safe name) and stored in a PRIVATE Backblaze bucket under
`classchat/<class>/<random>`. Nobody gets a permanent link: members ask the API for a link that works for ten minutes.
Tests replace `put`, `signed_url` and `gif_search` with fakes, so they never reach the network."""
from __future__ import annotations

import re
import secrets
import uuid
from urllib.parse import urlparse

import httpx

from app.core.config import settings

MAX_BYTES = 4 * 1024 * 1024        # Vercel functions accept bodies up to 4.5 MB
PREFIX = "classchat/"
LINK_SECONDS = 600
GIF_HOSTS = ("media.giphy.com", "media0.giphy.com", "media1.giphy.com", "media2.giphy.com", "media3.giphy.com", "media4.giphy.com", "i.giphy.com")


class FileError(ValueError):
    def __init__(self, msg: str, status: int = 422):
        super().__init__(msg)
        self.status = status


def sniff(data: bytes) -> tuple[str, str, str]:
    """Return (kind, mime, extension) from the file's own bytes. The name and the browser's claimed type are never trusted."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image", "image/png", "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image", "image/jpeg", "jpg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image", "image/gif", "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image", "image/webp", "webp"
    if data.startswith(b"%PDF-"):
        return "file", "application/pdf", "pdf"
    raise FileError("Only pictures (PNG, JPG, GIF, WebP) and PDF files can be shared.")


def clean_name(name: str, ext: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9 _.-]", "", (name or "").rsplit(".", 1)[0]).strip(" .")[:60]
    return f"{stem or 'file'}.{ext}"


def validate(name: str, data: bytes) -> dict:
    if not data:
        raise FileError("That file is empty.")
    if len(data) > MAX_BYTES:
        raise FileError("That file is too big. The limit is 4 MB.", 413)
    kind, mime, ext = sniff(data)
    return {"kind": kind, "type": mime, "name": clean_name(name, ext), "size": len(data), "ext": ext}


def new_key(class_id: uuid.UUID, ext: str) -> str:
    return f"{PREFIX}{class_id}/{secrets.token_hex(16)}.{ext}"


def _b2():
    from app.ops.backup import B2, BackupError
    try:
        return B2()
    except BackupError as e:
        raise FileError("File sharing is not set up yet.", 503) from e


def put(key: str, data: bytes, mime: str) -> None:
    import hashlib
    b2 = _b2()
    up = b2._post("b2_get_upload_url", {"bucketId": b2.bucket_id})
    r = b2.c.post(up["uploadUrl"], content=data, headers={"Authorization": up["authorizationToken"], "X-Bz-File-Name": key, "Content-Type": mime,
                                                          "X-Bz-Content-Sha1": hashlib.sha1(data).hexdigest()})
    if r.status_code != 200:
        raise FileError("The file could not be saved. Try again.", 502)


def signed_url(key: str) -> str:
    """A download link for exactly this one file that stops working after ten minutes."""
    if not key.startswith(PREFIX):
        raise FileError("Not found.", 404)
    b2 = _b2()
    j = b2._post("b2_get_download_authorization", {"bucketId": b2.bucket_id, "fileNamePrefix": key, "validDurationInSeconds": LINK_SECONDS})
    return f"{b2.dl}/file/{b2.bucket}/{key}?Authorization={j['authorizationToken']}"


def gif_url_ok(url: str) -> bool:
    u = urlparse(url or "")
    return u.scheme == "https" and u.hostname in GIF_HOSTS and len(url) < 400


def gif_search(q: str, limit: int = 12) -> list[dict]:
    """Search Giphy from the server (the key never reaches a browser). Rated G only; clients must show 'Powered by GIPHY'."""
    key = settings.GIPHY_API_KEY
    if not key:
        raise FileError("GIF search is not set up yet.", 503)
    path = "search" if q.strip() else "trending"
    r = httpx.get(f"https://api.giphy.com/v1/gifs/{path}", params={"api_key": key, "q": q.strip()[:60], "limit": limit, "rating": "g", "bundle": "messaging_non_clips"}, timeout=8)
    if r.status_code != 200:
        raise FileError("GIF search is busy. Try again in a moment.", 502)
    out = []
    for g in r.json().get("data", []):
        img = g.get("images", {})
        full, small = img.get("fixed_height", {}).get("url"), img.get("fixed_height_small", {}).get("url") or img.get("fixed_height", {}).get("url")
        if full and gif_url_ok(full):
            out.append({"id": g.get("id"), "title": (g.get("title") or "GIF")[:80], "url": full, "preview": small if small and gif_url_ok(small) else full})
    return out
