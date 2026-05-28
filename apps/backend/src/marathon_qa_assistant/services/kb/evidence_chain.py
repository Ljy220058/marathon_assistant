from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from marathon_qa_assistant.services.kb.models import EvidenceDisplayMode, PrescriptionPermission


EVIDENCE_CHAIN_DISPLAY_MODES = [
    EvidenceDisplayMode.VERIFIED_SOURCE.value,
    EvidenceDisplayMode.MODEL_GENERAL_KNOWLEDGE.value,
    EvidenceDisplayMode.NEEDS_EVIDENCE.value,
    EvidenceDisplayMode.GRAPH_HINT.value,
    EvidenceDisplayMode.LEGACY_EXPLANATION.value,
    EvidenceDisplayMode.REJECTED_SOURCE.value,
]

ANSWER_SOURCE_MODES = [
    "verified_rag",
    "model_general_knowledge",
    "needs_evidence",
    "medical_referral",
    "structured_plan_rule",
]

CORE_FIELDS = {
    "workout_type",
    "main_set",
    "intensity",
    "duration",
    "weekly_quality_count",
    "long_run_cap",
    "progression",
    "risk_downgrade",
}


def build_model_general_knowledge_item(summary: str = "") -> Dict[str, Any]:
    return {
        "evidence_id": "model_general_knowledge",
        "citation_label": "",
        "display_mode": EvidenceDisplayMode.MODEL_GENERAL_KNOWLEDGE.value,
        "source_label": "模型常识说明",
        "source_registry_id": "",
        "source_url": "",
        "page": None,
        "section": "",
        "chunk_id": "",
        "text_span": str(summary or "没有可定位的本地证据；当前回答来自模型通用知识。"),
        "evidence_domain": "llm_general_knowledge",
        "knowledge_layer": "llm_general_knowledge",
        "allowed_use": "explanation",
        "prescription_permission": PrescriptionPermission.BLOCKED_NEEDS_EVIDENCE.value,
        "retrieval_mode": "none",
        "quality_tier": "not_source",
        "review_status": "not_applicable",
        "field_binding": {},
        "user_facing_summary": "没有可定位的本地证据；这是模型常识说明，不作为核心训练处方依据。",
        "expert_metadata": {},
    }


