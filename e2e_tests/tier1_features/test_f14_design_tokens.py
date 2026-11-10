"""
Feature 14: "Kite & Chalk" Design System Tokens
Comprehensive non-tautological test suite verifying real CSS tokens from frontend/src/tokens.css.

Tests inspect tokens.css on disk to ensure:
- Canonical warm off-white parchment canvas (#FDFBF7)
- Dark ink charcoal borders (#1E1E1E) with 2px/1.5px heavy and medium borders
- Pastel tile fills (saffron, ultramarine, terracotta, peach, olive) with valid 7-char hex
- Hard-edged neo-brutalist drop shadows with 0px blur radius and monotonic offsets
- Rounded corner radii (sharp, micro, box, pill) and card radius binding
"""

import os
import re
import pytest

def _resolve_tokens_css_path() -> str:
    """Locates frontend/src/tokens.css relative to repository root or test directory."""
    candidates = [
        os.path.join("frontend", "src", "tokens.css"),
        os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src", "tokens.css"),
    ]
    for candidate in candidates:
        abs_path = os.path.abspath(candidate)
        if os.path.isfile(abs_path):
            return abs_path
    raise FileNotFoundError("Could not locate frontend/src/tokens.css on filesystem.")

def _read_tokens_css() -> str:
    path = _resolve_tokens_css_path()
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def _get_css_variable_definitions(css_content: str, var_name: str) -> list[str]:
    """Finds all defined values for a specific CSS variable in css_content."""
    pattern = rf"{re.escape(var_name)}\s*:\s*([^;]+);"
    return [match.strip() for match in re.findall(pattern, css_content)]


def test_canvas_color_token():
    """Feature 14: Canvas color is warm off-white #FDFBF7 in tokens.css and applied to body."""
    css = _read_tokens_css()
    
    # 1. Verify --canvas-parchment custom property exists on disk
    canvas_defs = _get_css_variable_definitions(css, "--canvas-parchment")
    assert len(canvas_defs) >= 1, "Missing --canvas-parchment in frontend/src/tokens.css"
    assert canvas_defs[0].upper() == "#FDFBF7", f"Expected #FDFBF7, got {canvas_defs[0]}"
    
    # 2. Verify backward-compatibility alias --bg-canvas references --canvas-parchment
    bg_canvas_defs = _get_css_variable_definitions(css, "--bg-canvas")
    assert any("var(--canvas-parchment)" in d for d in bg_canvas_defs), (
        f"--bg-canvas must reference var(--canvas-parchment), found: {bg_canvas_defs}"
    )
    
    # 3. Verify body or html rule binds background-color to var(--canvas-parchment)
    body_bg_match = re.search(r"background-color:\s*var\(--canvas-parchment\);", css)
    assert body_bg_match is not None, (
        "html, body rule must apply background-color: var(--canvas-parchment);"
    )


def test_dark_ink_borders():
    """Feature 14: Dark ink charcoal token (#1E1E1E) and heavy/medium solid border hierarchy."""
    css = _read_tokens_css()
    
    # 1. Canonical charcoal dark ink
    ink_defs = _get_css_variable_definitions(css, "--ink-charcoal")
    assert len(ink_defs) >= 1, "Missing --ink-charcoal in frontend/src/tokens.css"
    assert ink_defs[0].upper() == "#1E1E1E", f"Expected #1E1E1E, got {ink_defs[0]}"
    
    # 2. Heavy border (2px solid ink-charcoal)
    border_heavy_defs = _get_css_variable_definitions(css, "--border-heavy")
    assert any("2px solid var(--ink-charcoal)" in d for d in border_heavy_defs), (
        f"--border-heavy must be '2px solid var(--ink-charcoal)', found: {border_heavy_defs}"
    )
    
    # 3. Medium border (1.5px solid ink-charcoal)
    border_medium_defs = _get_css_variable_definitions(css, "--border-medium")
    assert any("1.5px solid var(--ink-charcoal)" in d for d in border_medium_defs), (
        f"--border-medium must define '1.5px solid var(--ink-charcoal)', found: {border_medium_defs}"
    )
    
    # 4. Hairline border (1px solid ink-charcoal)
    border_hairline_defs = _get_css_variable_definitions(css, "--border-hairline")
    assert any("1px solid var(--ink-charcoal)" in d for d in border_hairline_defs), (
        f"--border-hairline must define '1px solid var(--ink-charcoal)', found: {border_hairline_defs}"
    )
    
    # 5. Component token alias binding
    card_border_defs = _get_css_variable_definitions(css, "--card-border")
    assert any("var(--border-heavy)" in d for d in card_border_defs), (
        f"--card-border must alias var(--border-heavy), found: {card_border_defs}"
    )


