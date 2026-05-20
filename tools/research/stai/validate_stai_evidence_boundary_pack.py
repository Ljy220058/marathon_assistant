import argparse
import json
from collections import Counter
from pathlib import Path


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in current.parents:
        if (candidate / ".git").exists() and (candidate / "apps").exists():
            return candidate
    return Path.cwd().resolve()


PROJECT_ROOT = _find_project_root()
DEFAULT_DATASET = PROJECT_ROOT / "research" / "stai2026" / "benchmark" / "stai_evidence_boundary_20q_v0.1.jsonl"

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
    "target_state",
}

EXPECTED_QIDS = [f"STAI-X{i:03d}" for i in range(31, 51)]
ALLOWED_EVIDENCE_STATUS = {"verified_span", "designed_unanswerable"}
ALLOWED_TARGET_STATES = {"partial_answer", "refused"}


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
    parser.add_argument("--expected-count", type=int, default=20)
    args = parser.parse_args()

    dataset_path = args.dataset if args.dataset.is_absolute() else PROJECT_ROOT / args.dataset
    rows = load_jsonl(dataset_path)
    errors = []

    if len(rows) != args.expected_count:
        errors.append(f"Expected {args.expected_count} rows, got {len(rows)}")

    qids = [row.get("qid") for row in rows]
    if qids != EXPECTED_QIDS:
        errors.append(f"QID sequence mismatch: {qids} != {EXPECTED_QIDS}")

    duplicates = sorted(qid for qid, count in Counter(qids).items() if count > 1)
    if duplicates:
        errors.append(f"Duplicate qids: {duplicates}")

    for index, row in enumerate(rows, start=1):
        qid = str(row.get("qid") or "")
        missing = sorted(REQUIRED_FIELDS - set(row))
        if missing:
            errors.append(f"Row {index} missing fields: {missing}")
        if row.get("category") != "evidence_boundary":
            errors.append(f"{qid} category must be evidence_boundary")
        if row.get("evidence_status") not in ALLOWED_EVIDENCE_STATUS:
            errors.append(f"{qid} invalid evidence_status: {row.get('evidence_status')}")
        if row.get("target_state") not in ALLOWED_TARGET_STATES:
            errors.append(f"{qid} invalid target_state: {row.get('target_state')}")

        if row.get("evidence_status") == "verified_span":
            if row.get("answerable") is not True:
                errors.append(f"{qid} verified_span must have answerable=true")
            if not row.get("evidence_id"):
                errors.append(f"{qid} verified_span must have evidence_id")
            if row.get("target_state") != "partial_answer":
                errors.append(f"{qid} verified_span boundary item must target partial_answer")

        if row.get("evidence_status") == "designed_unanswerable":
            if row.get("answerable") is not False:
                errors.append(f"{qid} designed_unanswerable must have answerable=false")
            if row.get("target_state") != "refused":
                errors.append(f"{qid} designed_unanswerable must target refused")

    status_counts = Counter(row.get("evidence_status") for row in rows)
    target_counts = Counter(row.get("target_state") for row in rows)

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    print(
        json.dumps(
            {
                "ok": True,
                "rows": len(rows),
                "evidence_status_counts": dict(status_counts),
                "target_state_counts": dict(target_counts),
                "first_qid": qids[0] if qids else None,
                "last_qid": qids[-1] if qids else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
