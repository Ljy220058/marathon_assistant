from marathon_qa_assistant.core.half_marathon_glossary import (
    evidence_basis_for_constraint,
    get_hmp_glossary_terms,
    term_ids_for_constraint,
    term_ids_for_phase,
    term_ids_for_workout,
)


def test_glossary_exposes_core_hmp_terms():
    terms = get_hmp_glossary_terms(["hmp", "cruise_recovery"])

    assert [term["id"] for term in terms] == ["hmp", "cruise_recovery"]
    assert terms[0]["label"] == "HMP"
    assert "source_docs" in terms[0]


def test_float_interval_workout_maps_to_race_specific_terms():
    term_ids = term_ids_for_workout("hm_100_float_intervals")

    assert "hmp" in term_ids
    assert "race_specific_100" in term_ids
    assert "cruise_recovery" in term_ids


def test_capacity_constraint_maps_to_budget_and_sub70_scaling():
    term_ids = term_ids_for_constraint("capacity_budget_exceeded")

    assert term_ids == ["capacity_budget", "sub70_volume_scaling"]


def test_evidence_basis_contains_source_docs_and_rationale():
    basis = evidence_basis_for_constraint("race_specific_timing", "hm_100_float_intervals")

    assert basis["constraint_id"] == "race_specific_timing"
    assert basis["workout_type"] == "hm_100_float_intervals"
    assert "100% HMP" in basis["summary"]
    assert "docs/half_marathon_hmp_protocol.md" in basis["source_docs"]
    assert "cruise_recovery" in basis["term_ids"]


def test_phase_terms_cover_general_supportive_and_race_specific_phases():
    assert term_ids_for_phase("general") == ["general_phase", "threshold_lt2", "progression_run"]
    assert term_ids_for_phase("race_supportive") == [
        "race_supportive_phase",
        "support_endurance_90",
        "specific_endurance_95",
        "specific_speed_105",
    ]
    assert term_ids_for_phase("race_specific") == [
        "race_specific_phase",
        "race_specific_100",
        "cruise_recovery",
    ]


def test_workout_terms_use_professional_glossary_ids():
    assert term_ids_for_workout("hm_base_threshold_progression") == [
        "hmp",
        "threshold_lt2",
        "ssmax",
        "progression_run",
        "dynamic_calibration",
    ]
    assert term_ids_for_workout("hm_95_long_fast_run") == [
        "hmp",
        "specific_endurance_95",
        "long_fast_run",
        "support_endurance_90",
        "capacity_budget",
    ]
    assert "alternating_kilometers" in term_ids_for_workout("hm_100_float_intervals")
    assert "vo2max" in term_ids_for_workout("hm_110_support_speed")


def test_environment_constraint_maps_to_fatigue_and_weather_terms():
    term_ids = term_ids_for_constraint("environment_or_fatigue_downgrade")

    assert term_ids == [
        "fatigue_downgrade",
        "environment_adjustment",
        "capacity_budget",
        "dynamic_calibration",
    ]


def test_unknown_constraint_evidence_basis_preserves_known_workout_terms():
    basis = evidence_basis_for_constraint("unknown_constraint", "hm_intro_fartlek_hills")

    assert basis["summary"] == "该问题来自半马 HMP 协议安全约束。"
    assert basis["term_ids"] == ["introductory_phase", "fartlek", "hill_sprints", "strides"]
