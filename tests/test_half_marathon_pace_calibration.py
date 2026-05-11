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


def test_calibrates_half_marathon_125_to_120_goal_from_colon_times():
    calibration = build_half_marathon_pace_calibration(
        {
            "goal": "突破半马120",
            "current_half_time": "1:25",
            "target_pace": "半马 1:20",
            "weekly_mileage": 70,
            "available_days": "周二,周四,周六,周日",
            "recovery_state": "正常",
        }
    )

    assert calibration["status"] == "ambitious_target"
    assert calibration["current_half_time_seconds"] == 5100
    assert calibration["target_half_time_seconds"] == 4800
    assert calibration["current_hmp_pace"] == "4:02/km"
    assert calibration["target_hmp_pace"] == "3:48/km"
    assert calibration["gap_seconds_per_km"] == 14
    assert calibration["time_gap_seconds"] == 300
    assert calibration["improvement_percent"] == 5.9
    assert "current_half_time" in calibration["source_fields"]
    assert "target_pace" in calibration["source_fields"]


def test_calibrates_half_marathon_71_to_69_from_target_time_field():
    calibration = build_half_marathon_pace_calibration(
        {
            "goal": "Half marathon PB 1:11:00, target 1:08:59, sub 69 race prep",
            "current_half_time": "1:11:00",
            "target_pace": "1:08:59",
            "weekly_mileage": "105 km",
            "available_days": "Mon Tue Thu Sat Sun",
            "recovery_state": "正常",
        }
    )

    assert calibration["current_half_time_seconds"] == 4260
    assert calibration["target_half_time_seconds"] == 4139
    assert calibration["current_half_time"] == "1:11"
    assert calibration["target_half_time"] == "1:08:59"
    assert calibration["target_hmp_pace"] == "3:16/km"
    assert calibration["gap_seconds_per_km"] == 6
    assert calibration["time_gap_seconds"] == 121
    assert calibration["improvement_percent"] == 2.8
    assert "target_pace" in calibration["source_fields"]


def test_goal_text_prefers_target_marker_over_pb_time():
    calibration = build_half_marathon_pace_calibration(
        {
            "goal": "Half marathon PB 1:11:00, target 1:08:59, sub 69",
            "current_half_time": "1:11:00",
            "weekly_mileage": "105 km",
            "available_days": "Mon Tue Thu Sat Sun",
            "recovery_state": "正常",
        }
    )

    assert calibration["target_half_time_seconds"] == 4139
    assert calibration["target_half_time"] == "1:08:59"
    assert "goal" in calibration["source_fields"]


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
