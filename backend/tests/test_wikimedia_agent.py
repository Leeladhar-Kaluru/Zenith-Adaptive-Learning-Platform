from pathlib import Path

from app.core.config import settings
from app.ingest import commons

REPO = Path(__file__).resolve().parents[2]
NEEDLE = "chromatic" + "fuel"          # built in two parts so this file does not contain the address itself


def test_the_user_agent_names_zenith_a_version_the_library_and_the_configured_contact(monkeypatch):
    monkeypatch.setattr(settings, "BOT_CONTACT", "owner@school.example")
    monkeypatch.setattr(settings, "BOT_VERSION", "2.3")
    ua = commons.user_agent()
    assert ua.startswith("ZenithEducationBot/2.3 (") and "Zenith" in ua and "contact: owner@school.example" in ua and "httpx/" in ua
    assert "SETU" not in ua                                     # the product name only


def test_the_contact_lives_in_backend_configuration_and_never_in_source_or_the_frontend():
    hits = []
    for root in (REPO / "frontend" / "src", REPO / "frontend" / "public", REPO / "backend" / "app", REPO / "backend" / "tests", REPO / "docs"):
        if not root.exists():
            continue
        for f in root.rglob("*"):
            if f.is_file() and f.suffix in (".ts", ".tsx", ".js", ".html", ".py", ".md", ".json", ".css"):
                if NEEDLE in f.read_text(encoding="utf-8", errors="ignore"):
                    hits.append(str(f.relative_to(REPO)))
    assert hits == [], f"the contact address is written into: {hits}"


def test_the_frontend_build_env_does_not_carry_the_contact():
    assert not any("BOT_CONTACT" in p.read_text(encoding="utf-8", errors="ignore") for p in (REPO / "frontend").glob(".env*") if p.is_file())
