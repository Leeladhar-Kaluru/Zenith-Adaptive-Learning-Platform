import pytest
from sqlalchemy import select

from app.ingest import textsource, webtext
from app.models import SourceAsset

URL = "https://open.example.org/books/biology-2e/pages/8-1-overview-of-photosynthesis"
GOV = "https://www.usgs.gov/special-topics/water-science-school/science/water-cycle"


@pytest.fixture(autouse=True)
def cc_source(monkeypatch):
    """A made-up Creative Commons source, so the page-licence rules are tested without trusting any real publisher."""
    src = textsource.OpenSource(name="CCTest", hosts=("open.example.org",), path_prefix="/books/", licence="CC-BY-4.0", homepage="https://open.example.org/",
                                terms="https://open.example.org/terms", attribution="Adapted from CCTest, {title} ({url}), CC BY 4.0.")
    monkeypatch.setitem(textsource.SOURCES, "cc-test", src)
BODY1 = ("Photosynthesis is the process plants use to make food. In this process plants take in carbon dioxide from the air and water from the soil, and with the energy of "
         "sunlight they build sugar and release oxygen. The sugar feeds the plant and, through the food chain, nearly every other living thing on Earth.")
BODY2 = ("The leaves are the main place where photosynthesis happens. Inside leaf cells are small green structures called chloroplasts. They contain chlorophyll, the green "
         "pigment that captures light. Without chlorophyll a plant could not use sunlight to make sugar.")
NOISE = "Subscribe to our newsletter. Click here to sign in. Privacy policy and terms of use. All rights reserved. " * 3


def page(licence_links='<a rel="license" href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>', extra=""):
    return f"""<html><head><title>8.1 Overview of Photosynthesis - Biology 2e</title><script>var x = 'Photosynthesis is not text';</script></head>
<body><nav><a href="/">Home</a><p>{BODY1}</p></nav>
<main><h1>Overview of Photosynthesis</h1>
<h2>What is photosynthesis?</h2><p>{BODY1}</p>
<figure><figcaption>Figure 8.2 A leaf diagram with a long caption that must never be taught from {BODY2}</figcaption></figure>
<h2>Where it happens</h2><p>{BODY2}</p><p>Short.</p>
<table><tr><td>{BODY1}</td></tr></table>
<h2>Footer noise</h2><p>{NOISE}</p>
{extra}</main><footer>{licence_links}<p>{BODY1}</p></footer></body></html>"""


def fake(html):
    return lambda url, *, user_agent: html.encode()


def test_the_parser_keeps_body_text_under_headings_and_drops_page_furniture():
    p = webtext.parse(page())
    assert p.title == "Overview of Photosynthesis"
    heads = [s.heading for s in p.sections]
    assert "What is photosynthesis?" in heads and "Where it happens" in heads
    text = " ".join(s.text for s in p.sections)
    assert "chloroplasts" in text and "not text" not in text and "Figure 8.2" not in text and "Home" not in text
    assert text.count(BODY1[:40]) == 1                     # the copies inside nav, table and footer are gone
    assert p.licences == {"CC-BY-4.0"}                     # found in the footer link even though footer text is skipped


def test_licence_links_map_to_licence_ids():
    f = webtext.licence_id
    assert f("https://creativecommons.org/licenses/by/4.0/") == "CC-BY-4.0"
    assert f("http://creativecommons.org/licenses/by-sa/3.0/") == "CC-BY-SA-3.0"
    assert f("https://creativecommons.org/licenses/by-nc-sa/4.0/") == "CC-BY-NC-SA-4.0"
    assert f("https://creativecommons.org/publicdomain/zero/1.0/") == "CC0-1.0"
    assert f("https://example.com/licence") is None


def test_clean_drops_short_foreign_boilerplate_and_repeated_sections_and_cuts_long_ones():
    long = ("A long sentence about plants. " * 300).strip()
    secs = [webtext.Section("a", BODY1), webtext.Section("dup", BODY1), webtext.Section("short", "Too short to teach from."), webtext.Section("noise", NOISE),
            webtext.Section("hindi", "पौधे सूर्य के प्रकाश से अपना भोजन बनाते हैं। " * 8), webtext.Section("long", long)]
    out = webtext.clean(secs)
    assert [s.heading for s in out] == ["a", "long"]
    assert len(out[1].text) <= 4000 and out[1].text.endswith(".")


def test_select_keeps_on_topic_sections_in_reading_order():
    secs = [webtext.Section("one", "Roots take in water from the soil. " * 8), webtext.Section("two", BODY1), webtext.Section("three", BODY2)]
    got = webtext.select(secs, ["photosynthesis", "chlorophyll", "sugar"])
    assert [s.heading for s in got] == ["two", "three"] and webtext.relevance(BODY2, ["Chlorophyll", "chloroplasts"]) == 2


