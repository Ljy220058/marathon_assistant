"""生成20周半马大周期训练计划并输出完整内容用于专业评审"""
import json
import sys
from pathlib import Path

def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in current.parents:
        if (candidate / ".git").exists() and (candidate / "apps").exists():
            return candidate
    return Path.cwd().resolve()


PROJECT_ROOT = _find_project_root()
root = PROJECT_ROOT
sys.path.insert(0, str(root))
backend_src = root / "apps" / "backend" / "src"
if backend_src.exists():
    sys.path.insert(0, str(backend_src))

from marathon_qa_assistant.core.training_plan_models import (
    DayPlan,
    PhaseBlock,
    PlanMeta,
    RepeatGuardSignature,
    StructuredTrainingPlan,
    WeekPlan,
    compare_all_adjacent_weeks,
    validate_full_training_plan,
)
from marathon_qa_assistant.core.training_plan_skeleton import build_structured_training_plan_skeleton

PROFILE = {
    "goal": "半马 1小时30分",
    "experience_level": "进阶",
    "weekly_mileage": 50,
    "t_pace": "4:15/km",
    "target_race_date": "5个月",
    "plan_duration_weeks": 20,
    "available_days": "周二,周四,周六,周日",
    "max_session_minutes": 110,
}

QUERY = "请给我制定20周半马训练计划，目标半马130，每周二周四周六周日训练。"


def plan_from_dict(data):
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


def fmt_day(day):
    if day.training_type == "休息":
        return f"  {day.day} 休息"
    parts = [f"  {day.day} {day.training_type}"]
    main = (day.main_set or "").strip()
    if main:
        parts.append(main[:80])
    return " | ".join(parts)


def main():
    data = build_structured_training_plan_skeleton(query=QUERY, profile=PROFILE, requested_weeks=20)
    plan = plan_from_dict(data)

    print("=" * 100)
    print("【20周半马大周期训练计划 - 完整内容】")
    print("=" * 100)
    print(f"目标: {plan.plan_meta.goal}")
    print(f"水平: {plan.plan_meta.experience_level}")
    print(f"计划周数: {plan.plan_meta.actual_weeks} 周")
    print(f"计划类型: {plan.plan_meta.plan_type}")
    print()

    print("-" * 100)
    print("【阶段概览】")
    print("-" * 100)
    for ps in plan.phase_summary:
        print(f"  {ps.phase}: 第{ps.start_week}周 - 第{ps.end_week}周 | 目标: {ps.objective}")
    print()

    # 按阶段分组输出每周详情
    phase_groups = {}
    for phase in plan.phase_summary:
        phase_groups[phase.phase] = {"start": phase.start_week, "end": phase.end_week, "weeks": []}
    for week in plan.week_plans:
        for phase_name, pg in phase_groups.items():
            if pg["start"] <= week.week_index <= pg["end"]:
                pg["weeks"].append(week)
                break

    for phase in plan.phase_summary:
        pg = phase_groups[phase.phase]
        print("-" * 100)
        print(f"【{phase.phase}】 第{phase.start_week}-{phase.end_week}周 | {phase.objective}")
        print("-" * 100)
        for week in sorted(pg["weeks"], key=lambda w: w.week_index):
            print(f"\n第{week.week_index}周 [{week.load_level}] | {week.week_goal}")
            print(f"  负荷进阶: {week.load_progression_note}")
            for day in week.days:
                print(fmt_day(day))
            if week.key_workouts:
                print(f"  关键训练: {'; '.join(week.key_workouts)}")
            if week.action_suggestions:
                for sug in week.action_suggestions[:2]:
                    print(f"  建议: {sug}")
            # 打印防重复签名
            sig = week.repeat_guard_signature
            if sig and sig.quality_sessions:
                print(f"  质量课: {'; '.join(sig.quality_sessions)}")

    print("\n" + "=" * 100)
    print("【防重复对比】相邻周相似度")
    print("=" * 100)
    comparisons = compare_all_adjacent_weeks(plan)
    for comp in comparisons:
        status_icon = "OK" if comp["status"] == "pass" else ("~" if comp["status"] == "normalized" else "XX")
        a_idx = comp["week_a"]
        b_idx = comp["week_b"]
        print(f"  {status_icon} W{a_idx} vs W{b_idx}: {comp['status']} (similarity={comp.get('similarity_pct', 'N/A')})")

    print("\n" + "=" * 100)
    print("【结构校验】")
    print("=" * 100)
    errors = validate_full_training_plan(plan)
    if errors:
        for e in errors:
            print(f"  ERR {e}")
    else:
        print("  PASS: all validations passed, no structural errors")

    # ---------- 统计 ----------
    print("\n" + "=" * 100)
    print("【统计概览】")
    print("=" * 100)
    training_type_count = {}
    long_run_main_sets = []
    quality_types = []
    for week in plan.week_plans:
        for day in week.days:
            if day.training_type == "休息":
                continue
            training_type_count[day.training_type] = training_type_count.get(day.training_type, 0) + 1
            if day.training_type == "长距离":
                long_run_main_sets.append((week.week_index, day.main_set))
            if day.training_type in ("间歇跑", "无氧阈跑", "节奏跑", "马拉松配速跑", "有氧阈跑", "摄氧量跑", "渐进跑"):
                quality_types.append((week.week_index, week.phase, day.training_type))

    print("\n训练类型分布:")
    for ttype, count in sorted(training_type_count.items(), key=lambda x: -x[1]):
        print(f"  {ttype}: {count}次")

    print(f"\n长距离跑 ({len(long_run_main_sets)} 次):")
    for idx, (wi, ms) in enumerate(long_run_main_sets):
        print(f"  W{wi:2d}: {ms[:80]}")

    print(f"\n质量课类型分布 (各阶段):")
    phase_quality = {}
    for wi, phase, qtype in quality_types:
        phase_quality.setdefault(phase, []).append(qtype)
    for phase in plan.phase_summary:
        if phase.phase in phase_quality:
            types = phase_quality[phase.phase]
            unique = sorted(set(types))
            print(f"  {phase.phase}: {unique} (共{len(types)}次)")

    print(f"\n如果有需求，可将以上 plan 的 dict 导出为 JSON 供进一步分析。")
    print("=" * 100)


if __name__ == "__main__":
    main()
