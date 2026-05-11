import sys
import types
import re
from pathlib import Path


root = Path(__file__).parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))


if "langchain_community.vectorstores" not in sys.modules:
    fake_langchain_community = types.ModuleType("langchain_community")
    fake_vectorstores = types.ModuleType("langchain_community.vectorstores")

    class _FakeFAISS:
        pass

    fake_vectorstores.FAISS = _FakeFAISS
    sys.modules["langchain_community"] = fake_langchain_community
    sys.modules["langchain_community.vectorstores"] = fake_vectorstores

if "langchain_ollama" not in sys.modules:
    fake_langchain_ollama = types.ModuleType("langchain_ollama")

    class _FakeOllamaEmbeddings:
        def __init__(self, *args, **kwargs):
            pass

    class _FakeChatOllama:
        def __init__(self, *args, **kwargs):
            pass

    fake_langchain_ollama.OllamaEmbeddings = _FakeOllamaEmbeddings
    fake_langchain_ollama.ChatOllama = _FakeChatOllama
    sys.modules["langchain_ollama"] = fake_langchain_ollama

if "langchain_core.documents" not in sys.modules:
    fake_langchain_core = types.ModuleType("langchain_core")
    fake_documents = types.ModuleType("langchain_core.documents")
    fake_messages = types.ModuleType("langchain_core.messages")

    class _FakeDocument:
        def __init__(self, page_content="", metadata=None):
            self.page_content = page_content
            self.metadata = metadata or {}

    class _FakeMessage:
        def __init__(self, content="", **kwargs):
            self.content = content
            self.additional_kwargs = kwargs

    fake_documents.Document = _FakeDocument
    fake_messages.HumanMessage = _FakeMessage
    fake_messages.SystemMessage = _FakeMessage
    sys.modules["langchain_core"] = fake_langchain_core
    sys.modules["langchain_core.documents"] = fake_documents
    sys.modules["langchain_core.messages"] = fake_messages


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


_DAY_PLAN_FIELDS = set(DayPlan.__dataclass_fields__)


def _plan_from_dict(data):
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
                days=[
                    DayPlan(**{key: value for key, value in day.items() if key in _DAY_PLAN_FIELDS})
                    for day in item["days"]
                ],
                execution_reminder=item["execution_reminder"],
                key_workouts=item.get("key_workouts", []),
                action_suggestions=item.get("action_suggestions", []),
                repeat_guard_signature=RepeatGuardSignature(**item.get("repeat_guard_signature", {})),
            )
            for item in data["week_plans"]
        ],
        first_week_actions=data.get("first_week_actions", []),
    )


def test_build_structured_training_plan_skeleton_outputs_valid_four_week_plan():
    data = build_structured_training_plan_skeleton(
        query="请给我制定4周半马训练计划，训练日固定周二、周四、周日。",
        profile={
            "goal": "半马 90 分",
            "experience_level": "进阶",
            "weekly_mileage": 58,
            "t_pace": "4:00/km",
            "target_race_date": "3个月",
            "plan_duration_weeks": 12,
            "available_days": "周二,周四,周日",
            "max_session_minutes": 100,
        },
        requested_weeks=4,
    )

    plan = _plan_from_dict(data)

    assert plan.plan_meta.actual_weeks == 4
    assert plan.plan_meta.plan_type == "multi_week"
    assert validate_full_training_plan(plan) == []
    assert all(len(week.days) == 7 for week in plan.week_plans)
    assert len(plan.first_week_actions) >= 2
    assert all(week.key_workouts for week in plan.week_plans)
    assert all(week.action_suggestions for week in plan.week_plans)


