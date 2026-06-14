"""L1/L2/L3 个性化技术单元测试。

覆盖取消硬编码后的三层个性化：
- L1 参数化主课时长（典型值 × 经验/跑量系数，替代硬编码 40）
- L2 Fitness-Fatigue 标准化指标（CTL/ATL/TSB）
- L3 Critical Speed 拟合（从 PB 反推临界速度，作为无 T-Pace 时的强度锚）
"""
from marathon_qa_assistant.core.workout_constraints import WORKOUT_CONSTRAINTS


# ──────────────────────────────────────────────────────────────
# L1: 参数化主课时长
# ──────────────────────────────────────────────────────────────

def test_l1_duration_scales_with_experience_and_mileage():
    from marathon_qa_assistant.core.training_plan_skeleton import _personalized_target_duration
    novice_low = _personalized_target_duration("长距离", {"experience_level": "新手", "weekly_mileage": 20})
    elite_high = _personalized_target_duration("长距离", {"experience_level": "精英", "weekly_mileage": 80})
    # 精英高跑量应明显长于新手低跑量
    assert elite_high > novice_low
    # 长距离 typical=100：新手 0.85×0.9≈76；精英 1.1×1.1≈121
    assert 60 <= novice_low <= 90
    assert 110 <= elite_high <= 130


def test_l1_duration_always_within_workout_constraint_bounds():
    from marathon_qa_assistant.core.training_plan_skeleton import _personalized_target_duration
    # 极端 profile（精英+超高跑量）也必须 clamp 到 [min, max]
    for training_type, constraint in WORKOUT_CONSTRAINTS.items():
        val = _personalized_target_duration(training_type, {"experience_level": "精英", "weekly_mileage": 120})
        assert constraint.min_minutes <= val <= constraint.max_minutes, f"{training_type} 越界: {val}"


def test_l1_duration_degrades_to_typical_without_profile():
    from marathon_qa_assistant.core.training_plan_skeleton import _personalized_target_duration
    val = _personalized_target_duration("节奏跑")
    assert val == WORKOUT_CONSTRAINTS["节奏跑"].typical_minutes


def test_l1_duration_differentiates_training_types():
    from marathon_qa_assistant.core.training_plan_skeleton import _personalized_target_duration
    profile = {"experience_level": "进阶", "weekly_mileage": 50}
    long_run = _personalized_target_duration("长距离", profile)
    interval = _personalized_target_duration("间歇跑", profile)
    # 长距离典型 100min 应远长于间歇 25min，不再是一律 40
    assert long_run > 60 and interval < 40


# ──────────────────────────────────────────────────────────────
# L2: Fitness-Fatigue (TSB)
# ──────────────────────────────────────────────────────────────

def test_l2_tsb_neutral_when_acute_equals_chronic():
    from marathon_qa_assistant.services.training_load import build_training_load_summary
    days = [{"training_load": 100, "week_index": i} for i in range(1, 8)]
    s = build_training_load_summary(days)
    assert s["ctl_42d_weekly_equivalent"] == s["atl_7d"]
    assert s["tsb"] == 0
    assert s["tsb_label"] == "neutral"


def test_l2_tsb_overreaching_when_acute_far_exceeds_chronic():
    from marathon_qa_assistant.services.training_load import build_training_load_summary
    # 前 7 天极高负荷、后 35 天低 → 急性远超慢性 → TSB 极负 → overreaching_risk
    loads = [200] * 7 + [50] * 35
    days = [{"training_load": l, "week_index": i // 7 + 1} for i, l in enumerate(loads)]
    s = build_training_load_summary(days)
    assert s["atl_7d"] > s["ctl_42d_weekly_equivalent"]
    assert s["tsb"] < -30
    assert s["tsb_label"] == "overreaching_risk"


def test_l2_classify_tsb_boundaries():
    from marathon_qa_assistant.services.training_load import classify_tsb
    # 对齐 TrainingPeaks 官方 Form/TSB 区间
    assert classify_tsb(30) == "very_fresh"               # ≥25
    assert classify_tsb(15) == "fresh"                    # 10~25
    assert classify_tsb(0) == "neutral"                   # -10~10
    assert classify_tsb(-20) == "productive_training"     # -30~-10（高效训练区，非疲劳）
    assert classify_tsb(-35) == "overreaching_risk"       # <-30


# ──────────────────────────────────────────────────────────────
# L3: Critical Speed 拟合
# ──────────────────────────────────────────────────────────────

def test_l3_critical_speed_elite_in_reasonable_band():
    from marathon_qa_assistant.core.physiology import calculate_critical_speed
    r = calculate_critical_speed({5000: 900, 10000: 1860, 21097.5: 3900, 42195: 8400})
    assert r["n_points"] == 4
    assert r["r_squared"] > 0.95
    # 精英 CS 约 4.5-5.5 m/s（3:00-3:40/km）
    assert 4.5 <= r["cs_mps"] <= 5.5
    assert r["d_prime_m"] > 0


def test_l3_critical_speed_amateur_slower_than_elite():
    from marathon_qa_assistant.core.physiology import calculate_critical_speed
    elite = calculate_critical_speed({5000: 900, 10000: 1860, 42195: 8400})
    amateur = calculate_critical_speed({5000: 1500, 10000: 3120, 42195: 14400})
    assert amateur["cs_mps"] < elite["cs_mps"]


def test_l3_critical_speed_insufficient_points_returns_empty():
    from marathon_qa_assistant.core.physiology import calculate_critical_speed
    assert calculate_critical_speed({5000: 1200}) == {}
    assert calculate_critical_speed({}) == {}


def test_l3_collect_pb_distance_time_parses_profile_fields():
    from marathon_qa_assistant.core.physiology import collect_pb_distance_time
    dt = collect_pb_distance_time({
        "pb_5k": "20:00", "pb_10k": "42:00", "pb_half": "1:35:00", "pb_full": "3:25:00",
    })
    assert 5000 in dt and 42195 in dt
    assert dt[5000] == 1200  # 20:00
    assert dt[42195] == 12300  # 3:25:00


def test_l3_pace_zones_fallback_to_critical_speed_from_pbs():
    from marathon_qa_assistant.nodes.plan_nodes import _compute_pace_zones
    zones = _compute_pace_zones({
        "pb_5k": "15:00", "pb_10k": "31:00", "pb_half": "65:00", "pb_full": "2:20:00",
    })
    # 无 pace_zones/t_pace/goal 时，应从 PB 拟合 CS 推导
    assert "Critical Speed" in zones.get("_derived_from", "")
    assert all(zones.get(f"Z{i}") for i in range(1, 10))


def test_l3_pace_zones_prefers_explicit_t_pace_over_cs():
    from marathon_qa_assistant.nodes.plan_nodes import _compute_pace_zones
    zones = _compute_pace_zones({"t_pace": "3:30", "pb_5k": "15:00"})
    # 有 T-Pace 时不应走 CS 兜底
    assert "T-Pace" in zones.get("_derived_from", "")
    assert "Critical Speed" not in zones.get("_derived_from", "")
