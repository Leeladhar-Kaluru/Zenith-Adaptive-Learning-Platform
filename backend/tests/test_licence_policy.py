import pytest

from app.ingest.policy import evaluate


@pytest.mark.parametrize("lic", ["CC0-1.0", "PDM-1.0", "CC-BY-4.0", "CC-BY-3.0", "GODL-India", "US-GOV-PD"])
def test_open_licences_are_allowed(lic):
    d = evaluate(lic)
    assert d.allowed and not d.share_alike and d.reason


@pytest.mark.parametrize("lic", ["CC-BY-SA-4.0", "CC-BY-SA-3.0", "ODbL-1.0"])
def test_share_alike_is_allowed_only_as_flagged(lic):
    d = evaluate(lic)
    assert d.allowed and d.share_alike
    assert "separate" in d.reason.lower()


@pytest.mark.parametrize("lic", ["CC-BY-NC-4.0", "CC-BY-NC-SA-4.0", "CC-BY-ND-4.0", "CC-BY-NC-ND-4.0", "cc by-nc-sa 3.0"])
def test_non_commercial_and_no_derivatives_are_refused_even_when_called_open(lic):
    d = evaluate(lic)
    assert not d.allowed
    assert "commercial" in d.reason.lower() or "derivative" in d.reason.lower()


@pytest.mark.parametrize("lic", ["", "   ", None, "all rights reserved", "free to use", "public", "CC-BY-9.9", "GPL-3.0"])
def test_missing_unknown_or_vague_licences_are_refused(lic):
    d = evaluate(lic)
    assert not d.allowed and d.reason


def test_ids_are_case_and_spacing_insensitive():
    assert evaluate("cc-by-4.0").allowed
    assert evaluate(" CC-BY-4.0 ").allowed
    assert evaluate("cc by 4.0").allowed
