from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = ROOT / "apps" / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from marathon_qa_assistant.services.kb.live_eval_runner import (  # noqa: E402
    LiveEvalConfigError,
    run_live_rag_vs_base_eval,
    save_live_eval_summary,
)
from marathon_qa_assistant.services.kb.live_eval_artifacts import load_live_eval_answer_artifacts  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GPT/DS RAG-vs-base evaluation with redacted governance output.")
    parser.add_argument("--dry-run", action="store_true", help="Run deterministic contract scoring without network calls.")
    parser.add_argument("--max-questions", type=int, default=None, help="Limit evaluated golden questions.")
    parser.add_argument("--domain-pack", default="", help="Only evaluate one domain_pack.")
    parser.add_argument("--provider", default="", choices=["", "gpt", "ds"], help="Only evaluate one provider.")
    parser.add_argument(
        "--artifact-input",
        default="",
        help="JSONL file produced by build_live_eval_answer_artifacts.py. Required for non-dry-run live proof.",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "data" / "knowledge" / "governance" / "live_rag_vs_base_eval_summary.json"),
        help="Redacted governance summary path.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    fixture_path = ROOT / "tests" / "fixtures" / "kb_golden_questions_v2.json"
    questions = json.loads(fixture_path.read_text(encoding="utf-8"))
    answer_artifacts = load_live_eval_answer_artifacts(args.artifact_input) if args.artifact_input else None
    try:
        summary = run_live_rag_vs_base_eval(
            questions,
            dry_run=bool(args.dry_run),
            max_questions=args.max_questions,
            domain_pack=args.domain_pack,
            provider_filter=args.provider,
            answer_artifacts=answer_artifacts,
        )
    except LiveEvalConfigError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error_code": "live_eval_config_error",
                    "message": str(exc),
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 2
    save_live_eval_summary(summary, args.output)
    public_keys = (
        "eval_version",
        "dry_run",
        "proof_status",
        "commercial_proof_ready",
        "question_count",
        "row_count",
        "head_to_head",
        "release_gate_blockers",
    )
    print(json.dumps({k: summary[k] for k in public_keys if k in summary}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