def test_half_marathon_plan_uses_hmp_protocol_archetype_and_candidates():
    data = build_structured_training_plan_skeleton(
        query="请给我制定8周半马训练计划，我刚比完全马，想转入半马专项。",
        profile={
            "goal": "半马 90 分",
            "experience_level": "进阶",
            "weekly_mileage": 58,
            "t_pace": "4:00/km",
            "target_race_date": "8周后",
            "plan_duration_weeks": 8,
            "available_days": "周二,周四,周日",
            "max_session_minutes": 100,
            "recent_marathon": True,
            "training_background": "全马背景，刚完成一场马拉松",
        },
        requested_weeks=8,
    )

    plan = _plan_from_dict(data)
    protocol = data["half_marathon_protocol"]

    assert protocol["active"] is True
    assert protocol["selected_archetype"]["archetype_id"] == "short_build_after_marathon"
    assert protocol["input_weekly_mileage_km"] == 58
    assert protocol["phase_sequence"][0] == "introductory"
    assert data["half_marathon_protocol_validation"]["active"] is True
    assert data["half_marathon_protocol_validation"]["passed"] is True
    assert any("HMP协议阶段目标" in item["objective"] for item in data["phase_summary"])
    assert "C 型" in plan.week_plans[0].week_goal
    assert any("HMP协议" in item and "候选课表" in item for item in plan.week_plans[0].key_workouts)
    assert any("HMP协议" in item for item in plan.week_plans[0].action_suggestions)
    assert validate_full_training_plan(plan) == []


def test_half_marathon_skeleton_cleans_stale_pace_and_repaired_validation_warnings():
    data = build_structured_training_plan_skeleton(
        query="请给我生成12周半马训练计划。",
        profile={
            "goal": "半马 PB 1小时45分",
            "experience_level": "进阶",
            "weekly_mileage": 35,
            "target_pace": "半马 1:45",
            "t_pace": "3:15/km",
            "available_days": "周二,周四,周日",
        },
        requested_weeks=12,
    )

    validation = data["half_marathon_protocol_validation"]
    main_sets = [
        day["main_set"]
        for week in data["week_plans"]
        for day in week["days"]
    ]

    assert validation["active"] is True
    assert validation["passed"] is True
    assert validation["warnings"] == []
    assert validation["issues"] == []
    assert all(not text.startswith("hm_") for text in main_sets)
    assert not any("3:15/km" in text or "3:20/km" in text for text in main_sets)
    assert not any(re.search(r"配速3:\d{2}/km", text) for text in main_sets)
    assert "3×2000m" not in data["week_plans"][0]["days"][1]["main_set"]
    assert any(
        text in data["week_plans"][0]["days"][1]["main_set"]
        for text in ("有氧阈值", "阈值巡航", "渐进跑")
    )


def test_half_marathon_skeleton_exposes_competitive_performance_calibration():
    data = build_structured_training_plan_skeleton(
        query="我是半马125水平，想突破半马120，请生成训练计划。",
        profile={
            "goal": "突破半马120",
            "experience_level": "竞技跑者",
            "weekly_mileage": 70,
            "current_half_time": "1:25",
            "target_pace": "半马 1:20",
            "available_days": "周二,周四,周六,周日",
            "max_session_minutes": 110,
            "recovery_state": "正常",
        },
        requested_weeks=12,
    )

    calibration = data["plan_meta"]["performance_calibration"]
    protocol_calibration = data["half_marathon_protocol"]["pace_calibration"]

    assert calibration["status"] == "ambitious_target"
    assert calibration["current_half_time_seconds"] == 5100
    assert calibration["target_half_time_seconds"] == 4800
    assert calibration["current_hmp_pace"] == "4:02/km"
    assert calibration["target_hmp_pace"] == "3:48/km"
    assert calibration["gap_seconds_per_km"] == 14
    assert calibration["time_gap_seconds"] == 300
    assert calibration["improvement_percent"] == 5.9
    assert calibration["decision_reason"]
    assert protocol_calibration["target_hmp_pace"] == calibration["target_hmp_pace"]


