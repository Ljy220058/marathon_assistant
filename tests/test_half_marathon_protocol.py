import sys
from pathlib import Path


root = Path(__file__).parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))


from marathon_qa_assistant.core.half_marathon_protocol import (
    HM_SAFETY_CONSTRAINTS,
    HM_WORKOUT_RULES,
    build_hmp_zone_pace_table,
    pace_range_for_zone,
    pace_seconds_at_hmp_percent,
    protocol_summary,
    recommend_archetypes,
    select_phase_sequence,
    workout_rules_for_archetype,
    RunnerArchetypeInput,
)


def test_pace_seconds_at_hmp_percent_converts_faster_percent_to_faster_pace():
    hmp_pace = 200

    assert pace_seconds_at_hmp_percent(hmp_pace, 100) == 200
    assert pace_seconds_at_hmp_percent(hmp_pace, 105) == 190
    assert pace_seconds_at_hmp_percent(hmp_pace, 95) == 211


def test_pace_range_for_zone_formats_hmp_support_speed_range():
    faster, slower = pace_range_for_zone(200, "support_speed_107_110")

    assert faster == 182
    assert slower == 187


def test_build_hmp_zone_pace_table_contains_core_hmp_zones():
    rows = build_hmp_zone_pace_table(200)
    by_zone = {row["zone_id"]: row for row in rows}

    assert by_zone["race_specific_100"]["pace"] == "3:20/km"
    assert by_zone["specific_endurance_95"]["percent"] == "95%"
    assert by_zone["support_speed_107_110"]["percent"] == "107%-110%"


def test_recommend_archetypes_prioritizes_short_build_after_marathon():
    decisions = recommend_archetypes(RunnerArchetypeInput(
        recent_marathon=True,
        build_weeks=8,
        marathon_background=True,
        injury_or_fatigue=True,
    ))

    assert decisions[0].archetype_id == "short_build_after_marathon"
    assert "备战期不超过 8 周" in decisions[0].reasons


def test_recommend_archetypes_detects_speed_based_endurance_gap():
    decisions = recommend_archetypes(RunnerArchetypeInput(
        middle_distance_background=True,
        speed_strength=True,
        half_marathon_experience_low=True,
    ))

    assert decisions[0].archetype_id == "speed_based_endurance_gap"
    assert workout_rules_for_archetype("speed_based_endurance_gap")[0].id == "hm_90_support_endurance"


def test_select_phase_sequence_respects_recent_marathon_introductory_phase():
    assert select_phase_sequence(8, recent_marathon=True) == [
        "introductory",
        "race_supportive",
        "race_specific",
    ]
    assert select_phase_sequence(12, recent_marathon=False) == [
        "general",
        "race_supportive",
        "race_specific",
    ]


def test_protocol_summary_exposes_rules_and_safety_constraints():
    summary = protocol_summary()

    assert "hm_100_float_intervals" in HM_WORKOUT_RULES
    assert "no_sub70_volume_copy" in HM_SAFETY_CONSTRAINTS
    assert len(summary["zones"]) >= 8
    assert len(summary["workouts"]) >= 7
    assert len(summary["safety_constraints"]) >= 5
