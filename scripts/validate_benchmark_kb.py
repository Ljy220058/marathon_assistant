import argparse
import json
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).absolute().parents[1]
DEFAULT_KB_DIR = PROJECT_ROOT / "docs" / "paper_project" / "benchmark_kb"
DEFAULT_EVIDENCE_ITEMS = DEFAULT_KB_DIR / "evidence_items_v0.1.jsonl"
DEFAULT_QID_MAP = DEFAULT_KB_DIR / "qid_to_gold_evidence_v0.1.json"

REQUIRED_FIELDS = {
    "evidence_id",
    "domain",
    "topic",
    "source_type",
    "source_title",
    "source_url_or_path",
    "page",
    "section",
    "quote",
    "paraphrase",
    "supports_qids",
    "risk_category",
    "verification_status",
    "notes",
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
    parser.add_argument("--evidence-items", type=Path, default=DEFAULT_EVIDENCE_ITEMS)
    parser.add_argument("--qid-map", type=Path, default=DEFAULT_QID_MAP)
    args = parser.parse_args()

    evidence_items = load_jsonl(args.evidence_items)
    qid_map = json.loads(args.qid_map.read_text(encoding="utf-8"))
    errors = []

    evidence_ids = [item.get("evidence_id") for item in evidence_items]
    duplicate_ids = sorted(eid for eid, count in Counter(evidence_ids).items() if count > 1)
    if duplicate_ids:
        errors.append(f"Duplicate evidence_id values: {duplicate_ids}")

    evidence_by_id = {item.get("evidence_id"): item for item in evidence_items}

    for index, item in enumerate(evidence_items, start=1):
        missing = sorted(REQUIRED_FIELDS - set(item))
        if missing:
            errors.append(f"Row {index} missing fields: {missing}")

        status = item.get("verification_status")
        if status not in {"verified", "pending", "rejected"}:
            errors.append(f"{item.get('evidence_id')} has invalid verification_status: {status}")

        if status == "verified":
            for field in ["source_title", "source_url_or_path", "section", "quote", "paraphrase"]:
                if not item.get(field):
                    errors.append(f"{item.get('evidence_id')} is verified but {field} is empty")

        if not isinstance(item.get("supports_qids"), list):
            errors.append(f"{item.get('evidence_id')} supports_qids is not a list")

    for qid, mapped_ids in qid_map.items():
        if not isinstance(mapped_ids, list) or not mapped_ids:
            errors.append(f"{qid} mapping must be a non-empty list")
            continue
        for evidence_id in mapped_ids:
            if evidence_id not in evidence_by_id:
                errors.append(f"{qid} maps to unknown evidence_id: {evidence_id}")
                continue
            if qid not in evidence_by_id[evidence_id].get("supports_qids", []):
                errors.append(f"{qid} maps to {evidence_id}, but item.supports_qids does not include the qid")

    status_counts = Counter(item.get("verification_status") for item in evidence_items)
    mapped_qid_count = len(qid_map)

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    print(
        json.dumps(
            {
                "ok": True,
                "evidence_items": len(evidence_items),
                "mapped_qids": mapped_qid_count,
                "verification_status_counts": dict(status_counts),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
