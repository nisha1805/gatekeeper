"""Exact text of the provisions that the rules cite.

The text comes from data/ai_act.json, which data/build_ai_act_data.py copies from
EUR-Lex. Nothing here is written or changed by an AI: a lookup either finds the
copied text or says that it is not included.
"""
from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "ai_act.json"

_ANNEX = re.compile(r"Annex III point (\d+)")


@lru_cache(maxsize=1)
def _data() -> dict:
    with open(DATA_FILE, encoding="utf-8") as handle:
        return json.load(handle)


def meta() -> dict:
    return _data()["meta"]


def unit_digest(unit: dict) -> str:
    """The same fingerprint the build script stores, to detect accidental edits."""
    payload = "\n".join([unit["label"], unit.get("context") or "", unit["text"], json.dumps(unit.get("added", []))])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _provision(unit: dict) -> dict:
    return {
        "label": unit["label"],
        "heading": unit["heading"],
        "context": unit.get("context"),
        "text": unit["text"],
        "added": unit.get("added", []),
        "status": unit["status"],
        "note": unit.get("note"),
    }


def _missing(label: str, heading: str | None, note: str) -> dict:
    return {"label": label, "heading": heading, "context": None, "text": None,
            "added": [], "status": "not_included", "note": note}


def lookup(cited: str) -> list[dict]:
    """The provisions behind one cited article string, for example
    "Art. 6(3), Annex III point 4" or "Art. 5, 6, 50"."""
    data = _data()
    units, headings = data["units"], data["article_headings"]
    found: list[dict] = []

    article_part = re.split(r",?\s*Annex", cited)[0].strip()
    if article_part.startswith("Art."):
        items = [item.strip() for item in article_part[len("Art."):].split(",") if item.strip()]
        for item in items:
            label = f"Art. {item}"
            if label in units:
                found.append(_provision(units[label]))
            elif item.isdigit() and item in headings:
                found.append(_missing(label, f"Article {item}: {headings[item]}",
                                      "The whole article applies. Read it on EUR-Lex."))
            else:
                found.append(_missing(label, None, "The exact text of this provision is not included yet."))

    annex = _ANNEX.search(cited)
    if annex:
        label = f"Annex III point {annex.group(1)}"
        if label in units:
            found.append(_provision(units[label]))
        else:
            found.append(_missing(label, None, "The exact text of this provision is not included yet."))
    return found


def sources_for(assessment: dict) -> dict:
    """Exact text for every article an assessment cites, in citation order."""
    seen, items = set(), []
    for item in list(assessment.get("reasons", [])) + list(assessment.get("transparency_duties", [])):
        cited = item["article"]
        if cited in seen:
            continue
        seen.add(cited)
        items.append({"cited": cited, "provisions": lookup(cited)})
    return {"items": items, "meta": meta()}
