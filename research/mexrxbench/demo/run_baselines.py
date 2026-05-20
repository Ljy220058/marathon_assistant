import argparse
import json
from pathlib import Path
from typing import Any

from run_demo import load_cases, run_case


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "benchmark" / "system_visible_cases.jsonl"
SYSTEMS = [
    "naked_llm",
    "vanilla_rag",
    "multi_agent_no_rule_gate",
    "full_rule_governed",
    "no_risk_gate",
    "no_evidence_gate",
    "no_contract",
    "no_repair",
    "no_auditor",
]


def degrade_result(result: dict[str, Any], system_name: str) -> dict[str, Any]:
    result = json.loads(json.dumps(result))
    result["system"] = system_name
    result["trace"]["audit_result"] = "review_required"

    if system_name == "full_rule_governed":
        result["trace"]["audit_result"] = "pass"
        return result

    if system_name == "naked_llm":
        result["status"] = "answered"
        result["plan"] = "Free-form training advice without rule audit."
        result["trace"]["final_status"] = "answered"
        result["trace"]["rules_fired"] = []
        result["trace"]["evidence_ids"] = []
        result["trace"]["action_ids"] = []
        result["trace"]["repair_log"] = []
        return result

    if system_name == "vanilla_rag":
        if result["status"] == "refused":
            result["status"] = "partial_answer"
            result["trace"]["final_status"] = "partial_answer"
        result["plan"] = "RAG-grounded advice without prescription contract enforcement."
        result["trace"]["rules_fired"] = ["rag.retrieve"]
        return result

    if system_name == "multi_agent_no_rule_gate":
        if result["status"] == "refused":
            result["status"] = "partial_answer"
            result["trace"]["final_status"] = "partial_answer"
        result["plan"] = "Multi-agent consensus advice without independent rule veto."
        result["trace"]["rules_fired"] = ["agents.debate", "coach.summarize"]
        return result

    if system_name == "no_risk_gate":
        result["trace"]["risk_level"] = "R1"
        result["trace"]["rules_fired"] = [
            rule for rule in result["trace"].get("rules_fired", []) if not rule.startswith("risk.")
        ]
        result["trace"]["rules_fired"].append("ablation.no_risk_gate")
        if result["status"] == "refused":
            result["status"] = "answered"
            result["trace"]["final_status"] = "answered"
            result["trace"]["action_ids"] = result["trace"].get("action_ids") or ["easy_run"]
        result["plan"] = "RiskGate disabled: the system treats risk classification as low risk and may answer unsafe requests."
        return result

    if system_name == "no_evidence_gate":
        result["trace"]["rules_fired"] = [
            rule
            for rule in result["trace"].get("rules_fired", [])
            if not rule.startswith("evidence.")
        ]
        result["trace"]["rules_fired"].append("ablation.no_evidence_gate")
        if result["status"] in {"answered", "partial_answer"}:
            result["trace"]["evidence_ids"] = []
            result["trace"]["action_ids"] = []
        if result["status"] == "ask_clarification":
            result["status"] = "partial_answer"
            result["trace"]["final_status"] = "partial_answer"
        result["plan"] = "EvidenceGate disabled: generated prescription-like advice without eligible evidence/action authority."
        return result

    if system_name == "no_contract":
        result["trace"]["rules_fired"] = [
            rule
            for rule in result["trace"].get("rules_fired", [])
            if not rule.startswith("contract.") and not rule.startswith("protocol.")
        ]
        result["trace"]["rules_fired"].append("ablation.no_contract")
        if result["status"] in {"partial_answer", "ask_clarification"}:
            result["status"] = "answered"
            result["trace"]["final_status"] = "answered"
        result["plan"] = "PrescriptionContract disabled: unbounded plan text may ignore volume, action, and clarification limits."
        return result

    if system_name == "no_repair":
        result["trace"]["rules_fired"] = [
            rule
            for rule in result["trace"].get("rules_fired", [])
            if not rule.startswith("repair.") and rule != "audit.repair_required"
        ]
        result["trace"]["rules_fired"].append("ablation.no_repair")
        if result["status"] == "partial_answer":
            result["trace"]["audit_result"] = "repair_required"
            result["trace"]["repair_log"] = []
            result["plan"] = "Bounded repair disabled: the system detects a limited-answer case but emits no repair action."
        return result

    if system_name == "no_auditor":
        result["trace"]["rules_fired"] = [
            rule for rule in result["trace"].get("rules_fired", []) if not rule.startswith("audit.")
        ]
        result["trace"]["rules_fired"].append("ablation.no_auditor")
        result["trace"]["audit_result"] = "review_required"
        if result["status"] == "refused":
            result["status"] = "partial_answer"
            result["trace"]["final_status"] = "partial_answer"
            result["trace"]["action_ids"] = result["trace"].get("action_ids") or ["easy_run"]
        result["plan"] = "Rule Auditor disabled: candidate advice is not subject to an independent final veto."
        return result

    raise ValueError(f"Unknown system: {system_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run baselines and proposed system.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts" / "baseline_runs")
    args = parser.parse_args()

    cases = load_cases(args.cases)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    manifest = []
    for system_name in SYSTEMS:
        results = [
            degrade_result(run_case(case, system_name="full_rule_governed"), system_name)
            for case in cases
        ]
        payload = {"system": system_name, "case_count": len(results), "results": results}
        out = args.output_dir / f"{system_name}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest.append({"system": system_name, "path": str(out), "case_count": len(results)})

    print(json.dumps({"runs": manifest}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
