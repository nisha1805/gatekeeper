"""Every article the rules cite must exist in the EUR-Lex copy."""
import json
from pathlib import Path

import classifier

DATA = json.loads((Path(__file__).resolve().parent.parent / "data" / "ai_act.json").read_text(encoding="utf-8"))
UNITS = DATA["units"]


def test_prohibited_and_transparency_citations_exist():
    cited = {a for _, a, _ in classifier._PROHIBITED} | {a for _, a, _ in classifier._TRANSPARENCY}
    cited |= {"Art. 5(1)(f)", "Art. 6(1)", "Art. 6(2)", "Art. 6(3)", "Art. 2"}
    missing = sorted(a for a in cited if a not in UNITS)
    assert missing == []


def test_every_annex_iii_point_exists():
    missing = [p for p in classifier.ANNEX_III_POINT.values() if f"Annex III point {p}" not in UNITS]
    assert missing == []


def test_source_note_no_longer_claims_third_party_site():
    assert "third-party reference" not in classifier.SOURCE_NOTE
    assert classifier.RULES_VERSION == "0.1.1"
