from marathon_qa_assistant.core.half_marathon_glossary import (
    evidence_basis_for_constraint,
    get_hmp_glossary_terms,
    term_ids_for_constraint,
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
