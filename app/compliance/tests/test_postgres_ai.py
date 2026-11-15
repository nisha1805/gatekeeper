import os
import uuid

import psycopg
import pytest

from store import PostgresStore

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not URL, reason="set TEST_DATABASE_URL to run the Postgres tests"
)

RESULT = {"model": "fake-model", "proposals": [{"field": "role", "kind": "role", "value": "deployer"}],
          "check_these": [], "dropped": 0}


def assessment(name):
    return {"system_name": name, "role": "provider", "tier": "minimal_risk", "reasons": [],
            "transparency_duties": [], "notes": [], "rules_version": "0.1.0", "disclaimer": "x"}


@pytest.fixture
def store():
    return PostgresStore(URL)


def test_an_extraction_can_be_stored_and_read_back(store):
    created = store.add_extraction(RESULT, "a" * 64)
    assert store.get_extraction(created["id"]) == created


def test_an_assessment_keeps_the_link_to_its_extraction(store):
    ext = store.add_extraction(RESULT, "b" * 64)
    created = store.add({"name": "x"}, assessment(f"test-{uuid.uuid4()}"), ext["id"])
    assert created["extraction_id"] == ext["id"]
    assert store.get(created["id"]) == created
    assert store.get(created["id"])["extraction_id"] == ext["id"]


def test_an_assessment_without_extraction_has_no_link(store):
    created = store.add({"name": "x"}, assessment(f"test-{uuid.uuid4()}"))
    assert store.get(created["id"])["extraction_id"] is None


def test_an_unknown_extraction_is_simply_not_found(store):
    assert store.get_extraction(str(uuid.uuid4())) is None
    assert store.get_extraction("not-a-uuid") is None


def test_the_database_refuses_a_link_to_a_missing_extraction(store):
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        store.add({"name": "x"}, assessment(f"test-{uuid.uuid4()}"), str(uuid.uuid4()))


def test_the_app_role_cannot_change_or_delete_extractions(store):
    created = store.add_extraction(RESULT, "c" * 64)
    with psycopg.connect(URL, autocommit=True) as conn:
        for statement in ("UPDATE extraction_events SET model = 'changed'",
                          "DELETE FROM extraction_events"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(statement)
    assert store.get_extraction(created["id"]) == created
