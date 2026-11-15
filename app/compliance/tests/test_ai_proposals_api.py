import json
import uuid

import pytest
from fastapi.testclient import TestClient

import api
from store import MemoryStore

client = TestClient(api.app)

TEXT = "We use an AI tool that reads incoming CVs and ranks candidates for our recruiters."


class FakeLLM:
    model = "fake-model"

    def complete(self, system, user):
        return json.dumps({"answers": [
            {"field": "annex3_areas", "value": ["employment"],
             "evidence": "ranks candidates for our recruiters", "confidence": "high"},
            {"field": "role", "value": "deployer", "evidence": "We use an AI tool", "confidence": "high"},
        ]})


@pytest.fixture(autouse=True)
def fresh():
    original_store, original_llm = api.store, api.llm
    api.store, api.llm = MemoryStore(), FakeLLM()
    yield
    api.store, api.llm = original_store, original_llm


def extraction_id():
    return client.post("/extractions", json={"description": TEXT}).json()["extraction_id"]


def test_an_extraction_is_stored_and_its_id_returned():
    body = client.post("/extractions", json={"description": TEXT}).json()
    assert body["proposals"][0]["field"] == "annex3_areas"
    stored = api.store.get_extraction(body["extraction_id"])
    assert stored["model"] == "fake-model"
    assert stored["result"]["proposals"] == body["proposals"]


def test_the_description_itself_is_not_stored():
    extraction = api.store.get_extraction(extraction_id())
    assert TEXT not in json.dumps(extraction)
    assert len(extraction["description_sha256"]) == 64


def test_an_assessment_can_start_from_an_extraction():
    ext = extraction_id()
    created = client.post(f"/assessments?extraction_id={ext}",
                          json={"name": "cv", "annex3_areas": ["employment"], "role": "deployer"})
    assert created.status_code == 201
    assert created.json()["extraction_id"] == ext
    assert "extraction_id" not in created.json()["request"]
    assert client.get(f"/assessments/{created.json()['id']}").json()["extraction_id"] == ext


def test_an_unknown_extraction_is_a_404():
    response = client.post(f"/assessments?extraction_id={uuid.uuid4()}", json={"name": "cv"})
    assert response.status_code == 404


def test_an_assessment_without_extraction_has_none():
    created = client.post("/assessments", json={"name": "plain"}).json()
    assert created["extraction_id"] is None
    assert client.get(f"/assessments/{created['id']}/ai-agreement").json() == {"ai_used": False}


def test_the_agreement_of_one_assessment_is_measured():
    ext = extraction_id()
    created = client.post(f"/assessments?extraction_id={ext}",
                          json={"name": "cv", "annex3_areas": ["employment"], "role": "provider",
                                "performs_profiling": True}).json()
    result = client.get(f"/assessments/{created['id']}/ai-agreement").json()
    assert result["ai_used"] is True
    assert (result["proposed"], result["accepted_unchanged"], result["changed"]) == (2, 1, 1)
    assert result["added_by_person"] == ["performs_profiling"]


def test_the_overall_agreement_counts_only_assessments_with_ai():
    client.post("/assessments", json={"name": "no ai"})
    ext = extraction_id()
    client.post(f"/assessments?extraction_id={ext}",
                json={"name": "cv", "annex3_areas": ["employment"], "role": "deployer"})
    total = client.get("/ai-agreement").json()
    assert total["assessments_with_ai"] == 1
    assert total["accepted_unchanged"] == 2 and total["accepted_rate"] == 1.0


def test_agreement_of_an_unknown_assessment_is_a_404():
    assert client.get("/assessments/nope/ai-agreement").status_code == 404
