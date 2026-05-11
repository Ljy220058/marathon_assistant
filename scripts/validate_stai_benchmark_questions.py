import argparse
import json
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).absolute().parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "docs" / "paper_project" / "stai_benchmark_v0.2_50_question_draft.jsonl"

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

EXPECTED_CATEGORY_COUNTS_BY_SIZE = {
    50: {
        "fact": 15,
        "applied_reasoning": 15,
        "risk_safety": 15,
        "evidence_insufficient": 5,
    },
    100: {
        "fact": 30,
        "applied_reasoning": 30,
        "risk_safety": 30,
        "evidence_insufficient": 10,
    },
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
    parser.add_argument("--expected-count", type=int, default=50)
    args = parser.parse_args()

    rows = load_jsonl(args.dataset)
    errors = []

    if len(rows) != args.expected_count:
        errors.append(f"Expected {args.expected_count} rows, got {len(rows)}")

    qids = [row.get("qid") for row in rows]
    duplicates = sorted(qid for qid, count in Counter(qids).items() if count > 1)
    if duplicates:
        errors.append(f"Duplicate qids: {duplicates}")

    missing_by_row = {}
    for index, row in enumerate(rows, start=1):
        missing = sorted(REQUIRED_FIELDS - set(row))
        if missing:
            missing_by_row[index] = missing
        if not row.get("qid", "").startswith("STAI-P"):
            errors.append(f"Row {index} has invalid qid: {row.get('qid')}")
        if row.get("category") == "risk_safety" and row.get("safety_required") is not True:
            errors.append(f"{row.get('qid')} is risk_safety but safety_required is not true")
        if row.get("category") == "evidence_insufficient" and row.get("answerable") is not False:
            errors.append(f"{row.get('qid')} is evidence_insufficient but answerable is not false")
        if row.get("evidence_status") == "pending" and not row.get("evidence_id"):
            errors.append(f"{row.get('qid')} is pending but evidence_id is empty")

    if missing_by_row:
        errors.append(f"Rows with missing fields: {missing_by_row}")

    category_counts = Counter(row.get("category") for row in rows)
    expected_category_counts = EXPECTED_CATEGORY_COUNTS_BY_SIZE.get(args.expected_count)
    if expected_category_counts and dict(category_counts) != expected_category_counts:
        errors.append(f"Category counts mismatch: {dict(category_counts)} != {expected_category_counts}")

    status_counts = Counter(row.get("evidence_status") for row in rows)

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    print(
        json.dumps(
            {
                "ok": True,
                "rows": len(rows),
                "category_counts": dict(category_counts),
                "evidence_status_counts": dict(status_counts),
                "first_qid": qids[0] if qids else None,
                "last_qid": qids[-1] if qids else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
