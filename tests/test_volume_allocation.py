"""跑量约束分配引擎测试"""
import sys
from pathlib import Path

root = Path(__file__).parents[1]
sys.path.insert(0, str(root))

from marathon_qa_assistant.core.periodization import (
    BlockParams,
    compute_week_volume_factor,
    resolve_4week_blocks,
)
from marathon_qa_assistant.core.training_plan_models import (
    DayPlan,
    PhaseBlock,
    PlanMeta,
    RepeatGuardSignature,
    StructuredTrainingPlan,
    WeekPlan,
    validate_full_training_plan,
)
from marathon_qa_assistant.core.training_plan_skeleton import build_structured_training_plan_skeleton


def _build_plan(data):
    return StructuredTrainingPlan(
        plan_meta=PlanMeta(**data["plan_meta"]),
        phase_summary=[PhaseBlock(**item) for item in data["phase_summary"]],
        week_plans=[
            WeekPlan(
                week_index=item["week_index"],
                phase=item["phase"],
                week_goal=item["week_goal"],
                load_level=item["load_level"],
                load_progression_note=item["load_progression_note"],
                days=[DayPlan(**day) for day in item["days"]],
                execution_reminder=item["execution_reminder"],
                key_workouts=item.get("key_workouts", []),
                action_suggestions=item.get("action_suggestions", []),
                repeat_guard_signature=RepeatGuardSignature(**item.get("repeat_guard_signature", {})),
            )
            for item in data["week_plans"]
        ],
        first_week_actions=data.get("first_week_actions", []),
    )


def test_dayplan_km_fields_default_to_zero_for_old_data():
    day = DayPlan(day="周一", training_type="休息", warmup="无", main_set="休息", cooldown="无", venue="居家")
    assert day.warmup_km == 0.0
    assert day.main_km == 0.0
    assert day.cooldown_km == 0.0
    assert day.total_km == 0.0


def test_dayplan_total_km_sums_correctly():
    day = DayPlan(
        day="周二", training_type="节奏跑",
        warmup="慢跑15分钟", main_set="25分钟", cooldown="慢跑10分钟",
        venue="田径场",
        warmup_km=3.0, main_km=6.5, cooldown_km=1.5,
    )
    assert day.total_km == 11.0


def test_4week_block_resolution_for_20_weeks():
    blocks = resolve_4week_blocks(20, 50.0)
    assert len(blocks) == 5
    assert blocks[0].start_week == 1
    assert blocks[0].end_week == 4
    assert blocks[0].weeks == 4
    assert blocks[4].start_week == 17
    assert blocks[4].end_week == 20
    assert blocks[4].block_coeff <= 0.65


def test_within_block_factors_produce_peak_at_w3():
    blocks = resolve_4week_blocks(20, 50.0)
    f1 = compute_week_volume_factor(1, blocks)
    f2 = compute_week_volume_factor(2, blocks)
    f3 = compute_week_volume_factor(3, blocks)
    f4 = compute_week_volume_factor(4, blocks)
    assert f3 > f1
    assert f3 > f2
    assert f4 < f3


def test_taper_block_uses_descending_factors():
    blocks = resolve_4week_blocks(20, 50.0)
    f17 = compute_week_volume_factor(17, blocks)
    f18 = compute_week_volume_factor(18, blocks)
    f19 = compute_week_volume_factor(19, blocks)
    f20 = compute_week_volume_factor(20, blocks)
    assert f17 > f18 > f19 > f20


def test_profile_weekly_mileage_is_baseline_before_cutback_week():
    blocks = resolve_4week_blocks(20, 80.0)
    targets = [80.0 * compute_week_volume_factor(w, blocks) for w in range(1, 5)]
    assert targets[0] == 80.0
    assert targets[2] > targets[1] > targets[0]
    assert targets[3] < targets[0]
    assert targets[3] == 72.0


