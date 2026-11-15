import pytest
from fastapi.testclient import TestClient

import api
from classifier import AnnexIIIArea, SystemDescription, classify
from explainer import explain, problems_in, template_explanation, _cited_items
from extractor import LLMError

client = TestClient(api.app)


def assessment(**kwargs):
    kwargs.setdefault("name", "x")
    return classify(SystemDescription(**kwargs)).to_dict()


HIGH = lambda: assessment(annex3_areas=frozenset({AnnexIIIArea.EMPLOYMENT}))
LIMITED = lambda: assessment(interacts_directly_with_people=True)


class FakeLLM:
    model = "fake-model"

    def __init__(self, reply=None, error=None):
        self.reply, self.error, self.calls = reply, error, []

    def complete(self, system, user):
        self.calls.append((system, user))
        if self.error:
            raise self.error
        return self.reply


GOOD = "Art. 6(2) puts this use case in Annex III point 4, so the system counts as high-risk."


def test_a_good_explanation_is_used():
    result = explain(HIGH(), FakeLLM(GOOD))
    assert result["source"] == "ai"
    assert result["text"] == GOOD
    assert result["fallback_reason"] is None
    assert result["model"] == "fake-model"


def test_the_prompt_has_the_cited_reasons_but_not_the_system_name():
    llm = FakeLLM(GOOD)
    data = assessment(name="Secret Project Name", annex3_areas=frozenset({AnnexIIIArea.EMPLOYMENT}))
    explain(data, llm)
    system, user = llm.calls[0]
    assert "Art. 6(2)" in user and "high-risk" in user
    assert "Secret Project Name" not in user and "Secret Project Name" not in system


def test_an_uncited_article_is_rejected_and_the_template_is_used():
    result = explain(HIGH(), FakeLLM("Art. 6(2) applies, and Art. 99 adds a fine."))
    assert result["source"] == "template"
    assert "99" in result["fallback_reason"]
    assert "Art. 99" not in result["text"]


@pytest.mark.parametrize("text", [
    "Article 10 requires data governance, besides Art. 6(2).",
    "Articles 6(2) and 15 apply.",
    "Art. 6(2) and Art. 5(1)(a) apply.",
    "Under art. 6(2) and Annex I this is high-risk.",
    "Art. 6(2) and Annex III point 7 apply.",
    "Art. 6(2) in Annex III point 4, see also point 2.",
    "Art. 6(2) was in force since 2024.",
])
def test_these_texts_are_rejected(text):
    assert problems_in(text, _cited_items(HIGH()))


@pytest.mark.parametrize("text", [
    GOOD,
    "Article 6(2) and Annex III point 4 make this high-risk.",
    "Under Art. 6, an employment use case is high-risk.",
])
def test_these_texts_pass(text):
    assert problems_in(text, _cited_items(HIGH())) == []


def test_a_different_paragraph_of_a_cited_article_is_rejected():
    items = _cited_items(HIGH())
    assert problems_in("Art. 6(3) applies.", items)


def test_a_list_of_cited_articles_is_allowed():
    data = assessment()  # minimal risk cites "Art. 5, 6, 50"
    assert problems_in("Nothing in Art. 5, Art. 6 or Art. 50 applies.", _cited_items(data)) == []
    assert problems_in("Nothing in Art. 5 or Art. 7 applies.", _cited_items(data))


def test_an_explanation_without_any_cited_article_is_rejected():
    assert problems_in("This system is high-risk.", _cited_items(HIGH()))


def test_empty_and_too_long_texts_are_rejected():
    items = _cited_items(HIGH())
    assert problems_in("   ", items)
    assert problems_in(GOOD + " x" * 700, items)


def test_a_gateway_error_gives_the_template():
    result = explain(HIGH(), FakeLLM(error=LLMError("the gateway answered 502")))
    assert result["source"] == "template"
    assert "502" in result["fallback_reason"]
    assert "Art. 6(2)" in result["text"]


def test_no_llm_gives_the_template():
    result = explain(HIGH(), None)
    assert result["source"] == "template"
    assert "not configured" in result["fallback_reason"]


def test_the_template_passes_its_own_check():
    for data in (HIGH(), LIMITED(), assessment(), assessment(social_scoring=True),
                 assessment(eu_nexus=False)):
        items = _cited_items(data)
        assert problems_in(template_explanation(data, items), items) == []


def test_limited_risk_duties_are_cited_once():
    items = _cited_items(LIMITED())
    assert [i["article"] for i in items] == ["Art. 50(1)"]


@pytest.fixture
def restore_llm():
    original = api.llm
    yield
    api.llm = original


def test_the_endpoint_explains_a_stored_assessment(restore_llm):
    created = client.post("/assessments", json={"name": "ep-test", "annex3_areas": ["employment"]}).json()
    api.llm = FakeLLM(GOOD)
    response = client.post(f"/assessments/{created['id']}/explanation")
    assert response.status_code == 200
    assert response.json()["source"] == "ai"


def test_the_endpoint_falls_back_without_an_ai_step(restore_llm):
    created = client.post("/assessments", json={"name": "ep-test2", "social_scoring": True}).json()
    api.llm = None
    response = client.post(f"/assessments/{created['id']}/explanation")
    assert response.status_code == 200
    assert response.json()["source"] == "template"


def test_the_endpoint_returns_404_for_an_unknown_assessment():
    assert client.post("/assessments/does-not-exist/explanation").status_code == 404
