import json

import pytest
from fastapi.testclient import TestClient

import api
import articles
from classifier import AnnexIIIArea, SystemDescription, _PROHIBITED, _TRANSPARENCY, classify
from store import MemoryStore

client = TestClient(api.app)


def test_every_stored_text_still_matches_its_fingerprint():
    for unit in articles._data()["units"].values():
        assert articles.unit_digest(unit) == unit["sha256"], unit["label"]


def test_the_source_and_date_are_recorded():
    meta = articles.meta()
    celex = {source["celex"] for source in meta["sources"]}
    assert celex == {"32024R1689", "32026R1744"}
    assert all(source["url"].startswith("https://eur-lex.europa.eu/") for source in meta["sources"])
    assert len(meta["retrieved"]) == 10
    assert "authentic" in meta["not_official"]


def test_known_phrases_are_in_the_copied_text():
    expected = {
        "Art. 5(1)(c)": "social score",
        "Art. 5(1)(f)": "workplace and education institutions",
        "Art. 5(1)(h)": "real-time",
        "Art. 5(1)(ba)": "intimate parts",
        "Art. 5(1)(bb)": "Directive 2011/93/EU",
        "Art. 6(2)": "AI systems referred to in Annex III shall be considered to be high-risk",
        "Art. 6(3)": "performs profiling of natural persons",
        "Art. 50(1)": "interacting with an AI system",
        "Art. 50(2)": "machine-readable format",
        "Art. 50(3)": "emotion recognition system",
        "Art. 50(4)": "deep fake",
        "Annex III point 4": "to analyse and filter job applications",
        "Annex III point 8": "democratic processes",
    }
    for label, phrase in expected.items():
        text = articles._data()["units"][label]["text"]
        assert phrase in text, label


def test_the_new_bans_are_marked_as_added_and_the_old_ones_are_not():
    units = articles._data()["units"]
    assert units["Art. 5(1)(ba)"]["status"] == "added"
    assert units["Art. 5(1)(bb)"]["status"] == "added"
    assert "2 December 2026" in units["Art. 5(1)(ba)"]["note"]
    assert units["Art. 5(1)(c)"]["status"] == "original"


def test_article_6_1_carries_the_inserted_paragraphs():
    unit = articles._data()["units"]["Art. 6(1)"]
    assert [a["label"] for a in unit["added"]] == ["Art. 6(1a)", "Art. 6(1b)", "Art. 6(1c)"]
    assert "safety components" in unit["added"][0]["text"]


def test_a_point_keeps_its_sub_points():
    text = articles._data()["units"]["Art. 5(1)(h)"]["text"]
    assert "(i)" in text and "(iii)" in text and "four years" in text


def test_lookup_of_a_combined_citation_gives_article_and_annex():
    labels = [p["label"] for p in articles.lookup("Art. 6(3), Annex III point 4")]
    assert labels == ["Art. 6(3)", "Annex III point 4"]


def test_a_whole_article_list_gives_headings_only():
    found = articles.lookup("Art. 5, 6, 50")
    assert [p["label"] for p in found] == ["Art. 5", "Art. 6", "Art. 50"]
    assert all(p["text"] is None and "EUR-Lex" in p["note"] for p in found)
    assert found[0]["heading"] == "Article 5: Prohibited AI practices"


def test_an_unknown_provision_says_so_and_invents_nothing():
    found = articles.lookup("Art. 99(9)")
    assert found[0]["text"] is None and found[0]["status"] == "not_included"
    assert "not included" in found[0]["note"]
    assert articles.lookup("Annex III point 42")[0]["text"] is None


def test_every_article_the_rules_can_cite_has_exact_text():
    """If a rule starts citing something new, this test says that its text is missing."""
    cited = {article for _, article, _ in _PROHIBITED} | {article for _, article, _ in _TRANSPARENCY}
    cited |= {"Art. 2", "Art. 6(1)"}
    for area in AnnexIIIArea:
        for flags in ({}, {"performs_profiling": True}):
            result = classify(SystemDescription(name="x", annex3_areas=frozenset({area}), **flags))
            cited |= {r.article for r in result.reasons}
    for citation in cited:
        if citation == "Art. 5, 6, 50":
            continue
        provisions = articles.lookup(citation)
        assert provisions, citation
        assert all(p["text"] for p in provisions), f"no exact text for {citation}"


@pytest.fixture(autouse=True)
def fresh_store():
    original = api.store
    api.store = MemoryStore()
    yield
    api.store = original


def test_the_sources_endpoint_returns_the_cited_text():
    created = client.post("/assessments", json={"name": "cv", "annex3_areas": ["employment"]}).json()
    body = client.get(f"/assessments/{created['id']}/sources").json()
    assert [item["cited"] for item in body["items"]] == ["Art. 6(2), Annex III point 4"]
    labels = [p["label"] for p in body["items"][0]["provisions"]]
    assert labels == ["Art. 6(2)", "Annex III point 4"]
    assert "analyse and filter job applications" in body["items"][0]["provisions"][1]["text"]
    assert body["meta"]["sources"][0]["celex"] == "32024R1689"


def test_the_sources_endpoint_lists_transparency_duties_once():
    created = client.post("/assessments", json={"name": "bot", "interacts_directly_with_people": True}).json()
    body = client.get(f"/assessments/{created['id']}/sources").json()
    assert [item["cited"] for item in body["items"]] == ["Art. 50(1)"]


def test_the_sources_endpoint_for_an_unknown_assessment_is_a_404():
    assert client.get("/assessments/nope/sources").status_code == 404


def test_the_sources_endpoint_does_not_use_the_ai_or_the_rate_limit():
    from guards import RateLimiter
    original = api.limiter
    api.limiter = RateLimiter(per_client=1, overall=1)
    try:
        created = client.post("/assessments", json={"name": "x", "social_scoring": True}).json()
        for _ in range(4):
            assert client.get(f"/assessments/{created['id']}/sources").status_code == 200
    finally:
        api.limiter = original
