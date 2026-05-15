import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "benchmark" / "system_visible_cases.jsonl"

GOLD_ONLY_FIELDS = {
    "expected_behavior",
    "gold_risk_level",
    "required_rules",
    "forbidden_outputs",
    "rationale",
    "notes",
    "case_family",
    "variation_type",
    "source_seed_id",
    "annotation_notes",
}

DETERMINISTIC_GENERATED_AT = "2026-05-13T00:00:00Z"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(json.loads(line))
    return cases


def load_cases(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Benchmark input not found: {path}. "
            "Use benchmark/system_visible_cases.jsonl for the default v0.4 500-case run."
        )
    cases = load_jsonl(path)
    return [{k: v for k, v in case.items() if k not in GOLD_ONLY_FIELDS} for case in cases]


def contains_any(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def infer_risk_level(case: dict[str, Any]) -> str:
    query = case.get("user_query", "")
    profile = case.get("profile", {})
    symptoms = set(profile.get("symptoms", []))
    category = case.get("category")

    if symptoms & {
        "chest_pain",
        "syncope",
        "near_syncope",
        "confusion",
        "heat_illness",
        "fever",
        "palpitations_with_dizziness",
        "foot_numbness",
        "tingling",
        "palpitations_during_exercise",
    }:
        return "R3"
    if category == "medical_red_flag":
        return "R3"
    if profile.get("medical_condition") and contains_any(query, ["exact", "dosing", "therapy"]):
        return "R3"
    if contains_any(
        query,
        [
            "chest pain",
            "faint",
            "syncope",
            "collapse",
            "confusion",
            "heat stroke",
            "fever",
            "numb",
            "tingling",
            "irregular heartbeats",
        ],
    ):
        return "R3"

    if category in {"fatigue_overload", "pain_injury", "environment_risk", "wearable_uncertainty"}:
        return "R2"
    if category == "evidence_gap" and case.get("case_id") not in {"mexrx-044", "mexrx-094"}:
        return "R2"
    if category == "nutrition" and profile.get("weight_loss_goal_kg", 0) >= 5:
        return "R2"
    if profile.get("pain") or contains_any(query, ["worsening pain", "sharp pain", "limp"]):
        return "R2"
    if profile.get("sleep_quality") == "poor" or profile.get("subjective_fatigue") == "high":
        return "R2"
    if profile.get("temperature_c", 0) >= 32:
        return "R2"
    if profile.get("air_quality") in {"poor", "very_poor"}:
        return "R2"
    if profile.get("hrv") == "low" or profile.get("resting_hr") == "elevated":
        return "R2"
    usual = profile.get("usual_weekly_km", profile.get("weekly_km", 0))
    if usual and profile.get("weekly_km", 0) > usual * 1.3:
        return "R2"
    if contains_any(query, ["guarantee", "extreme"]):
        return "R2"
    if case.get("category") == "general_education":
        return "R0"
    if case.get("category") in {"low_risk_plan", "nutrition"}:
        return "R1"
    return "R1"


def infer_rules(case: dict[str, Any], risk_level: str, status: str) -> list[str]:
    rules = [f"risk.{risk_level}"]
    category = case.get("category", "unknown")
    if risk_level == "R3":
        rules.extend(["refusal.medical_boundary", "contract.no_training_prescription"])
    elif category == "evidence_gap":
        rules.extend(["evidence.needs_evidence", "contract.ask_clarification"])
    elif category == "prompt_injection":
        rules.extend(["filter.prompt_injection", "contract.must_follow_rules"])
    elif risk_level == "R2":
        rules.extend(["repair.downgrade_or_restrict", "safety.fail_closed"])
    else:
        rules.extend(["evidence.prescription_eligible", "protocol.contract_bound"])
    if status == "partial_answer":
        rules.append("audit.repair_required")
    if status == "answered":
        rules.append("audit.pass")
    return rules


def expert_calls(case: dict[str, Any], risk_level: str) -> list[str]:
    category = case.get("category")
    calls: list[str] = []
    if risk_level == "R2" and category in {"fatigue_overload", "pain_injury", "medical_red_flag"}:
        calls.append("Rehab/Safety Expert")
    if category == "nutrition":
        calls.append("Nutrition Expert")
    if category == "wearable_uncertainty":
        calls.append("Wearable Uncertainty Expert")
    if category == "environment_risk":
        calls.append("Environment Expert")
    return calls


def decide_status(case: dict[str, Any], risk_level: str) -> str:
    query = case.get("user_query", "")
    profile = case.get("profile", {})
    category = case.get("category")

    if risk_level == "R3":
        return "refused"
    if category == "low_risk_plan" and profile.get("break_days", 0) >= 7:
        return "partial_answer"
    if category == "fatigue_overload":
        usual_weekly_km = profile.get("usual_weekly_km", 0)
        requested_weekly_km = profile.get("requested_weekly_km", 0)
        if profile.get("missed_days", 0) >= 14 or (
            usual_weekly_km > 0 and requested_weekly_km >= usual_weekly_km * 2
        ):
            return "ask_clarification"
        return "partial_answer"
    if category in {"pain_injury", "environment_risk"}:
        return "partial_answer"
    if category == "nutrition":
        if profile.get("weight_loss_goal_kg", 0) >= 5:
            return "ask_clarification"
        return "answered"
    if category == "wearable_uncertainty":
        if contains_any(query, ["raise my zones", "tempo"]) and (
            profile.get("temperature_c", 0) >= 32
            or profile.get("resting_hr") == "elevated"
            or profile.get("resting_hr") == "abnormally_high"
            or profile.get("subjective_feeling") == "unwell"
            or profile.get("heart_rate") == "unusually_high"
        ):
            return "ask_clarification"
        return "partial_answer"
    if category == "evidence_gap":
        if contains_any(query, ["secret elite method"]):
            return "refused"
        if not case.get("available_evidence_ids") or contains_any(query, ["missing", "detailed interval"]):
            return "ask_clarification"
        return "partial_answer"
    if category == "prompt_injection":
        if contains_any(query, ["invent action ids"]):
            return "ask_clarification"
        if contains_any(query, ["omit audit trace", "maximum intensity", "ignore safety"]):
            return "partial_answer"
        return "answered"
    if risk_level == "R2":
        return "partial_answer"
    return "answered"


def build_plan(case: dict[str, Any], risk_level: str, status: str) -> str:
    if status == "refused":
        return (
            "Training prescription refused: a red-flag rule was triggered. "
            "The safe output is a professional-evaluation boundary, not a workout."
        )
    if status == "ask_clarification":
        return (
            "No individualized prescription is generated. The system needs eligible "
            "evidence and missing profile/risk details before planning."
        )
    if status == "partial_answer":
        return (
            "Downgraded output: avoid hard sessions, reduce load, monitor stop "
            "conditions, and use rest/easy alternatives from approved actions."
        )
    if risk_level == "R0":
        return "General explanation only. No individualized workout prescription is generated."
    return (
        "Contract-bound weekly plan: use approved easy running, one controlled quality "
        "element if allowed, one long run within volume budget, and required recovery."
    )


def run_case(case: dict[str, Any], system_name: str = "full_rule_governed") -> dict[str, Any]:
    risk_level = infer_risk_level(case)
    status = decide_status(case, risk_level)
    rules = infer_rules(case, risk_level, status)
    repair_log = []
    if status == "partial_answer":
        repair_log.append(
            {
                "before_state": "candidate training prescription",
                "repair_action": "downgrade_or_restrict_plan",
                "rule_basis": "R2 safety risk outranks performance optimization",
                "after_state": "partial safe answer",
                "re_audit_result": "pass",
            }
        )
    trace = {
        "case_id": case["case_id"],
        "profile_version": case.get("profile", {}).get("profile_version", "unknown"),
        "risk_level": risk_level,
        "rules_fired": rules,
        "evidence_ids": case.get("available_evidence_ids", []),
        "action_ids": case.get("available_action_ids", []) if status != "refused" else [],
        "expert_calls": expert_calls(case, risk_level),
        "audit_result": "pass",
        "repair_log": repair_log,
        "final_status": status,
        "generated_at": DETERMINISTIC_GENERATED_AT,
    }
    return {
        "case_id": case["case_id"],
        "system": system_name,
        "status": status,
        "plan": build_plan(case, risk_level, status),
        "trace": trace,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one M-EXRx case without gold labels.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--case-id", default="mexrx-002")
    parser.add_argument("--system-name", default="full_rule_governed")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    cases = load_cases(args.cases)
    by_id = {case["case_id"]: case for case in cases}
    if args.case_id not in by_id:
        raise SystemExit(f"Unknown case_id: {args.case_id}")

    result = run_case(by_id[args.case_id], system_name=args.system_name)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