def test_half_marathon_skeleton_uses_recent_four_week_mileage_for_capacity_budget():
    data = build_structured_training_plan_skeleton(
        query="我是半马125水平，想突破半马120，请生成训练计划。",
        profile={
            "goal": "突破半马120",
            "experience_level": "竞技跑者",
            "weekly_mileage": 70,
            "recent_four_week_mileage": 38,
            "current_half_time": "1:25",
            "target_pace": "半马 1:20",
            "available_days": "周二,周四,周六,周日",
            "max_session_minutes": 110,
            "recovery_state": "正常",
        },
        requested_weeks=12,
    )

    protocol = data["half_marathon_protocol"]
    first_budget = protocol["weekly_decisions"][0]["capacity_budget"]
    first_week_quality_days = [
        day
        for day in data["week_plans"][0]["days"]
        if day["training_type"] != "长距离"
        and any(token in f"{day['training_type']} {day['main_set']}" for token in ("有氧阈值", "阈值", "间歇", "摄氧", "专项"))
    ]

    assert protocol["input_weekly_mileage_km"] == 70
    assert protocol["input_recent_four_week_mileage_km"] == 38
    assert first_budget["volume_basis"] == "recent_four_week_mileage"
    assert first_budget["effective_weekly_volume_km"] == 38
    assert first_budget["quality_sessions_max"] == 1
    assert "近4周平均周跑量" in " ".join(first_budget["notes"])
    assert data["week_plans"][0]["repeat_guard_signature"]["weekly_volume_km"] <= 38
    assert len(first_week_quality_days) <= 1
    assert data["half_marathon_protocol_validation"]["passed"] is True
    assert not data["half_marathon_protocol_validation"]["issues"]


def test_build_structured_training_plan_skeleton_supports_twenty_four_weeks_without_adjacent_failures():
    data = build_structured_training_plan_skeleton(
        query="请给我制定24周全马训练计划。",
        profile={
            "goal": "全马 330",
            "experience_level": "进阶",
            "weekly_mileage": 62,
            "t_pace": "4:15/km",
            "target_race_date": "6个月",
            "plan_duration_weeks": 24,
            "available_days": "周二,周四,周六,周日",
            "max_session_minutes": 120,
        },
        requested_weeks=24,
    )

    plan = _plan_from_dict(data)
    comparisons = compare_all_adjacent_weeks(plan)

    assert plan.plan_meta.actual_weeks == 24
    assert validate_full_training_plan(plan) == []
    assert len(comparisons) == 23
    assert all(result["status"] != "fail" for result in comparisons)
    assert plan.first_week_actions
    assert all(len(week.key_workouts) >= 2 for week in plan.week_plans[:4])
    assert all(len(week.action_suggestions) >= 2 for week in plan.week_plans[:4])


def test_goal_race_type_changes_first_week_structure_and_long_run_strategy():
    base_profile = {
        "experience_level": "进阶",
        "weekly_mileage": 50,
        "t_pace": "4:15/km",
        "target_race_date": "1个月",
        "plan_duration_weeks": 4,
        "available_days": "周二,周四,周日",
        "max_session_minutes": 100,
    }

    half_data = build_structured_training_plan_skeleton(
        query="请给我制定4周训练计划。",
        profile={**base_profile, "goal": "半马 90 分"},
        requested_weeks=4,
    )
    marathon_data = build_structured_training_plan_skeleton(
        query="请给我制定4周训练计划。",
        profile={**base_profile, "goal": "全马 3小时30分"},
        requested_weeks=4,
    )

    half_week = half_data["week_plans"][0]
    marathon_week = marathon_data["week_plans"][0]
    half_long_run = next(day for day in half_week["days"] if day["training_type"] == "长距离")
    marathon_long_run = next(day for day in marathon_week["days"] if day["training_type"] == "长距离")

    assert "半马目标" in half_week["week_goal"]
    assert "全马目标" in marathon_week["week_goal"]
    assert "half_marathon_protocol" in half_data
    assert any("HMP协议" in item and "候选课表" in item for item in half_week["key_workouts"])
    assert not any("HMP协议" in item for item in marathon_week["key_workouts"])
    assert "半马专项" in half_long_run["main_set"]
    assert "补给" in marathon_long_run["main_set"]
    assert half_long_run["main_set"] != marathon_long_run["main_set"]


