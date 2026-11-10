"""Import one file from Wikimedia Commons through its official API, keeping its licence and credit."""
from __future__ import annotations

import hashlib
import html
import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingest.assets import get_source
from app.ingest.fetch import fetch
from app.ingest.policy import evaluate
from app.models import SourceAsset

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "ZenithEducationBot/1.0 (school learning platform; respects robots.txt)"
IMAGE_HOSTS = {"upload.wikimedia.org", "commons.wikimedia.org"}
RECHECK_DAYS = 180


class CommonsError(ValueError):
    pass


class LicenceRefused(CommonsError):
    pass


def licence_id(short_name: str) -> str:
    """Map the licence name Commons reports ("CC BY-SA 4.0", "CC0", "Public domain") to our ids."""
    t = re.sub(r"\s+", " ", (short_name or "").strip())
    if not t:
        return ""
    low = t.lower()
    if low in ("cc0", "cc0 1.0", "cc-zero"):
        return "CC0-1.0"
    if low.startswith("public domain") or low == "pd":
        return "PDM-1.0"
    m = re.match(r"cc[ -]by((?:-[a-z]{2})*)[ -]?(\d\.\d)", low)
    if m:
        return f"CC-BY{m.group(1).upper()}-{m.group(2)}"
    return t


def _text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", value or ""))).strip()


def import_file(db: Session, title: str, actor_id: uuid.UUID) -> SourceAsset:
    if not title.startswith("File:"):
        raise CommonsError("Give the file title as it appears on Commons, for example File:Example.jpg")
    source = get_source(db, "Wikimedia Commons", "https://commons.wikimedia.org", "https://commons.wikimedia.org/wiki/Commons:Licensing",
                        "https://www.mediawiki.org/wiki/API:Etiquette")
    existing = db.scalar(select(SourceAsset).where(SourceAsset.source_id == source.id, SourceAsset.external_id == title))
    if existing:
        return existing
    url = f"{API}?action=query&format=json&prop=imageinfo&iiprop=url|size|extmetadata&titles={quote(title)}"
    data = json.loads(fetch(url, user_agent=USER_AGENT))
    pages = (data.get("query") or {}).get("pages") or {}
    info = next((p.get("imageinfo", [None])[0] for p in pages.values() if p.get("imageinfo")), None)
    if not info:
        raise CommonsError("Commons has no such file.")
    meta = info.get("extmetadata") or {}
    lic = licence_id((meta.get("LicenseShortName") or {}).get("value", ""))
    decision = evaluate(lic)
    if not decision.allowed:
        raise LicenceRefused(decision.reason)
    file_url = info["url"]
    if urlsplit(file_url).hostname not in IMAGE_HOSTS:
        raise CommonsError("The file is not on a Wikimedia host, so it is not imported.")
    body = fetch(file_url, user_agent=USER_AGENT)
    artist = _text((meta.get("Artist") or {}).get("value", "")) or "Unknown author"
    licence_name = _text((meta.get("LicenseShortName") or {}).get("value", ""))
    licence_link = _text((meta.get("LicenseUrl") or {}).get("value", ""))
    credit = f"{title[5:]} by {artist}, {licence_name}{f' ({licence_link})' if licence_link else ''}, via Wikimedia Commons"
    now = datetime.now(timezone.utc)
    asset = SourceAsset(source_id=source.id, external_id=title, url=file_url, kind="image", licence_id=lic, attribution_text=credit, author=artist,
                        sha256=hashlib.sha256(body).hexdigest(), bytes=len(body), status="pending", retrieved_at=now, recheck_at=now + timedelta(days=RECHECK_DAYS))
    db.add(asset)
    db.commit()
    return asset
