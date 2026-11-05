import dataclasses

import pytest
from fastapi.testclient import TestClient

import api
from classifier import SystemDescription

client = TestClient(api.app)

CV_SCREENING = {"name": "CV screening tool", "annex3_areas": ["employment"]}


@pytest.fixture(autouse=True)
def empty_store():
    api._STORE.clear()


def test_health_reports_the_rules_version():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["rules_version"]


def test_an_empty_request_is_minimal_risk():
    response = client.post("/assessments", json={})
    assert response.status_code == 201
    assert response.json()["assessment"]["tier"] == "minimal_risk"


def test_cv_screening_is_high_risk_with_an_id_and_a_timestamp():
    response = client.post("/assessments", json=CV_SCREENING)
    body = response.json()
    assert response.status_code == 201
    assert body["assessment"]["tier"] == "high_risk"
    assert body["id"]
    assert body["created_at"].endswith("+00:00")


def test_every_result_carries_the_disclaimer():
    body = client.post("/assessments", json=CV_SCREENING).json()
    assert body["assessment"]["disclaimer"].startswith("Decision support only")


def test_a_misspelled_field_is_rejected_not_ignored():
    response = client.post("/assessments", json={"social_scorring": True})
    assert response.status_code == 422


def test_an_unknown_annex_area_is_rejected():
    response = client.post("/assessments", json={"annex3_areas": ["cooking"]})
    assert response.status_code == 422


def test_an_empty_name_is_rejected():
    response = client.post("/assessments", json={"name": ""})
    assert response.status_code == 422


def test_a_stored_assessment_can_be_read_back():
    created = client.post("/assessments", json=CV_SCREENING).json()
    response = client.get(f"/assessments/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_an_unknown_id_is_a_404():
    assert client.get("/assessments/does-not-exist").status_code == 404


def test_the_same_request_twice_gives_two_records_and_the_same_tier():
    first = client.post("/assessments", json=CV_SCREENING).json()
    second = client.post("/assessments", json=CV_SCREENING).json()
    assert first["id"] != second["id"]
    assert first["assessment"]["tier"] == second["assessment"]["tier"]
    assert len(client.get("/assessments").json()) == 2


def test_the_request_fields_match_the_classifier_inputs():
    # Guards against drift: a field added to one side and forgotten on the other.
    classifier_fields = {f.name for f in dataclasses.fields(SystemDescription)}
    assert set(api.AssessmentRequest.model_fields) == classifier_fields