from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional

from marathon_qa_assistant.core.half_marathon_glossary import get_hmp_glossary_terms
from marathon_qa_assistant.core.kb_bootstrap import get_knowledge_base_health_snapshot
from marathon_qa_assistant.core.state_models import EvidenceBundle, EvidenceBundleItem
from marathon_qa_assistant.services.security_guards import InputGuard


_INPUT_GUARD = InputGuard()
_EMBEDDED_CITATION_RE = re.compile(r"\[(\d+)\]")


def _neutralize_embedded_citation_numbers(text: str) -> str:
    """Prevent source-local reference numbers from looking like system citations."""
    return _EMBEDDED_CITATION_RE.sub(lambda match: f"({match.group(1)})", str(text or ""))


class EvidenceTier(str, Enum):
    """证据层级：区分科学文献、动作库参考、系统规则三种来源。"""
    SCIENTIFIC = "scientific_evidence"      # 同行评审文献 / 运动科学文献
    EXERCISE_REF = "exercise_reference"     # 动作库 / 教练实践参考
    PROTOCOL_RULE = "protocol_rule"          # 系统规则层


def _infer_evidence_tier(item: Dict) -> str:
    """从 source_file / domain_pack / knowledge_layer 推断证据层级。

    优先级：domain_pack > knowledge_layer > source_file 关键词匹配。
    默认 fallback 为 exercise_reference（最保守分类）。
    """
    source_file = str(item.get("source_file", "")).lower()
    domain_pack = str(item.get("domain_pack", "")).lower()
    knowledge_layer = str(item.get("knowledge_layer", "")).lower()

    # 科学文献：含 DOI/PMID 或 domain_pack 为 sports_science/literature
    if any(kw in source_file for kw in ["doi", "pmid", "10.", "pubmed"]):
        return EvidenceTier.SCIENTIFIC.value
    if domain_pack in ("sports_science", "literature", "research_paper"):
        return EvidenceTier.SCIENTIFIC.value
    if knowledge_layer == "literature":
        return EvidenceTier.SCIENTIFIC.value

    # 动作库参考
    if "动作库" in source_file or domain_pack == "action_library":
        return EvidenceTier.EXERCISE_REF.value

    # 系统规则
    if domain_pack in ("protocol_rule", "system_rule") or knowledge_layer in ("protocol", "system"):
        return EvidenceTier.PROTOCOL_RULE.value
    if item.get("evidence_domain") == "protocol_rule":
        return EvidenceTier.PROTOCOL_RULE.value

    # 默认：动作库参考（最保守的分类）
    return EvidenceTier.EXERCISE_REF.value


PROTOCOL_SOURCE_DOCS = (
    "Sub-70半程马拉松训练_图片OCR整理.md",
    "docs/product/half_marathon_hmp_protocol.md",
    "docs/half_marathon_source_audit.md",
)

