import copy
import sys
from pathlib import Path


root = Path(__file__).parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))


from marathon_qa_assistant.core.training_plan_models import (
    DayPlan,
    PhaseBlock,
    PlanMeta,
    StructuredTrainingPlan,
    WeekPlan,
    compare_adjacent_weeks,
    compare_all_adjacent_weeks,
    ensure_repeat_guard_signature,
    validate_full_training_plan,
)


def _build_week(
    week_index: int,
    interval: str,
    long_run_minutes: int,
    weekly_volume_km: float,
    *,
    phase: str = "构建期",
    load_level: str = "medium",
) -> WeekPlan:
    week = WeekPlan(
        week_index=week_index,
        phase=phase,
        week_goal=f"第{week_index}周提升专项能力",
        load_level=load_level,
        load_progression_note="按周期逐步推进负荷",
        days=[
            DayPlan("周一", "休息", "无", "休息", "无", "居家", "主动恢复"),
            DayPlan("周二", "轻松跑", "慢跑10分钟", "45分钟，配速4:55/km", "慢跑10分钟", "公园", ""),
            DayPlan("周三", "间歇跑", "慢跑15分钟 + 动态拉伸", interval, "慢跑10分钟 + 拉伸", "田径场", ""),
            DayPlan("周四", "轻松跑", "慢跑10分钟", "40分钟，配速5:00/km", "慢跑10分钟", "公园", ""),
            DayPlan("周五", "节奏跑", "慢跑15分钟 + 动态拉伸", "25分钟，配速4:05/km", "慢跑10分钟", "公园", ""),
            DayPlan("周六", "轻松跑", "慢跑10分钟", "35分钟，配速5:05/km", "慢跑10分钟", "公园", ""),
            DayPlan(
                "周日",
                "长距离",
                "慢跑15分钟 + 动态拉伸",
                f"{long_run_minutes}分钟，配速4:50-5:05/km",
                "慢跑10分钟 + 拉伸",
                "公路",
                "",
            ),
        ],
        execution_reminder="按计划执行，避免额外加量。",
        key_workouts=[
            f"周三 间歇跑：{interval}",
            f"周日 长距离：{long_run_minutes}分钟，配速4:50-5:05/km",
        ],
        action_suggestions=[
            "先锁定本周质量课与长距离的时间窗口。",
            "主课完成后不要额外加量，优先恢复。",
        ],
    )
    signature = ensure_repeat_guard_signature(week)
    signature.weekly_volume_km = weekly_volume_km
    return week


def _build_plan(weeks):
    return StructuredTrainingPlan(
        plan_meta=PlanMeta(
            request_text="请给我制定四周训练计划",
            requested_weeks=len(weeks),
            actual_weeks=len(weeks),
            goal="全马 sub330",
            experience_level="进阶",
            target_race_date="4周后",
            plan_type="multi_week" if len(weeks) > 1 else "single_week",
            generated_at="2026-05-02",
        ),
        phase_summary=[
            PhaseBlock("构建期", 1, max(1, len(weeks) - 1), "逐步提高专项负荷"),
            PhaseBlock("减量期", len(weeks), len(weeks), "恢复并准备比赛"),
        ],
        week_plans=weeks,
        first_week_actions=["先完成首周主质量课。", "长距离前准备补给。"],
    )


def test_validate_full_training_plan_accepts_valid_multi_week_plan():
    weeks = [
        _build_week(1, "6×800m，配速3:45/km，组间慢跑200m", 90, 58.0),
        _build_week(2, "5×1000m，配速3:50/km，组间慢跑200m", 100, 62.0),
        _build_week(3, "4×1200m，配速3:55/km，组间慢跑200m", 105, 64.0),
        _build_week(4, "20分钟，配速4:00/km", 80, 50.0, phase="减量期", load_level="taper"),
    ]
    plan = _build_plan(weeks)

    errors = validate_full_training_plan(plan)

    assert errors == []


def test_validate_full_training_plan_rejects_missing_day_structure():
    invalid_week = _build_week(1, "6×800m，配速3:45/km，组间慢跑200m", 90, 58.0)
    invalid_week.days = invalid_week.days[:-1]
    plan = _build_plan([invalid_week])
    plan.plan_meta.plan_type = "single_week"

    errors = validate_full_training_plan(plan)

    assert any("必须完整覆盖 7 天" in error for error in errors)


def test_compare_adjacent_weeks_flags_exact_duplicate_weeks():
    week1 = _build_week(1, "6×800m，配速3:45/km，组间慢跑200m", 90, 58.0)
    week2 = copy.deepcopy(week1)
    week2.week_index = 2

    result = compare_adjacent_weeks(week1, week2)

    assert result["status"] == "fail"
    assert result["similarity_score"] >= 85
    assert any("关键训练安排完全一致" in reason for reason in result["reasons"])


def test_compare_adjacent_weeks_allows_progressive_weeks():
    week1 = _build_week(1, "6×800m，配速3:45/km，组间慢跑200m", 90, 58.0)
    week2 = _build_week(2, "5×1000m，配速3:50/km，组间慢跑200m", 100, 62.0)

    result = compare_adjacent_weeks(week1, week2)

    assert result["status"] == "pass"
    assert result["similarity_score"] < 70


def test_compare_adjacent_weeks_relaxes_threshold_for_taper_week():
    week3 = _build_week(3, "20分钟，配速4:00/km", 85, 54.0)
    week4 = _build_week(4, "20分钟，配速4:00/km", 75, 54.0, phase="减量期", load_level="taper")

    result = compare_adjacent_weeks(week3, week4)

    assert result["status"] == "warn"
    assert any("恢复/减量周" in reason for reason in result["reasons"])


def test_compare_all_adjacent_weeks_detects_middle_repeat_in_twenty_week_plan():
    weeks = []
    for week_index in range(1, 21):
        week = _build_week(
            week_index,
            f"{5 + (week_index % 3)}×{800 + week_index * 20}m，配速3:5{week_index % 10}/km，组间慢跑200m",
            85 + week_index,
            50.0 + week_index,
            phase="构建期" if week_index < 18 else "减量期",
            load_level="medium" if week_index < 18 else "taper",
        )
        weeks.append(week)

    weeks[8] = copy.deepcopy(weeks[7])
    weeks[8].week_index = 9
    ensure_repeat_guard_signature(weeks[8]).weekly_volume_km = ensure_repeat_guard_signature(weeks[7]).weekly_volume_km

    plan = _build_plan(weeks)
    results = compare_all_adjacent_weeks(plan)

    repeat_result = next(item for item in results if item["week_a"] == 8 and item["week_b"] == 9)
    assert repeat_result["status"] == "fail"
    assert len(results) == 19