def test_20_week_half_marathon_volume_constraint_all_weeks():
    data = build_structured_training_plan_skeleton(
        query="20周半马训练计划",
        profile={
            "goal": "半马130", "experience_level": "进阶",
            "weekly_mileage": 50, "t_pace": "4:15/km",
            "available_days": "周二,周四,周六,周日",
        },
        requested_weeks=20,
    )
    plan = _build_plan(data)
    assert validate_full_training_plan(plan) == []
    assert plan.plan_meta.actual_weeks == 20

    gaps = []
    for week in plan.week_plans:
        target = week.repeat_guard_signature.weekly_volume_km or 0
        actual = sum(day.total_km for day in week.days)
        gaps.append(abs(actual - target))

    within_2km = sum(1 for g in gaps if g <= 2.0)
    assert within_2km >= 18, f"Only {within_2km}/20 weeks within 2km, gaps: {gaps}"
    assert max(gaps) <= 5.0, f"Max gap {max(gaps):.1f}km exceeds 5km tolerance"


def test_4_week_plan_volume_constraint():
    data = build_structured_training_plan_skeleton(
        query="4周半马训练计划",
        profile={
            "goal": "半马145", "experience_level": "初级",
            "weekly_mileage": 35, "t_pace": "5:00/km",
            "available_days": "周二,周四,周日",
        },
        requested_weeks=4,
    )
    plan = _build_plan(data)
    assert validate_full_training_plan(plan) == []
    for week in plan.week_plans:
        target = week.repeat_guard_signature.weekly_volume_km or 0
        actual = sum(day.total_km for day in week.days)
        assert abs(actual - target) <= 5.0, f"W{week.week_index}: target={target:.1f} actual={actual:.1f}"


def test_daily_km_fields_populated_for_training_days():
    data = build_structured_training_plan_skeleton(
        query="12周全马训练计划",
        profile={
            "goal": "全马330", "experience_level": "进阶",
            "weekly_mileage": 60, "t_pace": "4:30/km",
            "available_days": "周二,周三,周五,周日",
        },
        requested_weeks=12,
    )
    plan = _build_plan(data)
    for week in plan.week_plans:
        for day in week.days:
            if day.training_type == "休息":
                assert day.total_km == 0.0, f"W{week.week_index} {day.day} rest should have 0km"
            elif day.training_type == "长距离":
                assert day.main_km > 5.0, f"W{week.week_index} {day.day} long run should have >5km main"
            elif day.training_type in ("间歇跑", "无氧阈跑", "节奏跑", "有氧阈值训练", "摄氧量训练", "马拉松配速跑", "渐进跑"):
                assert day.main_km > 1.5, f"W{week.week_index} {day.day} {day.training_type} should have >1.5km main, got {day.main_km}"


def test_block_peak_progression_across_blocks():
    data = build_structured_training_plan_skeleton(
        query="20周全马训练计划，比赛半年后",
        profile={
            "goal": "全马400", "experience_level": "中级",
            "weekly_mileage": 55, "t_pace": "5:15/km",
            "available_days": "周二,周四,周六,周日",
        },
        requested_weeks=20,
    )
    plan = _build_plan(data)
    block_peaks = {}
    for week in plan.week_plans:
        block_idx = (week.week_index - 1) // 4
        vol = week.repeat_guard_signature.weekly_volume_km or 0
        if block_idx not in block_peaks:
            block_peaks[block_idx] = vol
        else:
            block_peaks[block_idx] = max(block_peaks[block_idx], vol)

    peak_values = [block_peaks[k] for k in sorted(block_peaks)]
    last_block_idx = max(block_peaks.keys())
    for i in range(len(peak_values) - 2):
        if i < last_block_idx - 1:
            assert peak_values[i] <= peak_values[i + 1] or abs(peak_values[i] - peak_values[i + 1]) < 5.0


