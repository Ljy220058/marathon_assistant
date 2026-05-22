from __future__ import annotations

import asyncio
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from marathon_qa_assistant.services.workout_template_retriever import (
    WORKOUT_TEMPLATE_REGISTRY,
    ZONE_LABELS,
    ZONE_LABELS_DETAIL,
    EVIDENCE_TIER_LABELS,
    build_daily_workout_template_card_from_hits,
    get_action_library_foundation_hits,
    normalize_workout_type_for_template,
    _select_relevant_action_library_hits,
)
from marathon_qa_assistant.services.vector_store import load_vector_kb, retrieve
from marathon_qa_assistant.core.app_state import get_preferred_vector_dir, has_vector_kb_artifacts
from marathon_qa_assistant.core.zone_constants import sanitize_all_pace
from marathon_qa_assistant.services.training_load import (
    build_training_load_summary,
    calculate_plan_training_load,
    infer_duration_min,
)

HMP_WORKOUT_TYPES = {
    "hm_intro_fartlek_hills",
    "hm_base_threshold_progression",
    "hm_90_support_endurance",
    "hm_95_long_fast_run",
    "hm_100_float_intervals",
    "hm_105_specific_speed",
    "hm_110_support_speed",
}

HMP_LONG_ENDURANCE_TYPES = {
    "long_run",
    "progression_run",
    "marathon_pace",
    "tempo_run",
    "anaerobic_threshold",
}

HMP_SPEED_TYPES = {
    "interval_run",
    "vo2max_interval",
    "anaerobic_threshold",
    "tempo_run",
    "fartlek",
    "hill_repeats",
    "strides",
}


@dataclass
class DailyScheduleItem:
    date: str
    day_label: str
    week_index: int
    day_index: int
    phase: str
    training_type: str
    training_type_label: str
    workout_type: str
    zone_range: str
    zone_label: str
    intensity_target: str
    main_set: str
    warmup: str
    cooldown: str
    alternative: str
    training_objective: str
    evidence_tier: str
    evidence_tier_label: str
    source: List[str] = field(default_factory=list)
    evidence_ids: List[int] = field(default_factory=list)
    is_rest: bool = False
    notes: str = ""
    duration_min: int = 0
    training_load: int = 0
    training_load_method: str = ""
    training_load_factors: Dict[str, Any] = field(default_factory=dict)
    card_status: str = "generated"
    field_sources: Dict[str, Any] = field(default_factory=dict)
    protocol_check: Dict[str, Any] = field(default_factory=dict)
    action_match: Dict[str, Any] = field(default_factory=dict)
    kb_fallback: Dict[str, Any] = field(default_factory=dict)
    risk_gate: Dict[str, Any] = field(default_factory=dict)
    trace: Dict[str, Any] = field(default_factory=dict)
    kb_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["intensity"] = self.intensity_target
        result["duration"] = self.duration_min
        result["objective"] = self.training_objective
        return result


@dataclass
class MonthlyTrainingCalendar:
    year: int
    month: int
    start_week_index: int
    end_week_index: int
    total_days: int
    days: List[DailyScheduleItem] = field(default_factory=list)
    phases: List[Dict[str, Any]] = field(default_factory=list)
    evidence_summary: Dict[str, int] = field(default_factory=dict)
    training_load_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["days"] = [d.to_dict() for d in self.days]
        return result


def _extract_kb_evidence_for_workout(
    workout_type: str,
    top_k: int = 20,
) -> Tuple[List[Dict[str, Any]], str]:
    selected_vector_dir = get_preferred_vector_dir()
    if not has_vector_kb_artifacts(selected_vector_dir):
        return [], ""

    try:
        chunks, vectorizer, matrix, bm25 = load_vector_kb(selected_vector_dir)
    except Exception:
        return [], ""

    registry_entry = WORKOUT_TEMPLATE_REGISTRY.get(workout_type, {})
    aliases = registry_entry.get("aliases", [workout_type])
    search_query = " ".join(aliases[:5])

    hits = retrieve(search_query, chunks, vectorizer, matrix, top_k=top_k, bm25=bm25)
    return hits, search_query