def test_a_vetted_openstax_page_becomes_a_pending_credited_text_asset(db):
    a = textsource.import_page(db, URL, "cc-test", None, keywords=["photosynthesis", "chlorophyll"], fetcher=fake(page()))
    assert a.status == "pending" and a.kind == "text" and a.licence_id == "CC-BY-4.0" and a.external_id == URL
    assert "CCTest" in a.attribution_text and URL in a.attribution_text and "CC BY 4.0" in a.attribution_text
    assert [s["heading"] for s in a.data["sections"]] == ["What is photosynthesis?", "Where it happens"] and all("grade" in s for s in a.data["sections"])
    again = textsource.import_page(db, URL, "cc-test", None, fetcher=fake(page()))
    assert again.id == a.id and len(db.scalars(select(SourceAsset).where(SourceAsset.external_id == URL)).all()) == 1          # importing twice never duplicates


@pytest.mark.parametrize("url,key,why", [
    ("https://example.com/books/x", "cc-test", "not an https page under open.example.org"),
    ("http://open.example.org/books/x", "cc-test", "not an https page"),
    ("https://open.example.org/about", "cc-test", "not an https page under"),
    ("https://user:pw@open.example.org/books/x", "cc-test", "not an https page"),
    ("https://open.example.org.evil.example/books/x", "cc-test", "not an https page"),
    (URL, "unknown-key", "not a vetted source"),
])
def test_only_vetted_hosts_and_paths_are_fetched(db, url, key, why):
    called = []
    with pytest.raises(textsource.TextSourceError, match=why):
        textsource.import_page(db, url, key, None, fetcher=lambda *a, **k: called.append(1) or b"")
    assert called == []                                    # refused BEFORE any request is made


@pytest.mark.parametrize("links,why", [
    ("", "does not show a Creative Commons licence"),
    ('<a href="https://creativecommons.org/licenses/by-sa/4.0/">x</a>', "other licences"),
    ('<a href="https://creativecommons.org/licenses/by/4.0/">x</a><a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">y</a>', "other licences"),
    ('<a href="https://creativecommons.org/licenses/by-nd/4.0/">x</a>', "other licences"),
])
def test_the_licence_shown_on_the_page_must_be_exactly_the_one_we_expect(db, links, why):
    with pytest.raises(textsource.TextSourceError, match=why):
        textsource.import_page(db, URL, "cc-test", None, fetcher=fake(page(licence_links=links)))
    assert db.scalars(select(SourceAsset)).all() == []


def test_a_page_with_no_teaching_text_or_nothing_on_topic_is_refused(db):
    empty = "<html><body><main><h1>Empty</h1><p>Short.</p></main><footer><a href='https://creativecommons.org/licenses/by/4.0/'>CC</a></footer></body></html>"
    with pytest.raises(textsource.TextSourceError, match="No usable teaching text"):
        textsource.import_page(db, URL, "cc-test", None, fetcher=fake(empty))
    with pytest.raises(textsource.TextSourceError, match="No usable teaching text"):
        textsource.import_page(db, URL, "cc-test", None, keywords=["volcano"], fetcher=fake(page()))


def test_the_user_agent_sent_with_every_request_is_ours(db):
    seen = {}
    textsource.import_page(db, URL, "cc-test", None, fetcher=lambda url, *, user_agent: seen.setdefault("ua", user_agent) and page().encode())
    assert seen["ua"].startswith("ZenithEducationBot/")


def test_a_public_domain_publisher_page_is_accepted_but_text_with_its_own_copyright_notice_is_dropped(db):
    extra = f"<h2>Photo credit</h2><p>{BODY2} Image courtesy of a private photographer. Copyright 2020.</p>"
    a = textsource.import_page(db, GOV, "usgs-water", None, fetcher=fake(page(licence_links="", extra=extra)))
    assert a.licence_id == "US-GOV-PD" and a.status == "pending" and "public domain" in a.attribution_text
    assert "Photo credit" not in [s["heading"] for s in a.data["sections"]]


def test_a_public_domain_publisher_page_that_shows_a_restrictive_licence_is_refused(db):
    links = '<a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">x</a>'
    with pytest.raises(textsource.TextSourceError, match="restrictive"):
        textsource.import_page(db, GOV, "usgs-water", None, fetcher=fake(page(licence_links=links)))


@pytest.mark.parametrize("key", ["openstax", "ncert", "wikipedia", "khan-academy", "ck12", "nroer"])
def test_known_unusable_sources_are_refused_with_the_reason_before_any_request(db, key):
    with pytest.raises(textsource.TextSourceError, match="refused"):
        textsource.import_page(db, URL, key, None, fetcher=lambda *a, **k: pytest.fail("fetched"))
