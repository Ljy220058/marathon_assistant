import asyncio
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).absolute().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from marathon_qa_assistant.core.workflow import integrated_app, IntegratedState

HIGH_INTENSITY_FORBIDDEN_IN_BASE = {"间歇跑", "摄氧量训练", "无氧阈"}

PROFILE_4DAY_4W = {
    "experience_level": "进阶",
    "weekly_mileage": 80,
    "goal": "半马 90 分",
    "injury_history": ["无"],
    "long_term_memory": [],
    "verified_facts": {},
    "last_race_time": "未知",
    "pb_800m": "",
    "pb_1500m": "",
    "pb_5k": "",
    "pb_10k": "",
    "pb_half": "",
    "pb_full": "",
    "lthr": 170,
    "t_pace": "400",
    "target_race_date": "3个月",
    "plan_duration_weeks": 12,
    "available_days": "周二,周四,周六,周日",
    "max_session_minutes": 100,
    "vo2max": 55,
}

PROFILE_4DAY_8W = {
    **PROFILE_4DAY_4W,
    "goal": "全马 330",
    "target_race_date": "5个月",
    "plan_duration_weeks": 20,
    "weekly_mileage": 70,
    "t_pace": "430",
}

def build_state(query: str, profile: dict) -> IntegratedState:
    return {
        "query": query,
        "mode": "team",
        "intent_type": "qa",
        "category": "",
        "subtasks": [],
        "draft_plan": "",
        "review_feedback": "",
        "is_approved": False,
        "iteration_count": 0,
        "final_report": "",
        "structured_training_plan": None,
        "structured_report": None,
        "reasoning_log": [],
        "rag_sources": [],
        "graph_context": "",
        "wiki_context": "",
        "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "audit_scores": {"consistency": 0, "safety": 0, "roi": 0, "summary": ""},
        "roi_history": [],
        "risk_alert": "",
        "entities": [],
        "mermaid_graph": "",
        "guided_questions": [],
        "user_profile": profile,
        "adaptive_feedback": {},
        "adaptive_adjustment": {},
        "missing_info_status": "",
        "enhancement_missing_fields": [],
        "history": [],
    }


def validate_base_phase(weeks: list, label: str) -> list:
    violations = []
    base_phases = ("基础期-1", "基础期-2", "基础期")
    for week in weeks:
        phase = week.get("phase_name", week.get("week_label", ""))
        is_base = any(bp in str(phase) for bp in base_phases)
        if not is_base:
            continue
        wn = week.get("week_number", "?")
        for day in week.get("daily_plans", week.get("days", [])):
            dl = day.get("day_label", "")
            q = day.get("quality_session_type", "")
            s = day.get("secondary_session_type", "")
            e = day.get("easy_run_type", "")
            lr = day.get("long_run_type", "")
            all_text = f"{q} {s} {e} {lr}"
            for forbidden in HIGH_INTENSITY_FORBIDDEN_IN_BASE:
                if forbidden in all_text:
                    violations.append(
                        f"  [FAIL] [{label}] W{wn} {dl} [{phase}] has forbidden: {forbidden} (q={q}, s={s})"
                    )
    return violations


def count_new_types(weeks: list) -> dict:
    counts = {"法特莱克": 0, "坡道训练": 0, "短冲": 0}
    all_text = json.dumps(weeks, ensure_ascii=False)
    for key in counts:
        counts[key] = all_text.count(key)
    return counts


def print_weekly(weeks: list, max_w: int = 12):
    for w in weeks[:max_w]:
        wn = w.get("week_number", "?")
        ph = w.get("phase_name", w.get("week_label", "?"))
        print(f"\n  [Week{wn}] [{ph}]")
        for d in w.get("daily_plans", w.get("days", [])):
            dl = d.get("day_label", "?")
            q = d.get("quality_session_type", "")
            s = d.get("secondary_session_type", "")
            e = d.get("easy_run_type", "")
            lr = d.get("long_run_type", "")
            ws = d.get("workout_summary", "")
            cd = d.get("cooldown_suggestion", "")
            al = d.get("alternative_workout", "")
            extra = ""
            if cd and cd != "missing":
                extra += f" [cool:{cd[:20]}]"
            if al and al != "missing":
                extra += f" [alt:{al[:20]}]"
            print(f"    {dl}: q={q} | s={s} | e={e} | lr={lr}{extra}")


async def run_test(label: str, query: str, profile: dict):
    print(f"\n{'='*70}")
    print(f"TEST: {label}")
    print(f"  query: {query}")
    print(f"  profile: goal={profile['goal']}, wk={profile['weekly_mileage']}km, days={profile['available_days']}")
    print(f"{'='*70}")

    state = build_state(query, profile)
    print("  [RUN] executing LangGraph workflow...")
    try:
        result = await integrated_app.ainvoke(state)
    except Exception as e:
        print(f"  [FAIL] workflow error: {e}")
        return

    stp = result.get("structured_training_plan") or {}
    sr = result.get("structured_report") or {}

    # Debug: show key workflow state
    print(f"  [DEBUG] intent_type={result.get('intent_type')}, mode={result.get('mode')}")
    print(f"  [DEBUG] missing_fields={result.get('missing_fields')}, missing_info_status={result.get('missing_info_status')}")
    print(f"  [DEBUG] requested_weeks={result.get('requested_weeks')}, final_report len={len(result.get('final_report', '') or '')}")

    # Try multiple paths to find training_plan_weeks
    weeks = (
        (stp or {}).get("training_plan_weeks")
        or (sr or {}).get("training_plan_weeks")
        or (stp or {}).get("week_plans")
        or (sr or {}).get("week_plans")
        or []
    )

    # Also check structured_training_plan nested inside structured_report
    if not weeks and isinstance(sr, dict):
        nested_stp = sr.get("structured_training_plan") or {}
        weeks = nested_stp.get("training_plan_weeks") or nested_stp.get("week_plans") or []

    print(f"  [INFO] total {len(weeks)} weeks")
    print_weekly(weeks)

    # Verify base phase safety
    violations = validate_base_phase(weeks, label)
    print(f"\n  [CHECK] base phase safety: {'PASS' if not violations else 'FAIL'}")
    for v in violations:
        print(v)

    # New types
    ntc = count_new_types(weeks)
    print(f"\n  [CHECK] new workout type occurrences:")
    for k, v in ntc.items():
        print(f"    {k}: {v}")

    # Save
    filename = f"tests/_wf_{label.replace(' ', '_')}.json"
    serializable = {
        "query": query,
        "profile_goal": profile["goal"],
        "structured_training_plan": {k: v for k, v in (stp or {}).items()},
        "structured_report": {k: v for k, v in ((sr or {}) if isinstance(sr, dict) else {}).items()},
        "final_report": result.get("final_report", "")[:2000],
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  [SAVED] {filename}")


async def main():
    print("=" * 70)
    print("Marathon Assistant - Training Plan Quality Validation (LangGraph)")
    print("=" * 70)

    await run_test(
        "4W_short_plan_base_safety",
        "请给我制定4周半马训练计划，我每周跑80公里，可训练日为周二、周四、周六、周日，目标安全完赛，避免受伤。",
        PROFILE_4DAY_4W,
    )

    await run_test(
        "8W_medium_plan_phase_aware",
        "请给我制定8周全马训练计划，我每周跑70公里，可训练日为周二、周四、周六、周日，目标安全完赛。",
        PROFILE_4DAY_8W,
    )

    print("\n" + "=" * 70)
    print("Validation complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
