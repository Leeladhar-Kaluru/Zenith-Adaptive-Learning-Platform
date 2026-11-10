import pytest

from app.cms.schema import FigureBlock
from app.services import diagrams

CELL = {"kind": "labelled", "width": 320, "height": 220,
        "shapes": [{"type": "ellipse", "id": "cell", "cx": 160, "cy": 110, "rx": 140, "ry": 90, "fill": "#e6f4ea"},
                   {"type": "circle", "id": "nucleus", "cx": 160, "cy": 110, "r": 28, "fill": "#8f9bff"},
                   {"type": "rect", "id": "vacuole", "x": 205, "y": 85, "width": 40, "height": 30, "fill": "#cde"}],
        "labels": [{"text": "Cell membrane", "x": 20, "y": 20, "target": "cell"}, {"text": "Nucleus", "x": 20, "y": 200, "target": "nucleus"}, {"text": "Vacuole", "x": 250, "y": 200, "target": "vacuole"}]}


def test_every_label_is_drawn_and_named_in_the_alt_text():
    svg, alt = diagrams.render(CELL)
    for label in ("Cell membrane", "Nucleus", "Vacuole"):
        assert label in svg and label in alt
    assert svg.startswith("<svg") and "viewBox" in svg


def test_markup_and_external_references_are_neutralised():
    evil = {**CELL, "labels": [{"text": '<script>alert(1)</script><img src=x onerror=alert(2)>', "x": 10, "y": 10, "target": "cell", "href": "https://evil.example"}],
            "shapes": [{**CELL["shapes"][0], "onclick": "x()", "href": "https://evil.example/a"}, *CELL["shapes"][1:]]}
    svg, alt = diagrams.render(evil)
    low = svg.lower()
    assert "<script" not in low and "<img" not in low and "onerror" not in low.replace("&lt;img src=x onerror", "") and "onclick" not in low and "href" not in low
    assert "http" not in low


def test_rendering_is_deterministic():
    assert diagrams.render(CELL) == diagrams.render(CELL)


def test_axes_and_table_kinds():
    svg, alt = diagrams.render({"kind": "axes", "xmin": -5, "xmax": 5, "ymin": -5, "ymax": 5, "points": [[1, 2], [-3, 4]], "line": {"m": 1, "c": 0}, "caption": "y = x"})
    assert "<line" in svg and "<circle" in svg and "y = x" in alt
    svg, alt = diagrams.render({"kind": "table", "headers": ["Mass (g)", "Volume (cm3)"], "rows": [["60", "20"], ["30", "10"]]})
    assert "Mass (g)" in svg and "60" in svg and "2 rows" in alt


@pytest.mark.parametrize("bad", [
    {"kind": "labelled", "width": 320, "height": 220, "shapes": [{"type": "script", "id": "x"}], "labels": []},
    {"kind": "labelled", "width": 99999, "height": 220, "shapes": [], "labels": []},
    {"kind": "labelled", "width": 320, "height": 220, "shapes": [{"type": "circle", "id": "c", "cx": "nan", "cy": 1, "r": 1}], "labels": []},
    {"kind": "labelled", "width": 320, "height": 220, "shapes": [{"type": "circle", "id": "c", "cx": 1, "cy": 1, "r": 1, "fill": "url(http://x)"}], "labels": []},
    {"kind": "labelled", "width": 320, "height": 220, "shapes": [], "labels": [{"text": "x", "x": 1, "y": 1, "target": "missing"}]},
    {"kind": "pie"},
])
def test_bad_specs_are_refused(bad):
    with pytest.raises(diagrams.DiagramError):
        diagrams.render(bad)


def test_a_figure_can_be_defined_by_a_diagram_spec():
    f = FigureBlock(kind="figure", diagram=CELL, alt="", caption="A cell.")
    assert f.svg.startswith("<svg") and "Nucleus" in f.alt
    kept = FigureBlock(kind="figure", diagram=CELL, alt="My own alt text for the cell", caption="")
    assert kept.alt == "My own alt text for the cell"
