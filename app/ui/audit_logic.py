"""Turns stored assessments into audit-trail rows. Pure functions, no Streamlit."""
from __future__ import annotations

import csv
import io

from ui_logic import TIER_STYLE

COLUMNS = ["time", "system", "result", "cited", "id"]
_FORMULA_STARTS = ("=", "+", "-", "@")


def safe_cell(value: str) -> str:
    """Stops a spreadsheet from running a name like '=1+1' as a formula."""
    text = str(value)
    return "'" + text if text.startswith(_FORMULA_STARTS) else text


def audit_row(record: dict) -> dict:
    assessment = record["assessment"]
    label = TIER_STYLE.get(assessment["tier"], (assessment["tier"],))[0]
    return {
        "time": record["created_at"],
        "system": assessment["system_name"],
        "result": label,
        "cited": ", ".join(reason["article"] for reason in assessment["reasons"]),
        "id": record["id"],
    }


def audit_rows(records: list[dict]) -> list[dict]:
    """Newest first."""
    ordered = sorted(records, key=lambda record: record["created_at"], reverse=True)
    return [audit_row(record) for record in ordered]


def filter_rows(rows: list[dict], result: str = "All", text: str = "") -> list[dict]:
    needle = text.strip().lower()
    kept = []
    for row in rows:
        if result != "All" and row["result"] != result:
            continue
        if needle and needle not in (row["system"] + " " + row["cited"]).lower():
            continue
        kept.append(row)
    return kept


def to_csv(rows: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: safe_cell(value) for key, value in row.items()})
    return buffer.getvalue()