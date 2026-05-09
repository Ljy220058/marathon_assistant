from marathon_qa_assistant.core.half_marathon_schedule_composer import (
    build_hmp_repair_suggestions,
    compose_hmp_week_sessions,
)
from marathon_qa_assistant.core.training_plan_skeleton import build_structured_training_plan_skeleton


def test_composer_blocks_hard_hmp_sessions_in_introductory_phase():
    decision = compose_hmp_week_sessions(
        week_index=1,
        total_weeks=8,
        phase_id="introductory",
        archetype_id="short_build_after_marathon",
        recent_marathon=True,
        weekly_volume_km=55,
    )

    main_sets = " ".join(item["main_set"] for item in decision["sessions"])

    assert decision["active"] is True
    assert "hm_intro_fartlek_hills" in main_sets
    assert "95% HMP" not in main_sets
    assert "100% HMP" not in main_sets
    assert decision["repair_notes"] == ["导入期自动屏蔽95/100/105/107-110% HMP硬课。"]


def test_composer_uses_100_hmp_ladder_only_inside_race_specific_window():
    early = compose_hmp_week_sessions(
        week_index=6,
        total_weeks=14,
        phase_id="race_specific",
        archetype_id="general_half_marathon",
        weekly_volume_km=60,
    )
    close = compose_hmp_week_sessions(
        week_index=10,
        total_weeks=14,
        phase_id="race_specific",
        archetype_id="general_half_marathon",
        weekly_volume_km=60,
    )

    early_text = " ".join(item["main_set"] for item in early["sessions"])
    close_text = " ".join(item["main_set"] for item in close["sessions"])

    assert "hm_100_float_intervals" not in early_text
    assert "hm_90_support_endurance" in early_text
    assert "hm_100_float_intervals" in close_text
    assert "1km@100% HMP" in close_text


def test_repair_suggestions_map_validation_issues_to_actions():
    suggestions = build_hmp_repair_suggestions(
        {
            "issues": [
                {
                    "severity": "error",
                    "constraint_id": "race_specific_timing",
                    "week_index": 1,
                    "day": "周二",
                },
                {
                    "severity": "warning",
                    "constraint_id": "dynamic_hmp_calibration",
                },
            ]
        }
    )

    assert suggestions[0]["action"].startswith("100% HMP课延后到赛前6周内")
    assert "当前5K/8K/10K" in suggestions[1]["action"]


def test_composer_keeps_speed_sessions_calibrated_when_current_race_times_exist():
    decision = compose_hmp_week_sessions(
        week_index=6,
        total_weeks=12,
        phase_id="race_supportive",
        archetype_id="marathoner_aerobic_power_gap",
        weekly_volume_km=55,
        speed_calibration_available=True,
        pace_calibration_status="ready",
    )

    main_sets = " ".join(item["main_set"] for item in decision["sessions"])

    assert "按当前" in main_sets
    assert "能力校准" in main_sets
    assert "未校准" not in main_sets
    assert not decision["repair_notes"]


def test_composer_downgrades_speed_sessions_when_short_race_times_are_missing():
    decision = compose_hmp_week_sessions(
        week_index=6,
        total_weeks=12,
        phase_id="race_supportive",
        archetype_id="marathoner_aerobic_power_gap",
        weekly_volume_km=55,
        speed_calibration_available=False,
        pace_calibration_status="ambitious_target",
    )

    main_sets = " ".join(item["main_set"] for item in decision["sessions"])
    repair_notes = " ".join(decision["repair_notes"])

    assert "体感10K强度" in main_sets
    assert "缺少当前5K/10K成绩" in repair_notes
    assert "目标HMP快于当前能力估计" in repair_notes


