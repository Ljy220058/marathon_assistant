from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = ROOT / "apps" / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from marathon_qa_assistant.services.kb.source_gap_report import build_source_gap_report  # noqa: E402


GOVERNANCE_DIR = ROOT / "data" / "knowledge" / "governance"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    report = build_source_gap_report(
        source_review_queue=_load_jsonl(GOVERNANCE_DIR / "source_review_queue.jsonl"),
        release_report=_load_json(GOVERNANCE_DIR / "kb_release_report.json"),
    )
    output_path = GOVERNANCE_DIR / "source_gap_report.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
