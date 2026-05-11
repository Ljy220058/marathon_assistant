import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List


PROJECT_ROOT = Path(__file__).absolute().parents[1]
DEFAULT_RUNS_ROOT = PROJECT_ROOT / "docs" / "paper_project" / "runs"
UNANSWERABLE_EVIDENCE_STATUSES = {"designed_unanswerable", "safety_stress_unanswerable"}


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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


def resolve_run_dir(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        candidate = DEFAULT_RUNS_ROOT / value
        path = candidate if candidate.exists() else PROJECT_ROOT / path
    if not path.exists():
        raise SystemExit(f"Run directory not found: {path}")
    return path


def status_of(row: Dict[str, Any]) -> str:
    return str(row.get("final_status") or row.get("status") or "answered")


def gate_status_of(row: Dict[str, Any]) -> str:
    gate = row.get("evidence_gate")
    if isinstance(gate, dict):
        return str(gate.get("gate_status") or "missing")
    return "not_applicable"


def audit_status_of(row: Dict[str, Any]) -> str:
    audit = row.get("audit")
    if isinstance(audit, dict):
        return str(audit.get("audit_status") or "missing")
    return "not_applicable"


def repair_action_of(row: Dict[str, Any]) -> str:
    repair = row.get("repair")
    if isinstance(repair, dict):
        return str(repair.get("repair_action") or "missing")
    return "not_applicable"


def pre_gate_rule_of(row: Dict[str, Any]) -> str:
    pre_gate = row.get("pre_gate")
    if isinstance(pre_gate, dict) and pre_gate.get("rule_id"):
        return str(pre_gate["rule_id"])
    return "not_triggered"


def count_by(rows: Iterable[Dict[str, Any]], key_fn) -> Dict[str, int]:
    return dict(Counter(key_fn(row) for row in rows))


def nested_category_status(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    table: Dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        category = str(row.get("category") or "unknown")
        table[category][status_of(row)] += 1
    return {category: dict(counter) for category, counter in sorted(table.items())}


def summarize(run_dir: Path) -> Dict[str, Any]:
    metadata = load_json(run_dir / "metadata.json")
    output_path = run_dir / "outputs.jsonl"
    if not output_path.exists() and metadata.get("output_path"):
        output_path = PROJECT_ROOT / str(metadata["output_path"])
    rows = load_jsonl(output_path)
    qids = [str(row.get("qid") or "") for row in rows]
    unique_qids = sorted({qid for qid in qids if qid})
    latencies = [float(row["latency_sec"]) for row in rows if isinstance(row.get("latency_sec"), (int, float))]

    unanswerable_controls = [
        row for row in rows if str(row.get("evidence_status") or "") in UNANSWERABLE_EVIDENCE_STATUSES
    ]
    verified_or_answerable = [
        row
        for row in rows
        if str(row.get("evidence_status") or "") not in UNANSWERABLE_EVIDENCE_STATUSES
    ]
    refused_rows = [row for row in rows if status_of(row) == "refused"]
    citation_repaired_rows = [
        row
        for row in rows
        if repair_action_of(row) == "repaired_invalid_or_missing_citations"
    ]
    evidence_counts = [len(row.get("evidence_contexts") or row.get("retrieved_contexts") or []) for row in rows]
    gold_counts = [len(row.get("gold_evidence_contexts") or []) for row in rows]
    retrieved_counts = [len(row.get("retrieved_contexts") or []) for row in rows]

    return {
        "run_id": metadata.get("run_id") or run_dir.name,
        "system_id": metadata.get("system_id"),
        "system_name": metadata.get("system_name"),
        "dataset": metadata.get("dataset"),
        "model": metadata.get("model"),
        "evidence_mode": metadata.get("evidence_mode"),
        "ablation_mode": metadata.get("ablation_mode", "full"),
        "pre_gate_mode": metadata.get("pre_gate_mode", "off"),
        "rows": len(rows),
        "unique_qids": len(unique_qids),
        "duplicate_qids": sorted(qid for qid, count in Counter(qids).items() if qid and count > 1),
        "missing_qid_rows": sum(1 for qid in qids if not qid),
        "status_counts": count_by(rows, status_of),
        "category_x_status": nested_category_status(rows),
        "gate_status_counts": count_by(rows, gate_status_of),
        "audit_status_counts": count_by(rows, audit_status_of),
        "repair_action_counts": count_by(rows, repair_action_of),
        "pre_gate_rule_counts": count_by(rows, pre_gate_rule_of),
        "designed_unanswerable_count": len(unanswerable_controls),
        "designed_unanswerable_refused": sum(1 for row in unanswerable_controls if status_of(row) == "refused"),
        "unanswerable_control_count": len(unanswerable_controls),
        "unanswerable_control_refused": sum(1 for row in unanswerable_controls if status_of(row) == "refused"),
        "verified_or_answerable_count": len(verified_or_answerable),
        "verified_or_answerable_refused": sum(1 for row in verified_or_answerable if status_of(row) == "refused"),
        "citation_repair_count": len(citation_repaired_rows),
        "refused_qids": [str(row.get("qid")) for row in refused_rows],
        "avg_latency_sec": round(mean(latencies), 3) if latencies else None,
        "avg_evidence_contexts": round(mean(evidence_counts), 3) if evidence_counts else None,
        "avg_gold_contexts": round(mean(gold_counts), 3) if gold_counts else None,
        "avg_retrieved_contexts": round(mean(retrieved_counts), 3) if retrieved_counts else None,
        "metadata_elapsed_sec": metadata.get("elapsed_sec"),
    }


def format_markdown(summary: Dict[str, Any]) -> str:
    lines = [
        f"# STAI Run Summary: {summary['run_id']}",
        "",
        "## Basic",
        "",
        f"- system: {summary.get('system_id')} / {summary.get('system_name')}",
        f"- dataset: {summary.get('dataset')}",
        f"- model: {summary.get('model')}",
        f"- evidence_mode: {summary.get('evidence_mode')}",
        f"- ablation_mode: {summary.get('ablation_mode')}",
        f"- pre_gate_mode: {summary.get('pre_gate_mode')}",
        f"- rows / unique_qids: {summary['rows']} / {summary['unique_qids']}",
        f"- elapsed_sec: {summary.get('metadata_elapsed_sec')}",
        "",
        "## Status Counts",
        "",
    ]
    for key, value in summary["status_counts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Gate / Audit / Repair", ""])
    for label, block in [
        ("gate", summary["gate_status_counts"]),
        ("audit", summary["audit_status_counts"]),
        ("repair", summary["repair_action_counts"]),
        ("pre_gate", summary["pre_gate_rule_counts"]),
    ]:
        lines.append(f"- {label}: {json.dumps(block, ensure_ascii=False)}")
    lines.extend(["", "## Category x Status", ""])
    for category, counts in summary["category_x_status"].items():
        lines.append(f"- {category}: {json.dumps(counts, ensure_ascii=False)}")
    lines.extend(
        [
            "",
            "## Refusal Diagnostics",
            "",
            f"- unanswerable_control_refused: {summary['unanswerable_control_refused']} / {summary['unanswerable_control_count']}",
            f"- designed_unanswerable_refused: {summary['designed_unanswerable_refused']} / {summary['designed_unanswerable_count']}",
            f"- verified_or_answerable_refused: {summary['verified_or_answerable_refused']} / {summary['verified_or_answerable_count']}",
            f"- citation_repair_count: {summary['citation_repair_count']}",
            f"- refused_qids: {', '.join(summary['refused_qids']) if summary['refused_qids'] else 'none'}",
            "",
            "## Context / Latency",
            "",
            f"- avg_latency_sec: {summary.get('avg_latency_sec')}",
            f"- avg_evidence_contexts: {summary.get('avg_evidence_contexts')}",
            f"- avg_gold_contexts: {summary.get('avg_gold_contexts')}",
            f"- avg_retrieved_contexts: {summary.get('avg_retrieved_contexts')}",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize a STAI run outputs.jsonl file.")
    parser.add_argument("--run", required=True, help="Run id or run directory path.")
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--md-out", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = resolve_run_dir(args.run)
    summary = summarize(run_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.json_out is not None:
        json_out = args.json_out if args.json_out.is_absolute() else PROJECT_ROOT / args.json_out
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.md_out is not None:
        md_out = args.md_out if args.md_out.is_absolute() else PROJECT_ROOT / args.md_out
        md_out.parent.mkdir(parents=True, exist_ok=True)
        md_out.write_text(format_markdown(summary), encoding="utf-8")


if __name__ == "__main__":
    main()
