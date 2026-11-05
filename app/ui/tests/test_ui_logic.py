from ui_logic import DEFAULTS, SAMPLES, build_payload, sample_values


def test_the_defaults_answer_no_to_everything_except_eu_scope():
    yes = [key for key, value in DEFAULTS.items() if value is True]
    assert yes == ["eu_nexus"]


def test_the_payload_contains_only_the_yes_answers():
    payload = build_payload(sample_values("Social scoring app"))
    assert payload["social_scoring"] is True
    assert "manipulative_techniques" not in payload


def test_a_blank_name_gets_a_default_name():
    values = sample_values("Spam filter")
    values["name"] = "   "
    assert build_payload(values)["name"] == "unnamed system"


def test_every_sample_only_uses_known_answers():
    for label in SAMPLES:
        assert set(SAMPLES[label]) <= set(DEFAULTS)


def test_samples_are_copies_and_never_share_a_list():
    first = sample_values("CV screening")
    first["annex3_areas"].append("education")
    assert sample_values("CV screening")["annex3_areas"] == ["employment"]