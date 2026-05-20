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
DEFAULT_DATASET = PROJECT_ROOT / "research" / "stai2026" / "benchmark" / "stai_supplementary_generalization_boundary_v0.1_60_question_draft.jsonl"

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

EXPECTED_CATEGORY_COUNTS = {
    "cross_domain_advisory": 30,
    "evidence_boundary": 20,
    "additional_safety_stress": 10,
}

ALLOWED_EVIDENCE_STATUS = {
    "needs_evidence_mapping",
    "designed_unanswerable",
    "safety_stress_unanswerable",
}

ALLOWED_TARGET_STATES = {"answered", "partial_answer", "refused"}


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
    parser.add_argument("--expected-count", type=int, default=60)
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
        if not qid.startswith("STAI-X"):
            errors.append(f"Row {index} has invalid supplementary qid: {qid}")

        category = row.get("category")
        if category not in EXPECTED_CATEGORY_COUNTS:
            errors.append(f"{qid} has unexpected category: {category}")

        evidence_status = row.get("evidence_status")
        if evidence_status not in ALLOWED_EVIDENCE_STATUS:
            errors.append(f"{qid} has unexpected evidence_status: {evidence_status}")

        target_state = row.get("target_state")
        if target_state not in ALLOWED_TARGET_STATES:
            errors.append(f"{qid} has unexpected target_state: {target_state}")

        if category == "additional_safety_stress":
            if row.get("answerable") is not False:
                errors.append(f"{qid} additional_safety_stress must be unanswerable")
            if evidence_status != "safety_stress_unanswerable":
                errors.append(f"{qid} additional_safety_stress must use safety_stress_unanswerable")
            if target_state != "refused":
                errors.append(f"{qid} additional_safety_stress must target refused")

        if evidence_status == "needs_evidence_mapping" and not row.get("evidence_id"):
            errors.append(f"{qid} needs evidence mapping but evidence_id is empty")

        if evidence_status in {"designed_unanswerable", "safety_stress_unanswerable"}:
            if row.get("answerable") is not False:
                errors.append(f"{qid} unanswerable evidence status must have answerable=false")
            if target_state != "refused":
                errors.append(f"{qid} unanswerable evidence status must target refused")

        if category == "evidence_boundary" and target_state not in {"partial_answer", "refused"}:
            errors.append(f"{qid} evidence_boundary should target partial_answer or refused")

    category_counts = Counter(row.get("category") for row in rows)
    evidence_counts = Counter(row.get("evidence_status") for row in rows)
    target_counts = Counter(row.get("target_state") for row in rows)

    if dict(category_counts) != EXPECTED_CATEGORY_COUNTS:
        errors.append(f"Category counts mismatch: {dict(category_counts)} != {EXPECTED_CATEGORY_COUNTS}")

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    print(
        json.dumps(
            {
                "ok": True,
                "rows": len(rows),
                "category_counts": dict(category_counts),
                "evidence_status_counts": dict(evidence_counts),
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
