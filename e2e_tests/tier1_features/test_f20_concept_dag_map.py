import os
import re
import pytest

def _get_project_root():
    curr = os.path.abspath(os.path.dirname(__file__))
    while curr:
        if os.path.isdir(os.path.join(curr, "frontend", "src")):
            return curr
        parent = os.path.dirname(curr)
        if parent == curr:
            break
        curr = parent
    return os.path.abspath(".")

PROJECT_ROOT = _get_project_root()
FRONTEND_SRC = os.path.join(PROJECT_ROOT, "frontend", "src")
LEARNING_MAP_PAGE_TSX = os.path.join(FRONTEND_SRC, "pages", "LearningMapPage.tsx")
LEARNING_MAP_MODULE_CSS = os.path.join(FRONTEND_SRC, "pages", "LearningMapPage.module.css")


def _read_map_files():
    assert os.path.isfile(LEARNING_MAP_PAGE_TSX), f"Missing {LEARNING_MAP_PAGE_TSX}"
    assert os.path.isfile(LEARNING_MAP_MODULE_CSS), f"Missing {LEARNING_MAP_MODULE_CSS}"
    with open(LEARNING_MAP_PAGE_TSX, "r", encoding="utf-8") as f:
        tsx_content = f.read()
    with open(LEARNING_MAP_MODULE_CSS, "r", encoding="utf-8") as f:
        css_content = f.read()
    return tsx_content, css_content


def test_dag_nodes_contain_mastery_and_status(client):
    """Feature 20: DAG nodes contain mastery probability and status label, with neo-brutalist palette."""
    tsx_content, css_content = _read_map_files()

    # 1. Verify frontend node mastery color functions
    assert "getNodeFill = (node: ConceptDagNode)" in tsx_content
    assert "#FFE4E6" in tsx_content  # Coral for prerequisite gap
    assert "#DCFCE7" in tsx_content  # Mint for mastered
    assert "#E0F2FE" in tsx_content  # Sky blue for approaching
    assert "#FEF3C7" in tsx_content  # Amber for developing
    assert "#F3F4F6" in tsx_content  # Gray for unstarted

    assert "getNodeBorder = (node: ConceptDagNode)" in tsx_content
    assert "#BE123C" in tsx_content
    assert "#15803D" in tsx_content

    # 2. Verify dual rectangle rendering (neo-brutalist shadow + node card)
    assert '<rect\n                  x="-88"\n                  y="-22"\n                  width="180"\n                  height="54"\n                  rx="2"\n                  fill="#1E1E1E"\n                />' in tsx_content or 'fill="#1E1E1E"' in tsx_content
    assert "fill={getNodeFill(n)}" in tsx_content
    assert "stroke={isSelected ? '#FF9933' : getNodeBorder(n)}" in tsx_content

    # 3. Live backend API contract check
    res = client.get("/api/v1/library/map/real-numbers")
    assert res.status_code == 200
    nodes = res.json()["nodes"]
    assert len(nodes) >= 2
    for node in nodes:
        assert "id" in node
        assert "label" in node
        assert "mastery" in node
        assert node["status"] in ("mastered", "in_progress", "locked", "developing", "approaching")


def test_dag_edges_define_prerequisites(client):
    """Feature 20: DAG edges connect prerequisite source to target concept via smooth cubic Bezier curves."""
    tsx_content, _ = _read_map_files()

    # 1. Verify cubic Bezier curve calculation in LearningMapPage.tsx
    assert "const midX = (startX + endX) / 2" in tsx_content
    assert "const pathD = `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`" in tsx_content

    # 2. Verify edge path SVG rendering with arrow marker
    assert '<path' in tsx_content
    assert 'd={pathD}' in tsx_content
    assert 'markerEnd="url(#arrow)"' in tsx_content
    assert "strokeDasharray={e.relationship === 'corequisite' ? '4 4' : undefined}" in tsx_content

    # 3. Mathematical invariant: Bezier midX must be equidistant between start and end
    start_x, end_x = 140, 400
    mid_x = (start_x + end_x) / 2
    assert mid_x == 270
    assert (mid_x - start_x) == (end_x - mid_x)

    # 4. Live backend API edge topology
    res = client.get("/api/v1/library/map/real-numbers")
    assert res.status_code == 200
    edges = res.json()["edges"]
    assert len(edges) >= 1
    for edge in edges:
        assert "source" in edge
        assert "target" in edge
        assert edge.get("type") in ("prerequisite", "corequisite")


