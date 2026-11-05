from audit_logic import audit_row, audit_rows, filter_rows, safe_cell, to_csv


def record(name, tier, articles, created_at, record_id="id-1"):
    return {
        "id": record_id,
        "created_at": created_at,
        "assessment": {
            "system_name": name,
            "tier": tier,
            "reasons": [{"article": a, "text": "x"} for a in articles],
        },
    }


def test_a_row_shows_the_label_and_the_cited_articles():
    row = audit_row(record(
        "CV tool", "high_risk", ["Art. 6(2)", "Annex III point 4"], "2026-11-05T10:00:00+00:00",
    ))
    assert row["result"] == "High risk"
    assert row["cited"] == "Art. 6(2), Annex III point 4"


def test_rows_are_newest_first():
    older = record("A", "minimal_risk", [], "2026-11-05T09:00:00+00:00", "a")
    newer = record("B", "minimal_risk", [], "2026-11-05T10:00:00+00:00", "b")
    assert [row["system"] for row in audit_rows([older, newer])] == ["B", "A"]


def test_rows_can_be_filtered_by_result_and_by_text():
    rows = audit_rows([
        record("CV tool", "high_risk", ["Art. 6(2)"], "2026-11-05T10:00:00+00:00", "a"),
        record("Spam filter", "minimal_risk", [], "2026-11-05T09:00:00+00:00", "b"),
    ])
    assert [r["system"] for r in filter_rows(rows, result="High risk")] == ["CV tool"]
    assert [r["system"] for r in filter_rows(rows, text="spam")] == ["Spam filter"]
    assert len(filter_rows(rows)) == 2


def test_a_name_that_looks_like_a_formula_is_neutralised():
    assert safe_cell("=1+1") == "'=1+1"
    assert safe_cell("Normal name") == "Normal name"


def test_the_csv_has_a_header_and_neutralised_cells():
    rows = audit_rows([record('=HYPERLINK("x")', "minimal_risk", [], "2026-11-05T10:00:00+00:00")])
    text = to_csv(rows)
    assert text.splitlines()[0] == "time,system,result,cited,id"
    assert "'=HYPERLINK" in text