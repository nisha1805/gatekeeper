"""How far the person's final answers agree with what the AI proposed.

Pure functions, no database. A proposal is "accepted unchanged" when the person's
final answer for that field equals the proposed value. Everything else is "changed".
Answers the person gave that the AI never proposed are counted as "added by person".
"""
from __future__ import annotations

from questions import QUESTIONS

# What each question means when nobody answers it (same as the API defaults).
_DEFAULTS = {"eu_nexus": True, "role": "provider"}


def _default(question):
    if question.field in _DEFAULTS:
        return _DEFAULTS[question.field]
    return [] if question.kind == "areas" else False


def _same(kind: str, proposed, final) -> bool:
    if kind == "areas":
        return set(final or []) == set(proposed or [])
    return final == proposed


def measure(extraction: dict, request: dict) -> dict:
    """Compare the stored proposals with the final request of one assessment."""
    proposals = extraction.get("proposals", [])
    details = []
    for proposal in proposals:
        field = proposal["field"]
        final = request.get(field)
        accepted = _same(proposal["kind"], proposal["value"], final)
        details.append({
            "field": field,
            "proposed": proposal["value"],
            "final": final,
            "pre_filled": proposal.get("applied") is not None,
            "outcome": "accepted_unchanged" if accepted else "changed",
        })
    proposed_fields = {proposal["field"] for proposal in proposals}
    added = []
    for question in QUESTIONS:
        if question.field in proposed_fields:
            continue
        final = request.get(question.field, _default(question))
        if not _same(question.kind, _default(question), final):
            added.append(question.field)
    accepted_count = sum(d["outcome"] == "accepted_unchanged" for d in details)
    return {
        "ai_used": True,
        "proposed": len(details),
        "accepted_unchanged": accepted_count,
        "changed": len(details) - accepted_count,
        "added_by_person": added,
        "details": details,
    }


def summarise(measurements: list[dict]) -> dict:
    """Totals over many assessments that started from AI proposals."""
    proposed = sum(m["proposed"] for m in measurements)
    accepted = sum(m["accepted_unchanged"] for m in measurements)
    return {
        "assessments_with_ai": len(measurements),
        "proposed": proposed,
        "accepted_unchanged": accepted,
        "changed": proposed - accepted,
        "added_by_person": sum(len(m["added_by_person"]) for m in measurements),
        "accepted_rate": round(accepted / proposed, 3) if proposed else None,
    }
