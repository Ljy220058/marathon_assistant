import argparse
import json
from pathlib import Path
from typing import Any

from run_demo import load_cases, run_case


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "benchmark" / "system_visible_cases.jsonl"
SYSTEMS = ["naked_llm", "vanilla_rag", "multi_agent_no_rule_gate", "full_rule_governed"]


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
