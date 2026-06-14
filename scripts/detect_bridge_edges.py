"""
从候选队列和已有 KG 中检测跨领域桥接边。

桥接边（bridges_to）连接不同 expert_domain 的实体，
带 bridge_type: causal | dependency | constraint | handoff

检测策略：
1. 同一实体出现在 ≥2 个领域的边中 → 该实体是桥接点
2. 沿桥接点创建跨域边，推断 bridge_type
3. 写入候选队列（status=candidate），与普通候选统一审核流

用法: python scripts/detect_bridge_edges.py [--dry-run]
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
KG_PATH = ROOT / "data" / "vector_kb" / "v2" / "knowledge_graph.json"
QUEUE_PATH = ROOT / "data" / "knowledge" / "governance" / "kg_candidate_triples.jsonl"

# ─── bridge_type 推断规则 ──────────────────────────────────

# 领域 pair → 常见桥接类型和方向
DOMAIN_BRIDGE_RULES: Dict[Tuple[str, str], str] = {
    # 训练负荷 → 伤病风险 (因果)
    ("training_theory", "rehab_safety"): "causal",
    ("rehab_safety", "training_theory"): "causal",
    # 营养 → 训练效果 (依赖)
    ("nutrition", "training_theory"): "dependency",
    ("training_theory", "nutrition"): "dependency",
    # 康复 → 训练容量限制 (约束)
    ("rehab_safety", "capacity_management"): "constraint",
    ("capacity_management", "rehab_safety"): "constraint",
    # 营养 → 比赛策略 (依赖)
    ("nutrition", "race_strategy"): "dependency",
    ("race_strategy", "nutrition"): "dependency",
    # 训练理论 → 比赛策略 (handoff)
    ("training_theory", "race_strategy"): "handoff",
    ("race_strategy", "training_theory"): "handoff",
    # 训练理论 → 训练处方 (handoff)
    ("training_theory", "workout_prescription"): "handoff",
    ("workout_prescription", "training_theory"): "handoff",
    # 容量管理 → 训练处方 (约束: 容量限制约束了课表设计)
    ("capacity_management", "workout_prescription"): "constraint",
    ("workout_prescription", "capacity_management"): "constraint",
    # 康复 → 训练处方 (约束: 伤病限制约束了训练动作选择)
    ("rehab_safety", "workout_prescription"): "constraint",
    ("workout_prescription", "rehab_safety"): "constraint",
    # 训练处方 → 训练理论 (depends: 课表设计依赖训练理论)
    ("workout_prescription", "training_theory"): "dependency",
    ("training_theory", "workout_prescription"): "dependency",
}


def _node_label(node_id: str, nodes: Dict[str, Any]) -> str:
    """获取节点标签，截断到 40 字。"""
    label = str(nodes.get(node_id, {}).get("label", node_id))
    return label[:40]


def _infer_bridge_type(source_domain: str, target_domain: str) -> str:
    """根据领域 pair 推断桥接类型。"""
    if source_domain == target_domain:
        return "none"
    key = (source_domain, target_domain)
    return DOMAIN_BRIDGE_RULES.get(key, "causal")


def detect_bridge_candidates(
    kg_path: Path,
    queue_path: Path,
    *,
    dry_run: bool = False,
) -> List[Dict[str, Any]]:
    """检测跨领域桥接候选。返回新增候选列表。"""
    with open(kg_path, "r", encoding="utf-8") as f:
        kg = json.load(f)

    nodes = kg.get("nodes", {})
    edges = kg.get("edges", [])

    # ─── 1. 构建实体 → 领域映射 ───
    entity_domains: Dict[str, Set[str]] = defaultdict(set)  # node_id → {domain1, domain2, ...}

    for nid, node in nodes.items():
        domain = str(node.get("expert_domain", "")).strip()
        if domain and domain != "?":
            entity_domains[nid].add(domain)

    # 也参与边的领域
    for edge in edges:
        ed = str(edge.get("expert_domain", "")).strip()
        if ed and ed != "?":
            entity_domains[edge["source"]].add(ed)
            entity_domains[edge["target"]].add(ed)

    # ─── 2. 找桥接点（同一实体出现在 ≥2 个领域） ───
    bridge_nodes: Dict[str, Set[str]] = {}
    for nid, domains in entity_domains.items():
        if len(domains) >= 2:
            bridge_nodes[nid] = domains

    # ─── 3. 为桥接点生成跨域边 ───
    # 找在每个领域中与桥接点相连的实体
    domain_neighbors: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
    # bridge_id → {domain → {neighbor_ids}}

    for edge in edges:
        src, tgt = edge["source"], edge["target"]
        ed = str(edge.get("expert_domain", "")).strip()
        if not ed or ed == "?":
            continue

        # 如果一端是桥接点，另一端就是该领域的邻居
        if src in bridge_nodes and ed in bridge_nodes[src]:
            domain_neighbors[src][ed].add(tgt)
        if tgt in bridge_nodes and ed in bridge_nodes[tgt]:
            domain_neighbors[tgt][ed].add(src)

    # 为每个桥接点，连接不同领域的邻居
    candidates: List[Dict[str, Any]] = []
    seen_pairs: Set[Tuple[str, str, str]] = set()

    for bridge_id, domains in sorted(bridge_nodes.items()):
        bridge_label = _node_label(bridge_id, nodes)
        if len(domains) < 2:
            continue

        domain_list = sorted(domains)
        for i, d1 in enumerate(domain_list):
            neighbors1 = domain_neighbors.get(bridge_id, {}).get(d1, set())
            if not neighbors1:
                # 没有邻居，用桥接点自身作为备选
                neighbors1 = {bridge_id}

            for d2 in domain_list[i + 1:]:
                # 推断桥接方向：d1 → d2 还是 d2 → d1
                btype = _infer_bridge_type(d1, d2)
                if btype == "none":
                    continue

                neighbors2 = domain_neighbors.get(bridge_id, {}).get(d2, set())
                if not neighbors2:
                    neighbors2 = {bridge_id}

                for n1 in neighbors1:
                    for n2 in neighbors2:
                        if n1 == n2:
                            continue
                        label1 = _node_label(n1, nodes)
                        label2 = _node_label(n2, nodes)

                        pair_key = (label1, "bridges_to", label2)
                        if pair_key in seen_pairs:
                            continue
                        seen_pairs.add(pair_key)

                        candidate = {
                            "candidate_id": f"bridge_{d1[:4]}_{d2[:4]}_{hash(pair_key) & 0xFFFFF:05x}",
                            "head_entity": label1,
                            "relation": "bridges_to",
                            "tail_entity": label2,
                            "confidence": 0.7,
                            "expert_domain": d1,  # 来源领域
                            "bridge_type": btype,
                            "bridge_source_domain": d1,
                            "bridge_target_domain": d2,
                            "source_file": "bridge_detection",
                            "chunk_id": f"bridge_{bridge_id[:12]}",
                            "evidence_domain": d1,
                            "evidence_span": f"跨领域桥接: {label1}({d1}) → {label2}({d2}), 经由 {bridge_label}",
                            "status": "candidate",
                            "reviewed_by": "",
                            "review_note": f"auto-detected bridge via {bridge_label}",
                        }
                        candidates.append(candidate)

    # ─── 4. 去重后写入 ───
    if not dry_run and candidates:
        # 读取已有队列
        existing_ids: set = set()
        if queue_path.exists():
            with open(queue_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            existing_ids.add(entry.get("candidate_id", ""))
                        except json.JSONDecodeError:
                            pass

        new_count = 0
        with open(queue_path, "a", encoding="utf-8") as f:
            for cand in candidates:
                cid = cand["candidate_id"]
                if cid and cid not in existing_ids:
                    f.write(json.dumps(cand, ensure_ascii=False) + "\n")
                    existing_ids.add(cid)
                    new_count += 1

        print(f"写入 {new_count} 条桥接候选 (总去重后)")

    return candidates


def main():
    import argparse
    parser = argparse.ArgumentParser(description="KG 桥接边检测")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    candidates = detect_bridge_candidates(KG_PATH, QUEUE_PATH, dry_run=args.dry_run)
    print(f"\n检测到 {len(candidates)} 条桥接候选")
    for c in candidates[:10]:
        print(f"  [{c['bridge_type']:12}] {c['head_entity'][:25]:25} --bridges_to--> {c['tail_entity'][:25]} "
              f"({c['bridge_source_domain']} → {c['bridge_target_domain']})")


if __name__ == "__main__":
    main()
