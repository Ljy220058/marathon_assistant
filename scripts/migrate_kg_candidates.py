"""
将旧候选三元组（kg_candidate_triples.jsonl）迁移到新 schema（knowledge_graph_candidates.jsonl）。

迁移策略：
1. 加载所有 v2_sharded chunks，建立 (source_file, page) → chunks 的索引
2. 旧候选通过 (source_file, page) 找到对应的 v2_sharded chunk，绑定 source_chunk_id
3. 运行 auto-approve 门控（与 build_knowledge_graph_candidates.py 一致）
4. rebind 失败的写入隔离文件

用法:
  python scripts/migrate_kg_candidates.py [--dry-run]
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

from marathon_qa_assistant.services.kb.kg_extraction import (
    ALLOWED_RELATIONS,
    _entity_in_text,
)

V2_SHARDED_DIR = ROOT / "data" / "vector_kb" / "v2_sharded"
OLD_QUEUE_PATH = ROOT / "data" / "knowledge" / "governance" / "kg_candidate_triples.jsonl"
NEW_CANDIDATES_PATH = ROOT / "data" / "knowledge" / "governance" / "knowledge_graph_candidates.jsonl"
QUARANTINE_PATH = ROOT / "data" / "knowledge" / "governance" / "kg_candidates_quarantine.jsonl"

# 旧 expert_domain → v2_sharded domain_pack 名称映射
OLD_DOMAIN_TO_SHARD = {
    "nutrition": "nutrition",
    "rehab_safety": "injury_safety",
    "training_theory": "training_protocol",
    "race_strategy": "training_protocol",
    "workout_prescription": "training_protocol",
    "capacity_management": "training_protocol",
    "injury_safety": "injury_safety",
    "medical_safety": "medical_safety",
    "sport_psychology": "sport_psychology",
}


def _load_v2_sharded_index() -> tuple[dict[str, Any], dict[tuple[str, int], list[dict[str, Any]]]]:
    """加载所有 v2_sharded chunks，返回两个索引。"""
    by_id: dict[str, Any] = {}
    by_file_page: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)

    for chunks_file in sorted(V2_SHARDED_DIR.glob("*/chunks.jsonl")):
        with open(chunks_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                chunk = json.loads(line)
                chunk_id = chunk.get("chunk_id", "")
                if chunk_id:
                    by_id[chunk_id] = chunk
                src_file = chunk.get("source_file", "")
                page = chunk.get("page")
                if src_file and page is not None:
                    by_file_page[(src_file, int(page))].append(chunk)

    return by_id, by_file_page


def _auto_approve(cand: dict[str, Any], by_id: dict[str, Any]) -> tuple[bool, list[str]]:
    """运行严格 auto-approve 门控，返回 (approved, reasons)。"""
    reasons: list[str] = []

    chunk_id = cand.get("source_chunk_id", "")
    chunk = by_id.get(chunk_id)

    if not chunk:
        reasons.append("chunk_not_in_v2_sharded")
    else:
        text = (chunk.get("text") or "") + " " + (chunk.get("parent_text") or "")
        if not _entity_in_text(cand.get("head_entity", ""), text):
            reasons.append("head_not_traceable")
        if not _entity_in_text(cand.get("tail_entity", ""), text):
            reasons.append("tail_not_traceable")
        pp = chunk.get("prescription_permission", "explanation_only")
        if pp in ("write_core", "prescription_direct"):
            reasons.append(f"prescription_permission_elevated:{pp}")

    relation = cand.get("relation", "")
    if relation not in ALLOWED_RELATIONS:
        reasons.append(f"relation_not_in_whitelist:{relation}")

    if float(cand.get("confidence_score", 0.0)) < 0.8:
        reasons.append(f"low_confidence:{cand.get('confidence_score')}")

    return len(reasons) == 0, reasons


def _load_existing_candidate_ids() -> set[str]:
    """加载已存在的 candidate_id 集合，用于去重。"""
    if not NEW_CANDIDATES_PATH.exists():
        return set()
    ids: set[str] = set()
    with open(NEW_CANDIDATES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rec = json.loads(line)
                    cid = rec.get("candidate_id", "")
                    if cid:
                        ids.add(cid)
                except json.JSONDecodeError:
                    pass
    return ids


def migrate(*, dry_run: bool = False) -> None:
    print("加载 v2_sharded chunks 索引...")
    by_id, by_file_page = _load_v2_sharded_index()
    print(f"  已加载 {len(by_id):,} 条 chunks")

    if not OLD_QUEUE_PATH.exists():
        print(f"旧候选文件不存在: {OLD_QUEUE_PATH}")
        return

    existing_ids = _load_existing_candidate_ids()
    print(f"已有新候选记录: {len(existing_ids)} 条（用于去重）")

    old_records: list[dict[str, Any]] = []
    with open(OLD_QUEUE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    old_records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    print(f"待迁移旧候选: {len(old_records)} 条\n")

    stats = {"total": 0, "rebind_ok": 0, "rebind_fail": 0, "skipped_dup": 0,
             "auto_approved": 0, "rejected": 0, "written": 0, "quarantined": 0}

    new_records: list[dict[str, Any]] = []
    quarantine_records: list[dict[str, Any]] = []

    for rec in old_records:
        stats["total"] += 1
        old_cand_id = rec.get("candidate_id", "")

        if old_cand_id in existing_ids:
            stats["skipped_dup"] += 1
            continue

        # 旧 chunk_id 直接在 v2_sharded 找（很可能格式不同，不会命中）
        old_chunk_id = rec.get("chunk_id", "")
        rebind_chunk: dict[str, Any] | None = by_id.get(old_chunk_id)

        if not rebind_chunk:
            # 尝试 (source_file, page) rebind
            src_file = rec.get("source_file", "")
            page = rec.get("page")
            if src_file and page is not None:
                candidates_for_page = by_file_page.get((src_file, int(page)), [])
                if candidates_for_page:
                    rebind_chunk = candidates_for_page[0]

        if not rebind_chunk:
            stats["rebind_fail"] += 1
            quarantine_rec = {**rec, "quarantine_reason": "no_v2_sharded_match", "merge_status": "quarantine"}
            quarantine_records.append(quarantine_rec)
            continue

        stats["rebind_ok"] += 1

        # 旧 status 映射
        old_status = rec.get("status", "candidate")
        if old_status == "validated":
            new_review_status = "auto_approved"
        elif old_status == "rejected":
            new_review_status = "rejected"
        elif old_status == "merged":
            new_review_status = "auto_approved"
        else:
            new_review_status = "candidate"

        domain_pack = rebind_chunk.get("domain_pack", "")
        expert_domain = OLD_DOMAIN_TO_SHARD.get(rec.get("expert_domain", ""), domain_pack)

        new_cand: dict[str, Any] = {
            "candidate_id": old_cand_id,
            "source_chunk_id": rebind_chunk["chunk_id"],
            "source_registry_id": rebind_chunk.get("source_registry_id", rec.get("source_registry_id", "")),
            "source_file": rebind_chunk.get("source_file", rec.get("source_file", "")),
            "page": rebind_chunk.get("page", rec.get("page")),
            "expert_domain": expert_domain,
            "evidence_domain": rec.get("evidence_domain", f"{expert_domain}_reference"),
            "head_entity": rec.get("head_entity", ""),
            "relation": rec.get("relation", ""),
            "tail_entity": rec.get("tail_entity", ""),
            "confidence_score": float(rec.get("confidence", rec.get("confidence_score", 0.0))),
            "extraction_method": "llm_offline",
            "extraction_model": "qwen2.5:latest",
            "evidence_span": str(rec.get("evidence_span", ""))[:300],
            "review_status": new_review_status,
            "review_reasons": [],
            "merge_approved": False,
            "merge_status": "pending",
            "migrated_from": "kg_candidate_triples.jsonl",
            "migrated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

        # 跳过明确被拒的（不需要重新审核）
        if new_review_status == "rejected":
            new_cand["merge_approved"] = False
            new_cand["merge_status"] = "rejected"
            new_records.append(new_cand)
            stats["rejected"] += 1
            continue

        # 运行 auto-approve 门控
        approved, reasons = _auto_approve(new_cand, by_id)
        new_cand["merge_approved"] = approved
        new_cand["review_reasons"] = reasons
        if approved:
            new_cand["review_status"] = "auto_approved"
            stats["auto_approved"] += 1
        else:
            new_cand["review_status"] = "rejected"
            new_cand["merge_status"] = "rejected"
            stats["rejected"] += 1

        new_records.append(new_cand)

    stats["written"] = len(new_records)
    stats["quarantined"] = len(quarantine_records)

    print(f"迁移统计:")
    print(f"  总计: {stats['total']}")
    print(f"  rebind 成功: {stats['rebind_ok']}")
    print(f"  rebind 失败 → 隔离: {stats['rebind_fail']}")
    print(f"  跳过(重复): {stats['skipped_dup']}")
    print(f"  auto_approved: {stats['auto_approved']}")
    print(f"  rejected: {stats['rejected']}")
    print(f"  写入新候选文件: {stats['written']}")
    print(f"  写入隔离文件: {stats['quarantined']}")

    if dry_run:
        print("\n[dry-run] 未写入任何文件。")
        return

    NEW_CANDIDATES_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(NEW_CANDIDATES_PATH, "a", encoding="utf-8") as f:
        for rec in new_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"\n写入: {NEW_CANDIDATES_PATH}")

    if quarantine_records:
        with open(QUARANTINE_PATH, "a", encoding="utf-8") as f:
            for rec in quarantine_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"隔离: {QUARANTINE_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description="迁移旧 KG 候选到新 schema")
    parser.add_argument("--dry-run", action="store_true", help="预览统计，不写入文件")
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