EVIDENCE_METADATA_KEYS = (
    "source_registry_id",
    "source_url",
    "local_path",
    "section",
    "section_anchor",
    "paragraph_index",
    "paragraph_hash",
    "char_start",
    "char_end",
    "text_span_hash",
    "language",
    "evidence_domain",
    "knowledge_layer",
    "domain_pack",
    "allowed_use",
    "prescription_permission",
    "quality_tier",
    "review_status",
    "exclude_from_training_generation",
    "needs_review",
    "retrieval_mode",
    "retrieval_status",
    "query_variant",
    "query_variants",
    "query_variant_count",
    "best_query_variant",
    "bilingual_match",
    "consensus_count",
    "score_breakdown",
    "relevance_score",
    "relevance_percent",
    "raw_vector_score",
    "confidence_level",
    "graph_relation_strength",
    "evidence_source_type",
    "decision_gate",
    "decision_gate_reason",
    "governance_conflict_id",
    "conflict_detected",
    "conflict_reason",
    "conflicting_sources",
)
def _resolve_health_snapshot(health: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    live_health = get_knowledge_base_health_snapshot()
    if not isinstance(health, dict):
        return live_health
    if bool(health.get("ready") or health.get("ok")):
        return health
    # 运行时快照比初始 working_state 的占位值更可信；若 live 已 ready，则优先使用 live。
    if bool(live_health.get("ready") or live_health.get("ok")):
        return live_health
    return health


def build_evidence_bundle(
    *,
    query: str,
    rag_sources: Optional[List[Dict[str, Any]]] = None,
    ranked_evidence: Optional[List[Dict[str, Any]]] = None,
    structured_training_plan: Optional[Dict[str, Any]] = None,
    health: Optional[Dict[str, Any]] = None,
) -> EvidenceBundle:
    items: List[EvidenceBundleItem] = []
    seen = set()

    for source in ranked_evidence or []:
        item = _item_from_ranked_evidence(source)
        _append_item(items, seen, item)

    for source in rag_sources or []:
        item = _item_from_rag_source(source)
        _append_item(items, seen, item)

    if isinstance(structured_training_plan, dict):
        for item in _protocol_rule_items(structured_training_plan):
            _append_item(items, seen, item)
        if structured_training_plan and not items:
            _append_item(items, seen, _plan_only_item(structured_training_plan))

    _renumber(items)
    return {
        "query": str(query or ""),
        "evidence_items": items,
        # 初始 working_state 可能携带未初始化占位健康态；构建证据包时刷新一次 runtime 快照，避免 trace 误报 kb_not_ready。
        "health": _normalize_health(_resolve_health_snapshot(health)),
    }


def format_evidence_bundle_lines(bundle: Optional[Dict[str, Any]], limit: Optional[int] = None) -> str:
    if not isinstance(bundle, dict):
        return "（暂无可用证据）"
    items = [item for item in (bundle.get("evidence_items") or []) if isinstance(item, dict)]
    if limit is not None:
        items = items[:limit]
    if not items:
        return "（暂无可用证据）"

    lines = []
    for item in items:
        label = str(item.get("citation_label") or "").strip() or "[?]"
        tier = str(item.get("tier") or "kb_fallback").strip()
        permission = str(item.get("prescription_permission") or item.get("trace", {}).get("prescription_permission") or "").strip()
        display_mode = str(item.get("display_mode") or item.get("trace", {}).get("display_mode") or "").strip()
        is_core = permission == "can_write_core" and display_mode not in {"graph_hint", "legacy_explanation", "model_general_knowledge", "needs_evidence", "rejected_source"}
        boundary = "core evidence" if is_core else "visible context only: graph/model/legacy hint"
        source = str(item.get("source_label") or item.get("source_file") or item.get("source") or "unknown").strip()
        locator = str(item.get("locator_hint") or item.get("page_hint") or "").strip()
        page = item.get("page")
        page_text = f" p.{page}" if page not in (None, "", 0) and not locator else ""
        snippet = str(item.get("text_span") or item.get("snippet") or item.get("text") or "").replace("\n", " ").strip()
        snippet = _neutralize_embedded_citation_numbers(snippet)
        locator_text = f" {locator}" if locator else page_text
        lines.append(f"{label} [{boundary}] {source}{locator_text}: {snippet[:220]}")
    visible_count = len(items)
    lines.append(f"（可用引用编号范围：[1] 到 [{visible_count}]，请勿使用超出此范围的编号）")
    lines.append("（证据边界：只有 core evidence 可用于核心训练处方；graph/model/legacy hint 只能作为可见背景或待核验线索。）")
    return "\n".join(lines)


def citation_labels(bundle: Optional[Dict[str, Any]]) -> List[str]:
    if not isinstance(bundle, dict):
        return []
    return [
        str(item.get("citation_label") or "").strip()
        for item in (bundle.get("evidence_items") or [])
        if isinstance(item, dict) and str(item.get("citation_label") or "").strip()
    ]


def find_invalid_citations(text: str, bundle: Optional[Dict[str, Any]]) -> List[str]:
    labels = set(citation_labels(bundle))
    refs = [f"[{raw}]" for raw in re.findall(r"\[(\d+)\]", str(text or ""))]
    invalid = []
    for ref in refs:
        if ref not in labels and ref not in invalid:
            invalid.append(ref)
    return invalid


def evidence_base_from_bundle(bundle: Optional[Dict[str, Any]], limit: Optional[int] = None) -> List[Dict[str, Any]]:
    if not isinstance(bundle, dict):
        return []
    items = [item for item in (bundle.get("evidence_items") or []) if isinstance(item, dict)]
    if limit is not None:
        items = items[:limit]
    evidence_base = []
    for index, item in enumerate(items, start=1):
        page = item.get("page")
        pages = [] if page in (None, "", 0) else [int(page)]
        evidence_base.append({
            "id": index,
            "evidence_id": item.get("evidence_id", f"evidence_{index}"),
            "citation_label": item.get("citation_label", f"[{index}]"),
            "tier": item.get("tier", "kb_fallback"),
            "evidence_tier": item.get("evidence_tier", EvidenceTier.EXERCISE_REF.value),
            "document": item.get("source_file", "unknown"),
            "source": item.get("source_file", "unknown"),
            "path": item.get("source_path", "") or item.get("source_file", ""),
            "source_path": item.get("source_path", ""),
            "pages": pages,
            "text": item.get("text", ""),
            "chunk_id": item.get("chunk_id", ""),
            "score": item.get("score", 0.0),
            "trace": item.get("trace", {}),
        })
    return evidence_base


def _item_from_ranked_evidence(source: Dict[str, Any]) -> EvidenceBundleItem:
    kind = str(source.get("kind") or "vector").strip()
    tier = "graph" if kind == "graph" else "kb_fallback"
    if kind == "fusion":
        tier = "kb_fallback"
    text = _scan_and_clean_context(str(source.get("text") or source.get("snippet") or ""))
    # P0-2: 若 source_path 为空，尝试从 source_file 推断
    source_path = str(source.get("source_path") or "")
    if not source_path:
        source_file = str(source.get("source_file") or "")
        if source_file and source_file != "unknown":
            from marathon_qa_assistant.services.vector_store import infer_source_path as _infer_sp
            source_path = _infer_sp(source_file)
    # 证据层级标注：从 source 元数据推断 evidence_tier
    evidence_tier = _infer_evidence_tier(source)
    item = {
        "evidence_id": str(source.get("evidence_id") or source.get("chunk_id") or ""),
        "citation_label": str(source.get("citation_label") or ""),
        "tier": tier,
        "display_mode": str(source.get("display_mode") or ""),
        "evidence_tier": evidence_tier,
        "source_file": str(source.get("source_file") or "unknown"),
        "source_path": source_path,
        "page": _safe_int(source.get("page")),
        "chunk_id": str(source.get("chunk_id") or ""),
        "snippet": text[:300],
        "text": text,
        "score": float(source.get("relevance_score") or source.get("hybrid_score") or source.get("retrieval_score") or source.get("score") or 0.0),
        "trace": dict(source.get("trace") or {"kind": kind}),
    }
    for key in EVIDENCE_METADATA_KEYS:
        if key in source:
            item[key] = source.get(key)
            item["trace"].setdefault(key, source.get(key))
    # P0-2: 确保 source_path 不为空（metadata 循环可能会用空值覆盖）
    if not item.get("source_path"):
        item["source_path"] = source_path
    return item


def _item_from_rag_source(source: Dict[str, Any]) -> EvidenceBundleItem:
    text = _scan_and_clean_context(str(source.get("text") or source.get("snippet") or ""))
    chunk_id = str(source.get("chunk_id") or "")
    source_file = str(source.get("source_file") or source.get("source") or "unknown")
    evidence_tier = _infer_evidence_tier(source)
    item = {
        "evidence_id": f"kb_{chunk_id}" if chunk_id else _stable_evidence_id("kb", source_file, text),
        "citation_label": "",
        "tier": "kb_fallback",
        "display_mode": str(source.get("display_mode") or ""),
        "evidence_tier": evidence_tier,
        "source_file": source_file,
        "source_path": str(source.get("source_path") or ""),
        "page": _safe_int(source.get("page")),
        "chunk_id": chunk_id,
        "snippet": text[:300],
        "text": text,
        "score": float(source.get("score") or 0.0),
        "trace": {"source": "rag_sources"},
    }
    for key in EVIDENCE_METADATA_KEYS:
        if key in source:
            item[key] = source.get(key)
            item["trace"].setdefault(key, source.get(key))
    return item


def _protocol_rule_items(structured_training_plan: Dict[str, Any]) -> List[EvidenceBundleItem]:
    protocol = structured_training_plan.get("half_marathon_protocol") or {}
    if not isinstance(protocol, dict) or not protocol.get("active"):
        return []

    validation = structured_training_plan.get("half_marathon_protocol_validation") or {}
    issues = [item for item in (validation.get("issues") or []) if isinstance(item, dict)]
    terms = get_hmp_glossary_terms(["hmp", "capacity_budget", "dynamic_calibration"], limit=3)
    summary_parts = ["HMP 基石规则已作为机器规则层启用：画像原型、阶段序列、配速校准、容量预算与专项验证共同约束半马计划。"]
    if issues:
        summary_parts.append(f"当前 HMP 验证记录 {len(issues)} 条 issue，审计层必须检查是否仍有 error。")
    if terms:
        summary_parts.append("核心术语：" + "；".join(f"{term['label']}={term['definition']}" for term in terms))
    text = " ".join(summary_parts)
    return [{
        "evidence_id": "protocol_half_marathon_hmp",
        "citation_label": "",
        "tier": "protocol_rule",
        "display_mode": "verified_source",
        "evidence_tier": EvidenceTier.PROTOCOL_RULE.value,
        "source_file": PROTOCOL_SOURCE_DOCS[1],
        "source_path": PROTOCOL_SOURCE_DOCS[1],
        "page": None,
        "chunk_id": "",
        "snippet": text[:300],
        "text": text,
        "score": 1.0,
        "trace": {
            "source": "half_marathon_protocol",
            "source_docs": list(PROTOCOL_SOURCE_DOCS),
            "issue_count": len(issues),
        },
    }]


def _plan_only_item(structured_training_plan: Dict[str, Any]) -> EvidenceBundleItem:
    meta = structured_training_plan.get("plan_meta") or {}
    text = f"当前输出由结构化训练计划骨架生成：目标={meta.get('goal', '')}，周数={meta.get('actual_weeks', '')}。"
    return {
        "evidence_id": "plan_only_structured_skeleton",
        "citation_label": "",
        "tier": "plan_only",
        "display_mode": "needs_evidence",
        "evidence_tier": EvidenceTier.PROTOCOL_RULE.value,
        "source_file": "structured_training_plan",
        "source_path": "",
        "page": None,
        "chunk_id": "",
        "snippet": text,
        "text": text,
        "score": 0.5,
        "trace": {"source": "structured_training_plan"},
    }


def _append_item(items: List[EvidenceBundleItem], seen: set, item: EvidenceBundleItem) -> None:
    key = (
        str(item.get("tier") or ""),
        str(item.get("chunk_id") or ""),
        str(item.get("source_file") or ""),
        str(item.get("text") or "")[:120],
    )
    if key in seen:
        return
    seen.add(key)
    if not item.get("evidence_id"):
        item["evidence_id"] = _stable_evidence_id(str(item.get("tier") or "evidence"), str(item.get("source_file") or ""), str(item.get("text") or ""))
    items.append(item)


def _renumber(items: Iterable[EvidenceBundleItem]) -> None:
    for index, item in enumerate(items, start=1):
        item["citation_label"] = f"[{index}]"


def _normalize_health(health: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    raw = health if isinstance(health, dict) else get_knowledge_base_health_snapshot()
    source = str(raw.get("source") or raw.get("mode") or "")
    # 保留 evidence display boundary 需要的 runtime gate 字段，避免 bundle 投影时丢失健康态。
    return {
        "kb_ready": bool(raw.get("ready") or raw.get("ok")),
        "source": source,
        "chunks_count": int(raw.get("chunks_count") or 0),
        "faiss_ready": bool(raw.get("faiss_ready")),
        "index_schema_version": str(raw.get("index_schema_version") or source or "unknown"),
        "metadata_completeness": float(raw.get("metadata_completeness") or 0.0),
        "runtime_core_prescription_enabled": bool(raw.get("runtime_core_prescription_enabled")),
        "commercial_core_prescription_enabled": bool(raw.get("commercial_core_prescription_enabled")),
    }


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _stable_evidence_id(prefix: str, source: str, text: str) -> str:
    raw = f"{source}|{text[:160]}"
    total = 0
    for char in raw:
        total = (total * 131 + ord(char)) % 10_000_000
    return f"{prefix}_{total:07d}"


def _scan_and_clean_context(text: str) -> str:
    is_safe, reason = _INPUT_GUARD.check(text, input_type="rag")
    if is_safe:
        return text
    return f"[RAG内容因安全风险已清洗: {reason}]"


__all__ = [
    "EvidenceTier",
    "build_evidence_bundle",
    "citation_labels",
    "evidence_base_from_bundle",
    "find_invalid_citations",
    "format_evidence_bundle_lines",
    "_infer_evidence_tier",
]
