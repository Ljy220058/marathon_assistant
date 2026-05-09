from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from marathon_qa_assistant.services.workout_template_retriever import (
    WORKOUT_TEMPLATE_REGISTRY,
    ZONE_LABELS,
    ZONE_LABELS_DETAIL,
    EVIDENCE_TIER_LABELS,
    build_daily_workout_template_card_from_hits,
    normalize_workout_type_for_template,
    _select_relevant_action_library_hits,
)
from marathon_qa_assistant.services.vector_store import load_vector_kb, retrieve
from marathon_qa_assistant.core.app_state import get_preferred_vector_dir, has_vector_kb_artifacts
from marathon_qa_assistant.core.zone_constants import sanitize_all_pace
from marathon_qa_assistant.services.training_load import (
    build_training_load_summary,
    calculate_plan_training_load,
)

HMP_WORKOUT_TYPES = {
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

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


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
        "training_objective": f"基于{display_name}的通用训练原则生成（参考知识库证据）",
        "warmup_suggestion": "15-20分钟轻松跑 + 动态拉伸",
        "cooldown_suggestion": "10-15分钟慢跑 + 静态拉伸",
        "alternative_workout": "",
    }


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

    if candidate_id in {"hm_90_support_endurance", "hm_95_long_fast_run"}:
        return workout_type in HMP_LONG_ENDURANCE_TYPES
    if candidate_id in {"hm_100_float_intervals", "hm_105_specific_speed", "hm_110_support_speed"}:
        return workout_type in HMP_SPEED_TYPES
    return False


def _merge_objective_text(*values: str) -> str:
    parts = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in parts:
            parts.append(text)
    return "；".join(parts)


def generate_daily_schedule(
    structured_training_plan: Dict[str, Any],
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

            is_rest = training_type_raw in ("休息", "Rest", "恢复日")
            if not day_label:
                day_label = f"第{global_day_index}天"

            if is_rest:
                days.append(DailyScheduleItem(
                    date=f"第{week_index}周{day_label}",
                    day_label=day_label,
                    week_index=week_index,
                    day_index=global_day_index,
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
                ))
                continue

            workout_type = normalize_workout_type_for_template(
                training_type=training_type_raw,
                main_set=main_set_raw,
            )
            if hm_week_candidate_ids:
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
                days.append(DailyScheduleItem(
                    date=f"第{week_index}周{day_label}",
                    day_label=day_label,
                    week_index=week_index,
                    day_index=global_day_index,
                    training_type=training_type_raw,
                    training_type_label=training_type_raw,
                    workout_type="",
                    zone_range="",
                    zone_label="",
                    intensity_target="",
                    main_set=main_set_raw,
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
                ))
                continue

            registry_entry = WORKOUT_TEMPLATE_REGISTRY.get(workout_type, {})
            training_type_label = registry_entry.get("training_type_label", training_type_raw)
            zone_range = registry_entry.get("zone_range", "")
            intensity_target = registry_entry.get("intensity_target", "")

            card = build_daily_workout_template_card_from_hits(
                workout_type=workout_type,
                day=day_label,
                hits=[],
            )

            evidence_tier = card.get("evidence_tier", "plan_only")
            evidence_tier_label = EVIDENCE_TIER_LABELS.get(evidence_tier, "基础计划")
            source = card.get("source", [])

            if evidence_tier in ("plan_only", "") and workout_type and workout_type not in HMP_WORKOUT_TYPES:
                kb_hits, _ = _extract_kb_evidence_for_workout(workout_type)
                filtered_hits = _filter_kb_evidence_hits(workout_type, kb_hits)
                fallback = _try_generate_schedule_from_kb_llm(workout_type, filtered_hits)
                if fallback:
                    evidence_tier = "kb_fallback"
                    evidence_tier_label = EVIDENCE_TIER_LABELS["kb_fallback"]
                    source = fallback.get("source", [])
                    intensity_target = fallback.get("intensity_target", intensity_target)
                    card["main_set_candidates"] = fallback.get("main_set_candidates", [])
                    card["training_objective"] = fallback.get("training_objective", card.get("training_objective", ""))
                    card["warmup_suggestion"] = fallback.get("warmup_suggestion", card.get("warmup_suggestion", ""))
                    card["cooldown_suggestion"] = fallback.get("cooldown_suggestion", card.get("cooldown_suggestion", ""))
                    card["alternative_workout"] = fallback.get("alternative_workout", card.get("alternative_workout", ""))
                elif evidence_tier not in ("action_library", "kb_fallback"):
                    evidence_tier = "plan_only"
                    evidence_tier_label = EVIDENCE_TIER_LABELS["plan_only"]

            zone_label = ZONE_LABELS.get(
                zone_range.replace("→", "-").split("-")[0] if zone_range else "",
                intensity_target,
            ) if zone_range else intensity_target

            warmup_km = float(day.get("warmup_km") or 0)
            main_km = float(day.get("main_km") or 0)
            cooldown_km = float(day.get("cooldown_km") or 0)
            warmup_text = sanitize_all_pace(str(day.get("warmup") or card.get("warmup_suggestion") or "").strip())
            cooldown_text = sanitize_all_pace(str(day.get("cooldown") or card.get("cooldown_suggestion") or "").strip())
            if warmup_text and warmup_km > 0:
                warmup_text = f"{warmup_text} ({warmup_km:.1f}km)"
            if cooldown_text and cooldown_km > 0:
                cooldown_text = f"{cooldown_text} ({cooldown_km:.1f}km)"

            main_set_clean = sanitize_all_pace(main_set_raw or " / ".join(card.get("main_set_candidates", [])[:3]))
            load_estimate = calculate_plan_training_load(
                day,
                workout_type=workout_type,
                zone_range=zone_range,
                zone_label=zone_label,
                intensity_target=intensity_target,
            )
            days.append(DailyScheduleItem(
                date=f"第{week_index}周{day_label}",
                day_label=day_label,
                week_index=week_index,
                day_index=global_day_index,
                training_type=training_type_raw,
                training_type_label=training_type_label,
                workout_type=workout_type,
                zone_range=zone_range,
                zone_label=zone_label,
                intensity_target=intensity_target,
                main_set=main_set_clean,
                warmup=warmup_text,
                cooldown=cooldown_text,
                alternative=sanitize_all_pace(str(day.get("alternative") or card.get("alternative_workout") or "").strip()),
                training_objective=_merge_objective_text(
                    str(day.get("notes") or ""),
                    str(card.get("training_objective") or ""),
                ),
                evidence_tier=evidence_tier,
                evidence_tier_label=evidence_tier_label,
                source=source,
                evidence_ids=[int(i) for i in (card.get("evidence_ids") or []) if str(i).isdigit()],
                notes=str(day.get("notes") or "").strip(),
                duration_min=load_estimate.duration_min,
                training_load=load_estimate.training_load,
                training_load_method=load_estimate.method,
                training_load_factors=load_estimate.factors,
            ))

    total_days = len(days)
    evidence_summary = {"action_library": 0, "kb_fallback": 0, "plan_only": 0}
    for d in days:
        if d.evidence_tier in evidence_summary:
            evidence_summary[d.evidence_tier] += 1

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
