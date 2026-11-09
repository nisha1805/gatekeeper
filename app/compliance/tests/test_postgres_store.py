import os
import time
import uuid

import psycopg
import pytest

from store import PostgresStore

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not URL, reason="set TEST_DATABASE_URL to run the Postgres tests"
)

REQUEST = {"name": "test system"}


def assessment(name):
    return {
        "system_name": name,
        "role": "provider",
        "tier": "minimal_risk",
        "reasons": [],
        "transparency_duties": [],
        "notes": [],
        "rules_version": "0.1.0",
        "disclaimer": "Decision support only, not legal advice.",
    }


def unique():
    # The tables are append-only, so tests cannot clean up. Unique names keep them apart.
    return f"test-{uuid.uuid4()}"


@pytest.fixture
def store():
    return PostgresStore(URL)


def test_an_assessment_can_be_stored_and_read_back(store):
    created = store.add(REQUEST, assessment(unique()))
    assert created["created_at"].endswith("+00:00")
    assert created["review"] is None
    assert store.get(created["id"]) == created


def test_the_same_request_twice_gives_two_rows(store):
    name = unique()
    first = store.add(REQUEST, assessment(name))
    second = store.add(REQUEST, assessment(name))
    assert first["id"] != second["id"]
    names = [record["assessment"].get("system_name") for record in store.list()]
    assert names.count(name) == 2


def test_a_review_is_shown_with_the_assessment(store):
    created = store.add(REQUEST, assessment(unique()))
    event = store.add_review(created["id"], "approved", "Reviewer A", "looks right")
    assert event["decision"] == "approved"
    shown = store.get(created["id"])
    assert shown["review"]["decision"] == "approved"
    assert shown["review"]["reviewer"] == "Reviewer A"


def test_the_latest_review_is_current_and_both_events_are_kept(store):
    created = store.add(REQUEST, assessment(unique()))
    store.add_review(created["id"], "approved", "Reviewer A", None)
    time.sleep(0.02)
    store.add_review(created["id"], "rejected", "Reviewer B", "wrong tier")
    assert store.get(created["id"])["review"]["decision"] == "rejected"
    with psycopg.connect(URL) as conn:
        count = conn.execute(
            "SELECT count(*) FROM review_events WHERE assessment_id = %s::uuid",
            (created["id"],),
        ).fetchone()[0]
    assert count == 2


def test_a_review_of_an_unknown_assessment_is_refused(store):
    assert store.add_review(str(uuid.uuid4()), "approved", "Reviewer A", None) is None


def test_an_id_that_is_not_a_uuid_is_simply_not_found(store):
    assert store.get("not-a-uuid") is None
    assert store.add_review("not-a-uuid", "approved", "Reviewer A", None) is None


def test_the_app_role_cannot_change_or_delete_audit_rows(store):
    created = store.add(REQUEST, assessment(unique()))
    with psycopg.connect(URL, autocommit=True) as conn:
        for statement in (
            "UPDATE assessments SET system_name = 'changed'",
            "DELETE FROM assessments",
            "UPDATE review_events SET reviewer = 'changed'",
            "DELETE FROM review_events",
        ):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(statement)
    assert store.get(created["id"]) == created


def test_the_database_refuses_an_unknown_decision(store):
    created = store.add(REQUEST, assessment(unique()))
    with psycopg.connect(URL, autocommit=True) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                "INSERT INTO review_events (assessment_id, decision, reviewer) "
                "VALUES (%s::uuid, 'maybe', 'Reviewer A')",
                (created["id"],),
            )