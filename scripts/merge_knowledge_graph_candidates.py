"""
将 knowledge_graph_candidates.jsonl 中 merge_approved=True 的候选合并进主图，
生成质量报告 knowledge_graph_build_report.json。

用法:
  python scripts/merge_knowledge_graph_candidates.py [--dry-run] [--target-nodes 100]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "backend" / "src"))

from marathon_qa_assistant.services.knowledge_graph import GraphEngine

CANDIDATES_PATH = ROOT / "data" / "knowledge" / "governance" / "knowledge_graph_candidates.jsonl"
QUARANTINE_PATH = ROOT / "data" / "knowledge" / "governance" / "kg_candidates_quarantine.jsonl"
REPORT_PATH = ROOT / "data" / "knowledge" / "governance" / "knowledge_graph_build_report.json"

DEFAULT_TARGET_NODES = 100


def _load_candidates() -> list[dict[str, Any]]:
    if not CANDIDATES_PATH.exists():
        return []
    records: list[dict[str, Any]] = []
    with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def _count_quarantine() -> int:
    if not QUARANTINE_PATH.exists():
        return 0
    count = 0
    with open(QUARANTINE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def merge(*, dry_run: bool = False, target_nodes: int = DEFAULT_TARGET_NODES) -> None:
    candidates = _load_candidates()
    if not candidates:
        print(f"候选文件不存在或为空: {CANDIDATES_PATH}")
        sys.exit(1)

    total = len(candidates)
    approved = sum(1 for c in candidates if c.get("merge_approved"))
    pending = sum(1 for c in candidates if c.get("merge_approved") and c.get("merge_status") != "merged")
    quarantine_count = _count_quarantine()

    print(f"候选总数: {total}")
    print(f"merge_approved=True: {approved}")
    print(f"待合并 (pending): {pending}")
    print(f"隔离文件记录: {quarantine_count}")
    print(f"目标节点数: {target_nodes}")
    print(f"模式: {'dry-run' if dry_run else '正式合并'}\n")

    if dry_run:
        print("[dry-run] 未执行合并，未写入任何文件。")
        return

    engine = GraphEngine()
    nodes_before = len(engine.nodes)
    edges_before = len(engine.edges)

    print(f"主图现有: {nodes_before} 节点, {edges_before} 条边")
    print("开始合并...")

    result = engine.merge_approved_candidates(CANDIDATES_PATH)

    nodes_after = len(engine.nodes)
    edges_after = len(engine.edges)

    print(f"合并完成:")
    print(f"  新增边: {result['merged']}")
    print(f"  跳过: {result['skipped']}")
    if result.get("errors"):
        print(f"  错误: {result['errors']}")
    print(f"  图谱现有节点: {nodes_after}")
    print(f"  图谱现有边: {edges_after}")

    domain_breakdown: dict[str, dict[str, int]] = defaultdict(lambda: {"candidates": 0, "merged": 0, "rejected": 0})
    candidates_fresh = _load_candidates()
    for c in candidates_fresh:
        domain = c.get("expert_domain", "unknown")
        domain_breakdown[domain]["candidates"] += 1
        if c.get("merge_status") == "merged":
            domain_breakdown[domain]["merged"] += 1
        elif c.get("review_status") == "rejected":
            domain_breakdown[domain]["rejected"] += 1

    quality_issues: list[str] = []
    if result.get("errors"):
        quality_issues.extend(result["errors"][:20])

    report: dict[str, Any] = {
        "build_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source_shards": ["training_protocol", "nutrition", "injury_safety", "medical_safety", "sport_psychology"],
        "candidates_total": total,
        "candidates_auto_approved": approved,
        "candidates_merged_this_run": result["merged"],
        "candidates_quarantined": quarantine_count,
        "nodes_before": nodes_before,
        "nodes_total": nodes_after,
        "edges_before": edges_before,
        "edges_total": edges_after,
        "domain_breakdown": dict(domain_breakdown),
        "quality_issues": quality_issues,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n质量报告: {REPORT_PATH}")

    if nodes_after < target_nodes:
        print(f"\n[FAIL] 节点数 {nodes_after} < 目标 {target_nodes}。"
              f"请运行更多抽取（python scripts/build_knowledge_graph_candidates.py）后重试。")
        sys.exit(1)
    else:
        print(f"\n[OK] 节点数 {nodes_after} >= 目标 {target_nodes}。")


def main() -> None:
    parser = argparse.ArgumentParser(description="合并已审核的 KG 候选进主图")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--target-nodes", type=int, default=DEFAULT_TARGET_NODES)
    args = parser.parse_args()
    merge(dry_run=args.dry_run, target_nodes=args.target_nodes)


if __name__ == "__main__":
    main()
