"""Draw original diagrams from a small, strictly validated spec. Everything is escaped or range-checked, so a spec can never inject markup."""
from __future__ import annotations

import html
import math
import re

COLOR = re.compile(r"^#[0-9a-fA-F]{3,8}$")
NAMED = {"none", "currentColor"}
ID = re.compile(r"^[a-z0-9_-]{1,30}$")


class DiagramError(ValueError):
    pass


def _n(v, name: str, lo: float = -5000, hi: float = 5000) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise DiagramError(f"{name} must be a number")
    if not math.isfinite(f) or not lo <= f <= hi:
        raise DiagramError(f"{name} must be a number from {lo:g} to {hi:g}")
    return f


def _color(v, name: str, default: str) -> str:
    v = v if v is not None else default
    if v in NAMED or (isinstance(v, str) and COLOR.match(v)):
        return v
    raise DiagramError(f"{name} must be a hex colour like #8f9bff")


def _t(s, limit: int = 60) -> str:
    if not isinstance(s, str) or not s.strip() or len(s) > limit:
        raise DiagramError(f"text must be 1 to {limit} characters")
    return html.escape(s.strip(), quote=True)


def _f(x: float) -> str:
    return f"{x:.1f}".rstrip("0").rstrip(".")


def _open(w: float, h: float) -> str:
    return f'<svg viewBox="0 0 {_f(w)} {_f(h)}" font-family="sans-serif">'


def _labelled(spec: dict) -> tuple[str, str]:
    w, h = _n(spec.get("width"), "width", 50, 1000), _n(spec.get("height"), "height", 50, 1000)
    parts, anchors = [_open(w, h)], {}
    for sh in spec.get("shapes", []):
        t, sid = sh.get("type"), sh.get("id", "")
        if sid and not ID.match(str(sid)):
            raise DiagramError("shape id must be lowercase letters, digits, - or _")
        fill, stroke = _color(sh.get("fill"), "fill", "none"), _color(sh.get("stroke"), "stroke", "#14193a")
        style = f'fill="{fill}" stroke="{stroke}" stroke-width="2"'
        if t == "circle":
            cx, cy, r = _n(sh.get("cx"), "cx"), _n(sh.get("cy"), "cy"), _n(sh.get("r"), "r", 0, 2000)
            parts.append(f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r)}" {style}/>')
            anchors[sid] = (cx, cy)
        elif t == "ellipse":
            cx, cy = _n(sh.get("cx"), "cx"), _n(sh.get("cy"), "cy")
            rx, ry = _n(sh.get("rx"), "rx", 0, 2000), _n(sh.get("ry"), "ry", 0, 2000)
            parts.append(f'<ellipse cx="{_f(cx)}" cy="{_f(cy)}" rx="{_f(rx)}" ry="{_f(ry)}" {style}/>')
            anchors[sid] = (cx, cy)
        elif t == "rect":
            x, y = _n(sh.get("x"), "x"), _n(sh.get("y"), "y")
            rw, rh = _n(sh.get("width"), "width", 0, 2000), _n(sh.get("height"), "height", 0, 2000)
            parts.append(f'<rect x="{_f(x)}" y="{_f(y)}" width="{_f(rw)}" height="{_f(rh)}" rx="4" {style}/>')
            anchors[sid] = (x + rw / 2, y + rh / 2)
        elif t == "line":
            x1, y1, x2, y2 = (_n(sh.get(k), k) for k in ("x1", "y1", "x2", "y2"))
            parts.append(f'<line x1="{_f(x1)}" y1="{_f(y1)}" x2="{_f(x2)}" y2="{_f(y2)}" stroke="{stroke}" stroke-width="2"/>')
        else:
            raise DiagramError(f"unknown shape type '{t}'")
    names = []
    for lb in spec.get("labels", []):
        x, y, text = _n(lb.get("x"), "x"), _n(lb.get("y"), "y"), _t(lb.get("text"))
        target = lb.get("target")
        if target is not None:
            if target not in anchors:
                raise DiagramError(f"label points at '{target}', which is not a shape")
            ax, ay = anchors[target]
            parts.append(f'<line x1="{_f(x + 4)}" y1="{_f(y - 4)}" x2="{_f(ax)}" y2="{_f(ay)}" stroke="currentColor" stroke-width="1.5" stroke-dasharray="4 3"/>')
        parts.append(f'<text x="{_f(x)}" y="{_f(y)}" font-size="13" font-weight="700" fill="currentColor">{text}</text>')
        names.append(html.unescape(text))
    parts.append("</svg>")
    if len(names) > 1:
        alt = f"A labelled diagram. Labels: {', '.join(names[:-1])} and {names[-1]}."
    elif names:
        alt = f"A labelled diagram. Label: {names[0]}."
    else:
        alt = "A diagram."
    return "".join(parts), alt


