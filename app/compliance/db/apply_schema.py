"""Create the application role and apply the schema.

Used for local development and in CI. Safe to run again: every statement is
idempotent. The passwords come from the environment, never from this file.

Usage:
    ADMIN_DATABASE_URL=postgresql://... APP_PASSWORD=... python db/apply_schema.py
"""
import os
import pathlib

import psycopg
from psycopg import sql


def main() -> None:
    admin_url = os.environ["ADMIN_DATABASE_URL"]
    app_password = os.environ["APP_PASSWORD"]
    schema = pathlib.Path(__file__).with_name("001_schema.sql").read_text()
    with psycopg.connect(admin_url, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = 'compliance_app'"
        ).fetchone()
        if not exists:
            conn.execute(
                sql.SQL("CREATE ROLE compliance_app LOGIN PASSWORD {}").format(
                    sql.Literal(app_password)
                )
            )
        conn.execute(schema)
    print("schema applied")


if __name__ == "__main__":
    main()