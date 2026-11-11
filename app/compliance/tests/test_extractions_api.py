import json

import pytest
from fastapi.testclient import TestClient

import api
from extractor import LLMError
from questions import QUESTIONS

client = TestClient(api.app)

TEXT = "We use an AI tool that reads incoming CVs and ranks candidates for our recruiters."


class FakeLLM:
    model = "fake-model"

    def __init__(self, reply=None, error=None):
        self.reply = reply
        self.error = error

    def complete(self, system, user):
        if self.error:
            raise self.error
        return self.reply if isinstance(self.reply, str) else json.dumps(self.reply)


@pytest.fixture(autouse=True)
def restore_llm():
    original = api.llm
    yield
    api.llm = original


def test_an_extraction_returns_checked_proposals():
    api.llm = FakeLLM({"answers": [{
        "field": "annex3_areas", "value": ["employment"],
        "evidence": "ranks candidates for our recruiters", "confidence": "high",
    }]})
    response = client.post("/extractions", json={"description": TEXT})
    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "fake-model"
    assert body["proposals"][0]["applied"] == ["employment"]


def test_an_extraction_without_a_configured_gateway_is_a_503():
    api.llm = None
    assert client.post("/extractions", json={"description": TEXT}).status_code == 503


def test_a_gateway_failure_is_a_502_and_leaks_nothing():
    api.llm = FakeLLM(error=LLMError("the gateway answered 500"))
    response = client.post("/extractions", json={"description": TEXT})
    assert response.status_code == 502
    assert "500" in response.json()["detail"]


def test_an_unusable_answer_from_the_ai_is_a_502():
    api.llm = FakeLLM("not json at all")
    assert client.post("/extractions", json={"description": TEXT}).status_code == 502


def test_a_too_short_description_is_rejected():
    api.llm = FakeLLM({"answers": []})
    assert client.post("/extractions", json={"description": "too short"}).status_code == 422


def test_a_too_long_description_is_rejected():
    api.llm = FakeLLM({"answers": []})
    assert client.post("/extractions", json={"description": "x" * 4001}).status_code == 422


def test_unknown_extraction_fields_are_rejected():
    api.llm = FakeLLM({"answers": []})
    response = client.post("/extractions", json={"description": TEXT, "model": "other"})
    assert response.status_code == 422


def test_the_question_list_covers_exactly_the_assessment_fields():
    body = client.get("/questions").json()
    fields = {question["field"] for question in body["questions"]}
    assert fields | {"name"} == set(api.AssessmentRequest.model_fields)
    assert len(body["questions"]) == len(QUESTIONS)
    assert {area["value"] for area in body["annex3_areas"]} and body["roles"] == ["provider", "deployer"]
