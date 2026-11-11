"""Stage 4 of the source-to-lesson pipeline: turn the stored text of an APPROVED open-licence page into a simple draft lesson for one class.

The model only supplies content, as structured JSON. All markup, ids, schema fields and credits are built here, so the draft always has the
right shape and cannot carry HTML, scripts or links. What the model cannot supply (a diagram) is left as a TODO that blocks publishing.
The draft is always `origin: ai_assisted`, always cites its source, never publishes itself, and goes through the usual gates and review."""
from __future__ import annotations

import html
import json
import re
from typing import Awaitable, Callable

from app.cms.draft import TODO
from app.models import SourceAsset

MAX_SOURCE_CHARS = 9000
LEVELS = ("intro", "standard", "challenge")


class AutoDraftError(ValueError):
    pass


def build_prompt(asset: SourceAsset, grade: int, subject: str, title: str, concept_title: str) -> str:
    sections = "\n\n".join(f"## {s['heading']}\n{s['text']}" for s in asset.data["sections"])[:MAX_SOURCE_CHARS]
    return (
        f"You are an experienced Class {grade} {subject} teacher in India writing an ORIGINAL lesson called '{title}' about '{concept_title}'. "
        f"Use ONLY the facts in the SOURCE below. Rewrite everything in your own simple words for a Class {grade} student: short sentences (about 12 words), "
        "explain every new word where it first appears, give everyday Indian examples, and never copy sentences. Do not add facts that are not in the source. "
        "If you are not sure of something, leave it out.\n"
        "Reply with ONE JSON object and nothing else, with exactly these keys:\n"
        '{"objectives":[3 or 4 strings starting with a verb],'
        '"sections":[{"heading":str,"paragraphs":[1 to 3 short paragraphs]}] (2 to 4 sections),'
        '"examples":[{"prompt":str,"steps":[at least 3 strings, the last one checks the answer]}] (2 examples),'
        '"mistake":"the most common wrong idea and why it is wrong","real_life":"one everyday use",'
        '"items":[{"level":"intro|standard|challenge","stem":str,"options":[{"text":str,"mistake":"a short label of the wrong idea behind this option, or empty for the right one"} x4],'
        '"correct":0-3,"explanation":str}] (8 to 10 questions, at least one of each level, exactly one correct option, wrong options that are really wrong),'
        '"summary":[3 or 4 short points],"cards":[{"front":str,"back":str}] (4 cards)}\n\n'
        f"SOURCE ({asset.attribution_text}):\n{sections}")


def parse_model_json(raw: str) -> dict:
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        raise AutoDraftError("The model did not return a JSON object.")
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise AutoDraftError(f"The model's JSON could not be read: {e.msg}.") from e
    if not isinstance(data, dict):
        raise AutoDraftError("The model returned JSON that is not an object.")
    return data


def _t(v, limit: int) -> str:
    """Plain text only: tags removed, entities and control characters dropped, length capped."""
    s = re.sub(r"<[^>]*>", "", str(v or ""))
    s = re.sub(r"[\x00-\x1f\x7f]", " ", html.unescape(s))
    return re.sub(r"\s+", " ", s).strip()[:limit]


def _slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:40] or "mistake"