def test_pastel_tiles_palette():
    """Feature 14: Soft pastel tile palette (saffron/yellow, ultramarine/blue, terracotta/coral, peach, olive/mint)."""
    css = _read_tokens_css()
    
    expected_pastels = {
        "--pastel-saffron": "#FEF3C7",
        "--pastel-ultramarine": "#E0F2FE",
        "--pastel-terracotta": "#FFE4E6",
        "--pastel-peach": "#FFEDD5",
        "--pastel-olive": "#DCFCE7",
    }
    
    for token_name, expected_hex in expected_pastels.items():
        defs = _get_css_variable_definitions(css, token_name)
        assert len(defs) >= 1, f"Missing token {token_name} in tokens.css"
        actual_hex = defs[0].upper()
        assert actual_hex == expected_hex, f"Expected {token_name} to be {expected_hex}, got {actual_hex}"
        assert re.match(r"^#[0-9A-F]{6}$", actual_hex), f"Hex color format invalid for {token_name}: {actual_hex}"
    
    # Verify subject mapping semantics
    math_soft_defs = _get_css_variable_definitions(css, "--subject-math-soft")
    assert any("var(--pastel-saffron)" in d for d in math_soft_defs), (
        "--subject-math-soft must reference var(--pastel-saffron)"
    )
    science_soft_defs = _get_css_variable_definitions(css, "--subject-science-soft")
    assert any("var(--pastel-olive)" in d for d in science_soft_defs), (
        "--subject-science-soft must reference var(--pastel-olive)"
    )


def test_neobrutalist_shadows():
    """Feature 14: Neo-brutalist crisp hard-edged drop shadows with 0px blur and tactile press offsets."""
    css = _read_tokens_css()
    
    shadow_scale = {
        "--shadow-brutal-xs": ("1px 1px 0px var(--ink-charcoal)", 1),
        "--shadow-brutal-sm": ("2px 2px 0px var(--ink-charcoal)", 2),
        "--shadow-brutal-md": ("4px 4px 0px var(--ink-charcoal)", 4),
        "--shadow-brutal-lg": ("6px 6px 0px var(--ink-charcoal)", 6),
    }
    
    prev_offset = 0
    for shadow_token, (expected_spec, offset_px) in shadow_scale.items():
        defs = _get_css_variable_definitions(css, shadow_token)
        assert len(defs) >= 1, f"Missing {shadow_token} in tokens.css"
        val = defs[0]
        
        # Verify 0px blur radius (hallmark of neo-brutalist hard edges)
        assert "0px" in val, f"{shadow_token} must define 0px blur radius, got {val}"
        # Verify ink-charcoal color reference
        assert "var(--ink-charcoal)" in val, f"{shadow_token} must use var(--ink-charcoal)"
        assert val == expected_spec, f"Expected '{expected_spec}', got '{val}'"
        
        # Verify monotonic growth
        assert offset_px > prev_offset, "Shadow offsets must scale monotonically"
        prev_offset = offset_px
    
    # Verify tactile press translation offset
    press_defs = _get_css_variable_definitions(css, "--press-offset")
    assert len(press_defs) >= 1, "Missing --press-offset"
    assert "translate(2px, 2px)" in press_defs[0], (
        f"--press-offset must be translate(2px, 2px), got {press_defs[0]}"
    )


def test_rounded_radii():
    """Feature 14: Rounded corner radii tokens with micro (2px), box (4px), and pill (9999px)."""
    css = _read_tokens_css()
    
    expected_radii = {
        "--radius-sharp": "0px",
        "--radius-micro": "2px",
        "--radius-box": "4px",
        "--radius-pill": "9999px",
        "--radius-full": "9999px",
    }
    
    for token_name, expected_val in expected_radii.items():
        defs = _get_css_variable_definitions(css, token_name)
        assert len(defs) >= 1, f"Missing {token_name} in tokens.css"
        assert defs[0] == expected_val, f"Expected {token_name} to be {expected_val}, got {defs[0]}"
    
    # Verify card radius convention
    card_radius_defs = _get_css_variable_definitions(css, "--card-radius")
    assert any("var(--radius-micro)" in d for d in card_radius_defs), (
        "--card-radius must reference var(--radius-micro)"
    )
