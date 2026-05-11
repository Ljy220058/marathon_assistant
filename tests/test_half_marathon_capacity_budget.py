from marathon_qa_assistant.core.half_marathon_capacity_budget import build_half_marathon_capacity_budget


def test_capacity_budget_scales_sub70_caps_for_lower_mileage_runner():
    budget = build_half_marathon_capacity_budget(
        weekly_volume_km=40,
        phase_id="race_specific",
        available_days_count=3,
        speed_calibration_available=False,
    )

    assert budget["quality_sessions_max"] == 1
    assert budget["hmp_95_max_km"] < 20
    assert budget["hmp_100_total_max_km"] < 10
    assert budget["hmp_105_total_max_km"] < 6
    assert any("低跑量" in note for note in budget["notes"])
    assert any("速度容量" in note for note in budget["notes"])


def test_capacity_budget_allows_more_specific_volume_for_high_mileage_specific_phase():
    budget = build_half_marathon_capacity_budget(
        weekly_volume_km=95,
        phase_id="race_specific",
        available_days_count=5,
        speed_calibration_available=True,
    )

    assert budget["quality_sessions_max"] == 2
    assert budget["hmp_95_max_km"] == 20
    assert budget["hmp_100_total_max_km"] == 14
    assert budget["hmp_105_total_max_km"] == 8


def test_capacity_budget_uses_recent_four_week_mileage_as_conservative_base():
    budget = build_half_marathon_capacity_budget(
        weekly_volume_km=70,
        phase_id="general",
        available_days_count=4,
        recent_four_week_mileage_km=38,
        speed_calibration_available=True,
    )

    assert budget["weekly_volume_km"] == 70
    assert budget["effective_weekly_volume_km"] == 38
    assert budget["recent_four_week_mileage_km"] == 38
    assert budget["volume_basis"] == "recent_four_week_mileage"
    assert budget["quality_sessions_max"] == 1
    assert budget["long_run_max_km"] <= 12.5
    assert any("近4周平均周跑量" in note for note in budget["notes"])


def test_introductory_budget_blocks_hard_hmp_capacity_after_recent_marathon():
    budget = build_half_marathon_capacity_budget(
        weekly_volume_km=60,
        phase_id="introductory",
        available_days_count=4,
        recent_marathon=True,
    )

    assert budget["quality_sessions_max"] == 1
    assert budget["hmp_95_max_km"] == 0
    assert budget["hmp_100_total_max_km"] == 0
    assert budget["hmp_105_total_max_km"] == 0
    assert any("容量下调" in note for note in budget["notes"])
