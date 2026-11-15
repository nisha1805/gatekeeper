"""Build ai_act.json: the exact text of the AI Act provisions that the rules cite.

The text is copied, never written by hand or by an AI, from the Official Journal
versions on EUR-Lex:
  - Regulation (EU) 2024/1689 (CELEX 32024R1689), the original text
  - Regulation (EU) 2026/1744 (CELEX 32026R1744), which amends it

Usage (the two inputs are the EUR-Lex pages saved as markdown):
    python data/build_ai_act_data.py ORIGINAL.md AMENDING.md data/ai_act.json

The script stops with an error if a provision is missing or a check fails, so a
changed page cannot silently produce wrong text.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date

ORIGINAL_URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32024R1689"
AMENDING_URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32026R1744"

_ROW = re.compile(r"^\|\s*(\d+\.|\([a-z]+\))\s*\|\s*(.*)$")
_PARA = re.compile(r"^(\d+)\.\s{2,}(.*)$")
_ROMAN = {"(i)", "(ii)", "(iii)", "(iv)", "(v)", "(vi)", "(vii)", "(viii)", "(ix)", "(x)"}


def _clean_cell(text: str) -> str:
    text = re.sub(r"\s*\|(\s*\|)*\s*$", "", text).strip()
    return text.replace("<br>", "\n")


def _normalise(markdown: str) -> str:
    return markdown.replace("\xa0", " ")


def _section(markdown: str, start: str, end_patterns: list[str]) -> str:
    match = re.search(start, markdown)
    if not match:
        raise SystemExit(f"not found: {start!r}")
    rest = markdown[match.start():]
    stops = [m.start() for p in end_patterns if (m := re.search(p, rest[10:]))]
    return rest[: min(stops) + 10] if stops else rest


def _parse_body(lines: list[str], numbered_rows: bool = False) -> dict:
    """Paragraphs (or Annex points) with their lead text, lettered points and tails."""
    items: dict[str, dict] = {}
    current = None
    point = None
    for raw in lines:
        line = raw.rstrip()
        if not line.strip() or re.match(r"^\|\s*(---|\s)+\|", line.strip()) or line.strip() in ("|     |     |",):
            continue
        row = _ROW.match(line)
        if row:
            label, text = row.group(1), _clean_cell(row.group(2))
            if label.endswith(".") and numbered_rows:
                key = label[:-1]
                current = items[key] = {"lead": [text], "points": {}, "tail": []}
                point = None
                continue
            if current is None:
                raise SystemExit(f"point {label} before any paragraph")
            if label in _ROMAN and point is not None:
                point["subs"].append((label, text))
            else:
                point = current["points"][label] = {"text": text, "subs": []}
            continue
        para = _PARA.match(line)
        if para and not numbered_rows:
            current = items[para.group(1)] = {"lead": [para.group(2).strip()], "points": {}, "tail": []}
            point = None
            continue
        if current is None:
            continue
        if line.startswith("|"):
            continue
        (current["tail"] if current["points"] else current["lead"]).append(line.strip())
    return items


def _paragraph_text(item: dict) -> str:
    parts = list(item["lead"])
    for label, point in item["points"].items():
        parts.append(f"{label} {point['text']}")
        parts.extend(f"    {sub_label} {sub_text}" for sub_label, sub_text in point["subs"])
    parts.extend(item["tail"])
    return "\n".join(parts)


def _point_text(point: dict, label: str) -> str:
    lines = [f"{label} {point['text']}"]
    lines.extend(f"    {sub_label} {sub_text}" for sub_label, sub_text in point["subs"])
    return "\n".join(lines)


def _digest(unit: dict) -> str:
    payload = "\n".join([unit["label"], unit.get("context") or "", unit["text"], json.dumps(unit.get("added", []))])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build(original: str, amending: str) -> dict:
    original, amending = _normalise(original), _normalise(amending)
    units: dict[str, dict] = {}
    headings: dict[str, str] = {}

    def article(n: int, next_pattern: str):
        text = _section(original, rf"\nArticle {n}\n\n", [next_pattern, r"\nCHAPTER "])
        lines = text.split("\n")
        headings[str(n)] = lines[3].strip()
        return _parse_body(lines[4:])

    def put(label, heading, text, context=None, status="original", added=None, note=None):
        unit = {"label": label, "heading": heading, "context": context, "text": text, "status": status}
        if added:
            unit["added"] = added
        if note:
            unit["note"] = note
        unit["sha256"] = _digest(unit)
        units[label] = unit

    # Article 2: paragraph 1 (who the Regulation applies to)
    a2 = article(2, r"\nArticle 3\n")
    put("Art. 2", "Article 2: Scope", _paragraph_text(a2["1"]),
        note="Only paragraph 1 is shown. The later paragraphs list exemptions, for example for military use, which this tool does not model.")

    # Article 5: paragraph 1 points (a) to (h)
    a5 = article(5, r"\nArticle 6\n")
    lead5 = a5["1"]["lead"][0]
    for label, point in a5["1"]["points"].items():
        put(f"Art. 5(1){label}", "Article 5: Prohibited AI practices", _point_text(point, label),
            context=f"Article 5(1): {lead5}")
    # Points (ba) and (bb) come from the amending regulation
    for label in ("(ba)", "(bb)"):
        match = re.search(rf"^\|\s*‘?\({label[1:-1]}\)\s*\|\s*(.*)$", amending, re.MULTILINE)
        if not match:
            raise SystemExit(f"not found in the amending regulation: point {label}")
        text = _clean_cell(match.group(1)).rstrip("’").strip()
        put(f"Art. 5(1){label}", "Article 5: Prohibited AI practices", f"{label} {text}",
            context=f"Article 5(1): {lead5}", status="added",
            note="Added by Regulation (EU) 2026/1744. Under Article 113 as amended, this point applies from 2 December 2026. Article 5(1a) and (1b) of the amending text set conditions for when it applies.")

    # Article 6: paragraphs 1 to 3, with the paragraphs 1a to 1c that the amendment inserts
    a6 = article(6, r"\nArticle 7\n")
    added6 = []
    cell = re.search(r"^\|\s*\(8\)\s*\|\s*in Article 6, the following paragraphs are inserted:(.*)$", amending, re.MULTILINE)
    if not cell:
        raise SystemExit("not found in the amending regulation: Article 6 paragraphs 1a to 1c")
    for part in cell.group(1).split("<br>"):
        match = re.match(r"\s*‘?(1[abc])\.\s{2,}(.*?)(?:’)?\s*(?:;)?\s*\|?\s*$", part)
        if match:
            added6.append({"label": f"Art. 6({match.group(1)})", "text": match.group(2).strip().rstrip("’").strip()})
    if [a["label"] for a in added6] != ["Art. 6(1a)", "Art. 6(1b)", "Art. 6(1c)"]:
        raise SystemExit(f"unexpected paragraphs 1a to 1c: {added6}")
    put("Art. 6(1)", "Article 6: Classification rules for high-risk AI systems", _paragraph_text(a6["1"]),
        added=added6, note="Paragraphs 1a to 1c were inserted by Regulation (EU) 2026/1744 and are shown below the original paragraph 1.")
    put("Art. 6(2)", "Article 6: Classification rules for high-risk AI systems", _paragraph_text(a6["2"]))
    put("Art. 6(3)", "Article 6: Classification rules for high-risk AI systems", _paragraph_text(a6["3"]))

    # Article 50: paragraphs 1 to 4
    a50 = article(50, r"\nArticle 51\n")
    for n in ("1", "2", "3", "4"):
        put(f"Art. 50({n})", "Article 50: Transparency obligations for providers and deployers of certain AI systems",
            _paragraph_text(a50[n]))

    # Annex III: points 1 to 8
    annex = _section(original, r"\nANNEX III\n", [r"\nANNEX IV\n"])
    lines = annex.split("\n")
    annex_title = lines[3].strip()
    points = _parse_body(lines[4:], numbered_rows=True)
    for n in map(str, range(1, 9)):
        if n not in points:
            raise SystemExit(f"Annex III point {n} not found")
        put(f"Annex III point {n}", f"Annex III: {annex_title}", _paragraph_text(points[n]))

    return {
        "meta": {
            "retrieved": date.today().isoformat(),
            "sources": [
                {"name": "Regulation (EU) 2024/1689, original text", "celex": "32024R1689", "url": ORIGINAL_URL},
                {"name": "Regulation (EU) 2026/1744, amending Regulation (EU) 2024/1689", "celex": "32026R1744", "url": AMENDING_URL},
            ],
            "how": "Copied by data/build_ai_act_data.py from the EUR-Lex pages. Where the amending regulation changes a provision, it is shown as added text with a note. Provisions that the amendment does not touch are shown as in the original text.",
            "not_official": "Only the texts published in the Official Journal are authentic. This is a convenience copy.",
        },
        "article_headings": headings,
        "units": units,
    }


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    original = open(sys.argv[1], encoding="utf-8").read()
    amending = open(sys.argv[2], encoding="utf-8").read()
    data = build(original, amending)
    with open(sys.argv[3], "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(f"wrote {len(data['units'])} provisions")


if __name__ == "__main__":
    main()