def test_80km_four_day_high_load_no_implausible_easy_runs():
    """80km+4天高负荷模式：轻松跑单日不超过周跑量25%(20km)，不出>30km极端轻松跑"""
    data = build_structured_training_plan_skeleton(
        query="20周半马130训练计划，80km周跑量四练",
        profile={
            "goal": "半马130", "experience_level": "进阶",
            "weekly_mileage": 80, "t_pace": "4:15/km",
            "available_days": "周二,周四,周六,周日",
        },
        requested_weeks=20,
    )
    plan = _build_plan(data)
    assert validate_full_training_plan(plan) == []

    max_easy_km = 0.0
    for week in plan.week_plans:
        target = float(week.repeat_guard_signature.weekly_volume_km or 0)
        actual = sum(day.total_km for day in week.days)
        assert abs(actual - target) <= 2.0, f"W{week.week_index}: target={target:.1f} actual={actual:.1f}"
        for day in week.days:
            if day.training_type == "轻松跑":
                max_easy_km = max(max_easy_km, day.total_km)
                if target >= 65.0:
                    assert day.total_km <= target * 0.25 + 0.5, (
                        f"W{week.week_index} {day.day}: easy {day.total_km:.1f}km > 25% of {target:.1f}"
                    )

    assert max_easy_km <= 22.0, f"最大轻松跑单日 {max_easy_km:.1f}km 仍偏高"


def test_high_load_threshold_not_activated_under_18km_per_day():
    """日均<18km时不激活高负荷策略，确保普通场景不受影响"""
    data = build_structured_training_plan_skeleton(
        query="20周全马训练计划",
        profile={
            "goal": "全马400", "experience_level": "中级",
            "weekly_mileage": 55, "t_pace": "5:15/km",
            "available_days": "周二,周四,周六,周日",
        },
        requested_weeks=20,
    )
    plan = _build_plan(data)
    assert validate_full_training_plan(plan) == []

    for week in plan.week_plans:
        target = float(week.repeat_guard_signature.weekly_volume_km or 0)
        actual = sum(day.total_km for day in week.days)
        assert abs(actual - target) <= 5.0, f"W{week.week_index}: target={target:.1f} actual={actual:.1f}"


HIGH_INTENSITY_FORBIDDEN_IN_BASE = {"间歇跑", "摄氧量训练", "无氧阈"}


def test_phase_workout_safety_base_phase_no_high_intensity_intervals():
    """基础期不出现间歇跑/摄氧量训练等高强度课"""
    for weeks, profile in [
        (4, {"goal": "半马训练", "experience_level": "初级", "weekly_mileage": 30, "t_pace": "5:30/km", "available_days": "周二,周四,周日"}),
        (8, {"goal": "全马训练", "experience_level": "中级", "weekly_mileage": 40, "t_pace": "5:00/km", "available_days": "周二,周四,周六,周日"}),
        (12, {"goal": "半马145", "experience_level": "进阶", "weekly_mileage": 50, "t_pace": "4:30/km", "available_days": "周二,周四,周六,周日"}),
    ]:
        data = build_structured_training_plan_skeleton(
            query=f"{weeks}周训练计划",
            profile=profile,
            requested_weeks=weeks,
        )
        plan = _build_plan(data)
        assert validate_full_training_plan(plan) == []
        base_end_week = 0
        for phase in plan.phase_summary:
            if "基础" in (phase.phase or ""):
                base_end_week = max(base_end_week, phase.end_week)
        if base_end_week == 0:
            # 短周期计划按 HMP 协议可无独立基础阶段 (compact/short 模型直奔比赛专项)
            # 无基础阶段 → 无处检查高强度课 — 安全断言退化为空真
            if weeks >= 5:
                raise AssertionError(
                    f"≥5周计划缺少基础期: {[p.phase for p in plan.phase_summary]}"
                )
            continue
        for week in plan.week_plans:
            if week.week_index > base_end_week:
                continue
            for day in week.days:
                for forbidden in HIGH_INTENSITY_FORBIDDEN_IN_BASE:
                    assert forbidden not in day.training_type, (
                        f"W{week.week_index} {day.day} 基础期出现 {day.training_type}，包含禁止字样 '{forbidden}'"
                    )