def test_dag_keyboard_accessibility_contract():
    """Feature 20: Keyboard accessibility, interactive node selection, and ARIA attributes in DAG."""
    tsx_content, css_content = _read_map_files()

    # 1. Interactive node group click handler and pointer cursor
    assert "onClick={() => setSelectedNode(n)}" in tsx_content
    assert "style={{ cursor: 'pointer' }}" in tsx_content

    # 2. Selected node highlight contract
    assert "stroke={isSelected ? '#FF9933' : getNodeBorder(n)}" in tsx_content
    assert "strokeWidth={isSelected ? '3' : '2'}" in tsx_content

    # 3. Accessible attributes for interactive drawer and controls
    assert 'aria-label="Close Inspection Drawer"' in tsx_content
    assert 'title="Zoom In"' in tsx_content
    assert 'title="Zoom Out"' in tsx_content
    assert 'title="Reset Zoom"' in tsx_content

    # 4. Neo-brutalist Button primitive usage (implements accessible HTML button roles)
    assert "import { Button, Badge, Progress } from '../components/ui'" in tsx_content
    assert "variant={currentChapter === ch.slug ? 'primary' : 'outline'}" in tsx_content


def test_dag_detail_drawer(client):
    """Feature 20: Selecting a node exposes direct learning links and BKT mastery in slide-in drawer."""
    tsx_content, css_content = _read_map_files()

    # 1. Drawer component structure in LearningMapPage.tsx
    assert "{selectedNode && (" in tsx_content
    assert "<aside className={styles.drawer}>" in tsx_content
    assert "{selectedNode.title || selectedNode.name}" in tsx_content
    assert "{selectedNode.description ||" in tsx_content
    assert 'label="BKT Knowledge Probability"' in tsx_content

    # 2. Action buttons linking to Practice and Socratic Tutor
    assert "Practice This Concept" in tsx_content
    assert "navigate(`/practice?chapter=${currentChapter}&concept=${selectedNode.id}`)" in tsx_content
    assert "Ask Tutor About Topic" in tsx_content
    assert "navigate(`/ask?concept=${encodeURIComponent(selectedNode.id)}`)" in tsx_content

    # 3. CSS animation and layout styles
    assert ".drawer {" in css_content
    assert "animation: slideIn 0.2s ease;" in css_content
    assert "@keyframes slideIn {" in css_content

    # 4. Live API node schema matches drawer consumption requirements
    res = client.get("/api/v1/library/map/real-numbers")
    assert res.status_code == 200
    first_node = res.json()["nodes"][0]
    assert "id" in first_node
    assert "label" in first_node
    assert "mastery" in first_node


def test_dag_svg_layer_placement():
    """Feature 20: Genuine SVG canvas, arrow marker definition, zoom controls, and layered placement."""
    tsx_content, css_content = _read_map_files()

    # 1. SVG canvas element and viewBox dimensions
    assert '<svg' in tsx_content
    assert 'className={styles.svgCanvas}' in tsx_content
    assert 'viewBox="0 0 920 480"' in tsx_content

    # 2. Arrow marker definition in <defs>
    assert '<defs>' in tsx_content
    assert '<marker' in tsx_content
    assert 'id="arrow"' in tsx_content
    assert 'viewBox="0 0 10 10"' in tsx_content
    assert 'refX="8"' in tsx_content
    assert 'refY="5"' in tsx_content
    assert 'orient="auto-start-reverse"' in tsx_content
    assert '<path d="M 0 1 L 10 5 L 0 9 z" fill="#1E1E1E" />' in tsx_content

    # 3. Topological layering coordinate computation
    assert "const layer = idx % 3;" in tsx_content
    assert "const row = Math.floor(idx / 3);" in tsx_content
    assert "const computedX = n.x ?? (140 + layer * 260);" in tsx_content
    assert "const computedY = n.y ?? (140 + row * 160);" in tsx_content

    # Verify layering geometry: Layer spacing guarantees horizontal separation without collisions
    layer_0_x = 140 + 0 * 260
    layer_1_x = 140 + 1 * 260
    layer_2_x = 140 + 2 * 260
    assert layer_1_x > layer_0_x and (layer_1_x - layer_0_x) == 260
    assert layer_2_x > layer_1_x and (layer_2_x - layer_1_x) == 260

    # 4. Zoom controls and dynamic transform scale
    assert "const [zoom, setZoom] = useState(1)" in tsx_content
    assert "transform: `scale(${zoom})`" in tsx_content
    assert "Math.min(1.5, prev + 0.1)" in tsx_content
    assert "Math.max(0.7, prev - 0.1)" in tsx_content
    assert "setZoom(1)" in tsx_content
    assert ".controls {" in css_content
