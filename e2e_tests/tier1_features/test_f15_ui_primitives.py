"""
Feature 15: UI Primitives & Navigation Rail
Comprehensive non-tautological test suite verifying real React UI primitive components
and navigation layouts directly from frontend source files on disk.

Tests inspect:
- Button.tsx & Button.module.css: forwardRef, variants, heavy borders, brutalist shadow, tactile press, focus-visible
- Card.tsx & Card.module.css: compound exports, elevation shadows, pastel fills, interactive hover
- Badge.tsx & Badge.module.css: variant colors, pill (9999px) and tag shapes, border & shadow
- Progress.tsx & Progress.module.css: continuous clamped track and segmented step modes, ink borders
- Navigation.tsx & BottomNav.tsx: semantic sidebar, brand text ('ZENITH'), accessible aria attributes, study routes
"""

import os
import re
import pytest

def _resolve_repo_file(rel_path: str) -> str:
    """Resolves relative file path against workspace root or test runner directories."""
    candidates = [
        rel_path,
        os.path.join(os.path.dirname(__file__), "..", "..", rel_path),
        os.path.abspath(rel_path),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return os.path.abspath(c)
    raise FileNotFoundError(f"Could not locate {rel_path} on filesystem.")

def _read_file(rel_path: str) -> str:
    path = _resolve_repo_file(rel_path)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_button_primitive_contract():
    """Feature 15: Button primitive exports forwardRef component with neo-brutalist CSS bindings."""
    tsx = _read_file("frontend/src/components/ui/Button.tsx")
    css = _read_file("frontend/src/components/ui/Button.module.css")
    
    # 1. Structural TypeScript exports & contracts
    assert "export interface ButtonProps" in tsx, "Button.tsx must export ButtonProps"
    assert "forwardRef<HTMLButtonElement, ButtonProps>" in tsx, "Button must use forwardRef"
    assert ("displayName = 'Button'" in tsx) or ('displayName = "Button"' in tsx)
    
    # 2. Prop variants supported in TSX and styled in CSS module
    required_variants = ["primary", "secondary", "accent", "outline", "ghost", "danger"]
    for v in required_variants:
        assert f"'{v}'" in tsx or f'"{v}"' in tsx, f"ButtonProps missing variant: {v}"
        assert f".{v}" in css, f"Button.module.css missing class: .{v}"
        
    required_sizes = ["sm", "md", "lg"]
    for s in required_sizes:
        assert f"'{s}'" in tsx or f'"{s}"' in tsx, f"ButtonProps missing size: {s}"
        assert f".{s}" in css, f"Button.module.css missing class: .{s}"
        
    # 3. Neo-brutalist styling & accessibility contracts in CSS module
    assert "border: var(--border-heavy)" in css, "Button must have heavy brutalist border"
    assert "box-shadow: var(--shadow-brutal-sm)" in css, "Button must have brutalist shadow"
    assert "outline: 2px dashed var(--ink-charcoal)" in css, "Button must have high-contrast focus ring"
    assert "transform: var(--press-offset)" in css, "Button:active must trigger tactile press offset"
    assert "cursor: not-allowed" in css, "Button:disabled must indicate disabled state"


def test_card_primitive_contract():
    """Feature 15: Card primitive defines compound components, elevation shadows, and pastel fills."""
    tsx = _read_file("frontend/src/components/ui/Card.tsx")
    css = _read_file("frontend/src/components/ui/Card.module.css")
    
    # 1. Component exports and compound subcomponents
    compound_exports = ["Card", "CardHeader", "CardTitle", "CardDescription", "CardContent", "CardFooter"]
    for exp in compound_exports:
        assert f"export const {exp}" in tsx, f"Card.tsx must export {exp}"
        
    # 2. Elevation styling (0 through 3)
    for elev in [0, 1, 2, 3]:
        assert f".elevation{elev}" in css, f"Card.module.css missing .elevation{elev}"
    assert "box-shadow: var(--shadow-brutal-sm)" in css  # elevation1
    assert "box-shadow: var(--shadow-brutal-md)" in css  # elevation2
    assert "box-shadow: var(--shadow-brutal-lg)" in css  # elevation3
    
    # 3. Canonical pastel background fills
    for pastel in ["saffron", "ultramarine", "terracotta", "olive", "peach"]:
        assert f".{pastel}" in css, f"Card.module.css missing pastel class .{pastel}"
        
    # 4. Neo-brutalist frame and interactive transitions
    assert "border: var(--border-heavy)" in css, "Card must have heavy brutalist border"
    assert "border-radius: var(--radius-micro)" in css, "Card must have micro border radius"
    assert ".interactive" in css, "Card.module.css must define interactive modifier"
    assert "transform: var(--press-offset)" in css, "Interactive card press must translate offset"


def test_badge_primitive_contract():
    """Feature 15: Badge primitive supports pill and tag shapes with neo-brutalist borders."""
    tsx = _read_file("frontend/src/components/ui/Badge.tsx")
    css = _read_file("frontend/src/components/ui/Badge.module.css")
    
    # 1. TypeScript contract
    assert "export const Badge:" in tsx, "Badge.tsx must export Badge component"
    assert "export interface BadgeProps" in tsx, "Badge.tsx must export BadgeProps"
    
    # 2. Shapes
    assert ".pill" in css, "Badge.module.css must define .pill"
    assert "border-radius: var(--radius-pill)" in css, "Pill badge must use --radius-pill (9999px)"
    assert ".tag" in css, "Badge.module.css must define .tag"
    assert "border-radius: var(--radius-micro)" in css, "Tag badge must use --radius-micro"
    
    # 3. Variants
    badge_variants = ["saffron", "terracotta", "ultramarine", "olive", "charcoal", "neutral"]
    for v in badge_variants:
        assert f"'{v}'" in tsx or f'"{v}"' in tsx, f"BadgeProps missing variant: {v}"
        assert f".{v}" in css, f"Badge.module.css missing variant class: .{v}"
        
    # 4. Neo-brutalist styling
    assert "border: var(--border-medium)" in css, "Badge must have medium border"
    assert "box-shadow: var(--shadow-brutal-xs)" in css, "Badge must have brutalist xs shadow"


def test_progress_ring_primitive():
    """Feature 15: Progress primitive supports continuous clamped bar and segmented steps modes."""
    tsx = _read_file("frontend/src/components/ui/Progress.tsx")
    css = _read_file("frontend/src/components/ui/Progress.module.css")
    
    # 1. Structural exports & props
    assert "export const Progress:" in tsx, "Progress.tsx must export Progress component"
    assert "export interface ProgressProps" in tsx, "Progress.tsx must export ProgressProps"
    
    # 2. Value clamping contract (0 to 100%)
    assert "Math.min(100, Math.max(0, value))" in tsx, (
        "Progress.tsx must clamp value between 0 and 100 to prevent layout distortion"
    )
    
    # 3. Segmented steps mode vs continuous track mode
    assert "styles.segmentsContainer" in tsx, "Progress.tsx must support segmented container"
    assert "styles.segmentCompleted" in tsx, "Progress.tsx must mark completed segments"
    assert "styles.segmentCurrent" in tsx, "Progress.tsx must mark active step segment"
    assert "styles.track" in tsx and "styles.bar" in tsx, "Progress.tsx must support continuous track/bar"
    
    # 4. CSS styling
    assert "border: var(--border-heavy)" in css, "Track must have heavy brutalist border"
    assert "box-shadow: var(--shadow-brutal-xs)" in css, "Track must have brutalist shadow"
    assert "border-right: 1.5px solid var(--ink-charcoal)" in css, "Progress bar head must have ink border"
    for color in ["saffron", "ultramarine", "olive", "terracotta"]:
        assert f".{color}" in css, f"Progress.module.css missing color variant .{color}"


def test_left_navigation_rail_structure():
    """Feature 15: Navigation rail groups core study routes, ZENITH branding, and accessibility contracts."""
    nav_tsx = _read_file("frontend/src/components/Navigation.tsx")
    nav_css = _read_file("frontend/src/components/Navigation.module.css")
    bottom_tsx = _read_file("frontend/src/components/layout/BottomNav.tsx")
    
    # 1. Semantic landmarks & ARIA labels
    assert 'aria-label="Primary Navigation"' in nav_tsx, "Desktop rail must have aria-label='Primary Navigation'"
    assert 'aria-label="Mobile Navigation"' in bottom_tsx, "Mobile nav must have aria-label='Mobile Navigation'"
    assert "<aside" in nav_tsx, "Navigation component must use semantic <aside> landmark"
    
    # 2. Visible branding
    assert "ZENITH" in nav_tsx, "Brand title must display ZENITH"
    assert "Adaptive Companion" in nav_tsx, "Brand tag must display Adaptive Companion"
    
    # 3. Core study routes presence
    core_study_routes = ["/", "/explore", "/practice", "/map", "/achievements", "/ask", "/sources"]
    for route in core_study_routes:
        assert f'to="{route}"' in nav_tsx or f"to='{route}'" in nav_tsx, (
            f"Navigation.tsx must contain NavLink target for {route}"
        )
        
    # 4. Accessibility & state contracts
    assert 'aria-hidden="true"' in nav_tsx, "Decorative icon elements in navigation must set aria-hidden='true'"
    assert "syncManager.syncPendingData" in nav_tsx, "Navigation must connect to syncManager for offline sync"
    assert "styles.badgeOnline" in nav_tsx and "styles.badgeOffline" in nav_tsx, (
        "Navigation must display online/offline status indicators"
    )