def test_half_year_plan_anti_duplication_for_half_marathon():
    data = build_structured_training_plan_skeleton(
        query="请给我制定26周半马训练计划，比赛在半年后，每周二周四周日训练。",
        profile={
            "goal": "半马训练",
            "experience_level": "进阶",
            "weekly_mileage": 42,
            "t_pace": "4:45/km",
            "available_days": "周二,周四,周日",
            "max_session_minutes": 100,
        },
        requested_weeks=26,
    )
    plan = _plan_from_dict(data)
    weeks = plan.week_plans

    assert plan.plan_meta.actual_weeks >= 20
    assert validate_full_training_plan(plan) == []

    comparisons = compare_all_adjacent_weeks(plan)
    assert len(comparisons) == plan.plan_meta.actual_weeks - 1
    assert all(result["status"] != "fail" for result in comparisons)

    seen_phases = set(week.phase for week in weeks)
    assert len(seen_phases) >= 3

    main_set_pool = set()
    for week in weeks:
        for day in week.days:
            if day.training_type == "长距离":
                main_set_pool.add(day.main_set[:15])
    assert len(main_set_pool) >= 5

    taper_weeks = [w for w in weeks if "减量" in w.phase or "调整" in w.phase]
    assert len(taper_weeks) >= 3
    taper_long_run_minutes = []
    for w in taper_weeks:
        long_day = next((d for d in w.days if d.training_type == "长距离"), None)
        if long_day:
            import re
            m = re.search(r"(\d+)分钟", long_day.main_set)
            if m:
                taper_long_run_minutes.append(int(m.group(1)))
    assert len(taper_long_run_minutes) >= 2
    assert all(
        taper_long_run_minutes[i] <= taper_long_run_minutes[0]
        for i in range(1, len(taper_long_run_minutes))
    )

    adjacent_normalized = []
    for result in comparisons:
        if result["status"] == "pass":
            continue
        a_weeks = result.get("week_a_weeks", [])
        b_weeks = result.get("week_b_weeks", [])
        for a, b in zip(a_weeks, b_weeks):
            if a.phase == b.phase:
                adjacent_normalized.append((a.week_index, b.week_index))
    assert len(adjacent_normalized) < plan.plan_meta.actual_weeks // 2

    has_rest_day_recovery = any(
        "恢复跑" in d.training_type or "恢复" in d.main_set
        for w in weeks for d in w.days
    )
    has_progression = any(
        "渐进" in d.training_type for w in weeks for d in w.days
    )
    assert has_rest_day_recovery or has_progression


def test_half_year_plan_anti_duplication_for_marathon():
    data = build_structured_training_plan_skeleton(
        query="请给我制定26周全马训练计划，比赛在半年后，每周二四六日训练。",
        profile={
            "goal": "全马训练",
            "experience_level": "进阶",
            "weekly_mileage": 55,
            "t_pace": "5:00/km",
            "available_days": "周二,周四,周六,周日",
            "max_session_minutes": 120,
        },
        requested_weeks=26,
    )
    plan = _plan_from_dict(data)
    weeks = plan.week_plans

    assert plan.plan_meta.actual_weeks >= 20
    assert validate_full_training_plan(plan) == []

    comparisons = compare_all_adjacent_weeks(plan)
    assert all(result["status"] != "fail" for result in comparisons)

    primary_types_per_phase = {}
    for week in weeks:
        phase = week.phase
        if phase not in primary_types_per_phase:
            primary_types_per_phase[phase] = set()
        tue_day = next((d for d in week.days if d.day == "周二" and d.training_type != "休息"), None)
        if tue_day:
            primary_types_per_phase[phase].add(tue_day.training_type)

    for phase, types in primary_types_per_phase.items():
        if "减量" in phase or "调整" in phase:
            continue
        assert len(types) >= 2, f"Phase {phase} has only {len(types)} primary types: {types}"

    seen_exact_schedules = set()
    for week in weeks:
        sig = "|".join(f"{d.day}:{d.training_type}:{d.main_set}" for d in week.days)
        assert sig not in seen_exact_schedules, f"Week {week.week_index} has exact duplicate schedule"
        seen_exact_schedules.add(sig)

    has_base_phase = any("基础" in w.phase for w in weeks)
    has_build_phase = any("建设" in w.phase for w in weeks)
    has_peak_phase = any("巅峰" in w.phase for w in weeks)
    has_taper_phase = any("减量" in w.phase for w in weeks)
    assert has_base_phase and has_build_phase and has_peak_phase and has_taper_phase
