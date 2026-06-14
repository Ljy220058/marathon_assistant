"""
KG 终极形态进化脚本 — 一次性完成所有结构迁移和质量标记。

做的事：
1. 节点 expert_domain 回填（按 type 推断）
2. 旧关系 → 8-relation 白名单迁移
3. 边 expert_domain 回填
4. quality_tier 标记（seed→reviewed, literature→reviewed/candidate）
5. 备份原文件

用法: python scripts/evolve_kg_to_ultimate.py [--dry-run]
"""
from __future__ import annotations

import json
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
KG_PATH = ROOT / "data" / "vector_kb" / "v2" / "knowledge_graph.json"

# ─── 映射表 ───────────────────────────────────────────────

# 节点 type → expert_domain 主映射
NODE_TYPE_TO_DOMAIN: Dict[str, str] = {
    "constraint": "capacity_management",
    "template": "workout_prescription",
    "workout": "workout_prescription",
    "zone": "workout_prescription",
    "physiology": "training_theory",
    "adaptation": "training_theory",
    "nutrition": "nutrition",
    "injury": "rehab_safety",
    "strategy": "race_strategy",
    "concept": "training_theory",  # 兜底；文献概念节点会根据边覆盖
}

# 旧关系 → 白名单关系
RELATION_MIGRATION: Dict[str, str] = {
    "parameterized_by": "requires",
    "uses_zone": "requires",
    "targets": "improves",
    "produces": "supports",
    "constrained_by": "constrains",
}

# 8-relation 白名单
WHITELIST = {"supports", "constrains", "requires", "adjusts", "risks", "improves", "reduces", "bridges_to"}


def _domain_for_node(node: Dict[str, Any], node_id: str, edges: list) -> str:
    """推断节点的 expert_domain。优先 type 映射，文献节点按边覆盖。"""
    ntype = str(node.get("type", "")).strip().lower()
    label = str(node.get("label", "")).strip().lower()

    # 从边中查找该节点参与的领域
    edge_domains: set = set()
    for e in edges:
        if node_id in (e.get("source"), e.get("target")):
            ed = str(e.get("expert_domain", "")).strip()
            if ed and ed != "?":
                edge_domains.add(ed)
    if len(edge_domains) == 1:
        return edge_domains.pop()
    if "nutrition" in edge_domains:
        return "nutrition"

    # 标签关键词覆盖
    nutrition_kw = ["protein", "vitamin", "g/kg", "dose", "fat-free", "immunity",
                    "upper respiratory", "muscle protein", "carb", "fuel", "hydration"]
    rehab_kw = ["pain", "injury", "knee", "achilles", "plantar", "rehab"]
    race_kw = ["strategy", "pacing", "race day", "competition", "heat acclimation"]

    if any(kw in label for kw in nutrition_kw):
        return "nutrition"
    if any(kw in label for kw in rehab_kw):
        return "rehab_safety"
    if any(kw in label for kw in race_kw):
        return "race_strategy"

    # type 映射兜底
    return NODE_TYPE_TO_DOMAIN.get(ntype, "training_theory")


def _domain_for_edge(edge: Dict[str, Any], nodes: Dict[str, Any]) -> str:
    """推断边的 expert_domain。已有则保留，否则按两端节点类型推断。"""
    existing = str(edge.get("expert_domain", "")).strip()
    if existing and existing != "?":
        return existing

    src_t = str(nodes.get(edge.get("source", ""), {}).get("type", "")).strip().lower()
    tgt_t = str(nodes.get(edge.get("target", ""), {}).get("type", "")).strip().lower()

    # 约束边 → capacity_management
    if src_t == "template" and tgt_t == "constraint":
        return "capacity_management"
    # 训练课 ↔ 训练区 → workout_prescription
    if src_t in ("workout",) and tgt_t in ("zone", "template"):
        return "workout_prescription"
    # 训练课 → 生理/适应 → training_theory
    if src_t in ("workout", "template") and tgt_t in ("physiology", "adaptation"):
        return "training_theory"
    # 营养相关节点 → nutrition
    if src_t == "nutrition" or tgt_t == "nutrition":
        return "nutrition"

    return "training_theory"


def _quality_tier_for_edge(edge: Dict[str, Any]) -> str:
    """确定边的 quality_tier。"""
    if edge.get("expert_domain", "?") != "?" and edge.get("evidence", {}).get("source_file"):
        return "reviewed"  # 文献边带证据
    if edge.get("expert_domain", "?") != "?":
        return "reviewed"  # 种子边已审核
    return "candidate"


