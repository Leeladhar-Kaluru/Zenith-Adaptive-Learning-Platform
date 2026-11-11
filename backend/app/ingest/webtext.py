"""Turn a web page into clean, filtered text sections. Pure functions: no network, no database, so every rule can be tested.

Stage 2 of the source-to-lesson pipeline (fetch -> THIS -> store -> draft -> gates -> review). It keeps readable body text under headings
and throws away navigation, scripts, forms, tables of contents, figures and anything too short to teach from."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

from app.cms.gates import fk_grade

SKIP = {"script", "style", "nav", "header", "footer", "aside", "form", "noscript", "svg", "figure", "figcaption", "button", "select", "dialog", "iframe", "table"}
HEADINGS = {"h1", "h2", "h3", "h4"}
BLOCKS = {"p", "li", "blockquote", "dd"}
CC = re.compile(r"creativecommons\.org/(licenses|publicdomain)/([a-z\-]+)/([0-9.]+)|creativecommons\.org/publicdomain/(zero|mark)/([0-9.]+)", re.I)
BOILERPLATE = re.compile(r"(?i)\b(cookie|subscribe|sign in|log in|all rights reserved|privacy policy|terms of (use|service)|skip to|advertisement|click here)\b")


@dataclass
class Section:
    heading: str
    text: str


@dataclass
class Page:
    title: str = ""
    sections: list[Section] = field(default_factory=list)
    licences: set[str] = field(default_factory=set)       # normalised ids found in links on the page, e.g. CC-BY-4.0


def licence_id(url: str) -> str | None:
    """creativecommons.org URL -> licence id. 'by/4.0' -> CC-BY-4.0, 'by-nc-sa/4.0' -> CC-BY-NC-SA-4.0, 'zero/1.0' -> CC0-1.0, 'mark/1.0' -> PDM-1.0."""
    m = CC.search(url or "")
    if not m:
        return None
    if m.group(4):
        return "CC0-1.0" if m.group(4).lower() == "zero" else "PDM-1.0"
    kind, version = m.group(2).upper(), m.group(3)
    if kind in ("ZERO",):
        return "CC0-1.0"
    return f"CC-{kind}-{version}"


class _Reader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.page = Page()
        self._skip = 0
        self._tag: str | None = None
        self._buf: list[str] = []
        self._in_title = False
        self._title_tag = ""
        self._heading = ""
        self._paras: list[str] = []

    def _flush_block(self):
        text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
        self._buf = []
        return text

    def _close_section(self):
        if self._paras:
            self.page.sections.append(Section(self._heading, "\n".join(self._paras)))
        self._paras = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("a", "link") and a.get("href") and ("creativecommons.org" in a["href"]):
            lic = licence_id(a["href"])
            if lic:
                self.page.licences.add(lic)
        if tag == "title":
            self._in_title = True
        if tag in SKIP:
            self._skip += 1
            return
        if self._skip:
            return
        if tag in HEADINGS or tag in BLOCKS:
            self._buf = []
            self._tag = tag

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in SKIP:
            self._skip = max(0, self._skip - 1)
            return
        if self._skip or tag != self._tag:
            return
        text = self._flush_block()
        self._tag = None
        if not text:
            return
        if tag in HEADINGS:
            if tag == "h1" and not self.page.title:
                self.page.title = text
            self._close_section()
            self._heading = text
        else:
            self._paras.append(text)

    def handle_data(self, data):
        if self._in_title:
            self._title_tag += data
        if self._skip or self._tag is None:
            return
        self._buf.append(data)


def parse(html: str) -> Page:
    r = _Reader()
    r.feed(html)
    r.close()
    r._close_section()
    r.page.title = r.page.title or re.sub(r"\s+", " ", r._title_tag).strip()      # the visible heading beats the browser-tab title
    return r.page


def clean(sections: list[Section], *, min_chars: int = 200, max_chars: int = 4000) -> list[Section]:
    """Keep real teaching text: long enough, mostly English letters, not site boilerplate, no repeats. Over-long sections are cut at a sentence."""
    seen: set[str] = set()
    out: list[Section] = []
    for s in sections:
        text = s.text.strip()
        letters = [c for c in text if c.isalpha()]
        if len(text) < min_chars or not letters:
            continue
        if sum(c.isascii() for c in letters) / len(letters) < 0.95:        # sources are English; other scripts are handled separately by people
            continue
        if len(BOILERPLATE.findall(text)) >= 2:
            continue
        key = re.sub(r"\W+", " ", text.lower())[:200]
        if key in seen:
            continue
        seen.add(key)
        if len(text) > max_chars:
            cut = text[:max_chars]
            text = cut[: cut.rfind(". ") + 1] or cut
        out.append(Section(s.heading, text))
    return out


def has_copyright_notice(text: str) -> bool:
    """Text that carries its own copyright mark (a quoted third-party passage, a credit line) is not ours to adapt."""
    return bool(re.search(r"(?i)©|\(c\)\s*\d{4}|copyright|used with permission|courtesy of", text))


def relevance(text: str, keywords: list[str]) -> int:
    """How many of the topic's keywords the text mentions (whole words, case-insensitive)."""
    low = text.lower()
    return sum(1 for k in keywords if re.search(rf"\b{re.escape(k.lower())}\b", low))


def select(sections: list[Section], keywords: list[str], *, min_hits: int = 1, limit: int = 8) -> list[Section]:
    """The most on-topic sections first; sections that mention none of the keywords are dropped."""
    scored = [(relevance(s.heading + " " + s.text, keywords), i, s) for i, s in enumerate(sections)]
    keep = sorted((t for t in scored if t[0] >= min_hits), key=lambda t: (-t[0], t[1]))[:limit]
    return [s for _, _, s in sorted(keep, key=lambda t: t[1])]           # back into reading order


def difficulty(text: str) -> float:
    """Flesch-Kincaid grade of the source text, so a draft knows how much simplifying it needs."""
    return round(fk_grade(text), 1)
