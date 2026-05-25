from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = ROOT / "apps" / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from marathon_qa_assistant.services.kb.live_eval_artifacts import (  # noqa: E402
    LiveEvalArtifactConfigError,
    collect_live_eval_answer_artifacts,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture paired RAG/base answer artifacts for GPT live evaluation.")
    parser.add_argument("--api-url", default="http://127.0.0.1:8010/query", help="Backend /query URL or API base URL.")
    parser.add_argument("--provider", default="gpt", choices=["gpt", "ds"], help="LLM provider used for artifact capture.")
    parser.add_argument("--max-questions", type=int, default=200, help="Limit captured golden questions.")
    parser.add_argument("--user-id", default="default_user", help="Backend /query user_id used for RAG artifact capture.")
    parser.add_argument("--resume", action="store_true", help="Skip existing question/mode artifact rows.")
    parser.add_argument(
        "--output",
        default=str(ROOT / "data" / "knowledge" / "governance" / "live_rag_vs_base_answer_artifacts.jsonl"),
        help="Output JSONL artifact path.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    fixture_path = ROOT / "tests" / "fixtures" / "kb_golden_questions_v2.json"
    questions = json.loads(fixture_path.read_text(encoding="utf-8"))
    try:
        summary = collect_live_eval_answer_artifacts(
            questions,
            provider=args.provider,
            output_path=args.output,
            api_url=args.api_url,
            query_user_id=args.user_id,
            max_questions=args.max_questions,
            resume=bool(args.resume),
        )
    except LiveEvalArtifactConfigError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error_code": "live_eval_artifact_config_error",
                    "message": str(exc),
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps({"ok": True, **summary}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
