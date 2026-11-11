"""Load a content tree (YAML) into the database as reviewable draft/in_review versions. Idempotent by content hash."""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.cms import gates as gate_lib
from app.cms.schema import ChapterFile, ConceptDef, ConceptsFile, CurriculumFile, ItemDef, LessonFile
from app.engine import elo, graph
from app.models import (AuditLog, Board, Card, Chapter, ChapterConcept, Concept, ConceptEdge, CurriculumVersion, GateResult, Item,
                        ItemConcept, Lesson, LessonConcept, LessonVersion, LessonVersionItem, Misconception, OptionMisconception,
                        Subject, ContentProvenance, SourceAsset)


class ContentError(ValueError):
    pass


@dataclass
class Tree:
    curriculum: CurriculumFile
    concepts: list[ConceptDef]
    chapters: list[tuple[ChapterFile, dict[str, LessonFile]]] = field(default_factory=list)


def _yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_tree(root: Path) -> Tree:
    root = Path(root)
    curriculum = CurriculumFile(**_yaml(root / "curriculum.yaml"))
    concepts: list[ConceptDef] = []
    for f in sorted((root / "concepts").glob("*.yaml")):
        concepts += ConceptsFile(**_yaml(f)).concepts
    tree = Tree(curriculum, concepts)
    for d in sorted((root / "chapters").glob("*/chapter.yaml")):
        ch = ChapterFile(**_yaml(d))
        lessons: dict[str, LessonFile] = {}
        for slug in ch.lessons:
            lf = d.parent / "lessons" / f"{slug}.yaml"
            if not lf.exists():
                raise ContentError(f"{ch.slug}: lesson file missing: {lf.name}")
            lesson = LessonFile(**_yaml(lf))
            if lesson.slug != slug:
                raise ContentError(f"{lf.name}: slug '{lesson.slug}' does not match the chapter list '{slug}'")
            lessons[slug] = lesson
        tree.chapters.append((ch, lessons))
    return tree


def validate_tree(tree: Tree) -> list[str]:
    errs: list[str] = []
    ids = [c.id for c in tree.concepts]
    if len(set(ids)) != len(ids):
        errs.append("Duplicate concept ids")
    known = set(ids)
    subjects = {s.id for s in tree.curriculum.subjects}
    boards = {b.id for b in tree.curriculum.boards}
    labels = {(v.board, v.label) for v in tree.curriculum.versions}
    edges: list[tuple[str, str]] = []
    for c in tree.concepts:
        if c.subject not in subjects:
            errs.append(f"concept {c.id}: unknown subject {c.subject}")
        for p in c.prerequisites:
            if p.id not in known:
                errs.append(f"concept {c.id}: unknown prerequisite {p.id}")
            else:
                edges.append((p.id, c.id))
    try:
        graph.topological_order(ids, edges)
    except graph.CycleError as e:
        errs.append(str(e))
    except ValueError as e:
        errs.append(str(e))
    from app.cms.draft import find_todos
    for ch, lessons in tree.chapters:
        for slug, les in lessons.items():
            todos = find_todos(les.model_dump(mode="json"))
            if todos:
                errs.append(f"{ch.slug}/{slug}: unfinished TODO in {len(todos)} place(s), first at {todos[0]}")
        if ch.board not in boards:
            errs.append(f"{ch.slug}: unknown board {ch.board}")
        if (ch.board, ch.curriculum) not in labels:
            errs.append(f"{ch.slug}: unknown curriculum version {ch.curriculum}")
        if ch.subject not in subjects:
            errs.append(f"{ch.slug}: unknown subject {ch.subject}")
        for ref in ch.concepts:
            if ref.id not in known:
                errs.append(f"{ch.slug}: unknown concept {ref.id}")
        for slug, les in lessons.items():
            codes = {m.code for m in les.misconceptions}
            for cid in les.concepts:
                if cid not in known:
                    errs.append(f"{ch.slug}/{slug}: unknown concept {cid}")
            for m in les.misconceptions:
                if m.concept not in known:
                    errs.append(f"{ch.slug}/{slug}: misconception {m.code} has unknown concept {m.concept}")
            for it in les.items:
                for c in it.concepts:
                    if c.id not in known:
                        errs.append(f"{ch.slug}/{slug}/{it.key}: unknown concept {c.id}")
                for o in it.options:
                    if o.misconception and o.misconception not in codes:
                        errs.append(f"{ch.slug}/{slug}/{it.key}: option {o.key} uses undefined misconception {o.misconception}")
            for cd in les.cards:
                if cd.concept not in known:
                    errs.append(f"{ch.slug}/{slug}: card {cd.key} has unknown concept {cd.concept}")
    return errs


