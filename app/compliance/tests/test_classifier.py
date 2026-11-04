import json

from classifier import AnnexIIIArea, SystemDescription, Tier, classify

EMPLOYMENT = frozenset({AnnexIIIArea.EMPLOYMENT})


def articles(items):
    return [r.article for r in items]


def test_out_of_scope_is_decided_first():
    result = classify(SystemDescription(eu_nexus=False, social_scoring=True))
    assert result.tier == Tier.OUT_OF_SCOPE


def test_plain_internal_tool_is_minimal_risk():
    result = classify(SystemDescription())
    assert result.tier == Tier.MINIMAL_RISK
    assert result.transparency_duties == ()


def test_chatbot_only_has_transparency_duties():
    result = classify(SystemDescription(interacts_directly_with_people=True))
    assert result.tier == Tier.LIMITED_RISK
    assert articles(result.transparency_duties) == ["Art. 50(1)"]


def test_cv_screening_is_high_risk_under_annex_iii_point_4():
    result = classify(SystemDescription(annex3_areas=EMPLOYMENT))
    assert result.tier == Tier.HIGH_RISK
    assert any("Annex III point 4" in a for a in articles(result.reasons))


def test_narrow_task_exception_is_not_high_risk_but_notes_the_duty_to_document():
    result = classify(SystemDescription(annex3_areas=EMPLOYMENT, narrow_procedural_task=True))
    assert result.tier == Tier.MINIMAL_RISK
    assert any("Art. 6(4)" in n for n in result.notes)


def test_profiling_overrides_the_exception():
    result = classify(SystemDescription(
        annex3_areas=EMPLOYMENT, narrow_procedural_task=True, performs_profiling=True,
    ))
    assert result.tier == Tier.HIGH_RISK


def test_social_scoring_is_prohibited():
    result = classify(SystemDescription(social_scoring=True))
    assert result.tier == Tier.PROHIBITED
    assert articles(result.reasons) == ["Art. 5(1)(c)"]


def test_emotion_inference_at_work_is_prohibited_unless_medical_or_safety():
    banned = classify(SystemDescription(emotion_inference_at_work_or_school=True))
    allowed = classify(SystemDescription(
        emotion_inference_at_work_or_school=True,
        emotion_inference_medical_or_safety_reason=True,
    ))
    assert banned.tier == Tier.PROHIBITED
    assert allowed.tier != Tier.PROHIBITED


def test_prohibited_beats_high_risk():
    result = classify(SystemDescription(social_scoring=True, annex3_areas=EMPLOYMENT))
    assert result.tier == Tier.PROHIBITED


def test_high_risk_system_also_lists_transparency_duties():
    result = classify(SystemDescription(
        annex3_areas=EMPLOYMENT, interacts_directly_with_people=True,
    ))
    assert result.tier == Tier.HIGH_RISK
    assert len(result.transparency_duties) == 1


def test_safety_component_of_a_regulated_product_is_high_risk():
    result = classify(SystemDescription(annex1_safety_component=True))
    assert result.tier == Tier.HIGH_RISK
    assert articles(result.reasons) == ["Art. 6(1)"]


def test_same_input_always_gives_the_same_answer():
    system = SystemDescription(annex3_areas=EMPLOYMENT, generates_synthetic_content=True)
    assert classify(system) == classify(system)


def test_every_result_is_labelled_and_serialisable():
    systems = [
        SystemDescription(),
        SystemDescription(social_scoring=True),
        SystemDescription(annex3_areas=EMPLOYMENT),
        SystemDescription(eu_nexus=False),
    ]
    for system in systems:
        data = classify(system).to_dict()
        assert data["disclaimer"].startswith("Decision support only")
        assert data["rules_version"]
        json.dumps(data)


def test_several_annex_iii_areas_are_listed_in_annex_order():
    result = classify(SystemDescription(
        annex3_areas=frozenset({AnnexIIIArea.EMPLOYMENT, AnnexIIIArea.EDUCATION}),
    ))
    assert "point 3" in result.reasons[0].article
    assert "point 4" in result.reasons[1].article


def test_the_2026_image_ban_carries_a_date_to_verify():
    result = classify(SystemDescription(sexual_deepfakes_without_consent=True))
    assert result.tier == Tier.PROHIBITED
    assert any("2 December 2026" in n for n in result.notes)