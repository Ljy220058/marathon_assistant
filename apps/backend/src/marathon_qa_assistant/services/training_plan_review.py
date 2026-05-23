from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional

from marathon_qa_assistant.services.training_load import build_training_load_summary


CORE_PRESCRIPTION_FIELDS = {
    "workout_type",
    "main_set",
    "intensity",
    "duration",
    "weekly_quality_count",
    "long_run_cap",
    "progression",
    "risk_downgrade",
}

FORBIDDEN_CORE_SOURCE_TYPES = ["llm_expression", "llm_general_knowledge"]

QUALITY_KEYWORDS = {
    "interval",
    "vo2",
    "threshold",
    "tempo",
    "hmp",
    "race_pace",
    "hill",
    "speed",
    "hm_",
    "anaerobic",
}

STRENGTH_KEYWORDS = {
    "strength",
    "conditioning",
    "core",
    "gym",
    "resistance",
    "single-leg",
    "plyometric",
    "力量",
    "体能",
    "核心",
}

MOBILITY_KEYWORDS = {
    "stretch",
    "stretching",
    "mobility",
    "foam",
    "roll",
    "dynamic",
    "拉伸",
    "放松",
    "灵活性",
    "活动度",
}

REHAB_KEYWORDS = {
    "rehab",
    "return",
    "pain",
    "bike",
    "cycling",
    "elliptical",
    "swim",
    "walk",
    "low impact",
    "康复",
    "疼痛",
    "骑行",
    "游泳",
    "椭圆机",
    "步行",
    "低冲击",
}


