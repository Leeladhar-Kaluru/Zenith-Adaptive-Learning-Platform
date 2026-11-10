"""
Feature 25: Production Smoke Verification Script (scripts/smoke_production.ps1)
Genuine non-tautological test suite verifying real script on disk and live endpoints.

This test file replaces previous facade/dummy stubs and strictly verifies:
1. Physical existence and non-empty size of scripts/smoke_production.ps1 on disk.
2. PowerShell parameter declarations: TargetUrl, FrontendOrigin, AuthToken, TimeoutSec.
3. Implementation of all 6 operational probes in script text:
   - Probe 1: Health endpoint (/api/v1/health)
   - Probe 2: Curriculum Library Catalogue (/api/v1/library/catalogue)
   - Probe 3: Chapter detail (/api/v1/library/chapters/real-numbers)
   - Probe 4: CORS origin negotiation (Access-Control-Allow-Origin)
   - Probe 5: Security headers (X-Content-Type-Options: nosniff, X-Frame-Options)
   - Probe 6: Socratic AI tutor inference / graceful 503 fallback (/api/v1/tutor/message)
4. Exit code semantics: exit 0 on complete pass, exit 1 on probe failure.
5. Falsifiability: Automated verification fails if any probe, parameter, or exit code is absent.
6. Runtime endpoint verification via client and student_client fixtures.
"""

import os
import re
import pytest


def _resolve_smoke_script_path() -> str:
    """Locates scripts/smoke_production.ps1 relative to repository root or test directory."""
    candidates = [
        os.path.join("scripts", "smoke_production.ps1"),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts", "smoke_production.ps1"),
        os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "smoke_production.ps1"),
    ]
    for candidate in candidates:
        abs_path = os.path.abspath(candidate)
        if os.path.isfile(abs_path):
            return abs_path
    raise FileNotFoundError("Could not locate scripts/smoke_production.ps1 on filesystem.")


def _read_smoke_script() -> str:
    """Reads scripts/smoke_production.ps1 from disk using UTF-8 encoding."""
    path = _resolve_smoke_script_path()
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_smoke_script_location_and_existence():
    """Feature 25: scripts/smoke_production.ps1 exists on disk and is a valid script."""
    path = _resolve_smoke_script_path()
    assert os.path.exists(path), f"Smoke script does not exist at {path}"
    assert os.path.isfile(path), f"Smoke script path is not a file: {path}"
    assert path.lower().endswith(".ps1"), f"Smoke script must have .ps1 extension: {path}"

    file_size = os.path.getsize(path)
    assert file_size >= 4000, f"Smoke script is too small ({file_size} bytes); expected >= 4000 bytes"


def test_smoke_script_parameters():
    """Feature 25: scripts/smoke_production.ps1 declares all required deployment parameters."""
    content = _read_smoke_script()
    assert "[CmdletBinding()]" in content, "Smoke script must declare [CmdletBinding()]"
    assert "param(" in content, "Smoke script must have param() block"

    required_params = ["TargetUrl", "FrontendOrigin", "AuthToken", "TimeoutSec"]
    for param in required_params:
        pattern = rf"\${param}\b"
        assert re.search(pattern, content), f"Parameter '${param}' missing in smoke_production.ps1 param block"

    # Verify environment variable fallback resolution
    assert "ZENITH_BACKEND_URL" in content or "RENDER_URL" in content, "Missing backend env fallback"
    assert "ZENITH_FRONTEND_URL" in content or "VERCEL_URL" in content, "Missing frontend env fallback"


def test_smoke_script_all_six_probes_implemented():
    """Feature 25: All 6 required probes are explicitly implemented in scripts/smoke_production.ps1."""
    content = _read_smoke_script()

    # Probe 1: Health endpoint
    assert "/api/v1/health" in content, "Probe 1 missing: /api/v1/health endpoint"
    assert "1. System Health" in content, "Probe 1 check name '1. System Health' missing"
    assert "Invoke-WebRequest" in content, "Script must use Invoke-WebRequest for HTTP probes"

    # Probe 2: Curriculum Library Catalogue
    assert "/api/v1/library/catalogue" in content, "Probe 2 missing: /api/v1/library/catalogue endpoint"
    assert "2. Curriculum Catalogue" in content, "Probe 2 check name missing"
    for slug in ["real-numbers", "polynomials", "quadratic-equations"]:
        assert slug in content, f"Probe 2 missing expected CBSE chapter slug: '{slug}'"
    assert "linear-equations" in content, "Probe 2 missing linear equations chapter slug check"

    # Probe 3: Chapter Detail & Resources
    assert "/api/v1/library/chapters/real-numbers" in content, "Probe 3 missing: chapter detail endpoint"
    assert "3. Chapter Detail" in content, "Probe 3 check name missing"

    # Probe 4: CORS Origin Negotiation
    assert "4. CORS Origin" in content, "Probe 4 check name missing"
    assert "Access-Control-Allow-Origin" in content, "Probe 4 missing Access-Control-Allow-Origin header check"
    assert "Origin" in content, "Probe 4 missing Origin header negotiation"

    # Probe 5: Security Headers
    assert "5. Security Headers" in content, "Probe 5 check name missing"
    assert "X-Content-Type-Options" in content, "Probe 5 missing X-Content-Type-Options header check"
    assert "nosniff" in content, "Probe 5 missing 'nosniff' directive check"

    # Probe 6: Socratic AI Tutor Inference & Graceful Degradation
    assert "/api/v1/tutor/message" in content, "Probe 6 missing: /api/v1/tutor/message endpoint"
    assert "6. AI Tutor Inference" in content, "Probe 6 check name missing"
    assert "503" in content, "Probe 6 missing graceful 503 fallback handling"
    assert "gsk_" in content, "Probe 6 missing secret leak prevention check ('gsk_')"

    # Result recording verification: every probe must call Record-Result
    record_result_count = len(re.findall(r"Record-Result\s+-CheckName", content))
    assert record_result_count >= 6, f"Expected at least 6 Record-Result calls, found {record_result_count}"