def assemble(data: dict, *, slug: str, title: str, grade: int, concept_id: str, asset_id: str, minutes: int = 20) -> dict:
    """Model JSON -> a lesson dict in ZENITH's schema. Raises AutoDraftError for output too broken to use; thin output is kept and left for the gates."""
    secs = [s for s in data.get("sections", []) if isinstance(s, dict) and _t(s.get("heading"), 120)]
    items_in = [i for i in data.get("items", []) if isinstance(i, dict)]
    if not secs or not items_in:
        raise AutoDraftError("The model's answer has no teaching sections or no questions.")
    blocks: list[dict] = []
    for s in secs[:4]:
        paras = [_t(p, 700) for p in s.get("paragraphs", []) if _t(p, 700)][:3]
        blocks.append({"kind": "text", "heading": _t(s["heading"], 120), "html": "".join(f"<p>{html.escape(p, quote=False)}</p>" for p in paras) or f"<p>{TODO}</p>"})
    blocks.append({"kind": "figure", "svg": f"{TODO}: draw an original diagram", "alt": f"{TODO}: describe what the diagram shows", "caption": f"{TODO}: caption"})
    for ex in data.get("examples", [])[:2]:
        steps = [_t(x, 300) for x in (ex.get("steps") or []) if _t(x, 300)] if isinstance(ex, dict) else []
        if isinstance(ex, dict) and _t(ex.get("prompt"), 300) and len(steps) >= 2:
            blocks.append({"kind": "example", "heading": "Worked example", "prompt": _t(ex["prompt"], 300), "steps": steps[:6]})
    if _t(data.get("mistake"), 400):
        blocks.append({"kind": "callout", "tone": "watch", "html": html.escape(_t(data["mistake"], 400), quote=False)})
    if _t(data.get("real_life"), 400):
        blocks.append({"kind": "callout", "tone": "real", "html": html.escape(_t(data["real_life"], 400), quote=False)})

    items, misconceptions = [], {}
    for n, it in enumerate(items_in[:10], start=1):
        opts = [o for o in it.get("options", []) if isinstance(o, dict) and _t(o.get("text"), 200)]
        correct = it.get("correct")
        if len(opts) != 4 or not isinstance(correct, int) or not 0 <= correct <= 3 or len({_t(o["text"], 200).lower() for o in opts}) != 4 or not _t(it.get("stem"), 400):
            continue                                                # a broken question is dropped, never repaired by guessing
        options = []
        for k, o in zip("ABCD", opts):
            opt = {"key": k, "text": _t(o["text"], 200)}
            label = _t(o.get("mistake"), 160)
            if label and "ABCD".index(k) != correct:
                code = _slug(label)
                misconceptions.setdefault(code, label)
                opt["misconception"] = code
            options.append(opt)
        level = it.get("level") if it.get("level") in LEVELS else "standard"
        items.append({"key": f"q-{slug[:18]}-{n}", "kind": "mcq", "stem": _t(it["stem"], 400), "difficulty": level, "purpose": "check" if n <= 3 else "practice",
                      "concepts": [{"id": concept_id}], "explanation": _t(it.get("explanation"), 400) or f"{TODO}: explain why the answer is right",
                      "hints": [f"{TODO}: a nudge"], "options": options, "correct": "ABCD"[correct]})
    if not items:
        raise AutoDraftError("None of the model's questions were usable.")
    for i in range(min(3, len(items))):
        blocks.append({"kind": "check", "item": items[i]["key"]})
    summary = [_t(p, 200) for p in data.get("summary", []) if _t(p, 200)][:4]
    blocks.append({"kind": "summary", "points": summary or [f"{TODO}: key point"]})
    objectives = [_t(o, 160) for o in data.get("objectives", []) if _t(o, 160)][:4] or [f"{TODO}: what the student will be able to do"]
    cards = [{"key": f"{slug}-card-{i}", "concept": concept_id, "front": _t(c.get("front"), 160), "back": _t(c.get("back"), 240)}
             for i, c in enumerate(data.get("cards", [])[:4], start=1) if isinstance(c, dict) and _t(c.get("front"), 160) and _t(c.get("back"), 240)]
    return {"slug": slug, "title": title, "minutes": minutes, "objectives": objectives, "concepts": [concept_id], "origin": "ai_assisted", "sources": [asset_id],
            "blocks": blocks, "items": items, "misconceptions": [{"code": c, "concept": concept_id, "description": d} for c, d in misconceptions.items()], "cards": cards}


async def draft(asset: SourceAsset, *, grade: int, subject: str, slug: str, title: str, concept_id: str, concept_title: str,
                generate: Callable[..., Awaitable[str]]) -> dict:
    """Ask the model (any async `generate(messages=..., temperature=..., max_tokens=...)`) and assemble the draft. Only an approved source may be used."""
    if asset.kind != "text":
        raise AutoDraftError("Only a text source can be turned into a lesson draft.")
    if asset.status != "approved":
        raise AutoDraftError("The source page must be approved by a reviewer before it is used to draft a lesson.")
    raw = await generate(messages=[{"role": "user", "content": build_prompt(asset, grade, subject, title, concept_title)}], temperature=0.3, max_tokens=4500)
    return assemble(parse_model_json(raw), slug=slug, title=title, grade=grade, concept_id=concept_id, asset_id=str(asset.id))
