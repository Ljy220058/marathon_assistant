from marathon_qa_assistant.core.half_marathon_pace_calibration import (
    build_half_marathon_pace_calibration,
    detect_half_marathon_profile_gaps,
)


def test_parse_target_half_marathon_goal_as_90_minutes():
    calibration = build_half_marathon_pace_calibration(
        {
            "goal": "半马 90 分",
            "current_10k_time": "42:00",
            "weekly_mileage": 55,
            "available_days": "周二,周四,周日",
            "recovery_state": "正常",
        }
    )

    assert calibration["target_hmp_pace"] == "4:16/km"
    assert calibration["target_hmp_seconds_per_km"] == 256
    assert calibration["speed_calibration_available"] is True
    assert calibration["source_estimates"][0]["source"] == "10K"


def test_parse_compact_half_marathon_goal_130_as_one_hour_thirty():
    calibration = build_half_marathon_pace_calibration(
        {
            "goal": "半马130",
            "current_5k_time": "20:00",
            "current_10k_time": "42:00",
            "weekly_mileage": 55,
            "available_days": ["周二", "周四", "周日"],
            "injury": "无",
        }
    )

    assert calibration["target_hmp_pace"] == "4:16/km"
    assert calibration["target_hmp_seconds_per_km"] == 256


def test_missing_short_race_times_emit_profile_gaps_and_disable_speed_calibration():
    profile = {
        "goal": "半马 90 分",
        "weekly_mileage": 50,
        "available_days": "周二,周四,周日",
        "recovery_state": "正常",
    }

    gaps = detect_half_marathon_profile_gaps(profile)
    calibration = build_half_marathon_pace_calibration(profile)

    assert {item["field"] for item in gaps} == {"current_5k_time", "current_10k_time"}
    assert calibration["status"] == "insufficient"
    assert calibration["speed_calibration_available"] is False
    assert "体感10K强度" in " ".join(calibration["notes"])


def test_ambitious_target_status_when_current_estimate_is_slower_than_goal():
    calibration = build_half_marathon_pace_calibration(
        {
            "goal": "半马 90 分",
            "current_10k_time": "48:00",
            "weekly_mileage": 45,
            "available_days": "周二,周四,周日",
            "recovery_state": "正常",
        }
    )

    assert calibration["status"] == "ambitious_target"
    assert calibration["current_hmp_seconds_per_km"] > calibration["target_hmp_seconds_per_km"]
    assert calibration["gap_seconds_per_km"] > 0
    assert "当前能力配速" in " ".join(calibration["notes"])


def test_t_pace_fallback_builds_partial_hmp_table_when_race_times_are_missing():
    calibration = build_half_marathon_pace_calibration(
        {
            "t_pace": "4:20/km",
            "weekly_mileage": 50,
            "available_days": "周二,周四,周日",
            "recovery_state": "正常",
        }
    )

    assert calibration["fallback_used"] is True
    assert calibration["target_hmp_pace"] == "4:20/km"
    assert calibration["current_hmp_pace"] == "4:20/km"
    assert calibration["target_zone_table"]
    assert calibration["speed_calibration_available"] is False