def evolve_kg(kg_path: Path, *, dry_run: bool = False) -> Dict[str, Any]:
    """执行 KG 进化。返回统计信息。"""
    stats: Dict[str, Counter] = {
        "nodes": Counter(),
        "edges": Counter(),
    }

    # 读取
    with open(kg_path, "r", encoding="utf-8") as f:
        kg = json.load(f)

    nodes: Dict[str, Any] = kg.get("nodes", {})
    edges: list = kg.get("edges", [])

    # 备份
    if not dry_run:
        backup_path = kg_path.with_suffix(f".json.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(kg_path, backup_path)
        print(f"已备份至 {backup_path}")

    # ─── 1. 边关系迁移 ───
    for edge in edges:
        old_rel = edge["relation"]
        if old_rel in RELATION_MIGRATION:
            new_rel = RELATION_MIGRATION[old_rel]
            # 保留旧关系作为 canonical_relation
            if not edge.get("canonical_relation") or edge["canonical_relation"] == old_rel:
                edge["canonical_relation"] = old_rel
            edge["relation"] = new_rel
            stats["edges"][f"migrated:{old_rel}→{new_rel}"] += 1
        elif old_rel in WHITELIST:
            stats["edges"]["already_whitelist"] += 1
        else:
            stats["edges"][f"unknown_relation:{old_rel}"] += 1

    # ─── 2. 节点 expert_domain 回填 ───
    for nid, node in nodes.items():
        old_domain = str(node.get("expert_domain", "")).strip()
        if not old_domain or old_domain == "?":
            # 先按标签/类型/边推断
            new_domain = _domain_for_node(node, nid, edges)
            node["expert_domain"] = new_domain
            stats["nodes"][f"domain:{new_domain}"] += 1
        else:
            stats["nodes"]["already_has_domain"] += 1

        # quality_tier
        if not node.get("quality_tier") or node["quality_tier"] in ("?", ""):
            node["quality_tier"] = "reviewed"  # 现有节点均为已审核
            stats["nodes"]["quality_tier_set"] += 1

    # ─── 3. 边 expert_domain 回填 + quality_tier ───
    # 先做一轮节点 expert_domain 传播：节点已回填后，用节点 domain 反哺边
    for edge in edges:
        existing_ed = str(edge.get("expert_domain", "")).strip()
        if not existing_ed or existing_ed == "?":
            new_ed = _domain_for_edge(edge, nodes)
            edge["expert_domain"] = new_ed
            stats["edges"][f"domain_backfill:{new_ed}"] += 1
        else:
            stats["edges"]["already_has_domain"] += 1

        # quality_tier
        if not edge.get("quality_tier") or edge["quality_tier"] in ("?", ""):
            edge["quality_tier"] = "reviewed"  # 已迁移的种子边
            stats["edges"]["quality_tier_set"] += 1

        # 规范 evidence 结构
        ev = edge.get("evidence", {})
        if isinstance(ev, dict):
            # 统一 source_file 字段
            if not edge.get("source_file"):
                sf = ev.get("source") or ev.get("source_file") or ev.get("source_path") or ""
                if sf:
                    edge["source_file"] = sf
            if not edge.get("chunk_id"):
                cid = ev.get("chunk_id") or ""
                if cid:
                    edge["chunk_id"] = cid

    # ─── 4. 添加元数据 ───
    kg["_evolved_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    kg["_evolution_notes"] = "relation migration to 8-relation whitelist + expert_domain backfill + quality_tier"

    # ─── 写回 ───
    if not dry_run:
        with open(kg_path, "w", encoding="utf-8") as f:
            json.dump(kg, f, ensure_ascii=False, indent=2)
        print(f"已写入 {kg_path}")
    else:
        print("[dry-run] 未写入")

    return stats


def main():
    import argparse
    parser = argparse.ArgumentParser(description="KG 终极形态进化")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--path", type=str, default=str(KG_PATH))
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"KG 文件不存在: {path}")
        return

    print(f"进化目标: {path}")
    print(f"模式: {'dry-run' if args.dry_run else '正式执行'}\n")

    stats = evolve_kg(path, dry_run=args.dry_run)

    # 报告
    print("\n=== 节点变更 ===")
    for k, v in stats["nodes"].items():
        print(f"  {k}: {v}")
    print("\n=== 边变更 ===")
    for k, v in stats["edges"].items():
        print(f"  {k}: {v}")

    # 最终统计
    with open(path, "r", encoding="utf-8") as f:
        kg = json.load(f)
    nodes = kg.get("nodes", {})
    edges = kg.get("edges", [])
    from collections import Counter as C
    node_domains = C(n.get("expert_domain", "?") for n in nodes.values())
    edge_domains = C(e.get("expert_domain", "?") for e in edges)
    edge_rels = C(e.get("relation", "?") for e in edges)
    edge_qt = C(e.get("quality_tier", "?") for e in edges)

    print(f"\n=== 最终状态 ({len(nodes)} 节点 / {len(edges)} 边) ===")
    print(f"节点领域: {dict(node_domains)}")
    print(f"边领域: {dict(edge_domains)}")
    print(f"边关系: {dict(edge_rels)}")
    print(f"边质量: {dict(edge_qt)}")

    # 检查白名单合规
    foreign = [e for e in edges if e["relation"] not in WHITELIST]
    if foreign:
        print(f"\n⚠️  仍有 {len(foreign)} 条边不在白名单中!")
        for e in foreign[:5]:
            print(f"  {e.get('source','?')[:12]} --{e['relation']}--> {e.get('target','?')[:12]}")


if __name__ == "__main__":
    main()
