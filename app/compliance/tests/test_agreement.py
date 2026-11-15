from agreement import measure, summarise


def proposal(field, value, kind="bool", applied=True):
    return {"field": field, "kind": kind, "value": value, "applied": value if applied else None}


EXTRACTION = {"proposals": [
    proposal("annex3_areas", ["employment"], "areas"),
    proposal("interacts_directly_with_people", True),
    proposal("role", "deployer", "role", applied=False),
]}


def test_everything_kept_is_accepted_unchanged():
    request = {"annex3_areas": ["employment"], "interacts_directly_with_people": True, "role": "deployer"}
    result = measure(EXTRACTION, request)
    assert (result["proposed"], result["accepted_unchanged"], result["changed"]) == (3, 3, 0)
    assert result["added_by_person"] == []
    assert result["ai_used"] is True


def test_a_changed_answer_is_counted_as_changed():
    request = {"annex3_areas": ["education"], "interacts_directly_with_people": True, "role": "provider"}
    result = measure(EXTRACTION, request)
    assert result["accepted_unchanged"] == 1 and result["changed"] == 2
    outcomes = {d["field"]: d["outcome"] for d in result["details"]}
    assert outcomes["annex3_areas"] == "changed"
    assert outcomes["role"] == "changed"


def test_area_order_does_not_matter():
    extraction = {"proposals": [proposal("annex3_areas", ["employment", "education"], "areas")]}
    result = measure(extraction, {"annex3_areas": ["education", "employment"]})
    assert result["accepted_unchanged"] == 1


def test_a_proposal_the_person_switched_off_is_changed():
    result = measure({"proposals": [proposal("interacts_directly_with_people", True)]},
                     {"interacts_directly_with_people": False})
    assert result["changed"] == 1


def test_answers_the_ai_never_proposed_are_added_by_person():
    request = {"annex3_areas": ["employment"], "interacts_directly_with_people": True,
               "role": "deployer", "performs_profiling": True, "eu_nexus": False}
    result = measure(EXTRACTION, request)
    assert set(result["added_by_person"]) == {"performs_profiling", "eu_nexus"}


def test_defaults_are_not_counted_as_added():
    result = measure({"proposals": []}, {"eu_nexus": True, "role": "provider", "annex3_areas": [],
                                         "social_scoring": False, "name": "x"})
    assert result["added_by_person"] == []


def test_pre_filled_is_reported_per_proposal():
    result = measure(EXTRACTION, {"role": "deployer"})
    flags = {d["field"]: d["pre_filled"] for d in result["details"]}
    assert flags == {"annex3_areas": True, "interacts_directly_with_people": True, "role": False}


def test_summary_totals_and_rate():
    a = measure(EXTRACTION, {"annex3_areas": ["employment"], "interacts_directly_with_people": True, "role": "deployer"})
    b = measure(EXTRACTION, {"annex3_areas": [], "interacts_directly_with_people": True, "role": "provider"})
    total = summarise([a, b])
    assert total["assessments_with_ai"] == 2 and total["proposed"] == 6
    assert total["accepted_unchanged"] == 4 and total["changed"] == 2
    assert total["accepted_rate"] == round(4 / 6, 3)


def test_summary_of_nothing_has_no_rate():
    assert summarise([])["accepted_rate"] is None
