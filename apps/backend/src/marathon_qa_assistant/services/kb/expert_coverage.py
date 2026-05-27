from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List


EXPERT_DOMAIN_MAP = {
    "coach_node": ["training_protocols", "action_library", "training_load"],
    "executor_node": ["training_protocols", "action_library"],
    "nutritionist_node": ["nutrition_race_fueling", "nutrition_hydration_race_fueling"],
    "adaptive_coach_node": ["training_load", "medical_risk", "mobility_recovery"],
    "therapist_node": ["medical_risk", "rehab_return_to_run"],
    "critic_auditor_node": ["training_protocols", "action_library", "medical_risk", "rehab_return_to_run", "nutrition_race_fueling"],
    "research_analyst_node": ["endurance_training_protocols", "load_injury_safety", "nutrition_hydration_race_fueling"],
}

CORE_EXPERTS = {"coach_node", "executor_node"}
MIN_SOURCE_RATIO_FOR_CORE = 0.4
MIN_SOURCE_RATIO_FOR_PARTIAL = 0.25


def _ratio(current: int, target: int) -> float:
    """统一覆盖率算法，避免 report 和测试各算各的。"""
    if target <= 0:
        return 1.0 if current > 0 else 0.0
    return round(current / target, 4)


def _index_chunks(chunks: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "chunk_count": 0,
            "permission_counts": Counter(),
            "quality_tier_counts": Counter(),
            "knowledge_layer_counts": Counter(),
        }
    )
    for chunk in chunks:
        domain = str(chunk.get("domain_pack") or "missing")
        grouped[domain]["chunk_count"] += 1
        grouped[domain]["permission_counts"][str(chunk.get("prescription_permission") or "missing")] += 1
        grouped[domain]["quality_tier_counts"][str(chunk.get("quality_tier") or "missing")] += 1
        grouped[domain]["knowledge_layer_counts"][str(chunk.get("knowledge_layer") or "missing")] += 1
    return {
        domain: {
            **stats,
            "permission_counts": dict(stats["permission_counts"]),
            "quality_tier_counts": dict(stats["quality_tier_counts"]),
            "knowledge_layer_counts": dict(stats["knowledge_layer_counts"]),
        }
        for domain, stats in grouped.items()
    }


def _domain_summary(row: Dict[str, Any], chunk_stats: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    domain = str(row["domain_pack"])
    current_sources = int(row.get("current_source_count") or 0)
    target_sources = int(row.get("target_source_count") or 0)
    current_rules = int(row.get("current_rule_count") or 0)
    target_rules = int(row.get("target_rule_count") or 0)
    stats = chunk_stats.get(domain, {})
    source_ratio = _ratio(current_sources, target_sources)
    rule_ratio = _ratio(current_rules, target_rules)
    status = str(row.get("gap_status") or "gap")
    if status != "gap" and source_ratio < MIN_SOURCE_RATIO_FOR_PARTIAL:
        status = "weak_partial"
    return {
        "domain_pack": domain,
        "status": status,
        "can_write_core": bool(row.get("can_write_core")),
        "current_source_count": current_sources,
        "target_source_count": target_sources,
        "source_coverage_ratio": source_ratio,
        "current_rule_count": current_rules,
        "target_rule_count": target_rules,
        "rule_coverage_ratio": rule_ratio,
        "current_question_count": int(row.get("current_question_count") or 0),
        "target_question_count": int(row.get("target_question_count") or 0),
        "chunk_count": int(stats.get("chunk_count") or 0),
        "permission_counts": stats.get("permission_counts", {}),
        "quality_tier_counts": stats.get("quality_tier_counts", {}),
        "knowledge_layer_counts": stats.get("knowledge_layer_counts", {}),
    }


def _expert_status(expert: str, domains: Dict[str, Dict[str, Any]]) -> tuple[str, List[str]]:
    blocking = []
    for domain, summary in domains.items():
        # gap 是硬阻塞；核心专家还要额外卡 can_write_core 领域的来源覆盖率。
        if summary["status"] == "gap":
            blocking.append(domain)
            continue
        if expert in CORE_EXPERTS and summary["can_write_core"] and summary["source_coverage_ratio"] < MIN_SOURCE_RATIO_FOR_CORE:
            blocking.append(domain)
    if blocking:
        return "blocked", blocking
    if any(summary["status"] in {"partial", "weak_partial"} for summary in domains.values()):
        return "partial", []
    return "covered", []


def build_expert_coverage_report(coverage_rows: List[Dict[str, Any]], chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    chunk_stats = _index_chunks(chunks)
    row_by_domain = {str(row["domain_pack"]): row for row in coverage_rows}
    domain_summaries = {domain: _domain_summary(row, chunk_stats) for domain, row in row_by_domain.items()}

    # chunks 里出现但治理矩阵里没有的领域也要保留，方便发现 runtime-only 数据。
    for domain, stats in chunk_stats.items():
        if domain not in domain_summaries:
            domain_summaries[domain] = {
                "domain_pack": domain,
                "status": "runtime_only",
                "can_write_core": False,
                "current_source_count": 0,
                "target_source_count": 0,
                "source_coverage_ratio": 0.0,
                "current_rule_count": 0,
                "target_rule_count": 0,
                "rule_coverage_ratio": 0.0,
                "current_question_count": 0,
                "target_question_count": 0,
                "chunk_count": int(stats.get("chunk_count") or 0),
                "permission_counts": stats.get("permission_counts", {}),
                "quality_tier_counts": stats.get("quality_tier_counts", {}),
                "knowledge_layer_counts": stats.get("knowledge_layer_counts", {}),
            }

    experts = {}
    for expert, domain_names in EXPERT_DOMAIN_MAP.items():
        expert_domains = {domain: domain_summaries[domain] for domain in domain_names if domain in domain_summaries}
        status, blocking_domains = _expert_status(expert, expert_domains)
        experts[expert] = {
            "status": status,
            "blocking_domains": blocking_domains,
            "domain_names": list(expert_domains),
            "chunk_count": sum(summary["chunk_count"] for summary in expert_domains.values()),
            "domain_packs": expert_domains,
        }

    global_blockers = sorted(
        domain
        for domain, summary in domain_summaries.items()
        if summary["status"] == "gap" or (summary["can_write_core"] and summary["source_coverage_ratio"] < MIN_SOURCE_RATIO_FOR_CORE)
    )
    return {
        "status": "blocked" if global_blockers else "partial",
        "global_blockers": global_blockers,
        "domain_packs": domain_summaries,
        "experts": experts,
    }