def _day_dicts(days: Optional[Iterable[Any]]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for item in days or []:
        if hasattr(item, "to_dict"):
            result.append(item.to_dict())
        elif isinstance(item, dict):
            result.append(dict(item))
    return result


def _text_blob(day: Dict[str, Any], keys: Iterable[str]) -> str:
    return " ".join(str(day.get(key) or "") for key in keys).lower()


def _is_rest_day(day: Dict[str, Any]) -> bool:
    blob = _text_blob(day, ("training_type", "workout_type", "main_set"))
    return bool(day.get("is_rest")) or "rest" in blob or "休息" in blob


def _is_quality_day(day: Dict[str, Any]) -> bool:
    if _is_rest_day(day):
        return False
    blob = _text_blob(day, ("training_type", "workout_type", "main_set", "intensity", "zone_range"))
    return any(keyword in blob for keyword in QUALITY_KEYWORDS)


def _has_any_keyword(day: Dict[str, Any], keywords: set[str]) -> bool:
    blob = _text_blob(
        day,
        (
            "training_type",
            "workout_type",
            "main_set",
            "warmup",
            "cooldown",
            "alternative",
            "notes",
        ),
    )
    return any(keyword in blob for keyword in keywords)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _weekly_counts(days: List[Dict[str, Any]]) -> Dict[int, Dict[str, int]]:
    counts: Dict[int, Dict[str, int]] = defaultdict(lambda: {"training": 0, "rest": 0, "quality": 0})
    for day in days:
        week_index = _safe_int(day.get("week_index"))
        if week_index <= 0:
            continue
        if _is_rest_day(day):
            counts[week_index]["rest"] += 1
        else:
            counts[week_index]["training"] += 1
        if _is_quality_day(day):
            counts[week_index]["quality"] += 1
    return dict(counts)


def _evidence_counts(days: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Counter[str] = Counter()
    for day in days:
        tier = str(day.get("evidence_tier") or "unknown").strip() or "unknown"
        counts[tier] += 1
    return dict(counts)


def _core_source_violations(days: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    violations: List[Dict[str, Any]] = []
    for index, day in enumerate(days, start=1):
        field_sources = day.get("field_sources") if isinstance(day.get("field_sources"), dict) else {}
        for field_name in CORE_PRESCRIPTION_FIELDS:
            source = field_sources.get(field_name)
            if not isinstance(source, dict):
                continue
            source_type = str(source.get("source_type") or "").strip()
            if source_type in FORBIDDEN_CORE_SOURCE_TYPES:
                violations.append(
                    {
                        "day_index": day.get("day_index") or index,
                        "week_index": day.get("week_index"),
                        "field": field_name,
                        "source_type": source_type,
                    }
                )
    return violations


def _review_training_load(days: List[Dict[str, Any]], training_load_summary: Dict[str, Any]) -> Dict[str, Any]:
    summary = dict(training_load_summary or {})
    if not summary and days:
        summary = build_training_load_summary(days)
    weekly_loads = list(summary.get("weekly_loads") or summary.get("weekly_load_changes") or [])
    high_jumps = [
        {
            "week_index": item.get("week_index"),
            "delta_percent_from_previous": item.get("delta_percent_from_previous"),
            "trend_label": item.get("trend_label"),
        }
        for item in weekly_loads
        if abs(float(item.get("delta_percent_from_previous") or 0)) > 30
    ]
    not_device_metric = bool(summary.get("not_device_metric", True))
    status = "attention" if high_jumps or not not_device_metric else "reviewed"
    return {
        "status": status,
        "source_type": summary.get("source_type") or "planned_load_proxy",
        "load_kind": summary.get("load_kind") or "planned_load_proxy",
        "not_device_metric": not_device_metric,
        "method": summary.get("method") or "planned_zone_duration_proxy",
        "missing_inputs": list(
            summary.get("missing_inputs")
            or ["heart_rate", "hrv", "sleep_score", "device_recovery_status"]
        ),
        "weekly_loads": weekly_loads,
        "high_change_weeks": high_jumps,
        "boundary": "planned proxy only; not a Garmin/COROS/TrainingPeaks physiological load metric",
    }


def _review_plan_structure(days: List[Dict[str, Any]]) -> Dict[str, Any]:
    weekly = _weekly_counts(days)
    rest_days = sum(1 for day in days if _is_rest_day(day))
    quality_days = sum(1 for day in days if _is_quality_day(day))
    max_quality = max((item["quality"] for item in weekly.values()), default=0)
    status = "reviewed" if days and rest_days > 0 and max_quality <= 3 else "attention"
    return {
        "status": status,
        "total_days": len(days),
        "training_days": sum(1 for day in days if not _is_rest_day(day)),
        "rest_days": rest_days,
        "quality_days": quality_days,
        "weekly_counts": weekly,
        "max_quality_sessions_per_week": max_quality,
    }


def _review_periodization(structured_training_plan: Dict[str, Any], days: List[Dict[str, Any]]) -> Dict[str, Any]:
    phase_summary = list(structured_training_plan.get("phase_summary") or [])
    week_plans = list(structured_training_plan.get("week_plans") or [])
    phases_from_days = sorted({str(day.get("phase") or "").strip() for day in days if day.get("phase")})
    phase_names = [str(item.get("phase") or "").strip() for item in phase_summary if item.get("phase")]
    status = "reviewed" if phase_summary or phases_from_days else "gap"
    return {
        "status": status,
        "planned_weeks": len(week_plans) or _safe_int((structured_training_plan.get("plan_meta") or {}).get("actual_weeks")),
        "phase_count": len(phase_summary) or len(phases_from_days),
        "phase_names": phase_names or phases_from_days,
        "has_phase_boundaries": bool(phase_summary),
    }


def _review_injury_recovery(days: List[Dict[str, Any]]) -> Dict[str, Any]:
    risk_statuses = Counter(
        str((day.get("risk_gate") or {}).get("status") or "not_evaluated")
        for day in days
        if isinstance(day.get("risk_gate") or {}, dict)
    )
    medical_or_blocked = [
        day.get("day_index")
        for day in days
        if str((day.get("risk_gate") or {}).get("product_status") or "").strip() == "medical_referral"
        or str((day.get("risk_gate") or {}).get("status") or "").strip() == "blocked"
    ]
    status = "blocked" if medical_or_blocked else "reviewed"
    return {
        "status": status,
        "risk_gate_status_counts": dict(risk_statuses),
        "medical_or_blocked_day_indices": medical_or_blocked,
        "boundary": "medical red flags must stop training load generation and recommend professional evaluation",
    }


def _review_rehabilitation(days: List[Dict[str, Any]]) -> Dict[str, Any]:
    rehab_days = [day.get("day_index") for day in days if _has_any_keyword(day, REHAB_KEYWORDS)]
    recovery_days = [
        day.get("day_index")
        for day in days
        if "recovery" in _text_blob(day, ("training_type", "workout_type", "main_set")) or "恢复" in _text_blob(day, ("training_type", "workout_type", "main_set"))
    ]
    status = "supported" if rehab_days or recovery_days else "monitor"
    return {
        "status": status,
        "rehab_or_low_impact_day_indices": rehab_days,
        "recovery_day_indices": recovery_days,
        "boundary": "rehab suggestions are conservative unless backed by a clinician-specific protocol",
    }


def _review_strength_conditioning(days: List[Dict[str, Any]]) -> Dict[str, Any]:
    strength_days = [day.get("day_index") for day in days if _has_any_keyword(day, STRENGTH_KEYWORDS)]
    return {
        "status": "supported" if strength_days else "gap",
        "strength_day_indices": strength_days,
        "expectation": "commercial plan review should surface strength and conditioning support or explicitly mark the gap",
    }


def _review_mobility_recovery(days: List[Dict[str, Any]]) -> Dict[str, Any]:
    training_days = [day for day in days if not _is_rest_day(day)]
    with_warmup = [day for day in training_days if str(day.get("warmup") or "").strip()]
    with_cooldown = [day for day in training_days if str(day.get("cooldown") or "").strip()]
    mobility_days = [day.get("day_index") for day in training_days if _has_any_keyword(day, MOBILITY_KEYWORDS)]
    coverage = round((min(len(with_warmup), len(with_cooldown)) / len(training_days)) * 100, 1) if training_days else 0.0
    status = "supported" if training_days and coverage >= 80 else "gap"
    return {
        "status": status,
        "warmup_coverage_percent": coverage,
        "training_day_count": len(training_days),
        "warmup_day_count": len(with_warmup),
        "cooldown_day_count": len(with_cooldown),
        "mobility_day_indices": mobility_days,
    }


def _review_injury_prevention(days: List[Dict[str, Any]], load_review: Dict[str, Any]) -> Dict[str, Any]:
    weekly = _weekly_counts(days)
    weeks_without_rest = [week for week, counts in weekly.items() if counts.get("rest", 0) <= 0]
    weeks_with_many_quality = [week for week, counts in weekly.items() if counts.get("quality", 0) > 3]
    status = "attention" if weeks_without_rest or weeks_with_many_quality or load_review.get("high_change_weeks") else "reviewed"
    return {
        "status": status,
        "weeks_without_rest": weeks_without_rest,
        "weeks_with_more_than_three_quality_sessions": weeks_with_many_quality,
        "load_jump_weeks": list(load_review.get("high_change_weeks") or []),
        "prevention_checks": [
            "rest-day spacing",
            "weekly load progression",
            "quality-session density",
            "warmup/cooldown coverage",
        ],
    }


def _review_evidence_control(days: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = _evidence_counts(days)
    violations = _core_source_violations(days)
    needs_evidence_count = int(counts.get("needs_evidence", 0))
    return {
        "status": "attention" if violations or needs_evidence_count else "reviewed",
        "evidence_tier_counts": counts,
        "core_fields_checked": sorted(CORE_PRESCRIPTION_FIELDS),
        "core_fields_forbid": FORBIDDEN_CORE_SOURCE_TYPES,
        "core_source_violations": violations,
        "needs_evidence_count": needs_evidence_count,
    }


def _review_rag_vs_base_model(evidence_review: Dict[str, Any]) -> Dict[str, Any]:
    counts = evidence_review.get("evidence_tier_counts") or {}
    traceable_count = sum(int(counts.get(key, 0) or 0) for key in ("protocol_rule", "action_library", "kb_fallback"))
    llm_general_count = int(counts.get("llm_general_knowledge", 0) or 0)
    if traceable_count and llm_general_count:
        status = "partial_traceable"
    elif traceable_count:
        status = "traceable"
    else:
        status = "llm_general_knowledge_only"
    return {
        "status": status,
        "traceable_day_count": traceable_count,
        "llm_general_knowledge_day_count": llm_general_count,
        "proof_points": [
            "evidence_tier coverage is counted per day card",
            "core prescription fields are checked against forbidden LLM source types",
            "needs_evidence remains explicit instead of silently becoming a visible prescription",
        ],
        "comparison_boundary": "This proves traceability and controlled failure modes; it does not prove physiological truth without user/device outcome data.",
    }


def _review_layered_kb(days: List[Dict[str, Any]]) -> Dict[str, Any]:
    permission_counts: Counter[str] = Counter()
    layer_counts: Counter[str] = Counter()
    domain_counts: Counter[str] = Counter()
    retrieval_counts: Counter[str] = Counter()
    missing_metadata_day_indices: List[Any] = []

    for index, day in enumerate(days, start=1):
        metadata = day.get("kb_metadata") if isinstance(day.get("kb_metadata"), dict) else {}
        if not metadata:
            missing_metadata_day_indices.append(day.get("day_index") or index)
            continue
        permission_counts[str(metadata.get("prescription_permission") or "unknown")] += 1
        layer_counts[str(metadata.get("knowledge_layer") or "unknown")] += 1
        domain_counts[str(metadata.get("evidence_domain") or "unknown")] += 1
        retrieval_counts[str(metadata.get("retrieval_mode") or "unknown")] += 1

    if not permission_counts:
        status = "gap"
    elif missing_metadata_day_indices or permission_counts.get("blocked_needs_evidence"):
        status = "partial_traceable"
    else:
        status = "traceable"

    return {
        "status": status,
        "knowledge_layer_counts": dict(layer_counts),
        "evidence_domain_counts": dict(domain_counts),
        "retrieval_mode_counts": dict(retrieval_counts),
        "prescription_permission_counts": dict(permission_counts),
        "missing_metadata_day_indices": missing_metadata_day_indices,
        "normal_user_copy": "核心训练处方必须来自协议或动作库；知识库解释和模型常识不能伪装成处方证据。",
        "expert_boundary": "GraphRAG/vector evidence is explanation-only unless it maps back to protocol or action-library permission.",
    }


def _review_runtime_kb_boundary(rag_health: Dict[str, Any]) -> Dict[str, Any]:
    health = dict(rag_health or {})
    schema_version = str(health.get("index_schema_version") or health.get("source") or "unknown")
    metadata_completeness = health.get("metadata_completeness")
    runtime_core_enabled = bool(health.get("runtime_core_prescription_enabled"))
    commercial_core_enabled = bool(health.get("commercial_core_prescription_enabled", runtime_core_enabled))
    runtime_status = str(health.get("runtime_status") or "")
    if commercial_core_enabled:
        status = "core_enabled"
    elif runtime_core_enabled:
        status = "runtime_preview_not_commercial"
    elif schema_version in {"legacy", "mixed", "unknown", ""}:
        status = "explanation_only"
    else:
        status = "not_core_enabled"
    return {
        "status": status,
        "index_schema_version": schema_version,
        "metadata_completeness": metadata_completeness,
        "runtime_core_prescription_enabled": runtime_core_enabled,
        "commercial_core_prescription_enabled": commercial_core_enabled,
        "runtime_status": runtime_status,
        "can_replace_runtime": bool(health.get("can_replace_runtime", commercial_core_enabled)),
        "boundary": "vector KB can support retrieval, but core prescription is commercial-enabled only after runtime and source-review gates pass",
    }


def build_training_plan_review(
    *,
    structured_training_plan: Optional[Dict[str, Any]],
    daily_schedule_cards: Optional[Iterable[Any]],
    training_load_summary: Optional[Dict[str, Any]] = None,
    rag_health: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    plan = structured_training_plan if isinstance(structured_training_plan, dict) else {}
    days = _day_dicts(daily_schedule_cards)
    load_review = _review_training_load(days, dict(training_load_summary or {}))
    evidence_review = _review_evidence_control(days)
    dimensions = {
        "training_load": load_review,
        "plan_structure": _review_plan_structure(days),
        "periodization": _review_periodization(plan, days),
        "injury_recovery": _review_injury_recovery(days),
        "rehabilitation": _review_rehabilitation(days),
        "strength_conditioning": _review_strength_conditioning(days),
        "mobility_recovery": _review_mobility_recovery(days),
        "injury_prevention": _review_injury_prevention(days, load_review),
        "evidence_control": evidence_review,
        "rag_vs_base_model": _review_rag_vs_base_model(evidence_review),
        "layered_kb": _review_layered_kb(days),
        "runtime_kb_boundary": _review_runtime_kb_boundary(dict(rag_health or {})),
    }
    risks = [
        f"{name}: {dimension.get('status')}"
        for name, dimension in dimensions.items()
        if dimension.get("status") in {"attention", "gap", "blocked", "llm_general_knowledge_only"}
    ]
    strengths = [
        f"{name}: {dimension.get('status')}"
        for name, dimension in dimensions.items()
        if dimension.get("status") in {"reviewed", "supported", "traceable", "partial_traceable"}
    ]
    return {
        "review_version": "training_plan_review.v1",
        "status": "needs_attention" if risks else "reviewed",
        "summary": {
            "reviewed_dimensions_count": len(dimensions),
            "not_device_metric": bool(load_review.get("not_device_metric", True)),
            "strengths": strengths,
            "risks": risks,
            "review_scope": [
                "daily_schedule_cards",
                "structured_training_plan",
                "planned_load_proxy",
                "field_sources",
                "evidence_tier",
            ],
        },
        "dimensions": dimensions,
    }
