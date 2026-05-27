from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from marathon_qa_assistant.services.kb.expert_coverage import build_expert_coverage_report


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in current.parents:
        if (candidate / ".git").exists() and (candidate / "apps").exists():
            return candidate
    return Path.cwd().resolve()


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def build_report_from_paths(coverage_path: Path, chunks_path: Path) -> Dict[str, Any]:
    # report 输入固定来自治理矩阵和 runtime v2 chunks，保证结果可复现。
    coverage_rows = json.loads(coverage_path.read_text(encoding="utf-8"))
    chunks = _load_jsonl(chunks_path)
    return build_expert_coverage_report(coverage_rows, chunks)


def main() -> None:
    root = _find_project_root()
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage", default=str(root / "data/knowledge/governance/coverage_matrix.json"))
    parser.add_argument("--chunks", default=str(root / "data/vector_kb/v2/chunks.jsonl"))
    parser.add_argument("--output", default=str(root / "data/knowledge/governance/expert_coverage_report.json"))
    args = parser.parse_args()

    report = build_report_from_paths(Path(args.coverage), Path(args.chunks))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output_path), "status": report["status"], "global_blockers": report["global_blockers"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