def test_composer_shortens_specific_sessions_with_capacity_budget():
    decision = compose_hmp_week_sessions(
        week_index=10,
        total_weeks=12,
        phase_id="race_specific",
        archetype_id="general_half_marathon",
        weekly_volume_km=38,
        speed_calibration_available=True,
        capacity_budget={
            "quality_sessions_max": 1,
            "long_run_max_km": 12,
            "hmp_90_max_km": 10,
            "hmp_100_total_max_km": 4,
            "hmp_105_total_max_km": 4,
            "hmp_110_total_max_km": 2,
        },
    )

    main_sets = " ".join(item["main_set"] for item in decision["sessions"])

    assert decision["capacity_budget"]["quality_sessions_max"] == 1
    assert "累计HMP约4km" in main_sets
    assert "6×600m" in main_sets
    assert "容量预算" in main_sets


def test_training_skeleton_exposes_pace_calibration_and_profile_gaps():
    data = build_structured_training_plan_skeleton(
        query="请给我制定12周半马训练计划。",
        profile={
            "goal": "半马 90 分",
            "experience_level": "进阶",
            "weekly_mileage": 55,
            "t_pace": "4:10/km",
            "target_race_date": "12周后",
            "plan_duration_weeks": 12,
            "available_days": "周二,周三,周五,周日",
            "max_session_minutes": 105,
            "training_background": "全马经验丰富，但近期速度训练不足",
        },
        requested_weeks=12,
    )

    protocol = data["half_marathon_protocol"]
    gap_fields = {item["field"] for item in protocol["profile_gaps"]}
    decision_text = " ".join(
        " ".join(session["main_set"] for session in week["sessions"])
        + " "
        + " ".join(week["repair_notes"])
        for week in protocol["weekly_decisions"]
    )

    assert protocol["pace_calibration"]["target_hmp_pace"] == "4:16/km"
    assert protocol["pace_calibration"]["speed_calibration_available"] is False
    assert protocol["capacity_budget"]["quality_sessions_max"] >= 1
    assert protocol["weekly_decisions"][0]["capacity_budget"]
    assert {"current_5k_time", "current_10k_time"}.issubset(gap_fields)
    assert "体感10K强度" in decision_text


def test_training_skeleton_generates_different_hmp_bias_for_abcd_archetypes():
    cases = [
        (
            "A",
            {
                "training_background": "越野和超马背景，全马耐力强",
                "weaknesses": "速度训练不足",
            },
            "endurance_speed_rebuild",
            "hm_105_specific_speed",
        ),
        (
            "B",
            {
                "training_background": "全马经验丰富，但久疏战阵，近期无系统训练",
                "long_training_gap": True,
            },
            "marathoner_aerobic_power_gap",
            "hm_110_support_speed",
        ),
        (
            "C",
            {
                "recent_marathon": True,
                "training_background": "刚完成全马，8周后转半马",
            },
            "short_build_after_marathon",
            "hm_intro_fartlek_hills",
        ),
        (
            "D",
            {
                "training_background": "1500米和5K背景，中距离速度强",
                "strengths": "速度是优势",
                "weaknesses": "半马经验少，长距离不足",
            },
            "speed_based_endurance_gap",
            "hm_90_support_endurance",
        ),
    ]

    for _label, profile_patch, expected_archetype, expected_workout in cases:
        data = build_structured_training_plan_skeleton(
            query="请给我制定8周半马训练计划。",
            profile={
                "goal": "半马 90 分",
                "experience_level": "进阶",
                "weekly_mileage": 55,
                "t_pace": "4:05/km",
                "target_race_date": "8周后",
                "plan_duration_weeks": 8,
                "available_days": "周二,周四,周日",
                "max_session_minutes": 105,
                **profile_patch,
            },
            requested_weeks=8,
        )
        protocol = data["half_marathon_protocol"]
        decision_text = " ".join(
            session["workout_id"]
            for week in protocol["weekly_decisions"]
            for session in week["sessions"]
        )

        assert protocol["selected_archetype"]["archetype_id"] == expected_archetype
        assert expected_workout in decision_text
        assert data["half_marathon_protocol_validation"]["passed"] is True