def _axes(spec: dict) -> tuple[str, str]:
    xmin, xmax, ymin, ymax = (_n(spec.get(k), k, -1000, 1000) for k in ("xmin", "xmax", "ymin", "ymax"))
    if xmax <= xmin or ymax <= ymin:
        raise DiagramError("axes need max greater than min")
    W, H, pad = 300.0, 300.0, 24.0

    def px(v):
        return pad + (v - xmin) / (xmax - xmin) * (W - 2 * pad)

    def py(v):
        return H - pad - (v - ymin) / (ymax - ymin) * (H - 2 * pad)

    parts = [_open(W, H)]
    if xmin <= 0 <= xmax:
        parts.append(f'<line x1="{_f(px(0))}" y1="{_f(pad)}" x2="{_f(px(0))}" y2="{_f(H - pad)}" stroke="currentColor" stroke-width="1.5"/>')
    if ymin <= 0 <= ymax:
        parts.append(f'<line x1="{_f(pad)}" y1="{_f(py(0))}" x2="{_f(W - pad)}" y2="{_f(py(0))}" stroke="currentColor" stroke-width="1.5"/>')
    desc = []
    line = spec.get("line")
    if line:
        m, c = _n(line.get("m"), "m", -1000, 1000), _n(line.get("c"), "c", -1000, 1000)
        parts.append(f'<line x1="{_f(px(xmin))}" y1="{_f(py(m * xmin + c))}" x2="{_f(px(xmax))}" y2="{_f(py(m * xmax + c))}" stroke="#3a46d6" stroke-width="3"/>')
        desc.append(f"a straight line with slope {m:g} and intercept {c:g}")
    pts = spec.get("points", [])
    for p in pts:
        x, y = _n(p[0], "x", -1000, 1000), _n(p[1], "y", -1000, 1000)
        parts.append(f'<circle cx="{_f(px(x))}" cy="{_f(py(y))}" r="4" fill="#d62f58"/>')
    if pts:
        desc.append(f"{len(pts)} marked point{'s' if len(pts) != 1 else ''}")
    parts.append("</svg>")
    cap = html.unescape(_t(spec["caption"], 120)) if spec.get("caption") else ""
    alt = f"A graph with x from {xmin:g} to {xmax:g} and y from {ymin:g} to {ymax:g}"
    if desc:
        alt += ", showing " + " and ".join(desc)
    alt += "." + (f" {cap}" if cap else "")
    return "".join(parts), alt


def _table(spec: dict) -> tuple[str, str]:
    headers = [_t(h, 30) for h in spec.get("headers", [])]
    rows = [[_t(c, 30) for c in r] for r in spec.get("rows", [])]
    if not headers or not rows or any(len(r) != len(headers) for r in rows) or len(rows) > 20 or len(headers) > 6:
        raise DiagramError("a table needs 1 to 6 headers and up to 20 rows of the same width")
    cw, rh = 110.0, 28.0
    W, H = cw * len(headers), rh * (len(rows) + 1)
    parts = [_open(W, H)]
    for r, cells in enumerate([headers] + rows):
        for c, text in enumerate(cells):
            fill = "#e6e8ff" if r == 0 else "none"
            weight = ' font-weight="700"' if r == 0 else ""
            parts.append(f'<rect x="{_f(c * cw)}" y="{_f(r * rh)}" width="{_f(cw)}" height="{_f(rh)}" fill="{fill}" stroke="currentColor" stroke-width="1"/>')
            parts.append(f'<text x="{_f(c * cw + 8)}" y="{_f(r * rh + 18)}" font-size="13"{weight} fill="currentColor">{text}</text>')
    parts.append("</svg>")
    alt = f"A table with columns {', '.join(html.unescape(h) for h in headers)} and {len(rows)} rows."
    return "".join(parts), alt


def render(spec: dict) -> tuple[str, str]:
    """Return (svg, alt_text) for a diagram spec of kind labelled, axes or table."""
    kind = spec.get("kind") if isinstance(spec, dict) else None
    if kind == "labelled":
        return _labelled(spec)
    if kind == "axes":
        return _axes(spec)
    if kind == "table":
        return _table(spec)
    raise DiagramError("diagram kind must be labelled, axes or table")
