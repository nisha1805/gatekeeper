import pytest
from fastapi.testclient import TestClient

import api
from store import MemoryStore

client = TestClient(api.app)

CV_SCREENING = {"name": "CV screening tool", "annex3_areas": ["employment"]}


@pytest.fixture(autouse=True)
def fresh_store():
    api.store = MemoryStore()


def create():
    return client.post("/assessments", json=CV_SCREENING).json()


def review(assessment_id, **fields):
    body = {"decision": "approved", "reviewer": "Reviewer A", **fields}
    return client.post(f"/assessments/{assessment_id}/reviews", json=body)


def test_a_new_assessment_has_no_review():
    assert create()["review"] is None


def test_approving_records_the_decision_and_the_reviewer():
    created = create()
    response = review(created["id"], comment="looks right")
    assert response.status_code == 201
    assert response.json()["decision"] == "approved"
    shown = client.get(f"/assessments/{created['id']}").json()
    assert shown["review"]["decision"] == "approved"
    assert shown["review"]["reviewer"] == "Reviewer A"


def test_the_latest_review_is_the_current_one():
    created = create()
    review(created["id"], decision="approved")
    review(created["id"], decision="rejected", reviewer="Reviewer B")
    shown = client.get(f"/assessments/{created['id']}").json()
    assert shown["review"]["decision"] == "rejected"
    assert shown["review"]["reviewer"] == "Reviewer B"


def test_reviewing_an_unknown_assessment_is_a_404():
    assert review("does-not-exist").status_code == 404


def test_an_invalid_decision_is_rejected():
    created = create()
    assert review(created["id"], decision="maybe").status_code == 422


def test_a_blank_reviewer_is_rejected():
    created = create()
    assert review(created["id"], reviewer="   ").status_code == 422


def test_unknown_review_fields_are_rejected():
    created = create()
    assert review(created["id"], approved_by="someone").status_code == 422


def test_the_list_shows_the_review_status():
    created = create()
    review(created["id"])
    listed = client.get("/assessments").json()
    assert listed[0]["review"]["decision"] == "approved"