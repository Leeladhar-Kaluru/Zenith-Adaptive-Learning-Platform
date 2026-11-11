"""Stages 1 to 3 of the source-to-lesson pipeline: fetch a page from a VETTED open-licence source, check the licence on the page itself,
extract and filter its text, and store it as a pending, credited asset for a reviewer.

Only hosts in SOURCES can be fetched (no blind scraping). The licence must be allowed by ingest/policy.py, must be the one we expect for that
source, and must be shown on the page itself. Share-alike, non-commercial, no-derivatives and unknown licences are refused. Books whose text
is copyrighted (NCERT and other textbooks) are never fetched: they are a syllabus reference only."""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingest import webtext
from app.ingest.assets import get_source
from app.ingest.commons import user_agent
from app.ingest.fetch import fetch
from app.ingest.policy import evaluate
from app.models import SourceAsset

MAX_BYTES = 80 * 1024
RECHECK_DAYS = 180


class TextSourceError(ValueError):
    pass


@dataclass(frozen=True)
class OpenSource:
    name: str
    hosts: tuple[str, ...]
    path_prefix: str                # only pages under this path are fetched
    licence: str                    # the licence we expect
    homepage: str
    terms: str
    attribution: str                # {title} and {url} are filled in
    proof: str = "page"             # "page": the page itself must show exactly this Creative Commons licence; "publisher": public domain by the publisher's own law or policy


SOURCES: dict[str, OpenSource] = {
    "nasa": OpenSource(
        name="NASA", hosts=("spaceplace.nasa.gov", "science.nasa.gov"), path_prefix="/", licence="US-GOV-PD", homepage="https://www.nasa.gov/", proof="publisher",
        terms="https://www.nasa.gov/nasa-brand-center/images-and-media/",
        attribution="Adapted from NASA, {title} ({url}). NASA content is generally not copyrighted. Simplified for school students by ZENITH."),
    "usgs-water": OpenSource(
        name="USGS Water Science School", hosts=("www.usgs.gov",), path_prefix="/special-topics/water-science-school/", licence="US-GOV-PD", homepage="https://www.usgs.gov/",
        proof="publisher", terms="https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits",
        attribution="Adapted from the U.S. Geological Survey, {title} ({url}). USGS-authored content is in the public domain. Simplified for school students by ZENITH."),
    "noaa-ocean": OpenSource(
        name="NOAA National Ocean Service", hosts=("oceanservice.noaa.gov",), path_prefix="/facts/", licence="US-GOV-PD", homepage="https://oceanservice.noaa.gov/",
        proof="publisher", terms="https://www.noaa.gov/protecting-your-privacy",
        attribution="Adapted from NOAA National Ocean Service, {title} ({url}). NOAA-authored content is in the public domain. Simplified for school students by ZENITH."),
}

# Sources that were checked and REFUSED, with the reason, so nobody adds them again by mistake.
REFUSED: dict[str, str] = {
    "openstax": "OpenStax books are CC BY-NC-SA (non-commercial, refused by ingest/policy.py) and the site states its text may not be ingested into AI systems without written permission.",
    "ncert": "NCERT textbooks are copyrighted and may not be copied or rehosted. They are a syllabus reference only: lessons are original.",
    "wikipedia": "Wikipedia text is CC BY-SA (share-alike): it may not be merged into lesson text under our policy.",
    "nroer": "Most NROER resources are share-alike or carry other conditions; each would need a person to check it.",
    "khan-academy": "Khan Academy content is CC BY-NC-SA (non-commercial).",
    "ck12": "CK-12 content is CC BY-NC (non-commercial).",
}


def _source_for(url: str, key: str) -> OpenSource:
    if key in REFUSED:
        raise TextSourceError(f"'{key}' is refused: {REFUSED[key]}")
    src = SOURCES.get(key)
    if src is None:
        raise TextSourceError(f"'{key}' is not a vetted source. Vetted sources: {', '.join(sorted(SOURCES))}.")
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in src.hosts or not parts.path.startswith(src.path_prefix) or parts.username or parts.password:
        raise TextSourceError(f"{url} is not an https page under {src.hosts[0]}{src.path_prefix}.")
    return src


def import_page(db: Session, url: str, source_key: str, actor_id: uuid.UUID | None = None, keywords: list[str] | None = None,
                fetcher: Callable[..., bytes] = fetch) -> SourceAsset:
    """Fetch, verify, clean, filter and store one page. Left pending: a person approves it before any lesson may cite it."""
    src = _source_for(url, source_key)
    expected = evaluate(src.licence)
    if not expected.allowed or expected.share_alike:
        raise TextSourceError("This source's licence is not usable for text that is simplified into lessons.")
    html = fetcher(url, user_agent=user_agent()).decode("utf-8", errors="replace")
    page = webtext.parse(html)
    if src.proof == "page":
        if not page.licences:
            raise TextSourceError("The page does not show a Creative Commons licence, so it is refused.")
        bad = [lic for lic in page.licences if lic != src.licence]
        if bad:
            raise TextSourceError(f"The page shows other licences ({', '.join(sorted(bad))}) as well as {src.licence}. Refused until a person checks which part is which.")
    else:
        # public domain by the publisher's own policy: refuse if the page carries a restrictive Creative Commons licence, and drop any text with its own copyright notice
        restrictive = [lic for lic in page.licences if not evaluate(lic).allowed or evaluate(lic).share_alike]
        if restrictive:
            raise TextSourceError(f"The page shows a restrictive licence ({', '.join(sorted(restrictive))}). Refused.")
        page.sections = [s for s in page.sections if not webtext.has_copyright_notice(s.heading + " " + s.text)]
    sections = webtext.clean(page.sections)
    if keywords:
        sections = webtext.select(sections, keywords)
    if not sections:
        raise TextSourceError("No usable teaching text was found on that page.")
    data = {"title": page.title, "sections": [{"heading": s.heading, "text": s.text, "grade": webtext.difficulty(s.text)} for s in sections]}
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
    if len(blob) > MAX_BYTES:
        raise TextSourceError(f"The extracted text is too large ({len(blob) // 1024} kB; limit {MAX_BYTES // 1024} kB). Pass keywords to keep the relevant sections.")
    source = get_source(db, src.name, src.homepage, src.terms)
    existing = db.scalar(select(SourceAsset).where(SourceAsset.source_id == source.id, SourceAsset.external_id == url))
    if existing:
        return existing
    now = datetime.now(timezone.utc)
    a = SourceAsset(source_id=source.id, external_id=url, url=url, kind="text", licence_id=src.licence, author=src.name,
                    attribution_text=src.attribution.format(title=page.title or url, url=url), sha256=hashlib.sha256(blob).hexdigest(), bytes=len(blob), data=data,
                    status="pending", retrieved_at=now, recheck_at=now + timedelta(days=RECHECK_DAYS))
    db.add(a)
    db.commit()
    return a