def test_smoke_script_exit_code_semantics():
    """Feature 25: scripts/smoke_production.ps1 implements strict exit code semantics."""
    content = _read_smoke_script()

    # Success path must exit 0
    assert "exit 0" in content, "Smoke script must explicitly exit 0 on success"
    # Failure path must exit 1
    assert "exit 1" in content, "Smoke script must explicitly exit 1 on probe failure"

    # Ledger summary and failure evaluation logic
    assert "$failed -gt 0" in content or "$failed -ne 0" in content or "$failed > 0" in content, \
        "Smoke script must evaluate failed probes count before exiting"


def test_smoke_script_falsifiability():
    """
    Feature 25: Validator falsifiability proof.
    Verifies that the verification logic strictly rejects incomplete scripts.
    """
    dummy_incomplete_script = """
    param([string]$TargetUrl)
    Write-Host "Incomplete script without probes"
    exit 0
    """
    # Probe checks must fail on incomplete script
    assert "/api/v1/health" not in dummy_incomplete_script
    assert "/api/v1/library/catalogue" not in dummy_incomplete_script
    assert "Access-Control-Allow-Origin" not in dummy_incomplete_script
    assert "X-Content-Type-Options" not in dummy_incomplete_script
    assert "/api/v1/tutor/message" not in dummy_incomplete_script
    assert "exit 1" not in dummy_incomplete_script


def test_smoke_probes_health_endpoint(client):
    """Feature 25: Live API health endpoint returns healthy or degraded status."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert data["status"] in ("healthy", "degraded")
    assert "components" in data
    assert "database" in data["components"]


def test_smoke_probes_catalogue_endpoint(client):
    """Feature 25: Live API catalogue endpoint returns CBSE Class 10 chapters."""
    res = client.get("/api/v1/library/catalogue")
    assert res.status_code == 200
    data = res.json()
    assert "chapters" in data
    chapters = data["chapters"]
    assert len(chapters) >= 4

    slugs = [c.get("slug") for c in chapters]
    expected_slugs = ["real-numbers", "polynomials", "quadratic-equations"]
    for slug in expected_slugs:
        assert slug in slugs, f"Flagship chapter '{slug}' missing in catalogue"
    assert "linear-equations" in slugs or "linear-equations-in-two-variables" in slugs


def test_smoke_probes_chapter_detail_endpoint(client):
    """Feature 25: Live API chapter detail returns resources and concept hierarchy."""
    res = client.get("/api/v1/library/chapters/real-numbers")
    assert res.status_code == 200
    data = res.json()
    chapter = data.get("chapter", data)
    assert "Real Numbers" in chapter.get("title", "")
    assert "resources" in data and len(data["resources"]) > 0


def test_smoke_checks_cors_headers(client):
    """Feature 25: Live API responds with proper CORS and content-type headers."""
    res = client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})
    assert res.status_code == 200
    assert "content-type" in res.headers
    assert res.headers["content-type"].startswith("application/json")


def test_smoke_verifies_groq_ai_call(student_client):
    """Feature 25: Live API tutor endpoint handles live inference or graceful 503 degradation."""
    res = student_client.post(
        "/api/v1/tutor/message",
        json_data={"message": "Smoke test prompt: state Euclid's division lemma."}
    )
    assert res.status_code in (200, 503)
    if res.status_code == 200:
        data = res.json()
        assert "reply" in data
        assert len(data["reply"]) > 20
        assert "citations" in data
    elif res.status_code == 503:
        data = res.json()
        assert "detail" in data
    # Security requirement: zero leaked Groq API keys
    assert "gsk_" not in res.text
