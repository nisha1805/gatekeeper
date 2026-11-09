"""Storage for assessments and review events.

MemoryStore is used when no database is configured (tests, quick demos).
PostgresStore writes to the append-only tables from db/001_schema.sql.
Both return records of the same shape, so the API does not care which one it has.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb


def _utc(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat()


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
    except ValueError:
        return False
    return True


def _review(decision, reviewer, reviewed_at) -> dict | None:
    if decision is None:
        return None
    return {
        "decision": decision,
        "reviewer": reviewer,
        "reviewed_at": _utc(reviewed_at),
    }


class MemoryStore:
    def __init__(self) -> None:
        self._records: list[dict] = []

    def add(self, request: dict, assessment: dict) -> dict:
        record = {
            "id": str(uuid4()),
            "created_at": _utc(datetime.now(timezone.utc)),
            "request": request,
            "assessment": assessment,
            "review": None,
        }
        self._records.append(record)
        return dict(record)

    def list(self) -> list[dict]:
        return [dict(record) for record in self._records]

    def get(self, assessment_id: str) -> dict | None:
        for record in self._records:
            if record["id"] == assessment_id:
                return dict(record)
        return None

    def add_review(self, assessment_id, decision, reviewer, comment) -> dict | None:
        for record in self._records:
            if record["id"] == assessment_id:
                now = datetime.now(timezone.utc)
                record["review"] = _review(decision, reviewer, now)
                return {
                    "id": str(uuid4()),
                    "assessment_id": assessment_id,
                    "decision": decision,
                    "reviewer": reviewer,
                    "comment": comment,
                    "created_at": _utc(now),
                }
        return None


_COLUMNS = (
    "id, created_at, request, assessment, review_decision, reviewer, reviewed_at"
)


class PostgresStore:
    """One short connection per call. Simple, and fine for a prototype."""

    def __init__(self, url: str) -> None:
        self._url = url

    def _connect(self):
        return psycopg.connect(self._url, autocommit=True)

    @staticmethod
    def _record(row) -> dict:
        return {
            "id": str(row[0]),
            "created_at": _utc(row[1]),
            "request": row[2],
            "assessment": row[3],
            "review": _review(row[4], row[5], row[6]),
        }

    def add(self, request: dict, assessment: dict) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                "INSERT INTO assessments (system_name, request, assessment, rules_version) "
                "VALUES (%s, %s, %s, %s) RETURNING id, created_at",
                (
                    assessment["system_name"],
                    Jsonb(request),
                    Jsonb(assessment),
                    assessment["rules_version"],
                ),
            ).fetchone()
        return {
            "id": str(row[0]),
            "created_at": _utc(row[1]),
            "request": request,
            "assessment": assessment,
            "review": None,
        }

    def list(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT {_COLUMNS} FROM assessments_with_review ORDER BY created_at, id"
            ).fetchall()
        return [self._record(row) for row in rows]

    def get(self, assessment_id: str) -> dict | None:
        if not _is_uuid(assessment_id):
            return None
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT {_COLUMNS} FROM assessments_with_review WHERE id = %s::uuid",
                (assessment_id,),
            ).fetchone()
        return self._record(row) if row else None

    def add_review(self, assessment_id, decision, reviewer, comment) -> dict | None:
        if not _is_uuid(assessment_id):
            return None
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "INSERT INTO review_events (assessment_id, decision, reviewer, comment) "
                    "VALUES (%s::uuid, %s, %s, %s) RETURNING id, created_at",
                    (assessment_id, decision, reviewer, comment),
                ).fetchone()
        except psycopg.errors.ForeignKeyViolation:
            return None
        return {
            "id": str(row[0]),
            "assessment_id": assessment_id,
            "decision": decision,
            "reviewer": reviewer,
            "comment": comment,
            "created_at": _utc(row[1]),
        }


def make_store():
    """A Postgres store when DATABASE_URL is set, otherwise an in-memory one."""
    url = os.environ.get("DATABASE_URL")
    return PostgresStore(url) if url else MemoryStore()