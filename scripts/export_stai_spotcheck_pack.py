import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).absolute().parents[1]
DEFAULT_RUN = PROJECT_ROOT / "docs" / "paper_project" / "runs" / "stai_s3_retrieval_plus_gold_50q_v02_run01" / "outputs.jsonl"
DEFAULT_OUT_DIR = PROJECT_ROOT / "docs" / "paper_project" / "spotcheck"
DEFAULT_QIDS = [
    "STAI-P005",
    "STAI-P015",
    "STAI-P026",
    "STAI-P041",
    "STAI-P045",
    "STAI-P001",
    "STAI-P003",
    "STAI-P006",
    "STAI-P014",
    "STAI-P044",
    "STAI-P036",
    "STAI-P040",
    "STAI-P046",
    "STAI-P048",
    "STAI-P049",
]


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


def shorten(text: Any, max_chars: int = 900) -> str:
    value = str(text or "").strip()
    if len(value) <= max_chars:
        return value
    return value[:max_chars].rstrip() + " [...]"


def context_brief(context: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "rank": context.get("rank"),
        "chunk_id": context.get("chunk_id"),
        "source_file": context.get("source_file"),
        "page": context.get("page"),
        "section": context.get("section"),
        "evidence_source": context.get("evidence_source"),
        "text": shorten(context.get("text"), 700),
    }


def build_review_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "qid": row.get("qid"),
        "category": row.get("category"),
        "question": row.get("question"),
        "final_status": row.get("final_status"),
        "gate_status": (row.get("evidence_gate") or {}).get("gate_status"),
        "audit_status": (row.get("audit") or {}).get("audit_status"),
        "repair_action": (row.get("repair") or {}).get("repair_action"),
        "safety_required": row.get("safety_required"),
        "evidence_status": row.get("evidence_status"),
        "gold_contexts": [context_brief(item) for item in row.get("gold_evidence_contexts") or []],
        "retrieved_contexts": [context_brief(item) for item in row.get("retrieved_contexts") or []],
        "final_answer": row.get("final_answer"),
        "review": {
            "evidence_support": "",
            "citation_validity": "",
            "safety_status": "",
            "refusal_quality": "",
            "answer_completeness": "",
            "reviewer_note": "",
        },
    }


def format_markdown(rows: List[Dict[str, Any]]) -> str:
    lines = [
        "# STAI Spot-check Review Pack",
        "",
        "Source run: `stai_s3_retrieval_plus_gold_50q_v02_run01`",
        "",
        "Review labels: `supported / partially_supported / unsupported / not_applicable`; `valid / repaired_valid / invalid / not_applicable`; `safe / cautious_safe / unsafe / not_applicable`.",
        "",
    ]
    for item in rows:
        lines.extend(
            [
                f"## {item['qid']} ({item['category']}, {item['final_status']})",
                "",
                f"- gate: `{item['gate_status']}`",
                f"- audit: `{item['audit_status']}`",
                f"- repair: `{item['repair_action']}`",
                f"- safety_required: `{item['safety_required']}`",
                f"- evidence_status: `{item['evidence_status']}`",
                "",
                "**Question**",
                "",
                item.get("question") or "",
                "",
                "**Gold Evidence**",
                "",
            ]
        )
        if item["gold_contexts"]:
            for context in item["gold_contexts"]:
                lines.append(
                    f"- `{context.get('chunk_id')}` | {context.get('source_file')} | page={context.get('page')} | section={context.get('section')}\n\n  {context.get('text')}"
                )
        else:
            lines.append("- none")
        lines.extend(["", "**Retrieved Evidence Preview**", ""])
        for context in item["retrieved_contexts"][:2]:
            lines.append(
                f"- `{context.get('chunk_id')}` | {context.get('source_file')} | page={context.get('page')}\n\n  {context.get('text')}"
            )
        lines.extend(
            [
                "",
                "**Final Answer**",
                "",
                item.get("final_answer") or "",
                "",
                "**Human Review**",
                "",
                "- evidence_support:",
                "- citation_validity:",
                "- safety_status:",
                "- refusal_quality:",
                "- answer_completeness:",
                "- reviewer_note:",
                "",
            ]
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a clean STAI spot-check pack from a run output file.")
    parser.add_argument("--run-output", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--qids", default=",".join(DEFAULT_QIDS))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_output = args.run_output if args.run_output.is_absolute() else PROJECT_ROOT / args.run_output
    out_dir = args.out_dir if args.out_dir.is_absolute() else PROJECT_ROOT / args.out_dir
    qids = [item.strip() for item in args.qids.split(",") if item.strip()]
    rows = load_jsonl(run_output)
    by_qid = {str(row.get("qid")): row for row in rows}
    missing = [qid for qid in qids if qid not in by_qid]
    if missing:
        raise SystemExit(f"Missing qids in run output: {missing}")
    review_rows = [build_review_row(by_qid[qid]) for qid in qids]
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "stai_s3_retrieval_plus_gold_50q_v02_spotcheck.jsonl"
    md_path = out_dir / "stai_s3_retrieval_plus_gold_50q_v02_spotcheck.md"
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in review_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    md_path.write_text(format_markdown(review_rows), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "rows": len(review_rows),
                "jsonl_path": str(jsonl_path.relative_to(PROJECT_ROOT)),
                "md_path": str(md_path.relative_to(PROJECT_ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