def _filter_kb_evidence_hits(
    workout_type: str,
    hits: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    relevant = []
    for hit in hits:
        source_file = str(hit.get("source_file") or "")
        text = str(hit.get("text") or "")
        if source_file == "动作库.pdf":
            continue
        relevant.append(hit)
    return relevant


def _try_generate_schedule_from_kb_llm(
    workout_type: str,
    kb_hits: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not kb_hits:
        return None

    registry_entry = WORKOUT_TEMPLATE_REGISTRY.get(workout_type, {})
    display_name = registry_entry.get("display_name", workout_type)
    zone_range = registry_entry.get("zone_range", "")
    intensity_target = registry_entry.get("intensity_target", "")

    combined_text = "\n".join(
        str(hit.get("text") or "")[:500] for hit in kb_hits[:5]
    )

    if len(combined_text.strip()) < 50:
        return None
    blocked_main_set_candidates = _extract_kb_main_set_candidates(combined_text)

    source_labels = []
    seen_sources = set()
    for hit in kb_hits[:3]:
        sf = str(hit.get("source_file") or "")
        page = hit.get("page")
        label = sf if not page else f"{sf}，第 {page} 页"
        if label not in seen_sources:
            seen_sources.add(label)
            source_labels.append(label)

    return {
        "workout_type": workout_type,
        "training_type_label": registry_entry.get("training_type_label", display_name),
        "zone_range": zone_range,
        "intensity_target": intensity_target,
        "zone_label": ZONE_LABELS.get(zone_range.replace("→", "-"), intensity_target),
        "evidence_tier": "kb_fallback",
        "evidence_tier_label": EVIDENCE_TIER_LABELS["kb_fallback"],
        "source": source_labels,
        "evidence_text_snippet": combined_text[:600],
        "main_set_candidates": [],
        "blocked_core_candidates": {
            "main_set": blocked_main_set_candidates,
            "reason": "kb_fallback_cannot_source_core_prescription",
        },
        "training_objective": f"基于{display_name}的通用训练原则生成（参考知识库证据）",
        "warmup_suggestion": _extract_kb_field(combined_text, "warmup"),
        "cooldown_suggestion": _extract_kb_field(combined_text, "cooldown"),
        "alternative_workout": "",
    }


def _extract_kb_main_set_candidates(text: str) -> List[str]:
    patterns = [
        r"(\d+\s*[×xX*]\s*\d+\s*(?:m|米|分钟|min)[^。\n；;]{0,40})",
        r"(\d+\s*[-~至到]\s*\d+\s*分钟[^。\n；;]{0,40})",
        r"(\d+\s*分钟[^。\n；;]{0,30}(?:跑|训练|间歇|节奏|阈值))",
        r"(\d+(?:\.\d+)?\s*(?:km|公里)[^。\n；;]{0,40})",
    ]
    candidates: List[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, str(text or ""), flags=re.IGNORECASE):
            candidate = re.sub(r"\s+", " ", match.group(1)).strip(" ，,。；;")
            if 5 <= len(candidate) <= 80 and candidate not in candidates:
                candidates.append(candidate)
            if len(candidates) >= 3:
                return candidates
    return candidates


def _extract_kb_field(text: str, field: str) -> str:
    if field == "warmup":
        patterns = [
            r"(?:热身|warm[-_ ]?up)[:：]\s*(.{5,80}?)(?:\n|。|；|;|$)",
            r"(\d+分钟慢跑[^。\n；;]{0,40}(?:动态拉伸|加速跑|马克操)[^。\n；;]{0,30})",
        ]
    elif field == "cooldown":
        patterns = [
            r"(?:冷身|cooldown|cool[-_ ]?down)[:：]\s*(.{5,80}?)(?:\n|。|；|;|$)",
            r"(\d+分钟慢跑[^。\n；;]{0,40}(?:拉伸|放松)[^。\n；;]{0,30})",
        ]
    else:
        return ""
    for pattern in patterns:
        match = re.search(pattern, str(text or ""), flags=re.IGNORECASE | re.DOTALL)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip(" ，,。；;")
    return ""


def _hm_protocol_candidate_ids_for_week(
    structured_training_plan: Dict[str, Any],
    raw_week: Dict[str, Any],
) -> List[str]:
    protocol = structured_training_plan.get("half_marathon_protocol") or {}
    if not isinstance(protocol, dict) or not protocol.get("active"):
        return []

    preferred = [
        item
        for item in (protocol.get("preferred_workouts") or [])
        if isinstance(item, dict) and str(item.get("id") or "") in HMP_WORKOUT_TYPES
    ]
    if not preferred:
        return []

    week_text_parts = [
        raw_week.get("week_goal"),
        *(raw_week.get("key_workouts") or []),
        *(raw_week.get("action_suggestions") or []),
    ]
    week_text = " ".join(str(item or "") for item in week_text_parts)

    matched = []
    for item in preferred:
        workout_id = str(item.get("id") or "").strip()
        label = str(item.get("label") or "").strip()
        if workout_id and (workout_id in week_text or (label and label in week_text)):
            matched.append(workout_id)
    if matched:
        return list(dict.fromkeys(matched))

    if "HMP" in week_text:
        return []
    return [str(item.get("id")) for item in preferred]


def _can_project_hmp_candidate_to_day(
    candidate_id: str,
    workout_type: str,
    training_type: str,
    main_set: str,
) -> bool:
    if not candidate_id or candidate_id not in HMP_WORKOUT_TYPES:
        return False
    if workout_type in HMP_WORKOUT_TYPES:
        return False
    if not workout_type or workout_type == "easy_run":
        return False

    combined = f"{training_type} {main_set}"
    if "恢复" in combined or "轻松" in combined:
        return False

    if candidate_id in {"hm_base_threshold_progression", "hm_90_support_endurance", "hm_95_long_fast_run"}:
        return workout_type in HMP_LONG_ENDURANCE_TYPES
    if candidate_id in {"hm_intro_fartlek_hills", "hm_100_float_intervals", "hm_105_specific_speed", "hm_110_support_speed"}:
        return workout_type in HMP_SPEED_TYPES
    return False


def _strip_workout_id_prefix(value: str) -> str:
    return re.sub(r"^\s*hm_[a-z0-9_]+\s*(?:[：:]|\?|\s+)\s*", "", str(value or "").strip(), flags=re.IGNORECASE)


def _is_user_requested_workout_day(day: Dict[str, Any]) -> bool:
    notes = str(day.get("notes") or "")
    return "用户个性化周结构要求" in notes


def _merge_objective_text(*values: str) -> str:
    parts = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in parts:
            parts.append(text)
    return "；".join(parts)


def _build_no_evidence_training_card(training_type: str, notes: str = "") -> Dict[str, str]:
    return {
        "main_set": "动作库证据不足，暂不展示具体主课。",
        "warmup": "动作库证据不足，暂不展示热身建议。",
        "cooldown": "动作库证据不足，暂不展示冷身建议。",
        "alternative_workout": "",
        "training_objective": "当前训练类型缺少可直接绑定的动作库证据，待补全后再显示执行细节。",
        "evidence_tier": "needs_evidence",
        "evidence_tier_label": EVIDENCE_TIER_LABELS["needs_evidence"],
        "notes": notes,
        "training_type": training_type,
    }


SOURCE_TYPE_BY_EVIDENCE_TIER = {
    "protocol_rule": "protocol",
    "action_library": "action_library",
    "kb_fallback": "kb_fallback",
    "needs_evidence": "needs_evidence",
    "plan_only": "needs_evidence",
}

QUALITY_WORKOUT_TYPES = {
    *HMP_WORKOUT_TYPES,
    "aerobic_threshold",
    "anaerobic_threshold",
    "tempo_run",
    "interval_run",
    "vo2max_interval",
    "marathon_pace",
    "progression_run",
    "fartlek",
    "hill_repeats",
    "strides",
}

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

NON_CORE_KB_FIELDS = {
    "warmup",
    "cooldown",
    "notes",
    "alternative",
    "terminology",
    "recovery_advice",
}

ACTION_ID_PREFIX = {
    "aerobic_threshold": "AET",
    "anaerobic_threshold": "ANT",
    "tempo_run": "TMP",
    "interval_run": "INT",
    "vo2max_interval": "VO2",
    "long_run": "LSD",
    "easy_run": "EZY",
    "marathon_pace": "MP",
    "progression_run": "PRG",
    "fartlek": "FTL",
    "hill_repeats": "HIL",
    "strides": "STR",
}


def _action_library_type_for_hmp_protocol(workout_type: str, training_type: str, main_set: str) -> str:
    combined = f"{training_type} {main_set}"
    if workout_type == "hm_base_threshold_progression":
        return "progression_run" if ("渐进" in combined or "渐速" in combined or "肯尼亚" in combined) else "aerobic_threshold"
    if workout_type == "hm_intro_fartlek_hills":
        return "hill_repeats" if ("坡" in combined or "hill" in combined.lower()) else "fartlek"
    if workout_type in {"hm_90_support_endurance", "hm_95_long_fast_run"}:
        return "long_run" if "长距离" in combined or workout_type == "hm_95_long_fast_run" else "progression_run"
    if workout_type in {"hm_100_float_intervals", "hm_105_specific_speed"}:
        return "interval_run"
    if workout_type == "hm_110_support_speed":
        if "坡" in combined:
            return "hill_repeats"
        if "短冲" in combined or "加速" in combined:
            return "strides"
        return "fartlek"
    return workout_type


def _build_hmp_action_library_execution_card(
    workout_type: str,
    training_type: str,
    main_set: str,
    day_label: str,
) -> Dict[str, Any]:
    action_workout_type = _action_library_type_for_hmp_protocol(workout_type, training_type, main_set)
    hits = get_action_library_foundation_hits(action_workout_type)
    card = build_daily_workout_template_card_from_hits(
        workout_type=action_workout_type,
        day=day_label,
        hits=hits,
    )
    if card.get("evidence_tier") != "action_library":
        return {}
    if not any(str(item or "").strip() for item in (card.get("main_set_candidates") or [])):
        return {}
    card["protocol_workout_type"] = workout_type
    return card


def _first_evidence(card: Dict[str, Any]) -> Dict[str, Any]:
    evidence = card.get("evidence") or []
    if evidence and isinstance(evidence[0], dict):
        return evidence[0]
    return {}


def _source_record(
    *,
    value: Any,
    source_type: str,
    source_id: str = "",
    page: Any = None,
    chunk_id: str = "",
    confidence: str = "verified",
    note: str = "",
) -> Dict[str, Any]:
    return {
        "value": value,
        "source_type": source_type,
        "source_id": source_id,
        "page": page,
        "chunk_id": chunk_id,
        "confidence": confidence,
        "note": note,
    }


def _primary_source_from_card(card: Dict[str, Any], fallback_sources: Optional[List[str]] = None) -> Dict[str, Any]:
    evidence = _first_evidence(card)
    if evidence:
        return {
            "source_id": str(evidence.get("source_file") or ""),
            "page": evidence.get("page"),
            "chunk_id": str(evidence.get("chunk_id") or ""),
        }
    source_labels = fallback_sources or card.get("source") or []
    source_id = str(source_labels[0]) if source_labels else ""
    return {"source_id": source_id, "page": None, "chunk_id": ""}


def _field_status(card: Dict[str, Any], key: str) -> str:
    status = card.get("evidence_status") or {}
    return str(status.get(key) or "").strip()


def _source_type_for_tier(evidence_tier: str) -> str:
    return SOURCE_TYPE_BY_EVIDENCE_TIER.get(str(evidence_tier or ""), "needs_evidence")


def _normalize_load_bias(*values: Any) -> str:
    text = " ".join(str(value or "") for value in values).lower()
    if any(keyword in text for keyword in ("高", "峰", "强化", "冲刺", "peak", "high", "upper", "build")):
        return "high"
    if any(keyword in text for keyword in ("低", "减量", "恢复", "轻", "low", "deload", "recovery", "lower")):
        return "low"
    if any(keyword in text for keyword in ("中", "稳", "medium", "mid", "normal", "stable")):
        return "medium"
    return "medium"


def _load_bias_for_day(day: Dict[str, Any], raw_week: Dict[str, Any]) -> str:
    return _normalize_load_bias(
        day.get("load_level"),
        day.get("target_load_level"),
        day.get("load_bias"),
        raw_week.get("load_level"),
        raw_week.get("load_target"),
        raw_week.get("week_goal"),
    )


def _resolve_repetition_range_candidate(candidate_text: str, load_bias: str) -> Tuple[str, Dict[str, Any]]:
    text = str(candidate_text or "").strip()
    if not text:
        return text, {}

    match = re.search(
        r"(?P<lower>\d{1,2})\s*[-~至到]\s*(?P<upper>\d{1,2})\s*(?:组\s*)?(?:[×xX*]\s*)?(?P<unit>\d{2,5}(?:\.\d+)?)(?P<suffix>\s*(?:m|米|km|公里)?)",
        text,
    )
    if not match:
        return text, {}

    lower = int(float(match.group("lower")))
    upper = int(float(match.group("upper")))
    if lower <= 0 or upper <= lower:
        return text, {}

    if load_bias == "high":
        selected = upper
    elif load_bias == "low":
        selected = lower
    else:
        selected = int(round((lower + upper) / 2))
    selected = max(lower, min(upper, selected))

    unit_text = match.group("unit")
    suffix = (match.group("suffix") or "").strip()
    if not suffix and float(unit_text) >= 100:
        suffix = "m"
    selected_block = f"{selected}×{unit_text}{suffix}"
    resolved = f"{text[:match.start()]}{selected_block}{text[match.end():]}"
    resolved = resolved.replace(" / ", "，组间").replace("/", "，组间")
    resolved = re.sub(r"\s+", " ", resolved).strip()
    resolved = re.sub(r"\s*，\s*", "，", resolved)

    selection = {
        "source_type": "action_library",
        "original": text,
        "selected": resolved,
        "load_bias": load_bias,
        "range_lower": lower,
        "range_upper": upper,
        "selected_repetition_count": selected,
        "decision_reason": "依据本周目标负荷在动作库给定范围内选择具体组数。",
    }
    return resolved, selection


def _build_action_match(workout_type: str, card: Dict[str, Any], evidence_tier: str) -> Dict[str, Any]:
    execution_card = card.get("execution_action_card")
    if evidence_tier == "protocol_rule" and isinstance(execution_card, dict) and execution_card:
        action_workout_type = str(execution_card.get("workout_type") or "")
        match = _build_action_match(action_workout_type, execution_card, "action_library")
        if match:
            match["protocol_workout_type"] = workout_type
            match["selection_reason"] = "protocol_intent_projected_to_action_library"
        return match
    if evidence_tier != "action_library":
        return {}
    candidates = [
        str(item or "").strip()
        for item in (card.get("main_set_candidates") or [])
        if str(item or "").strip()
    ]
    if not candidates:
        return {
            "workout_type": workout_type,
            "action_id": "",
            "source": "",
            "page": None,
            "main_set": "",
            "alternatives": [],
            "needs_evidence": ["missing_action_library_match"],
        }
    source = _primary_source_from_card(card)
    prefix = ACTION_ID_PREFIX.get(workout_type, "ACT")
    page = source.get("page")
    suffix = f"{int(page):03d}" if isinstance(page, int) else "001"
    selected_main_set = str(card.get("selected_main_set") or "").strip()
    prescription_selection = card.get("prescription_selection") if isinstance(card.get("prescription_selection"), dict) else {}
    match_payload = {
        "workout_type": workout_type,
        "action_id": f"{prefix}-{suffix}",
        "source": source.get("source_id", ""),
        "page": page,
        "chunk_id": source.get("chunk_id", ""),
        "main_set": selected_main_set or candidates[0],
        "alternatives": candidates[1:4],
    }
    if prescription_selection:
        match_payload["prescription_selection"] = prescription_selection
    return match_payload


def _capacity_budget_for_week(
    structured_training_plan: Dict[str, Any],
    raw_week: Dict[str, Any],
) -> Dict[str, Any]:
    direct = raw_week.get("capacity_budget")
    if isinstance(direct, dict) and direct:
        return direct
    protocol = structured_training_plan.get("half_marathon_protocol") or {}
    if not isinstance(protocol, dict):
        return {}
    week_index = int(raw_week.get("week_index") or 0)
    for decision in protocol.get("weekly_decisions") or []:
        if not isinstance(decision, dict):
            continue
        if int(decision.get("week_index") or 0) == week_index:
            budget = decision.get("capacity_budget")
            if isinstance(budget, dict):
                return budget
    budget = protocol.get("capacity_budget")
    return budget if isinstance(budget, dict) else {}


def _is_quality_workout_type(workout_type: str) -> bool:
    return str(workout_type or "") in QUALITY_WORKOUT_TYPES


def _estimate_week_quality_count(raw_week: Dict[str, Any]) -> int:
    count = 0
    for item in raw_week.get("days") or []:
        if not isinstance(item, dict):
            continue
        workout_type = normalize_workout_type_for_template(
            training_type=str(item.get("training_type") or ""),
            main_set=str(item.get("main_set") or ""),
        )
        if _is_quality_workout_type(workout_type):
            count += 1
    return count


def _build_protocol_check(
    *,
    structured_training_plan: Dict[str, Any],
    raw_week: Dict[str, Any],
    workout_type: str,
    phase: str,
    main_km: float,
) -> Dict[str, Any]:
    budget = _capacity_budget_for_week(structured_training_plan, raw_week)
    quality_count = _estimate_week_quality_count(raw_week)
    quality_cap = int(budget.get("quality_sessions_max") or 2)
    long_run_cap = float(budget.get("long_run_max_km") or 18.0)
    violations: List[str] = []
    if quality_count > quality_cap:
        violations.append("quality_sessions_exceed_cap")
    if workout_type in {"long_run", "hm_95_long_fast_run", "hm_90_support_endurance"} and main_km > long_run_cap > 0:
        violations.append("long_run_exceed_cap")
    active = bool((structured_training_plan.get("half_marathon_protocol") or {}).get("active"))
    return {
        "allowed": not violations,
        "phase": phase,
        "quality_sessions_this_week": quality_count,
        "quality_session_cap": quality_cap,
        "long_run_cap_km": long_run_cap,
        "weekly_volume_km": budget.get("weekly_volume_km"),
        "effective_weekly_volume_km": budget.get("effective_weekly_volume_km"),
        "recent_four_week_mileage_km": budget.get("recent_four_week_mileage_km"),
        "volume_basis": budget.get("volume_basis", "planned_weekly_volume"),
        "violations": violations,
        "decision_reason": "协议容量检查通过" if not violations else "协议容量检查发现超限",
        "protocol_active": active,
    }


def _max_distance_km_from_text(value: Any) -> float:
    distances = [
        float(raw)
        for raw in re.findall(r"(\d+(?:\.\d+)?)\s*(?:km|公里)", str(value or ""), flags=re.IGNORECASE)
    ]
    distances.extend(
        float(raw) * 1.60934
        for raw in re.findall(r"(\d+(?:\.\d+)?)\s*英里", str(value or ""))
    )
    return max(distances) if distances else 0.0


def _has_explicit_duration_or_distance(value: Any) -> bool:
    text = str(value or "")
    return bool(re.search(r"\d+\s*(?:分钟|分|min|mins|minute|minutes|km|公里|英里)", text, flags=re.IGNORECASE))


def _append_protocol_violation(protocol_check: Dict[str, Any], violation: str) -> None:
    violations = protocol_check.setdefault("violations", [])
    if violation not in violations:
        violations.append(violation)
    protocol_check["allowed"] = False
    protocol_check["decision_reason"] = "协议容量检查发现超限"


def _apply_final_card_load_guards(
    *,
    day: Dict[str, Any],
    workout_type: str,
    main_set: str,
    protocol_check: Dict[str, Any],
    raw_load_estimate: Any,
    zone_range: str,
    zone_label: str,
    intensity_target: str,
) -> Any:
    load_estimate = raw_load_estimate
    long_endurance_workout = workout_type in {
        "long_run",
        "hm_90_support_endurance",
        "hm_95_long_fast_run",
    }

    final_main_km = _max_distance_km_from_text(main_set)
    long_run_cap = float(protocol_check.get("long_run_cap_km") or 0)
    if long_endurance_workout and final_main_km > long_run_cap > 0:
        _append_protocol_violation(protocol_check, "long_run_exceed_cap")

    if long_endurance_workout and _has_explicit_duration_or_distance(main_set):
        final_main_duration = infer_duration_min({"main_set": main_set}, workout_type=workout_type)
        raw_duration = int(getattr(raw_load_estimate, "duration_min", 0) or 0)
        if final_main_duration > 0 and raw_duration > max(final_main_duration + 25, int(round(final_main_duration * 1.35))):
            adjusted_day = {**day, "duration_min": final_main_duration, "main_set": main_set}
            load_estimate = calculate_plan_training_load(
                adjusted_day,
                workout_type=workout_type,
                zone_range=zone_range,
                zone_label=zone_label,
                intensity_target=intensity_target,
            )
            load_estimate.factors["raw_duration_min"] = raw_duration
            load_estimate.factors["duration_adjustment"] = "final_main_set_duration"
            load_estimate.factors["duration_guard"] = "main_set_overrode_inconsistent_allocated_distance"
            _append_protocol_violation(protocol_check, "duration_main_set_mismatch")

    return load_estimate


def _build_kb_fallback_trace(
    fallback: Optional[Dict[str, Any]],
    supplemented_fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    if not fallback:
        return {
            "used": False,
            "allowed_fields": sorted(NON_CORE_KB_FIELDS),
            "blocked_core_fields": sorted(CORE_PRESCRIPTION_FIELDS),
        }
    return {
        "used": True,
        "source": fallback.get("source", []),
        "allowed_fields": sorted(NON_CORE_KB_FIELDS),
        "supplemented_fields": supplemented_fields or [],
        "blocked_core_fields": sorted(CORE_PRESCRIPTION_FIELDS),
        "blocked_core_candidates": fallback.get("blocked_core_candidates", {}),
        "evidence_text_snippet": fallback.get("evidence_text_snippet", ""),
    }


def _default_risk_gate() -> Dict[str, Any]:
    return {
        "status": "not_evaluated",
        "risk_level": "unknown",
        "triggers": [],
        "adjustment_action": "none",
    }


def _status_for_card(
    evidence_tier: str,
    is_rest: bool = False,
    protocol_check: Optional[Dict[str, Any]] = None,
) -> str:
    if is_rest:
        return "generated"
    if isinstance(protocol_check, dict) and protocol_check.get("allowed") is False:
        return "needs_protocol_recheck"
    if evidence_tier in {"action_library", "protocol_rule"}:
        return "generated"
    if evidence_tier == "kb_fallback":
        return "partial_generated"
    if evidence_tier == "needs_evidence":
        return "needs_evidence"
    return "needs_evidence"


def _build_field_sources(
    *,
    workout_type: str,
    evidence_tier: str,
    card: Dict[str, Any],
    source: List[str],
    main_set: str,
    intensity_target: str,
    duration_min: int,
    protocol_check: Dict[str, Any],
    warmup: str,
    cooldown: str,
    alternative: str,
    training_objective: str,
    kb_supplemented_fields: List[str],
) -> Dict[str, Any]:
    source_type = _source_type_for_tier(evidence_tier)
    confidence = "verified" if source_type in {"protocol", "action_library"} else "needs_review"
    primary = _primary_source_from_card(card, source)
    execution_card = card.get("execution_action_card")
    main_set_primary = primary
    main_set_source_type = source_type
    if evidence_tier == "protocol_rule" and isinstance(execution_card, dict) and execution_card:
        main_set_primary = _primary_source_from_card(execution_card, execution_card.get("source") or [])
        main_set_source_type = "action_library"
    needs = _source_record(
        value="",
        source_type="needs_evidence",
        confidence="missing",
        note="critical_prescription_requires_protocol_or_action_library",
    )
    field_sources = {
        "workout_type": _source_record(
            value=workout_type,
            source_type=source_type if source_type in {"protocol", "action_library"} else "needs_evidence",
            confidence=confidence if source_type in {"protocol", "action_library"} else "missing",
            **primary,
        ),
        "main_set": _source_record(
            value=main_set,
            source_type=main_set_source_type if main_set_source_type in {"protocol", "action_library"} else "needs_evidence",
            confidence="verified" if main_set_source_type in {"protocol", "action_library"} else "missing",
            **main_set_primary,
        ),
        "intensity": _source_record(
            value=intensity_target,
            source_type=source_type if source_type in {"protocol", "action_library"} else "needs_evidence",
            confidence=confidence if source_type in {"protocol", "action_library"} else "missing",
            **primary,
        ),
        "duration": _source_record(
            value=duration_min,
            source_type="protocol" if protocol_check else "needs_evidence",
            confidence="verified" if protocol_check else "missing",
            source_id="training_load_estimator",
            note="duration is deterministic estimate from structured plan fields",
        ),
        "weekly_quality_count": _source_record(
            value=protocol_check.get("quality_sessions_this_week"),
            source_type="protocol",
            confidence="verified",
            source_id="protocol_check",
        ),
        "long_run_cap": _source_record(
            value=protocol_check.get("long_run_cap_km"),
            source_type="protocol",
            confidence="verified",
            source_id="protocol_check",
        ),
        "progression": _source_record(
            value="",
            source_type="protocol",
            confidence="needs_review",
            source_id="structured_training_plan.week_plans",
        ),
        "risk_downgrade": _source_record(
            value="",
            source_type="protocol",
            confidence="needs_review",
            source_id="risk_gate",
        ),
    }
    for key, value, status_key in [
        ("warmup", warmup, "warmup_suggestion"),
        ("cooldown", cooldown, "cooldown"),
        ("alternative", alternative, "alternative_workout"),
        ("training_objective", training_objective, "training_objective"),
    ]:
        if key in kb_supplemented_fields:
            field_sources[key] = _source_record(
                value=value,
                source_type="kb_fallback",
                confidence="supporting",
                source_id=(source[-1] if source else ""),
            )
        elif _field_status(card, status_key) in {"direct", "protocol"} and value:
            field_sources[key] = _source_record(
                value=value,
                source_type=source_type,
                confidence=confidence,
                **primary,
            )
        elif value:
            field_sources[key] = _source_record(
                value=value,
                source_type="llm_expression" if key in {"training_objective", "alternative"} else "needs_evidence",
                confidence="unverified" if key in {"training_objective", "alternative"} else "missing",
                note="non_core_expression_or_missing_execution_evidence",
            )
        else:
            field_sources[key] = dict(needs)
    return field_sources


def _build_trace(
    *,
    training_type_raw: str,
    main_set_raw: str,
    workout_type: str,
    protocol_check: Dict[str, Any],
    action_match: Dict[str, Any],
    kb_fallback_trace: Dict[str, Any],
    risk_gate: Dict[str, Any],
    final_card: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "intent_parse": {
            "training_type_raw": training_type_raw,
            "main_set_raw": main_set_raw,
            "resolved_workout_type": workout_type,
        },
        "protocol_check": protocol_check,
        "action_match": action_match,
        "kb_fallback": kb_fallback_trace,
        "risk_gate": risk_gate,
        "final_card": final_card,
    }


def _resolve_evidence_backed_main_set(
    *,
    evidence_tier: str,
    main_set_display: str,
    card: Dict[str, Any],
    training_type: str,
    notes: str,
    load_bias: str = "medium",
) -> Tuple[str, str]:
    execution_card = card.get("execution_action_card")
    if evidence_tier == "protocol_rule" and isinstance(execution_card, dict) and execution_card:
        action_candidates = [
            str(item or "").strip()
            for item in (execution_card.get("main_set_candidates") or [])
            if str(item or "").strip()
        ]
        if action_candidates:
            selected, selection = _resolve_repetition_range_candidate(action_candidates[0], load_bias)
            selected = sanitize_all_pace(selected)
            execution_card["selected_main_set"] = selected
            if selection:
                selection["selected"] = selected
                execution_card["prescription_selection"] = selection
            return selected, evidence_tier
        no_evidence = _build_no_evidence_training_card(training_type, notes)
        return no_evidence["main_set"], "needs_evidence"

    candidates = [
        str(item or "").strip()
        for item in (card.get("main_set_candidates") or [])
        if str(item or "").strip()
    ]
    candidate_text = candidates[0] if candidates else ""
    if evidence_tier == "protocol_rule":
        no_evidence = _build_no_evidence_training_card(training_type, notes)
        return no_evidence["main_set"], "needs_evidence"
    if evidence_tier == "action_library" and candidate_text:
        selected, selection = _resolve_repetition_range_candidate(candidate_text, load_bias)
        selected = sanitize_all_pace(selected)
        card["selected_main_set"] = selected
        if selection:
            selection["selected"] = selected
            card["prescription_selection"] = selection
        return selected, evidence_tier
    no_evidence = _build_no_evidence_training_card(training_type, notes)
    return no_evidence["main_set"], "needs_evidence"


def generate_daily_schedule(
    structured_training_plan: Dict[str, Any],
    *,
    enable_kb_fallback: bool = True,
) -> MonthlyTrainingCalendar:
    if not isinstance(structured_training_plan, dict):
        return MonthlyTrainingCalendar(year=2026, month=1, start_week_index=0, end_week_index=0, total_days=0)

    plan_meta = structured_training_plan.get("plan_meta", {}) or {}
    week_plans = structured_training_plan.get("week_plans", []) or []
    phase_summary = structured_training_plan.get("phase_summary", []) or []

    if not week_plans:
        return MonthlyTrainingCalendar(year=2026, month=1, start_week_index=0, end_week_index=0, total_days=0)

    first_week_idx = 1
    for week in week_plans:
        if isinstance(week, dict):
            first_week_idx = int(week.get("week_index") or 1)
            break

    start_week_index = first_week_idx
    end_week_index = 0
    days: List[DailyScheduleItem] = []
    global_day_index = 0
    kb_fallback_cache: Dict[str, Optional[Dict[str, Any]]] = {}

    for raw_week in week_plans:
        if not isinstance(raw_week, dict):
            continue
        week_index = int(raw_week.get("week_index") or len(days) + 1)
        end_week_index = max(end_week_index, week_index)
        phase = str(raw_week.get("phase") or "").strip()
        week_days = raw_week.get("days", []) or []
        if not isinstance(week_days, list):
            continue
        hm_week_candidate_ids = _hm_protocol_candidate_ids_for_week(structured_training_plan, raw_week)
        hm_week_candidate_cursor = 0

        for day in week_days:
            if not isinstance(day, dict):
                continue
            global_day_index += 1
            day_label = str(day.get("day") or "").strip()
            training_type_raw = str(day.get("training_type") or "").strip()
            main_set_raw = str(day.get("main_set") or "").strip()
            main_set_display = _strip_workout_id_prefix(main_set_raw)

            is_rest = training_type_raw in ("休息", "Rest", "恢复日")
            if not day_label:
                day_label = f"第{global_day_index}天"

            if is_rest:
                protocol_check = _build_protocol_check(
                    structured_training_plan=structured_training_plan,
                    raw_week=raw_week,
                    workout_type="",
                    phase=phase,
                    main_km=0.0,
                )
                protocol_check["allowed"] = True
                protocol_check["violations"] = []
                protocol_check["decision_reason"] = "休息日不消耗质量课或长跑容量，不因同周训练日违规而进入复核状态。"
                risk_gate = _default_risk_gate()
                kb_trace = _build_kb_fallback_trace(None)
                final_card = {"card_status": "generated", "evidence_tier": "plan_only", "is_rest": True}
                trace = _build_trace(
                    training_type_raw=training_type_raw,
                    main_set_raw=main_set_raw,
                    workout_type="",
                    protocol_check=protocol_check,
                    action_match={},
                    kb_fallback_trace=kb_trace,
                    risk_gate=risk_gate,
                    final_card=final_card,
                )
                days.append(DailyScheduleItem(
                    date=f"第{week_index}周{day_label}",
                    day_label=day_label,
                    week_index=week_index,
                    day_index=global_day_index,
                    phase=phase,
                    training_type="休息",
                    training_type_label="休息",
                    workout_type="",
                    zone_range="",
                    zone_label="",
                    intensity_target="",
                    main_set="",
                    warmup="",
                    cooldown="",
                    alternative="",
                    training_objective="主动恢复，充分休息",
                    evidence_tier="plan_only",
                    evidence_tier_label=EVIDENCE_TIER_LABELS["plan_only"],
                    is_rest=True,
                    notes=str(day.get("notes") or "").strip(),
                    duration_min=0,
                    training_load=0,
                    training_load_method="rest_day",
                    training_load_factors={"source": "rest day"},
                    card_status="generated",
                    field_sources={
                        "workout_type": _source_record(value="", source_type="protocol", source_id="structured_training_plan", confidence="verified"),
                        "main_set": _source_record(value="", source_type="protocol", source_id="structured_training_plan", confidence="verified"),
                        "intensity": _source_record(value="", source_type="protocol", source_id="structured_training_plan", confidence="verified"),
                        "duration": _source_record(value=0, source_type="protocol", source_id="structured_training_plan", confidence="verified"),
                        "weekly_quality_count": _source_record(value=protocol_check.get("quality_sessions_this_week"), source_type="protocol", source_id="protocol_check", confidence="verified"),
                        "long_run_cap": _source_record(value=protocol_check.get("long_run_cap_km"), source_type="protocol", source_id="protocol_check", confidence="verified"),
                        "progression": _source_record(value="", source_type="protocol", source_id="structured_training_plan", confidence="verified"),
                        "risk_downgrade": _source_record(value="", source_type="protocol", source_id="risk_gate", confidence="needs_review"),
                    },
                    protocol_check=protocol_check,
                    action_match={},
                    kb_fallback=kb_trace,
                    risk_gate=risk_gate,
                    trace=trace,
                ))
                continue

            workout_type = normalize_workout_type_for_template(
                training_type=training_type_raw,
                main_set=main_set_raw,
            )
            if hm_week_candidate_ids and not _is_user_requested_workout_day(day):
                for candidate_offset in range(len(hm_week_candidate_ids)):
                    candidate_index = (hm_week_candidate_cursor + candidate_offset) % len(hm_week_candidate_ids)
                    candidate_id = hm_week_candidate_ids[candidate_index]
                    if _can_project_hmp_candidate_to_day(candidate_id, workout_type, training_type_raw, main_set_raw):
                        workout_type = candidate_id
                        hm_week_candidate_cursor = candidate_index + 1
                        break

            if not workout_type and training_type_raw:
                load_estimate = calculate_plan_training_load(
                    day,
                    workout_type="",
                    zone_range="",
                    zone_label="",
                    intensity_target=training_type_raw,
                )
                protocol_check = _build_protocol_check(
                    structured_training_plan=structured_training_plan,
                    raw_week=raw_week,
                    workout_type="",
                    phase=phase,
                    main_km=float(day.get("main_km") or 0),
                )
                risk_gate = _default_risk_gate()
                kb_trace = _build_kb_fallback_trace(None)
                final_card = {"card_status": "needs_evidence", "evidence_tier": "plan_only", "main_set": main_set_display}
                trace = _build_trace(
                    training_type_raw=training_type_raw,
                    main_set_raw=main_set_raw,
                    workout_type="",
                    protocol_check=protocol_check,
                    action_match={},
                    kb_fallback_trace=kb_trace,
                    risk_gate=risk_gate,
                    final_card=final_card,
                )
                days.append(DailyScheduleItem(
                    date=f"第{week_index}周{day_label}",
                    day_label=day_label,
                    week_index=week_index,
                    day_index=global_day_index,
                    phase=phase,
                    training_type=training_type_raw,
                    training_type_label=training_type_raw,
                    workout_type="",
                    zone_range="",
                    zone_label="",
                    intensity_target="",
                    main_set=main_set_display,
                    warmup=str(day.get("warmup") or "").strip(),
                    cooldown=str(day.get("cooldown") or "").strip(),
                    alternative="",
                    training_objective=str(day.get("notes") or "").strip(),
                    evidence_tier="plan_only",
                    evidence_tier_label=EVIDENCE_TIER_LABELS["plan_only"],
                    notes=str(day.get("notes") or "").strip(),
                    duration_min=load_estimate.duration_min,
                    training_load=load_estimate.training_load,
                    training_load_method=load_estimate.method,
                    training_load_factors=load_estimate.factors,
                    card_status="needs_evidence",
                    field_sources={
                        "workout_type": _source_record(value="", source_type="needs_evidence", confidence="missing", note="unknown_workout_type"),
                        "main_set": _source_record(value=main_set_display, source_type="needs_evidence", confidence="missing", note="critical_prescription_requires_protocol_or_action_library"),
                        "intensity": _source_record(value="", source_type="needs_evidence", confidence="missing"),
                        "duration": _source_record(value=load_estimate.duration_min, source_type="protocol", source_id="training_load_estimator", confidence="verified"),
                        "weekly_quality_count": _source_record(value=protocol_check.get("quality_sessions_this_week"), source_type="protocol", source_id="protocol_check", confidence="verified"),
                        "long_run_cap": _source_record(value=protocol_check.get("long_run_cap_km"), source_type="protocol", source_id="protocol_check", confidence="verified"),
                        "progression": _source_record(value="", source_type="needs_evidence", confidence="missing"),
                        "risk_downgrade": _source_record(value="", source_type="protocol", source_id="risk_gate", confidence="needs_review"),
                    },
                    protocol_check=protocol_check,
                    action_match={},
                    kb_fallback=kb_trace,
                    risk_gate=risk_gate,
                    trace=trace,
                ))
                continue

            registry_entry = WORKOUT_TEMPLATE_REGISTRY.get(workout_type, {})
            training_type_label = registry_entry.get("training_type_label", training_type_raw)
            zone_range = registry_entry.get("zone_range", "")
            intensity_target = registry_entry.get("intensity_target", "")

            foundation_hits = [] if workout_type in HMP_WORKOUT_TYPES else get_action_library_foundation_hits(workout_type)
            card = build_daily_workout_template_card_from_hits(
                workout_type=workout_type,
                day=day_label,
                hits=foundation_hits,
            )
            if workout_type in HMP_WORKOUT_TYPES:
                execution_card = _build_hmp_action_library_execution_card(
                    workout_type=workout_type,
                    training_type=training_type_raw,
                    main_set=main_set_display,
                    day_label=day_label,
                )
                if execution_card:
                    card["execution_action_card"] = execution_card

            evidence_tier = card.get("evidence_tier", "plan_only")
            evidence_tier_label = EVIDENCE_TIER_LABELS.get(evidence_tier, "基础计划")
            source = card.get("source", [])
            kb_fallback_payload: Optional[Dict[str, Any]] = None
            kb_supplemented_fields: List[str] = []

            if enable_kb_fallback and evidence_tier in ("plan_only", "") and workout_type and workout_type not in HMP_WORKOUT_TYPES:
                if workout_type not in kb_fallback_cache:
                    kb_hits, _ = _extract_kb_evidence_for_workout(workout_type)
                    filtered_hits = _filter_kb_evidence_hits(workout_type, kb_hits)
                    kb_fallback_cache[workout_type] = _try_generate_schedule_from_kb_llm(workout_type, filtered_hits)
                fallback = kb_fallback_cache.get(workout_type)
                if fallback:
                    kb_fallback_payload = fallback
                    evidence_tier = "kb_fallback"
                    evidence_tier_label = EVIDENCE_TIER_LABELS["kb_fallback"]
                    source = fallback.get("source", [])
                    intensity_target = fallback.get("intensity_target", intensity_target)
                    card["main_set_candidates"] = fallback.get("main_set_candidates", [])
                    card["training_objective"] = fallback.get("training_objective", card.get("training_objective", ""))
                    card["warmup_suggestion"] = fallback.get("warmup_suggestion", card.get("warmup_suggestion", ""))
                    card["cooldown_suggestion"] = fallback.get("cooldown_suggestion", card.get("cooldown_suggestion", ""))
                    card["alternative_workout"] = fallback.get("alternative_workout", card.get("alternative_workout", ""))
                elif evidence_tier not in ("action_library", "kb_fallback", "protocol_rule"):
                    evidence_tier = "plan_only"
                    evidence_tier_label = EVIDENCE_TIER_LABELS["plan_only"]
            elif enable_kb_fallback and evidence_tier == "action_library" and workout_type and workout_type not in HMP_WORKOUT_TYPES:
                missing_execution_fields = not card.get("cooldown_suggestion") or not card.get("warmup_suggestion")
                if missing_execution_fields:
                    if workout_type not in kb_fallback_cache:
                        kb_hits, _ = _extract_kb_evidence_for_workout(workout_type)
                        filtered_hits = _filter_kb_evidence_hits(workout_type, kb_hits)
                        kb_fallback_cache[workout_type] = _try_generate_schedule_from_kb_llm(workout_type, filtered_hits)
                    fallback = kb_fallback_cache.get(workout_type)
                    if fallback:
                        kb_fallback_payload = fallback
                        fallback_sources = fallback.get("source", [])
                        if fallback_sources:
                            source = list(dict.fromkeys([*source, *fallback_sources]))
                        if not card.get("warmup_suggestion") and fallback.get("warmup_suggestion"):
                            kb_supplemented_fields.append("warmup")
                            card["warmup_suggestion"] = fallback.get("warmup_suggestion", "")
                        if not card.get("cooldown_suggestion") and fallback.get("cooldown_suggestion"):
                            kb_supplemented_fields.append("cooldown")
                            card["cooldown_suggestion"] = fallback.get("cooldown_suggestion", "")

            zone_label = ZONE_LABELS.get(
                zone_range.replace("→", "-").split("-")[0] if zone_range else "",
                intensity_target,
            ) if zone_range else intensity_target

            warmup_km = float(day.get("warmup_km") or 0)
            main_km = float(day.get("main_km") or 0)
            cooldown_km = float(day.get("cooldown_km") or 0)
            protocol_check = _build_protocol_check(
                structured_training_plan=structured_training_plan,
                raw_week=raw_week,
                workout_type=workout_type,
                phase=phase,
                main_km=main_km,
            )
            if evidence_tier in {"action_library", "kb_fallback", "protocol_rule"}:
                warmup_text = sanitize_all_pace(str(card.get("warmup_suggestion") or "").strip())
                cooldown_text = sanitize_all_pace(str(card.get("cooldown_suggestion") or "").strip())
                if not warmup_text and evidence_tier == "protocol_rule":
                    warmup_text = sanitize_all_pace(str(day.get("warmup") or "").strip())
                if not cooldown_text and evidence_tier == "protocol_rule":
                    cooldown_text = sanitize_all_pace(str(day.get("cooldown") or "").strip())
                if evidence_tier != "protocol_rule":
                    missing = _build_no_evidence_training_card(training_type_raw, str(day.get("notes") or "").strip())
                    warmup_text = warmup_text or missing["warmup"]
                    cooldown_text = cooldown_text or missing["cooldown"]
            else:
                warmup_text = sanitize_all_pace(str(day.get("warmup") or card.get("warmup_suggestion") or "").strip())
                cooldown_text = sanitize_all_pace(str(day.get("cooldown") or card.get("cooldown_suggestion") or "").strip())
            if evidence_tier == "plan_only" and workout_type not in HMP_WORKOUT_TYPES:
                no_evidence = _build_no_evidence_training_card(training_type_raw, str(day.get("notes") or "").strip())
                evidence_tier = no_evidence["evidence_tier"]
                evidence_tier_label = no_evidence["evidence_tier_label"]
                card["main_set_candidates"] = []
                card["training_objective"] = no_evidence["training_objective"]
                card["warmup_suggestion"] = no_evidence["warmup"]
                card["cooldown_suggestion"] = no_evidence["cooldown"]
                card["alternative_workout"] = no_evidence["alternative_workout"]
                source = []
                warmup_text = no_evidence["warmup"]
                cooldown_text = no_evidence["cooldown"]
            if warmup_text and warmup_km > 0 and evidence_tier != "needs_evidence":
                warmup_text = f"{warmup_text} ({warmup_km:.1f}km)"
            if cooldown_text and cooldown_km > 0 and evidence_tier != "needs_evidence":
                cooldown_text = f"{cooldown_text} ({cooldown_km:.1f}km)"

            main_set_clean, resolved_evidence_tier = _resolve_evidence_backed_main_set(
                evidence_tier=evidence_tier,
                main_set_display=main_set_display,
                card=card,
                training_type=training_type_raw,
                notes=str(day.get("notes") or "").strip(),
                load_bias=_load_bias_for_day(day, raw_week),
            )
            if resolved_evidence_tier != evidence_tier:
                no_evidence = _build_no_evidence_training_card(training_type_raw, str(day.get("notes") or "").strip())
                evidence_tier = resolved_evidence_tier
                evidence_tier_label = EVIDENCE_TIER_LABELS["needs_evidence"]
                source = []
                card["training_objective"] = no_evidence["training_objective"]
                card["alternative_workout"] = no_evidence["alternative_workout"]
                warmup_text = no_evidence["warmup"]
                cooldown_text = no_evidence["cooldown"]
            raw_load_estimate = calculate_plan_training_load(
                day,
                workout_type=workout_type,
                zone_range=zone_range,
                zone_label=zone_label,
                intensity_target=intensity_target,
            )
            load_estimate = _apply_final_card_load_guards(
                day=day,
                workout_type=workout_type,
                main_set=main_set_clean,
                protocol_check=protocol_check,
                raw_load_estimate=raw_load_estimate,
                zone_range=zone_range,
                zone_label=zone_label,
                intensity_target=intensity_target,
            )
            action_match = _build_action_match(workout_type, card, evidence_tier)
            prescription_selection = action_match.get("prescription_selection")
            if isinstance(prescription_selection, dict):
                prescription_selection["estimated_duration_min"] = load_estimate.duration_min
                prescription_selection["estimated_training_load"] = load_estimate.training_load
            kb_fallback_trace = _build_kb_fallback_trace(kb_fallback_payload, kb_supplemented_fields)
            risk_gate = _default_risk_gate()
            alternative_text = sanitize_all_pace(str(day.get("alternative") or card.get("alternative_workout") or "").strip())
            training_objective_text = _merge_objective_text(
                str(day.get("notes") or ""),
                str(card.get("training_objective") or ""),
            )
            kb_metadata = dict(card.get("kb_metadata") or {})
            if not kb_metadata:
                kb_metadata = {
                    "knowledge_layer": "prescription_library",
                    "evidence_domain": "protocol" if evidence_tier == "protocol_rule" else evidence_tier,
                    "retrieval_mode": "protocol_rule" if evidence_tier == "protocol_rule" else "none",
                    "prescription_permission": "can_write_core" if evidence_tier in {"action_library", "protocol_rule"} else "blocked_needs_evidence",
                }
            if evidence_tier not in {"action_library", "protocol_rule"}:
                kb_metadata["prescription_permission"] = "blocked_needs_evidence"
            card_status = _status_for_card(evidence_tier, protocol_check=protocol_check)
            final_card = {
                "card_status": card_status,
                "evidence_tier": evidence_tier,
                "workout_type": workout_type,
                "main_set": main_set_clean,
                "intensity_target": intensity_target,
                "duration_min": load_estimate.duration_min,
            }
            field_sources = _build_field_sources(
                workout_type=workout_type,
                evidence_tier=evidence_tier,
                card=card,
                source=source,
                main_set=main_set_clean,
                intensity_target=intensity_target,
                duration_min=load_estimate.duration_min,
                protocol_check=protocol_check,
                warmup=warmup_text,
                cooldown=cooldown_text,
                alternative=alternative_text,
                training_objective=training_objective_text,
                kb_supplemented_fields=kb_supplemented_fields,
            )
            trace = _build_trace(
                training_type_raw=training_type_raw,
                main_set_raw=main_set_raw,
                workout_type=workout_type,
                protocol_check=protocol_check,
                action_match=action_match,
                kb_fallback_trace=kb_fallback_trace,
                risk_gate=risk_gate,
                final_card=final_card,
            )
            days.append(DailyScheduleItem(
                date=f"第{week_index}周{day_label}",
                day_label=day_label,
                week_index=week_index,
                day_index=global_day_index,
                phase=phase,
                training_type=training_type_raw,
                training_type_label=training_type_label,
                workout_type=workout_type,
                zone_range=zone_range,
                zone_label=zone_label,
                intensity_target=intensity_target,
                main_set=main_set_clean,
                warmup=warmup_text,
                cooldown=cooldown_text,
                alternative=alternative_text,
                training_objective=training_objective_text,
                evidence_tier=evidence_tier,
                evidence_tier_label=evidence_tier_label,
                source=source,
                evidence_ids=[int(i) for i in (card.get("evidence_ids") or []) if str(i).isdigit()],
                notes=str(day.get("notes") or "").strip(),
                duration_min=load_estimate.duration_min,
                training_load=load_estimate.training_load,
                training_load_method=load_estimate.method,
                training_load_factors=load_estimate.factors,
                card_status=card_status,
                field_sources=field_sources,
                protocol_check=protocol_check,
                action_match=action_match,
                kb_fallback=kb_fallback_trace,
                risk_gate=risk_gate,
                kb_metadata=kb_metadata,
                trace=trace,
            ))

    total_days = len(days)
    evidence_summary = {key: 0 for key in EVIDENCE_TIER_LABELS}
    for d in days:
        evidence_summary[d.evidence_tier] = evidence_summary.get(d.evidence_tier, 0) + 1

    normalized_phases = []
    for item in phase_summary:
        if not isinstance(item, dict):
            continue
        normalized_phases.append({
            "phase": str(item.get("phase") or "").strip(),
            "start_week": int(item.get("start_week") or 0),
            "end_week": int(item.get("end_week") or 0),
            "objective": str(item.get("objective") or "").strip(),
        })

    return MonthlyTrainingCalendar(
        year=2026,
        month=5,
        start_week_index=start_week_index,
        end_week_index=end_week_index,
        total_days=total_days,
        days=days,
        phases=normalized_phases,
        evidence_summary=evidence_summary,
        training_load_summary=build_training_load_summary(days),
    )
