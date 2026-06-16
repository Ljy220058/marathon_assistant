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

    # 5 sessions → _frequency_bounds(5) = (1,1), 上限为 1
    # (Seiler 20%×5=1.0, Pfitzinger 保底 1)
    assert budget["quality_sessions_max"] == 1
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


# ── Task 5: 频次→强度课约束范围测试 ──
import pytest
from marathon_qa_assistant.core.half_marathon_capacity_budget import (
    _frequency_bounds, _compute_intensity_bounds,
)


class TestFrequencyBounds:
    @pytest.mark.parametrize("sessions, expected", [
        (1, (1, 1)),
        (3, (1, 1)),
        (5, (1, 1)),
        (7, (1, 2)),
        (10, (1, 2)),
        (12, (2, 3)),
        (14, (2, 3)),
    ])
    def test_bounds_by_session_count(self, sessions, expected):
        assert _frequency_bounds(sessions) == expected

    def test_zero_sessions_raises(self):
        with pytest.raises(ValueError, match="必须为正整数"):
            _frequency_bounds(0)

    def test_negative_sessions_raises(self):
        with pytest.raises(ValueError, match="必须为正整数"):
            _frequency_bounds(-1)


class TestComputeIntensityBounds:
    @pytest.mark.parametrize("sessions, phase, expected", [
        # 基础期: 上限=下限
        (5, "base_1", (1, 1)),
        (7, "base_2", (1, 1)),
        (14, "base_1", (2, 2)),
        # 建设期: max(lower, upper-1)
        (7, "build", (1, 1)),   # (1,2)->build->(1, max(1,1))=(1,1)
        (10, "build", (1, 1)),  # (1,2)->build->(1,1)
        (14, "build", (2, 2)),  # (2,3)->build->(2, max(2,2))=(2,2)
        # 比赛专项期: 取上限
        (6, "peak", (2, 2)),
        (7, "peak", (2, 2)),
        (10, "peak", (2, 2)),
        (14, "peak", (3, 3)),
        # 减量期: 强制 1
        (7, "taper", (1, 1)),
        (14, "taper", (1, 1)),
        # 导入期: 取下限
        (5, "intro", (1, 1)),
        (7, "intro", (1, 1)),
    ])
    def test_bounds_by_phase(self, sessions, phase, expected):
        assert _compute_intensity_bounds(sessions, phase) == expected

    def test_injury_forces_one(self):
        assert _compute_intensity_bounds(10, "peak", {"injury_or_fatigue": True}) == (1, 1)

    def test_recent_marathon_forces_one(self):
        assert _compute_intensity_bounds(14, "peak", {"recent_marathon": True}) == (1, 1)

    def test_both_injury_and_marathon_forces_one(self):
        assert _compute_intensity_bounds(7, "build", {
            "injury_or_fatigue": True, "recent_marathon": True,
        }) == (1, 1)

    def test_safety_clip_prevents_zero_lower(self):
        """如果频次极低 + 阶段修正会导致 lower=0，安全裁剪应强制为 1。"""
        result = _compute_intensity_bounds(1, "build")
        assert result[0] >= 1

    def test_safety_clip_prevents_four_upper(self):
        """上限不应超过 3（Seiler 精英数据中 14 练的 cap）。"""
        for sessions in range(1, 21):
            _, upper = _compute_intensity_bounds(sessions, "peak")
            assert upper <= 3, f"{sessions} sessions: upper={upper} > 3"


class TestCapacityBudgetIntegration:
    """集成验证: build_half_marathon_capacity_budget 使用新 bounds。"""

    def test_base_phase_caps_at_one(self):
        result = build_half_marathon_capacity_budget(
            weekly_volume_km=50, phase_id="general",
            available_days_count=7, phase_family="base_1",
            total_training_sessions=7,
        )
        assert result["quality_sessions_max"] == 1

    def test_peak_phase_with_many_sessions_allows_three(self):
        result = build_half_marathon_capacity_budget(
            weekly_volume_km=80, phase_id="race_specific",
            available_days_count=7, phase_family="peak",
            total_training_sessions=14,
        )
        assert result["quality_sessions_max"] == 3

    def test_low_volume_triggers_lower_bound(self):
        result = build_half_marathon_capacity_budget(
            weekly_volume_km=30, phase_id="race_specific",
            available_days_count=7, phase_family="peak",
            total_training_sessions=7,
        )
        assert result["quality_sessions_max"] == 1

    def test_backward_compat_no_new_params(self):
        """不传新参数时不应崩溃（向后兼容）。"""
        result = build_half_marathon_capacity_budget(
            weekly_volume_km=40, phase_id="general",
            available_days_count=5,
        )
        assert "quality_sessions_max" in result