def build_needs_evidence_item(reason: str = "", field_binding: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    binding = dict(field_binding or {})
    suffix = f"：{reason}" if reason else ""
    return {
        "evidence_id": f"needs_evidence:{binding.get('field') or reason or 'unknown'}",
        "citation_label": "",
        "display_mode": EvidenceDisplayMode.NEEDS_EVIDENCE.value,
        "source_label": "待补证据",
        "source_registry_id": "",
        "source_url": "",
        "page": None,
        "section": "",
        "chunk_id": "",
        "text_span": "",
        "evidence_domain": "",
        "knowledge_layer": "",
        "allowed_use": "core_prescription",
        "prescription_permission": PrescriptionPermission.BLOCKED_NEEDS_EVIDENCE.value,
        "retrieval_mode": "none",
        "quality_tier": "missing",
        "review_status": "missing",
        "field_binding": binding,
        "user_facing_summary": f"当前字段缺少可绑定证据{suffix}，不能显示为已验证处方。",
        "expert_metadata": {"missing_reason": reason},
    }


def build_evidence_chain_payload(
    *,
    query: str = "",
    evidence_bundle: Optional[Dict[str, Any]] = None,
    answer_source_mode: str = "",
    answer_text: str = "",
    health: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    bundle = evidence_bundle if isinstance(evidence_bundle, dict) else {}
    health_payload = health if isinstance(health, dict) else bundle.get("health") if isinstance(bundle.get("health"), dict) else {}
    items = [
        evidence_chain_item_from_bundle_item(item)
        for item in (bundle.get("evidence_items") or [])
        if isinstance(item, dict)
    ]
    _apply_runtime_display_boundaries(items, health_payload)
    if not items and answer_source_mode == "model_general_knowledge":
        items.append(build_model_general_knowledge_item())

    inferred_mode = answer_source_mode if answer_source_mode in ANSWER_SOURCE_MODES else _infer_answer_source_mode(items)
    payload = {
        "query": str(query or bundle.get("query") or ""),
        "answer_source_mode": inferred_mode,
        "runtime_index_schema_version": str(health_payload.get("index_schema_version") or health_payload.get("source") or "unknown"),
        "runtime_core_prescription_enabled": bool(health_payload.get("runtime_core_prescription_enabled")),
        "items": items,
        "core_permission_violations": _core_permission_violations(items),
        "source_path_leak_count": _source_path_leak_count(items),
    }
    citation_audit = validate_citation_faithfulness(answer_text, payload)
    payload["fake_citation_violations"] = citation_audit["violations"]
    payload["citation_gate"] = citation_audit
    return payload


def evidence_chain_item_from_bundle_item(item: Dict[str, Any]) -> Dict[str, Any]:
    trace = item.get("trace") if isinstance(item.get("trace"), dict) else {}
    source_url = str(item.get("source_url") or trace.get("source_url") or "")
    page = item.get("page")
    section = str(item.get("section") or trace.get("section") or "")
    source_file = str(item.get("source_file") or item.get("source") or "")
    tier = str(item.get("tier") or item.get("evidence_tier") or "")
    domain = str(item.get("evidence_domain") or trace.get("evidence_domain") or _domain_from_tier(tier))
    permission = str(item.get("prescription_permission") or trace.get("prescription_permission") or _permission_from_tier(tier))
    retrieval_mode = str(item.get("retrieval_mode") or trace.get("retrieval_mode") or trace.get("source") or item.get("kind") or "")
    source_registry_id = str(item.get("source_registry_id") or trace.get("source_registry_id") or "")
    chunk_id = str(item.get("chunk_id") or "")
    display_mode = _display_mode_for_item(
        tier=tier,
        domain=domain,
        permission=permission,
        source_url=source_url,
        page=page,
        section=section,
        kind=str(item.get("kind") or ""),
    )
    return {
        "evidence_id": str(item.get("evidence_id") or chunk_id or source_registry_id or source_file or display_mode),
        "citation_label": str(item.get("citation_label") or ""),
        "display_mode": display_mode,
        "source_label": source_file or source_registry_id or _label_for_mode(display_mode),
        "source_registry_id": source_registry_id,
        "source_url": source_url if display_mode == EvidenceDisplayMode.VERIFIED_SOURCE.value else "",
        "page": page if display_mode == EvidenceDisplayMode.VERIFIED_SOURCE.value else None,
        "section": section if display_mode == EvidenceDisplayMode.VERIFIED_SOURCE.value else "",
        "chunk_id": chunk_id,
        "text_span": str(item.get("text") or item.get("snippet") or "")[:500],
        "evidence_domain": domain,
        "knowledge_layer": str(item.get("knowledge_layer") or trace.get("knowledge_layer") or ""),
        "allowed_use": str(item.get("allowed_use") or trace.get("allowed_use") or ""),
        "prescription_permission": permission,
        "retrieval_mode": retrieval_mode,
        "quality_tier": str(item.get("quality_tier") or trace.get("quality_tier") or ""),
        "review_status": str(item.get("review_status") or trace.get("review_status") or ""),
        "field_binding": dict(item.get("field_binding") or {}),
        "user_facing_summary": _summary_for_mode(display_mode, item),
        "expert_metadata": {
            "source_path": str(item.get("source_path") or ""),
            "score": float(item.get("score") or item.get("hybrid_score") or 0.0),
            "trace": trace,
            "tier": tier,
        },
    }


def _display_mode_for_item(
    *,
    tier: str,
    domain: str,
    permission: str,
    source_url: str,
    page: Any,
    section: str,
    kind: str,
) -> str:
    if tier == EvidenceDisplayMode.NEEDS_EVIDENCE.value or permission == PrescriptionPermission.BLOCKED_NEEDS_EVIDENCE.value:
        return EvidenceDisplayMode.NEEDS_EVIDENCE.value
    if domain == "llm_general_knowledge":
        return EvidenceDisplayMode.MODEL_GENERAL_KNOWLEDGE.value
    if kind == "graph" and not (source_url and (page not in (None, "", 0) or section)):
        return EvidenceDisplayMode.GRAPH_HINT.value
    if source_url and (page not in (None, "", 0) or section):
        return EvidenceDisplayMode.VERIFIED_SOURCE.value
    if tier in {"kb_fallback", "plan_only"} or domain == "sports_science_reference":
        return EvidenceDisplayMode.LEGACY_EXPLANATION.value
    return EvidenceDisplayMode.NEEDS_EVIDENCE.value


def _infer_answer_source_mode(items: List[Dict[str, Any]]) -> str:
    if _core_permission_violations(items):
        return "needs_evidence"
    domains = {str(item.get("evidence_domain") or "") for item in items}
    allowed_uses = {str(item.get("allowed_use") or "") for item in items}
    if domains & {"medical_safety", "environment_race_context"} or "risk_gate" in allowed_uses:
        return "medical_referral"
    modes = {str(item.get("display_mode") or "") for item in items}
    if EvidenceDisplayMode.VERIFIED_SOURCE.value in modes:
        return "verified_rag"
    if EvidenceDisplayMode.MODEL_GENERAL_KNOWLEDGE.value in modes:
        return "model_general_knowledge"
    if EvidenceDisplayMode.NEEDS_EVIDENCE.value in modes:
        return "needs_evidence"
    return "model_general_knowledge" if not items else "needs_evidence"


def validate_citation_faithfulness(answer_text: str, evidence_chain: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate that numbered Markdown citations point to located verified sources."""
    refs = _numbered_citations(answer_text)
    items = [
        item
        for item in ((evidence_chain or {}).get("items") or [])
        if isinstance(item, dict)
    ]
    by_label: Dict[str, Dict[str, Any]] = {}
    citable_labels: List[str] = []
    for index, item in enumerate(items, start=1):
        label = str(item.get("citation_label") or f"[{index}]").strip()
        if not label:
            continue
        by_label.setdefault(label, item)
        if _is_located_verified_item(item):
            citable_labels.append(label)

    violations: List[Dict[str, Any]] = []
    for label in refs:
        item = by_label.get(label)
        if item is None:
            violations.append(
                {
                    "citation_label": label,
                    "reason": "unknown_citation",
                    "display_mode": "",
                    "evidence_id": "",
                    "severity": "blocking",
                }
            )
            continue
        reason = _citation_violation_reason(item)
        if reason:
            violations.append(
                {
                    "citation_label": label,
                    "reason": reason,
                    "display_mode": str(item.get("display_mode") or ""),
                    "evidence_id": str(item.get("evidence_id") or ""),
                    "severity": "blocking",
                }
            )

    return {
        "status": "passed" if not violations else "failed",
        "fake_citation_count": len(violations),
        "cited_labels": refs,
        "citable_labels": citable_labels,
        "violations": violations,
    }


def _numbered_citations(answer_text: str) -> List[str]:
    seen = set()
    labels: List[str] = []
    for raw in re.findall(r"\[(\d+)\]", str(answer_text or "")):
        label = f"[{raw}]"
        if label not in seen:
            labels.append(label)
            seen.add(label)
    return labels


def _is_located_verified_item(item: Dict[str, Any]) -> bool:
    if str(item.get("display_mode") or "") != EvidenceDisplayMode.VERIFIED_SOURCE.value:
        return False
    source_url = str(item.get("source_url") or "")
    page = item.get("page")
    section = str(item.get("section") or "")
    return bool(source_url and (page not in (None, "", 0) or section))


def _citation_violation_reason(item: Dict[str, Any]) -> str:
    display_mode = str(item.get("display_mode") or "")
    if display_mode == EvidenceDisplayMode.MODEL_GENERAL_KNOWLEDGE.value:
        return "model_general_knowledge_cited"
    if display_mode == EvidenceDisplayMode.LEGACY_EXPLANATION.value:
        return "legacy_explanation_cited"
    if display_mode != EvidenceDisplayMode.VERIFIED_SOURCE.value:
        return "non_citable_display_mode"
    if not _is_located_verified_item(item):
        return "unlocatable_citation"
    return ""


def _apply_runtime_display_boundaries(items: List[Dict[str, Any]], health_payload: Dict[str, Any]) -> None:
    if _runtime_allows_verified_vector_sources(health_payload):
        return
    for item in items:
        if item.get("display_mode") != EvidenceDisplayMode.VERIFIED_SOURCE.value:
            continue
        retrieval_mode = str(item.get("retrieval_mode") or "")
        if retrieval_mode not in {"vector", "rag_sources", "fusion", "similarity", "kb_fallback"}:
            continue
        item["display_mode"] = EvidenceDisplayMode.LEGACY_EXPLANATION.value
        item["source_url"] = ""
        item["page"] = None
        item["section"] = ""
        item["prescription_permission"] = PrescriptionPermission.EXPLANATION_ONLY.value
        item["allowed_use"] = "explanation"
        item["user_facing_summary"] = _summary_for_mode(EvidenceDisplayMode.LEGACY_EXPLANATION.value)
        expert_metadata = item.setdefault("expert_metadata", {})
        if isinstance(expert_metadata, dict):
            expert_metadata["runtime_downgrade_reason"] = "runtime_core_prescription_disabled"


def _runtime_allows_verified_vector_sources(health_payload: Dict[str, Any]) -> bool:
    schema_version = str(health_payload.get("index_schema_version") or health_payload.get("source") or "").lower()
    if schema_version in {"legacy", "mixed", "unknown", ""}:
        return False
    return bool(health_payload.get("runtime_core_prescription_enabled"))


def _core_permission_violations(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    violations = []
    for item in items:
        binding = item.get("field_binding") if isinstance(item.get("field_binding"), dict) else {}
        field = str(binding.get("field") or "")
        if field in CORE_FIELDS and item.get("prescription_permission") != PrescriptionPermission.CAN_WRITE_CORE.value:
            violations.append(
                {
                    "evidence_id": item.get("evidence_id"),
                    "field": field,
                    "prescription_permission": item.get("prescription_permission"),
                    "display_mode": item.get("display_mode"),
                }
            )
    return violations


def _source_path_leak_count(items: List[Dict[str, Any]]) -> int:
    return sum(1 for item in items if "source_path" in item or "local_path" in item)


def _domain_from_tier(tier: str) -> str:
    if tier == "protocol_rule":
        return "protocol"
    if tier == "action_library":
        return "action_library"
    if tier == "kb_fallback":
        return "sports_science_reference"
    return ""


def _permission_from_tier(tier: str) -> str:
    if tier in {"protocol_rule", "action_library"}:
        return PrescriptionPermission.CAN_WRITE_CORE.value
    if tier == "kb_fallback":
        return PrescriptionPermission.EXPLANATION_ONLY.value
    return PrescriptionPermission.BLOCKED_NEEDS_EVIDENCE.value


def _label_for_mode(display_mode: str) -> str:
    return {
        EvidenceDisplayMode.MODEL_GENERAL_KNOWLEDGE.value: "模型常识说明",
        EvidenceDisplayMode.NEEDS_EVIDENCE.value: "待补证据",
        EvidenceDisplayMode.GRAPH_HINT.value: "关联线索",
        EvidenceDisplayMode.LEGACY_EXPLANATION.value: "解释性旧知识库来源",
        EvidenceDisplayMode.REJECTED_SOURCE.value: "已阻断来源",
    }.get(display_mode, "证据来源")


def _summary_for_mode(display_mode: str, item: Optional[Dict[str, Any]] = None) -> str:
    item = item or {}
    permission = str(item.get("prescription_permission") or "")
    domain = str(item.get("evidence_domain") or "")
    allowed_use = str(item.get("allowed_use") or "")
    if display_mode == EvidenceDisplayMode.VERIFIED_SOURCE.value and permission != PrescriptionPermission.CAN_WRITE_CORE.value:
        if domain in {"medical_safety", "environment_race_context"} or allowed_use == "risk_gate":
            return "可定位风险提醒来源，只能用于停止训练、转诊或环境风险解释。"
        return "可定位解释性来源，不能作为核心训练处方依据。"
    return {
        EvidenceDisplayMode.VERIFIED_SOURCE.value: "真实来源可定位。",
        EvidenceDisplayMode.MODEL_GENERAL_KNOWLEDGE.value: "模型常识说明，不作为核心训练处方依据。",
        EvidenceDisplayMode.NEEDS_EVIDENCE.value: "当前字段缺少可绑定证据，不能显示为已验证处方。",
        EvidenceDisplayMode.GRAPH_HINT.value: "知识图谱关联线索，未绑定可点击引用。",
        EvidenceDisplayMode.LEGACY_EXPLANATION.value: "旧知识库解释性来源，不能写入核心处方。",
        EvidenceDisplayMode.REJECTED_SOURCE.value: "该来源已被阻断或隔离。",
    }.get(display_mode, "证据状态待复核。")
