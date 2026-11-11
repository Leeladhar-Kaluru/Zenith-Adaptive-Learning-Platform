"""Run the automated lesson gates on a content tree WITHOUT a database, so authors can fix problems before importing.

    python -m app.cms.dryrun ../content                 every lesson
    python -m app.cms.dryrun ../content slug-a slug-b   only these lessons

Prints PASS or FAIL per lesson and, for each failed gate, exactly what is wrong. Exit code 1 if any lesson fails.
Imported-asset checks need the database, so lessons that cite imported assets are checked for structure only here.
"""
from __future__ import annotations

import sys
from pathlib import Path

from app.cms import gates as gate_lib
from app.cms.importer import load_tree, validate_tree


def run(root: Path, only: set[str] | None = None) -> tuple[list[tuple[str, bool, list[str]]], list[str]]:
    tree = load_tree(root)
    errors = validate_tree(tree)
    known = {c.id for c in tree.concepts}
    out = []
    for ch, lessons in tree.chapters:
        for slug in ch.lessons:
            if only and slug not in only:
                continue
            les = lessons[slug]
            blocks = [{k: v for k, v in b.model_dump(mode="json").items() if not (k in ("asset", "diagram") and v is None)} for b in les.blocks]
            codes = {m.code for m in les.misconceptions}
            gates = gate_lib.lesson_gates(
                title=les.title, grade=ch.grade, objectives=les.objectives, blocks=blocks, items=[it.model_dump(mode="json") for it in les.items],
                concept_ids=set(les.concepts), known_concepts=known, graph_error=None, curriculum_verified=False, misconception_codes=codes,
                sources=list(les.sources), assets={})
            bad = [f"{g.name}: {g.detail}" for g in gates if not g.passed and not g.manual]
            out.append((f"{ch.slug}/{slug}", not bad, bad))
    return out, errors


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    results, errors = run(Path(argv[1]), set(argv[2:]) or None)
    for e in errors:
        print("CONTENT ERROR:", e)
    for name, ok, bad in results:
        print(("PASS " if ok else "FAIL ") + name)
        for b in bad:
            print("      -", b)
    failed = sum(1 for _, ok, _ in results if not ok)
    print(f"{len(results) - failed} pass, {failed} fail" + (f", {len(errors)} content errors" if errors else ""))
    return 1 if failed or errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
