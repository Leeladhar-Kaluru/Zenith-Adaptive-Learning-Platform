"""Start a new lesson from a skeleton. Never calls a model, never publishes: every part is a TODO until a person writes it."""
from __future__ import annotations

from pathlib import Path

import yaml

TODO = "TODO"


class DraftError(ValueError):
    pass


def new_lesson_skeleton(chapter_slug: str, slug: str, title: str, concept_ids: list[str]) -> dict:
    first = concept_ids[0]
    return {
        "slug": slug, "title": title, "minutes": 15,
        "objectives": [f"{TODO}: what the student will be able to do after this lesson", f"{TODO}: a second, different outcome"],
        "concepts": list(concept_ids), "origin": "ai_assisted",
        "blocks": [
            {"kind": "text", "heading": f"{TODO}: the big idea", "html": f"<p>{TODO}: explain the idea in your own words, in short sentences.</p>"},
            {"kind": "example", "heading": "Worked example", "prompt": f"{TODO}: a problem to solve", "steps": [f"{TODO}: step 1", f"{TODO}: step 2", f"{TODO}: check the answer"]},
            {"kind": "callout", "tone": "watch", "html": f"{TODO}: the most common mistake and why it is wrong"},
            {"kind": "check", "item": f"{slug}-q1"},
            {"kind": "summary", "points": [f"{TODO}: key point 1", f"{TODO}: key point 2", f"{TODO}: key point 3"]},
        ],
        "items": [{
            "key": f"{slug}-q1", "kind": "mcq", "stem": f"{TODO}: a question", "difficulty": "standard", "purpose": "check", "concepts": [{"id": first}],
            "explanation": f"{TODO}: why the right answer is right", "hints": [f"{TODO}: a nudge"],
            "options": [{"key": "A", "text": f"{TODO} right answer"}, {"key": "B", "text": f"{TODO} wrong answer 1"}, {"key": "C", "text": f"{TODO} wrong answer 2"}], "correct": "A",
        }],
        "misconceptions": [], "cards": [],
    }


def find_todos(obj, path: str = "") -> list[str]:
    """Paths of every string that still says TODO."""
    out: list[str] = []
    if isinstance(obj, str):
        if TODO in obj:
            out.append(path or "(root)")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            out += find_todos(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            out += find_todos(v, f"{path}[{i}]")
    return out


def write_skeleton(root: Path, chapter_slug: str, slug: str, title: str, concept_ids: list[str]) -> Path:
    root = Path(root)
    chapter_file = next((p for p in (root / "chapters").glob("*/chapter.yaml") if yaml.safe_load(p.read_text(encoding="utf-8")).get("slug") == chapter_slug), None)
    if chapter_file is None:
        raise DraftError(f"No chapter '{chapter_slug}' in {root}.")
    target = chapter_file.parent / "lessons" / f"{slug}.yaml"
    if target.exists():
        raise DraftError(f"{target.name} already exists; choose another slug.")
    if not concept_ids:
        raise DraftError("Give at least one concept id.")
    target.parent.mkdir(exist_ok=True)
    target.write_text(yaml.safe_dump(new_lesson_skeleton(chapter_slug, slug, title, concept_ids), sort_keys=False, allow_unicode=True, width=120), encoding="utf-8")
    chapter = yaml.safe_load(chapter_file.read_text(encoding="utf-8"))
    chapter.setdefault("lessons", []).append(slug)
    chapter_file.write_text(yaml.safe_dump(chapter, sort_keys=False, allow_unicode=True, width=120), encoding="utf-8")
    return target