def _hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


def _item_payload(it: ItemDef) -> tuple[dict, dict]:
    """(public payload, private answer_spec)."""
    if it.kind in ("mcq", "multi"):
        return {"options": [{"key": o.key, "text": o.text} for o in it.options]}, {"correct": it.correct}
    if it.kind == "truefalse":
        return {}, {"correct": it.correct}
    if it.kind == "numeric":
        return ({"unit": it.unit} if it.unit else {}), {"value": it.value, "tolerance": it.tolerance}
    if it.kind == "fill":
        return {}, {"accepted": it.accepted}
    if it.kind == "label_diagram":
        from app.services.diagrams import render
        svg, _ = render({**it.diagram, "numbered": True})
        return {"svg": svg, "regions": sorted(it.pairs), "labels": sorted(it.pairs.values())}, {"pairs": it.pairs}
    if it.kind == "find_error":
        return {"steps": list(it.steps)}, {"wrong_step": it.wrong_step}
    return {"left": list(it.pairs.keys()), "right": list(it.pairs.values())}, {"pairs": it.pairs}


def _upsert_item(db: Session, it: ItemDef, misc_ids: dict[tuple[str, str], uuid.UUID], codes_to_concept: dict[str, str]) -> Item:
    canon = it.model_dump(mode="json")
    if canon.get("pattern") is None:
        canon.pop("pattern", None)            # untagged items keep their old hash, so nothing is re-versioned
    h = _hash(canon)
    row = db.scalar(select(Item).where(Item.key == it.key, Item.content_hash == h))
    if row:
        return row
    version = (db.scalar(select(func.max(Item.version)).where(Item.key == it.key)) or 0) + 1
    payload, spec = _item_payload(it)
    if it.pattern:
        payload["pattern"] = it.pattern
    prior = db.scalar(select(Item.beta).where(Item.key == it.key).order_by(Item.version.desc()).limit(1))
    row = Item(key=it.key, version=version, kind=it.kind, stem=it.stem, payload=payload, answer_spec=spec,
               explanation=it.explanation, hints=it.hints, difficulty=it.difficulty, beta=prior if prior is not None else elo.BETA_PRIOR[it.difficulty],
               purpose=it.purpose, status="draft", origin="ai_assisted", content_hash=h)
    db.add(row)
    db.flush()
    for c in it.concepts:
        db.add(ItemConcept(item_id=row.id, concept_id=c.id, weight=c.weight))
    for o in it.options:
        if o.misconception:
            mid = misc_ids.get((codes_to_concept[o.misconception], o.misconception))
            if mid:
                db.add(OptionMisconception(item_id=row.id, option_key=o.key, misconception_id=mid))
    return row


