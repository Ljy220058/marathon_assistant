import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


PROJECT_ROOT = Path(__file__).absolute().parents[1]
DEFAULT_PATHS = [
    "docs/paper_project/stai2026_pilot_benchmark_v0.1.jsonl",
    "docs/paper_project/stai_benchmark_v0.2_50_question_draft.jsonl",
    "docs/paper_project/runs/stai_s0_norag_qwen2_5_20260510_run01/outputs.jsonl",
    "docs/paper_project/runs/stai_s1_vanilla_rag_qwen2_5_after_reboot_full01/outputs.jsonl",
    "docs/paper_project/runs/stai_s3_gold_only_50q_v02_run01/outputs.jsonl",
    "docs/paper_project/runs/stai_s3_retrieval_only_50q_v02_run01/outputs.jsonl",
    "docs/paper_project/runs/stai_s3_retrieval_plus_gold_50q_v02_run01/outputs.jsonl",
]

SUSPICIOUS_MARKERS = [
    "\ufffd",
    "锛",
    "浼",
    "妫€",
    "绱",
    "璇",
    "鎹",
    "俓n",
]


def iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from iter_strings(item)


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
    return rows


def analyze_path(path: Path, max_rows: int) -> Dict[str, Any]:
    rows = load_jsonl(path)
    scanned = rows[:max_rows] if max_rows > 0 else rows
    suspicious_examples = []
    marker_counts = {marker: 0 for marker in SUSPICIOUS_MARKERS}
    total_strings = 0
    total_chars = 0
    for row in scanned:
        for text in iter_strings(row):
            total_strings += 1
            total_chars += len(text)
            hit_markers = [marker for marker in SUSPICIOUS_MARKERS if marker in text]
            for marker in hit_markers:
                marker_counts[marker] += text.count(marker)
            if hit_markers and len(suspicious_examples) < 8:
                suspicious_examples.append(
                    {
                        "markers": hit_markers,
                        "text_preview": text[:180],
                    }
                )
    suspicious_count = sum(marker_counts.values())
    return {
        "path": str(path.relative_to(PROJECT_ROOT)),
        "rows": len(rows),
        "scanned_rows": len(scanned),
        "total_strings": total_strings,
        "total_chars": total_chars,
        "suspicious_marker_count": suspicious_count,
        "marker_counts": {k: v for k, v in marker_counts.items() if v},
        "suspicious_examples": suspicious_examples,
        "first_question": rows[0].get("question", "") if rows else "",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check STAI JSONL files for visible mojibake markers.")
    parser.add_argument("--paths", nargs="*", default=DEFAULT_PATHS)
    parser.add_argument("--max-rows", type=int, default=0, help="0 means scan all rows.")
    parser.add_argument("--json-out", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = []
    for value in args.paths:
        path = Path(value)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        if not path.exists():
            results.append({"path": str(path), "missing": True})
            continue
        results.append(analyze_path(path, args.max_rows))
    payload = {"ok": True, "results": results}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.json_out is not None:
        json_out = args.json_out if args.json_out.is_absolute() else PROJECT_ROOT / args.json_out
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
