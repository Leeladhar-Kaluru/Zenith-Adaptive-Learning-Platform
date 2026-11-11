import hashlib
import json

import pytest
from sqlalchemy import func, select

from app.ingest import commons
from app.models import Source, SourceAsset
from tests.conftest import make_profile

IMG = b"\x89PNG fake image bytes"


def api_payload(licence="CC BY 4.0", artist='<a href="//commons.wikimedia.org/wiki/User:Ann">Ann Lee</a>', url="https://upload.wikimedia.org/x/Cell.png", with_licence=True):
    meta = {"Artist": {"value": artist}, "Credit": {"value": "Own work"}, "LicenseUrl": {"value": "https://creativecommons.org/licenses/by/4.0"}}
    if with_licence:
        meta["LicenseShortName"] = {"value": licence}
    return json.dumps({"query": {"pages": {"1": {"title": "File:Cell.png", "imageinfo": [{"url": url, "size": len(IMG), "sha1": "x", "extmetadata": meta}]}}}}).encode()


@pytest.fixture()
def net(monkeypatch):
    monkeypatch.setattr(commons.settings, "BOT_CONTACT", "owner@school.example")
    calls = []
    payload = {"api": api_payload()}

    def fake_fetch(url, *, user_agent, client=None):
        calls.append(url)
        return payload["api"] if "api.php" in url else IMG

    monkeypatch.setattr(commons, "fetch", fake_fetch)
    return calls, payload


def test_cc_by_image_imports_with_credit_and_hash(db, net):
    actor = make_profile(db, "reviewer")
    a = commons.import_file(db, "File:Cell.png", actor.id)
    assert a.status == "pending" and a.licence_id == "CC-BY-4.0" and a.kind == "image"
    assert a.sha256 == hashlib.sha256(IMG).hexdigest() and a.bytes == len(IMG)
    assert "Ann Lee" in a.attribution_text and "CC BY 4.0" in a.attribution_text and "Wikimedia Commons" in a.attribution_text
    assert "<a" not in a.attribution_text                         # markup from the API is stripped
    assert db.scalar(select(Source.name).where(Source.id == a.source_id)) == "Wikimedia Commons"


def test_non_commercial_file_is_rejected_with_the_policy_reason(db, net):
    _, payload = net
    payload["api"] = api_payload(licence="CC BY-NC-SA 4.0")
    with pytest.raises(commons.LicenceRefused, match="[Nn]on-commercial"):
        commons.import_file(db, "File:Cell.png", make_profile(db, "reviewer").id)
    assert db.scalar(select(func.count(SourceAsset.id))) == 0


def test_file_with_no_licence_metadata_is_rejected(db, net):
    _, payload = net
    payload["api"] = api_payload(with_licence=False)
    with pytest.raises(commons.LicenceRefused, match="No licence"):
        commons.import_file(db, "File:Cell.png", make_profile(db, "reviewer").id)
    assert db.scalar(select(func.count(SourceAsset.id))) == 0


def test_reimport_is_idempotent_and_does_not_download_again(db, net):
    calls, _ = net
    actor = make_profile(db, "reviewer")
    a1 = commons.import_file(db, "File:Cell.png", actor.id)
    n = len(calls)
    a2 = commons.import_file(db, "File:Cell.png", actor.id)
    assert a1.id == a2.id and len(calls) == n
    assert db.scalar(select(func.count(SourceAsset.id))) == 1


def test_only_file_titles_and_commons_hosts_are_accepted(db, net):
    actor = make_profile(db, "reviewer")
    with pytest.raises(commons.CommonsError):
        commons.import_file(db, "Cell.png", actor.id)
    _, payload = net
    payload["api"] = api_payload(url="https://evil.example/Cell.png")
    with pytest.raises(commons.CommonsError, match="host"):
        commons.import_file(db, "File:Cell.png", actor.id)


def test_share_alike_is_imported_but_flagged_in_the_credit(db, net):
    _, payload = net
    payload["api"] = api_payload(licence="CC BY-SA 4.0")
    a = commons.import_file(db, "File:Cell.png", make_profile(db, "reviewer").id)
    assert a.licence_id == "CC-BY-SA-4.0"


def test_approval_needs_a_reviewer_and_rechecks_the_licence(db, net):
    from app.ingest.assets import approve_asset, AssetError
    actor = make_profile(db, "reviewer")
    a = commons.import_file(db, "File:Cell.png", actor.id)
    approve_asset(db, a.id, actor.id)
    db.refresh(a)
    assert a.status == "approved" and a.reviewer_id == actor.id
    b = SourceAsset(source_id=a.source_id, external_id="File:Bad.png", url="https://x/y", kind="image", licence_id="CC-BY-NC-4.0", attribution_text="x",
                    retrieved_at=a.retrieved_at, recheck_at=a.recheck_at)
    db.add(b)
    db.commit()
    with pytest.raises(AssetError):
        approve_asset(db, b.id, actor.id)


@pytest.mark.parametrize("name,expected", [
    ("CC BY 4.0", "CC-BY-4.0"), ("CC BY-SA 3.0", "CC-BY-SA-3.0"), ("CC BY-SA 4.0", "CC-BY-SA-4.0"), ("CC0", "CC0-1.0"), ("Public domain", "PDM-1.0"),
    ("CC BY-NC 4.0", "CC-BY-NC-4.0"), ("CC BY-NC-SA 2.0", "CC-BY-NC-SA-2.0"), ("CC BY-ND 4.0", "CC-BY-ND-4.0"),
])
def test_licence_names_map_to_policy_ids(name, expected):
    assert commons.licence_id(name) == expected


@pytest.mark.parametrize("name", ["Attribution", "Fair use", "", "GFDL"])
def test_unmapped_names_stay_unknown_and_are_refused_by_policy(name):
    from app.ingest.policy import evaluate
    assert not evaluate(commons.licence_id(name)).allowed