def import_tree(db: Session, tree: Tree, actor_id: uuid.UUID | None = None) -> dict:
    errs = validate_tree(tree)
    if errs:
        raise ContentError("Content failed validation:\n - " + "\n - ".join(errs))
    report = {"concepts": len(tree.concepts), "lesson_versions_created": 0, "lesson_versions_unchanged": 0, "items_created": 0, "in_review": 0, "draft": 0}

    for b in tree.curriculum.boards:
        row = db.get(Board, b.id)
        if row: row.name = b.name
        else: db.add(Board(id=b.id, name=b.name, active=True))
    for s in tree.curriculum.subjects:
        row = db.get(Subject, s.id)
        if row: row.name = s.name
        else: db.add(Subject(id=s.id, name=s.name))
    db.flush()
    versions: dict[tuple[str, str], CurriculumVersion] = {}
    for v in tree.curriculum.versions:
        row = db.scalar(select(CurriculumVersion).where(CurriculumVersion.board_id == v.board, CurriculumVersion.label == v.label))
        if row:
            row.effective_year, row.verified, row.note = v.effective_year, v.verified, v.note
        else:
            row = CurriculumVersion(board_id=v.board, label=v.label, effective_year=v.effective_year, verified=v.verified, note=v.note)
            db.add(row)
        versions[(v.board, v.label)] = row
    db.flush()

    for c in tree.concepts:
        row = db.get(Concept, c.id)
        vals = dict(title=c.title, description=c.description, grade=c.grade, subject_id=c.subject, keywords=c.keywords, enrichment=c.enrichment)
        if row:
            for k, v in vals.items(): setattr(row, k, v)
        else:
            db.add(Concept(id=c.id, **vals))
    db.flush()
    imported = [c.id for c in tree.concepts]
    db.query(ConceptEdge).filter(ConceptEdge.concept_id.in_(imported)).delete(synchronize_session=False)
    for c in tree.concepts:
        for p in c.prerequisites:
            db.add(ConceptEdge(prereq_id=p.id, concept_id=c.id, strength=p.strength, rationale=p.why))
    db.flush()
    all_edges = [(e.prereq_id, e.concept_id) for e in db.scalars(select(ConceptEdge))]
    all_ids = [c for (c,) in db.execute(select(Concept.id))]
    try:
        graph.topological_order(all_ids, all_edges)
        graph_error = None
    except graph.CycleError as e:
        raise ContentError(str(e)) from e
    known = set(all_ids)

    for ch, lessons in tree.chapters:
        cv = versions[(ch.board, ch.curriculum)]
        chapter = db.scalar(select(Chapter).where(Chapter.slug == ch.slug))
        if chapter is None:
            chapter = Chapter(slug=ch.slug, version_id=cv.id, grade=ch.grade, subject_id=ch.subject, number=ch.number, title=ch.title,
                              summary=ch.summary, status="in_production")
            db.add(chapter)
        else:
            chapter.version_id, chapter.grade, chapter.subject_id, chapter.number = cv.id, ch.grade, ch.subject, ch.number
            chapter.title, chapter.summary = ch.title, ch.summary
        db.flush()
        db.query(ChapterConcept).filter(ChapterConcept.chapter_id == chapter.id).delete()
        for ref in ch.concepts:
            db.add(ChapterConcept(chapter_id=chapter.id, concept_id=ref.id, role=ref.role))

        # Lessons may be inserted or reordered: park existing ones out of the way, then give each its final position.
        db.execute(update(Lesson).where(Lesson.chapter_id == chapter.id).values(position=Lesson.position + 1000))
        for pos, slug in enumerate(ch.lessons, start=1):
            les = lessons[slug]
            lesson = db.scalar(select(Lesson).where(Lesson.chapter_id == chapter.id, Lesson.slug == slug))
            if lesson is None:
                lesson = Lesson(chapter_id=chapter.id, slug=slug, position=pos)
                db.add(lesson)
            else:
                lesson.position = pos
            db.flush()
            misc_ids: dict[tuple[str, str], uuid.UUID] = {}
            codes_to_concept = {m.code: m.concept for m in les.misconceptions}
            for m in les.misconceptions:
                row = db.scalar(select(Misconception).where(Misconception.concept_id == m.concept, Misconception.code == m.code))
                if row: row.description = m.description
                else:
                    row = Misconception(concept_id=m.concept, code=m.code, description=m.description)
                    db.add(row)
                    db.flush()
                misc_ids[(m.concept, m.code)] = row.id
            before = db.scalar(select(func.count(Item.id)))
            item_rows = [_upsert_item(db, it, misc_ids, codes_to_concept) for it in les.items]
            report["items_created"] += (db.scalar(select(func.count(Item.id))) or 0) - (before or 0)

            # an unused figure `asset` key is dropped so lessons that never use imported images keep their existing content hash
            blocks = [{k: v for k, v in b.model_dump(mode="json").items() if not (k in ("asset", "diagram") and v is None)} for b in les.blocks]
            sig = {"t": les.title, "m": les.minutes, "o": les.objectives, "b": blocks, "i": [r.content_hash for r in item_rows],
                   "c": sorted(les.concepts), "l": les.language, "cards": [c.model_dump() for c in les.cards]}
            if les.sources:
                sig["s"] = sorted(les.sources)
            h = _hash(sig)

            def gate_version(lv, les=les, blocks=blocks, ch=ch, cv=cv, codes_to_concept=codes_to_concept):
                """Run the automated gates for a version and set draft or in_review. Safe to repeat: earlier results are replaced."""
                asset_rows = {}
                wanted = set(les.sources) | {b["asset"] for b in blocks if b["kind"] == "figure" and b.get("asset")} | {b["config"]["dataset"] for b in blocks if b["kind"] == "widget" and (b.get("config") or {}).get("dataset")} | {x.strip() for b in blocks if b["kind"] == "widget" for x in str((b.get("config") or {}).get("overlays", "")).split(",") if x.strip()}
                for sid in wanted:
                    try:
                        row = db.get(SourceAsset, uuid.UUID(sid))
                    except ValueError:
                        row = None
                    if row is not None:
                        asset_rows[sid] = row
                have = {x for (x,) in db.execute(select(ContentProvenance.asset_id).where(ContentProvenance.lesson_version_id == lv.id))}
                for sid in les.sources:
                    if sid in asset_rows and asset_rows[sid].id not in have:
                        db.add(ContentProvenance(lesson_version_id=lv.id, asset_id=asset_rows[sid].id))
                gates = gate_lib.lesson_gates(
                    title=les.title, grade=ch.grade, objectives=les.objectives, blocks=blocks,
                    items=[it.model_dump(mode="json") for it in les.items], concept_ids=set(les.concepts), known_concepts=known,
                    graph_error=graph_error, curriculum_verified=cv.verified, misconception_codes=set(codes_to_concept),
                    sources=list(les.sources), assets={k: {"status": v.status, "attribution": v.attribution_text, "kind": v.kind, "stored": bool(v.storage_path)} for k, v in asset_rows.items()})
                db.query(GateResult).filter(GateResult.lesson_version_id == lv.id).delete()
                for g in gates:
                    db.add(GateResult(lesson_version_id=lv.id, name=g.name, passed=g.passed, manual=g.manual, detail=g.detail))
                lv.status = "in_review" if all(g.passed for g in gates if not g.manual) else "draft"

            latest = db.scalar(select(LessonVersion).where(LessonVersion.lesson_id == lesson.id, LessonVersion.language == les.language)
                               .order_by(LessonVersion.version.desc()).limit(1))
            if latest and latest.content_hash == h:
                if latest.status in ("draft", "in_review"):         # an asset may have been approved since: look again. Published versions are never touched.
                    before = latest.status
                    gate_version(latest)
                    if latest.status != before:
                        report["regated"] = report.get("regated", 0) + 1
                report["lesson_versions_unchanged"] += 1
                continue

            lv = LessonVersion(lesson_id=lesson.id, version=(latest.version + 1) if latest else 1, language=les.language, title=les.title,
                               minutes=les.minutes, objectives=les.objectives, blocks=blocks, status="draft", origin=les.origin,
                               content_hash=h, author_id=actor_id)
            db.add(lv)
            db.flush()
            for i, r in enumerate(item_rows):
                db.add(LessonVersionItem(lesson_version_id=lv.id, item_id=r.id, position=i))
            db.query(LessonConcept).filter(LessonConcept.lesson_id == lesson.id).delete()
            for cid in les.concepts:
                db.add(LessonConcept(lesson_id=lesson.id, concept_id=cid))
            for cd in les.cards:
                db.add(Card(lesson_version_id=lv.id, key=cd.key, concept_id=cd.concept, front=cd.front, back=cd.back))

            gate_version(lv)
            report["in_review" if lv.status == "in_review" else "draft"] += 1
            report["lesson_versions_created"] += 1
            db.add(AuditLog(actor_id=actor_id, action="content.import", entity="lesson_version", entity_id=str(lv.id),
                            detail={"lesson": f"{ch.slug}/{slug}", "version": lv.version, "status": lv.status}))
    db.commit()
    return report
