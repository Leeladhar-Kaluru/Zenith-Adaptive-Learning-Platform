"""Original infographics built from structured text, so a draft gets a real diagram without any copied image.

Two layouts: a flow (numbered steps joined by arrows) and a comparison (two columns). Every string is escaped, text is wrapped to fixed widths, the SVG uses
no external references and no scripts, and an alt text is built from the same content. Colours come from the app's CSS tokens."""
from __future__ import annotations

import html
import textwrap

MAX_STEPS = 6
MAX_ROWS = 5
LINE = 26          # characters per line inside a box


def _t(v, limit: int) -> str:
    return " ".join(str(v or "").replace("<", " ").replace(">", " ").split())[:limit]


def _lines(text: str, width: int = LINE, most: int = 4) -> list[str]:
    out = textwrap.wrap(text, width) or [""]
    return out[:most - 1] + [out[most - 1].rstrip(" .,;") + "..."] if len(out) > most else out


def _text(x: int, y: int, lines: list[str], size: int = 13, anchor: str = "middle", weight: str = "400") -> str:
    spans = "".join(f'<tspan x="{x}" dy="{0 if i == 0 else size + 3}">{html.escape(l)}</tspan>' for i, l in enumerate(lines))
    return f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="currentColor">{spans}</text>'


def flow(title: str, steps: list[str]) -> tuple[str, str]:
    """Numbered boxes top to bottom with arrows between them."""
    steps = [s for s in (_t(x, 120) for x in steps) if s][:MAX_STEPS]
    if len(steps) < 2:
        raise ValueError("A flow needs at least two steps.")
    title = _t(title, 80) or "Steps"
    box_h, gap, w = 58, 22, 300
    h = 44 + len(steps) * box_h + (len(steps) - 1) * gap + 12
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="{html.escape(title)}">',
             f'<defs><marker id="ar" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="currentColor"/></marker></defs>',
             _text(w // 2, 24, [title], 15, weight="700")]
    y = 40
    for i, s in enumerate(steps):
        parts.append(f'<rect x="14" y="{y}" width="{w - 28}" height="{box_h}" rx="12" fill="var(--surface-2, #f4f1e8)" stroke="currentColor" stroke-width="2"/>')
        parts.append(f'<circle cx="38" cy="{y + box_h // 2}" r="13" fill="var(--brand, #ffb800)" stroke="currentColor" stroke-width="2"/>')
        parts.append(_text(38, y + box_h // 2 + 5, [str(i + 1)], 13, weight="700"))
        ls = _lines(s)
        parts.append(_text(168, y + box_h // 2 - (len(ls) - 1) * 8 + 4, ls, 12))
        if i < len(steps) - 1:
            parts.append(f'<line x1="{w // 2}" y1="{y + box_h + 2}" x2="{w // 2}" y2="{y + box_h + gap - 2}" stroke="currentColor" stroke-width="2.5" marker-end="url(#ar)"/>')
        y += box_h + gap
    parts.append("</svg>")
    alt = f"{title}. " + " Then ".join(f"Step {i + 1}: {s}" for i, s in enumerate(steps)) + "."
    return "".join(parts), alt[:600]


def compare(title: str, left_name: str, left: list[str], right_name: str, right: list[str]) -> tuple[str, str]:
    """Two columns with a heading each."""
    left = [s for s in (_t(x, 90) for x in left) if s][:MAX_ROWS]
    right = [s for s in (_t(x, 90) for x in right) if s][:MAX_ROWS]
    ln, rn, title = _t(left_name, 24), _t(right_name, 24), _t(title, 80) or "Compare"
    if not left or not right or not ln or not rn:
        raise ValueError("A comparison needs two named columns with at least one point each.")
    row_h, w = 56, 300
    rows = max(len(left), len(right))
    h = 80 + rows * row_h + 10
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="{html.escape(title)}">', _text(w // 2, 22, [title], 15, weight="700")]
    for col, (name, items, x) in enumerate(((ln, left, 12), (rn, right, 156))):
        parts.append(f'<rect x="{x}" y="36" width="132" height="30" rx="10" fill="var(--brand, #ffb800)" stroke="currentColor" stroke-width="2"/>')
        parts.append(_text(x + 66, 56, [name], 13, weight="700"))
        for i, s in enumerate(items):
            y = 76 + i * row_h
            parts.append(f'<rect x="{x}" y="{y}" width="132" height="{row_h - 6}" rx="10" fill="var(--surface-2, #f4f1e8)" stroke="currentColor" stroke-width="1.5"/>')
            ls = _lines(s, 17, 3)
            parts.append(_text(x + 66, y + (row_h - 6) // 2 - (len(ls) - 1) * 7 + 4, ls, 11))
    parts.append("</svg>")
    alt = f"{title}. {ln}: " + "; ".join(left) + f". {rn}: " + "; ".join(right) + "."
    return "".join(parts), alt[:600]


def build(spec: dict) -> tuple[str, str]:
    """From the model's structured spec to (svg, alt). Raises ValueError when the spec is unusable, so the caller keeps a visible TODO instead."""
    if not isinstance(spec, dict):
        raise ValueError("No infographic given.")
    kind = spec.get("type")
    if kind == "flow":
        return flow(spec.get("title"), [s for s in spec.get("steps", []) if isinstance(s, str)])
    if kind == "compare":
        return compare(spec.get("title"), spec.get("left_name"), [s for s in spec.get("left", []) if isinstance(s, str)],
                       spec.get("right_name"), [s for s in spec.get("right", []) if isinstance(s, str)])
    raise ValueError("Unknown infographic type.")
