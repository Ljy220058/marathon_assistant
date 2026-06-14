"""E2E 调试脚本：调用工作流并打印详细 state。"""
import asyncio
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "backend" / "src"))

from marathon_qa_assistant.core.working_state import build_working_state
from marathon_qa_assistant.core.workflow import integrated_app

async def main():
    state = build_working_state(
        query="请为我生成一个12周的半马训练计划",
        mode="subagent",
        user_profile={
            "goal": "半马完赛",
            "level": "进阶",
            "weekly_mileage": 200,
            "lthr": 155,
            "available_days": ["周二", "周四", "周六", "周日"],
            "race_date": "2026-09-14",
            "t_pace": "4:30",
        },
    )
    try:
        result = await asyncio.wait_for(integrated_app.ainvoke(state), timeout=240)
    except Exception as e:
        print(f"EXCEPTION: {type(e).__name__}: {e}")
        # If state was partially updated (fallback), print what we have
        result = state

    # Print key debugging fields
    for key in [
        "mode", "intent_type", "category",
        "workflow_error", "is_approved", "audit_verdict",
        "iteration_count", "hard_rule_retry_count", "rag_audit_retry_count",
    ]:
        v = result.get(key)
        if isinstance(v, (dict, list)):
            print(f"{key}: {json.dumps(v, ensure_ascii=False)[:300]}")
        else:
            print(f"{key}: {v}")

    # reasoning_log
    rl = result.get("reasoning_log") or []
    print(f"\nreasoning_log ({len(rl)} entries):")
    for entry in rl:
        print(f"  {str(entry)[:200]}")

    # execution_trace
    et = result.get("execution_trace") or []
    print(f"\nexecution_trace ({len(et)} entries):")
    for entry in et:
        if isinstance(entry, dict):
            print(f"  {entry.get('node','?')} | {str(entry.get('status',''))[:100]}")
        else:
            print(f"  {str(entry)[:200]}")

    # structured_training_plan
    stp = result.get("structured_training_plan") or {}
    wp = stp.get("week_plans") or []
    print(f"\nweek_plans: {len(wp)}")

    # draft_plan
    dp = str(result.get("draft_plan") or "")
    print(f"draft_plan length: {len(dp)}")
    if dp:
        print(f"draft_plan start: {dp[:200]}")

    # rule_check_result
    rc = result.get("rule_check_result")
    if rc:
        print(f"\nrule_check_result: {json.dumps(rc, ensure_ascii=False)[:400]}")

    # review_feedback
    rf = result.get("review_feedback")
    if rf:
        print(f"\nreview_feedback: {str(rf)[:300]}")

if __name__ == "__main__":
    asyncio.run(main())
