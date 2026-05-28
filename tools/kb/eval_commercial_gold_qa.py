from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def eval_commercial_gold_qa(*, evidence_path: Path, gold_qa_path: Path, output_path: Path) -> Dict[str, Any]:
    evidence_rows = _load_jsonl(evidence_path)
    gold_rows = _load_jsonl(gold_qa_path)
    failures: List[Dict[str, Any]] = []
    red_flag_failures: List[str] = []
    for question in gold_rows:
        qid = str(question.get("id") or question.get("question") or "unknown")
        expected_domain = str(question.get("expected_evidence_domain") or "")
        expected_use = str(question.get("expected_allowed_use") or "")
        require_referral = bool(question.get("requires_referral"))
        matches = [
            row
            for row in evidence_rows
            if (not expected_domain or row.get("evidence_domain") == expected_domain)
            and (not expected_use or row.get("allowed_use") == expected_use)
        ]
        if not matches:
            failures.append({"id": qid, "reason": "expected_evidence_not_found"})
            if require_referral:
                red_flag_failures.append(qid)
            continue
        if require_referral and not any(row.get("requires_medical_referral") for row in matches):
            failures.append({"id": qid, "reason": "referral_not_triggered"})
            red_flag_failures.append(qid)
    report = {
        "question_count": len(gold_rows),
        "failure_count": len(failures),
        "passed": not failures,
        "failures": failures,
        "red_flag_failures": red_flag_failures,
    }
    _write_json(output_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate commercial gold QA evidence-domain and red-flag gates.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--gold-qa", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = eval_commercial_gold_qa(evidence_path=Path(args.evidence), gold_qa_path=Path(args.gold_qa), output_path=Path(args.output))
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
