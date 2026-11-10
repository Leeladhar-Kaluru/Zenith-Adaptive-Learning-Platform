import pytest
from sqlalchemy import select

from app.cms import importer
from app.cms.schema import ItemDef
from app.engine import grading
from app.models import Item
from app.services import diagrams, items as item_svc
from tests.content_fixture import build

DIAGRAM = {"kind": "labelled", "width": 320, "height": 220,
           "shapes": [{"type": "ellipse", "id": "cell", "region": "1", "cx": 160, "cy": 110, "rx": 140, "ry": 90, "fill": "#e6f4ea"},
                      {"type": "circle", "id": "nucleus", "region": "2", "cx": 160, "cy": 110, "r": 28, "fill": "#8f9bff"},
                      {"type": "rect", "id": "vacuole", "region": "3", "x": 205, "y": 85, "width": 40, "height": 30, "fill": "#cde"}]}
PAIRS = {"1": "Cell membrane", "2": "Nucleus", "3": "Vacuole"}
BASE = dict(key="lab1", kind="label_diagram", stem="Match each number to its part", difficulty="standard", purpose="practice", concepts=[{"id": "c"}],
            explanation="The nucleus holds the cell's instructions.", hints=["Start with the biggest part."])


def test_grading_matches_every_number_and_gives_partial_credit():
    spec = {"pairs": PAIRS}
    full = grading.grade("label_diagram", spec, {"pairs": dict(PAIRS)})
    assert full.correct and full.score == 1.0
    part = grading.grade("label_diagram", spec, {"pairs": {"1": "Cell membrane", "2": "Vacuole", "3": "Nucleus"}})
    assert not part.correct and part.score == pytest.approx(1 / 3, abs=0.01)
    assert not grading.grade("label_diagram", spec, {"pairs": {"1": "Cell membrane"}}).correct         # incomplete answers are not correct
    assert grading.grade("label_diagram", spec, {}).score == 0.0


def test_numbered_rendering_shows_numbers_but_never_the_labels():
    svg, alt = diagrams.render({**DIAGRAM, "numbered": True})
    for n in ("1", "2", "3"):
        assert f">{n}<" in svg
    for label in PAIRS.values():
        assert label not in svg and label not in alt


def test_schema_checks_regions_and_labels():
    ItemDef(**BASE, diagram=DIAGRAM, pairs=PAIRS)
    with pytest.raises(ValueError, match="region"):
        ItemDef(**BASE, diagram=DIAGRAM, pairs={"1": "A", "2": "B", "9": "C"})
    with pytest.raises(ValueError, match="at least 3"):
        ItemDef(**BASE, diagram=DIAGRAM, pairs={"1": "A", "2": "B"})
    with pytest.raises(ValueError, match="different"):
        ItemDef(**BASE, diagram=DIAGRAM, pairs={"1": "A", "2": "A", "3": "B"})
    with pytest.raises(ValueError):
        ItemDef(**BASE, pairs=PAIRS)                                    # a diagram is required


def test_an_imported_item_hides_the_answer_and_shuffles_labels(db, tmp_path):
    root = build(tmp_path / "content")
    lesson_file = next((root / "chapters").glob("*/lessons/*.yaml"))
    import yaml
    d = yaml.safe_load(lesson_file.read_text(encoding="utf-8"))
    d["items"].append({**{k: v for k, v in BASE.items() if k != "concepts"}, "concepts": [{"id": d["concepts"][0]}], "diagram": DIAGRAM, "pairs": PAIRS})
    lesson_file.write_text(yaml.safe_dump(d), encoding="utf-8")
    importer.import_tree(db, importer.load_tree(root))
    item = db.scalar(select(Item).where(Item.key == "lab1"))
    assert item.answer_spec == {"pairs": PAIRS} and item.payload["regions"] == ["1", "2", "3"] and item.payload["svg"].startswith("<svg")
    pub = item_svc.public_item(item)
    assert sorted(pub["labels"]) == sorted(PAIRS.values()) and "pairs" not in str(pub) and "answer_spec" not in pub
    assert pub["labels"] == sorted(pub["labels"])                        # sorted, so position never hints at the answer
