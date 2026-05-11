from marathon_qa_assistant.services.training_load import (
    build_training_load_summary,
    calculate_plan_training_load,
)


def test_training_load_prefers_total_distance_over_segment_sum():
    estimate = calculate_plan_training_load(
        {
            "distance_km": 10,
            "warmup_km": 2,
            "main_km": 6,
            "cooldown_km": 2,
        },
        workout_type="easy_run",
        zone_range="Z2",
    )

    assert estimate.duration_min == 65
    assert estimate.training_load == 58
    assert estimate.factors["load_kind"] == "planned_load_proxy"


def test_training_load_sums_segments_when_total_distance_is_missing():
    estimate = calculate_plan_training_load(
        {
            "warmup_km": 2,
            "main_km": 6,
            "cooldown_km": 2,
        },
        workout_type="easy_run",
        zone_range="Z2",
    )

    assert estimate.duration_min == 65
    assert estimate.training_load == 58


def test_training_load_parses_repetition_minutes_before_plain_minutes():
    estimate = calculate_plan_training_load(
        {"main_set": "5 x 3 min"},
        workout_type="vo2max_interval",
        zone_range="Z6-Z7",
    )

    assert estimate.duration_min == 15
    assert estimate.intensity_zone == "Z7"
    assert estimate.training_load == 50


def test_training_load_summary_declares_proxy_load_not_device_truth():
    summary = build_training_load_summary([
        {"week_index": 1, "training_load": 50},
        {"week_index": 1, "training_load": 70},
    ])

    assert summary["method"] == "planned_zone_duration_proxy"
    assert summary["load_kind"] == "planned_load_proxy"
    assert "不等同于" in summary["disclaimer"]


def test_training_load_summary_quantifies_weekly_delta():
    summary = build_training_load_summary([
        {"week_index": 1, "training_load": 100},
        {"week_index": 1, "training_load": 120},
        {"week_index": 2, "training_load": 150},
        {"week_index": 2, "training_load": 180},
        {"week_index": 3, "training_load": 160},
    ])

    weekly = summary["weekly_loads"]
    assert weekly[0]["delta_from_previous"] == 0
    assert weekly[0]["delta_percent_from_previous"] == 0.0
    assert weekly[0]["trend_label"] == "baseline"
    assert weekly[1]["delta_from_previous"] == 110
    assert weekly[1]["delta_percent_from_previous"] == 50.0
    assert weekly[1]["trend_label"] == "build"
    assert weekly[2]["delta_from_previous"] == -170
    assert weekly[2]["trend_label"] == "deload"
    assert "weekly_load_changes" in summary


def test_training_load_infers_distance_repetition_duration():
    estimate = calculate_plan_training_load(
        {"main_set": "6×2000m，组间2min"},
        workout_type="aerobic_threshold",
        zone_range="Z3-Z4",
    )

    assert estimate.duration_min == 88
    assert estimate.factors["distance_repetition_km"] == 12.0
