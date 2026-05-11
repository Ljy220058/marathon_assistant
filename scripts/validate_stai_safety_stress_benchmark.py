import argparse
import json
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).absolute().parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "docs" / "paper_project" / "stai_safety_stress_benchmark_v0.1_15_question.jsonl"

REQUIRED_FIELDS = {
    "qid",
    "category",
    "question",
    "evidence_id",
    "source_id",
    "evidence_status",
    "answerable",
    "safety_required",
    "expected_answer_basis",
    "must_not_claim",
    "rubric",
    "expansion_role",
    "notes",
}

EXPECTED_CATEGORIES = {
    "prompt_injection",
    "unsafe_request",
    "citation_hallucination",
    "overclaim_request",
    "evidence_conflict",
}


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--expected-count", type=int, default=15)
    args = parser.parse_args()

    dataset_path = args.dataset if args.dataset.is_absolute() else PROJECT_ROOT / args.dataset
    rows = load_jsonl(dataset_path)
    errors = []

    if len(rows) != args.expected_count:
        errors.append(f"Expected {args.expected_count} rows, got {len(rows)}")

    qids = [row.get("qid") for row in rows]
    duplicates = sorted(qid for qid, count in Counter(qids).items() if count > 1)
    if duplicates:
        errors.append(f"Duplicate qids: {duplicates}")

    for index, row in enumerate(rows, start=1):
        missing = sorted(REQUIRED_FIELDS - set(row))
        if missing:
            errors.append(f"Row {index} missing fields: {missing}")
        qid = str(row.get("qid") or "")
        if not qid.startswith("STAI-S"):
            errors.append(f"Row {index} has invalid stress qid: {qid}")
        if row.get("category") not in EXPECTED_CATEGORIES:
            errors.append(f"{qid} has unexpected category: {row.get('category')}")
        if row.get("evidence_status") != "safety_stress_unanswerable":
            errors.append(f"{qid} evidence_status must be safety_stress_unanswerable")
        if row.get("answerable") is not False:
            errors.append(f"{qid} answerable must be false")
        if not row.get("must_not_claim"):
            errors.append(f"{qid} must_not_claim is empty")

    category_counts = Counter(row.get("category") for row in rows)
    safety_counts = Counter(bool(row.get("safety_required")) for row in rows)

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    print(
        json.dumps(
            {
                "ok": True,
                "rows": len(rows),
                "category_counts": dict(category_counts),
                "safety_required_counts": {str(key): value for key, value in safety_counts.items()},
                "first_qid": qids[0] if qids else None,
                "last_qid": qids[-1] if qids else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
