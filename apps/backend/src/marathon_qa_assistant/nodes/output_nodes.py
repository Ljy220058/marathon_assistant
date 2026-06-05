from typing import Any, Dict, List, Tuple

try:
    from langchain_core.runnables import RunnableConfig
except ImportError:
    RunnableConfig = Any

from marathon_qa_assistant.core.state_models import IntegratedState, build_workflow_trace
from marathon_qa_assistant.core.evidence_bundle import evidence_base_from_bundle
from marathon_qa_assistant.core.zone_constants import sanitize_all_pace
from marathon_qa_assistant.nodes.common import ensure_usage, output_guard_obj
from marathon_qa_assistant.services.workout_template_retriever import build_daily_workout_template_card_from_hits, normalize_workout_type_for_template
from marathon_qa_assistant.services.workout_template_retriever import EVIDENCE_TIER_LABELS as _EVIDENCE_TIER_LABELS
from marathon_qa_assistant.services.daily_schedule_generator import generate_daily_schedule
from marathon_qa_assistant.core.half_marathon_glossary import (
    evidence_basis_for_constraint,
    get_hmp_glossary_terms,
    term_ids_for_constraint,
    term_ids_for_phase,
    term_ids_for_workout,
)
from marathon_qa_assistant.core.half_marathon_protocol import HM_PHASE_RULES


def _safe_text(value: Any, fallback: str = "—") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _normalize_phase_summary(structured_training_plan: Any) -> List[Dict[str, Any]]:
    if not isinstance(structured_training_plan, dict):
        return []

    normalized: List[Dict[str, Any]] = []
    for item in structured_training_plan.get("phase_summary", []) or []:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "phase": _safe_text(item.get("phase")),
                "start_week": int(item.get("start_week") or 0),
                "end_week": int(item.get("end_week") or 0),
                "objective": _safe_text(item.get("objective")),
            }
        )
    return normalized


def _normalize_week_sections(structured_training_plan: Any) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if not isinstance(structured_training_plan, dict):
        return [], {}

    normalized: List[Dict[str, Any]] = []
    week_plans = structured_training_plan.get("week_plans", []) or []
    plan_meta = structured_training_plan.get("plan_meta", {}) or {}

    for fallback_index, week in enumerate(week_plans, start=1):
        if not isinstance(week, dict):
            continue

        days: List[Dict[str, Any]] = []
        for day in week.get("days", []) or []:
            if not isinstance(day, dict):
                continue
            days.append(
                {
                    "day": _safe_text(day.get("day")),
                    "training_type": _safe_text(day.get("training_type")),
                    "warmup": _safe_text(day.get("warmup")),
                    "main_set": _safe_text(day.get("main_set")),
                    "cooldown": _safe_text(day.get("cooldown")),
                    "venue": _safe_text(day.get("venue")),
                    "notes": _safe_text(day.get("notes"), fallback=""),
                }
            )

        repeat_guard = week.get("repeat_guard_signature", {}) or {}
        training_day_count = sum(1 for day in days if day["training_type"] != "休息")
        normalized.append(
            {
                "week_index": int(week.get("week_index") or fallback_index),
                "phase": _safe_text(week.get("phase")),
                "week_goal": _safe_text(week.get("week_goal")),
                "load_level": _safe_text(week.get("load_level")),
                "load_progression_note": _safe_text(week.get("load_progression_note")),
                "execution_reminder": _safe_text(week.get("execution_reminder")),
                "key_workouts": [
                    _safe_text(item) for item in (week.get("key_workouts") or []) if str(item or "").strip()
                ],
                "action_suggestions": [
                    _safe_text(item) for item in (week.get("action_suggestions") or []) if str(item or "").strip()
                ],
                "days": days,
                "training_day_count": training_day_count,
                "repeat_guard": {
                    "quality_session_count": int(repeat_guard.get("quality_session_count") or 0),
                    "hard_day_count": int(repeat_guard.get("hard_day_count") or 0),
                    "rest_day_count": int(repeat_guard.get("rest_day_count") or 0),
                    "long_run_minutes": int(repeat_guard.get("long_run_minutes") or 0),
                    "long_run_distance_km": repeat_guard.get("long_run_distance_km"),
                    "weekly_volume_km": repeat_guard.get("weekly_volume_km"),
                    "key_intensity": _safe_text(repeat_guard.get("key_intensity"), fallback=""),
                    "quality_sessions": [
                        _safe_text(item) for item in (repeat_guard.get("quality_sessions") or []) if str(item or "").strip()
                    ],
                },
            }
        )

    overview = {
        "plan_type": _safe_text(plan_meta.get("plan_type")),
        "requested_weeks": int(plan_meta.get("requested_weeks") or len(normalized) or 0),
        "actual_weeks": int(plan_meta.get("actual_weeks") or len(normalized) or 0),
        "goal": _safe_text(plan_meta.get("goal")),
        "experience_level": _safe_text(plan_meta.get("experience_level")),
        "target_race_date": _safe_text(plan_meta.get("target_race_date")),
        "render_version": _safe_text(plan_meta.get("render_version")),
        "first_week_actions": [
            _safe_text(item)
            for item in (structured_training_plan.get("first_week_actions") or []) if str(item or "").strip()
        ],
    }
    if not overview["first_week_actions"] and normalized:
        overview["first_week_actions"] = normalized[0].get("action_suggestions", [])[:3]
    return normalized, overview


def _pick_explanation_days(week: Dict[str, Any]) -> List[Dict[str, Any]]:
    days = [item for item in (week.get("days") or []) if isinstance(item, dict)]
    if not days:
        return []

    key_workouts = [str(item or "").strip() for item in (week.get("key_workouts") or []) if str(item or "").strip()]
    if not key_workouts:
        return [day for day in days if _safe_text(day.get("training_type")) != "休息"][:3]

    selected: List[Dict[str, Any]] = []
    for workout in key_workouts:
        for day in days:
            day_label = _safe_text(day.get("day"), "")
            training_type = _safe_text(day.get("training_type"), "")
            main_set = _safe_text(day.get("main_set"), "")
            if (
                day_label
                and day_label in workout
                and training_type
                and training_type in workout
            ) or (main_set and main_set in workout):
                if day not in selected:
                    selected.append(day)
                break

    if selected:
        return selected[:3]
    return [day for day in days if _safe_text(day.get("training_type")) != "休息"][:3]


def _pick_evidence_ids(evidence_base: List[Dict[str, Any]], limit: int = 2) -> List[int]:
    evidence_ids: List[int] = []
    for item in evidence_base:
        if not isinstance(item, dict):
            continue
        try:
            evidence_id = int(item.get("id", 0))
        except (TypeError, ValueError):
            continue
        if evidence_id > 0:
            evidence_ids.append(evidence_id)
        if len(evidence_ids) >= limit:
            break
    return evidence_ids


def _format_evidence_suffix(evidence_ids: List[int]) -> str:
    if not evidence_ids:
        return ""
    return " " + " ".join(f"`[{idx}]`" for idx in evidence_ids)


def _compact_text_list(values: Any, limit: int = 3) -> List[str]:
    if not isinstance(values, list):
        return []
    normalized: List[str] = []
    for item in values:
        text = _safe_text(item, "")
        if text and text not in normalized:
            normalized.append(text)
        if len(normalized) >= limit:
            break
    return normalized


def _normalize_constraint_reports(draft: Dict[str, Any], limit: int = 5) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []
    for item in (draft.get("constraints") or [])[:limit]:
        if not isinstance(item, dict):
            continue
        rule = _safe_text(item.get("rule"), "")
        status = _safe_text(item.get("status"), "")
        message = _safe_text(item.get("message"), "")
        if not (rule or status or message):
            continue
        normalized.append(
            {
                "rule": rule,
                "status": status or "unknown",
                "message": message,
            }
        )
    return normalized


def _normalize_decision_trace(draft: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in (draft.get("decision_trace") or [])[:limit]:
        if not isinstance(item, dict):
            continue
        warnings = _compact_text_list(item.get("warnings"), limit=2)
        normalized.append(
            {
                "requested": _safe_text(item.get("requested"), ""),
                "status": _safe_text(item.get("status"), "unknown"),
                "warnings": warnings,
            }
        )
    return normalized


def _build_target_labels(day: Dict[str, Any], draft: Dict[str, Any]) -> List[str]:
    targets: List[str] = []
    for item in (draft.get("physiology_targets") or []) + (draft.get("adaptation_targets") or []):
        label = _safe_text(item, "")
        if label and label not in targets:
            targets.append(label)
    if targets:
        return targets[:3]

    training_type = _safe_text(day.get("training_type"))
    if "节奏" in training_type:
        return ["乳酸阈", "专项节奏"]
    if "间歇" in training_type or "爬坡" in training_type:
        return ["速度耐力", "高强度稳定性"]
    if "长距离" in training_type:
        return ["有氧耐力", "补给节奏"]
    if "恢复" in training_type or "轻松" in training_type:
        return ["恢复", "低压力跑量维持"]
    if "力量" in training_type:
        return ["稳定性", "力量支撑"]
    if training_type == "休息":
        return ["恢复"]
    return [training_type]


def _build_explanation_source(draft: Dict[str, Any]) -> str:
    if (
        _safe_text(draft.get("template_id"), "")
        or _normalize_constraint_reports(draft, limit=1)
        or _normalize_decision_trace(draft, limit=1)
        or _compact_text_list(draft.get("warnings"), limit=1)
    ):
        return "decision_graph"
    return "fallback_heuristic"


def _build_primary_target(day: Dict[str, Any], draft: Dict[str, Any]) -> str:
    targets = [
        _safe_text(item, "")
        for item in (draft.get("physiology_targets") or draft.get("adaptation_targets") or [])
        if _safe_text(item, "")
    ]
    if targets:
        return "、".join(targets[:3])

    training_type = _safe_text(day.get("training_type"))
    if "节奏" in training_type:
        return "提升乳酸阈值附近的持续输出能力，稳定专项节奏。"
    if "间歇" in training_type or "爬坡" in training_type:
        return "提升速度耐力与高强度下的动作稳定性。"
    if "长距离" in training_type:
        return "建立有氧耐力、补给节奏和长时间稳定输出能力。"
    if "恢复" in training_type or "轻松" in training_type:
        return "以低压力方式维持跑量，同时给上一堂课留恢复窗口。"
    if "力量" in training_type:
        return "补足稳定性与力量支撑，降低专项训练中的代偿风险。"
    return f"支撑 `{training_type}` 对应的周内训练目标，并维持当前阶段节奏。"


def _build_alternative_workout(day: Dict[str, Any]) -> str:
    training_type = _safe_text(day.get("training_type"))
    if "长距离" in training_type:
        return "状态不佳时改为 45-60 分钟轻松跑，或直接休息并把长距离顺延到恢复更好的训练日。"
    if "节奏" in training_type or "间歇" in training_type or "爬坡" in training_type:
        return "状态不佳时改为 30-45 分钟 Z1-Z2 轻松跑，保留热身和放松，取消主刺激。"
    if "恢复" in training_type or "轻松" in training_type:
        return "状态不佳时缩短到 20-30 分钟恢复跑，或改为快走加拉伸。"
    if "力量" in training_type:
        return "状态不佳时改为低负荷核心激活和灵活性训练，避免额外疲劳堆积。"
    if training_type == "休息":
        return "维持休息与基础恢复，不额外加课。"
    return "状态不佳时优先降强度或缩短时长，必要时改为休息并观察恢复。"


def _build_risk_alert(day: Dict[str, Any], week: Dict[str, Any], draft: Dict[str, Any]) -> str:
    warnings = [_safe_text(item, "") for item in (draft.get("warnings") or []) if _safe_text(item, "")]
    if warnings:
        return "；".join(warnings[:2])

    constraints = [
        item for item in (draft.get("constraints") or []) if isinstance(item, dict)
    ]
    highlighted = [
        _safe_text(item.get("message"), "")
        for item in constraints
        if _safe_text(item.get("status"), "") in {"violated", "adjusted"} and _safe_text(item.get("message"), "")
    ]
    if highlighted:
        return "；".join(highlighted[:2])

    note = _safe_text(day.get("notes"), "")
    reminder = _safe_text(week.get("execution_reminder"), "")
    if note:
        return note
    if reminder:
        return reminder
    return "优先观察恢复、补给和动作质量；若主观疲劳明显升高，先降载再继续。"


def _build_decision_summary(draft: Dict[str, Any]) -> str:
    decision_trace = [
        item for item in (draft.get("decision_trace") or []) if isinstance(item, dict)
    ]
    if not decision_trace:
        template_id = _safe_text(draft.get("template_id"), "")
        if template_id:
            return f"当前课表直接命中模板 `{template_id}`，本轮未展开额外候选切换轨迹。"
        return "当前训练骨架未附带 decision trace，已按周目标和训练类型生成最小解释。"

    steps = []
    for item in decision_trace[:3]:
        requested = _safe_text(item.get("requested"))
        status = _safe_text(item.get("status"))
        step = f"{requested} -> {status}"
        warnings = [str(w).strip() for w in (item.get("warnings") or []) if str(w).strip()]
        if warnings:
            step += f"（{warnings[0]}）"
        steps.append(step)
    return "；".join(steps)


def _build_why_scheduled(day: Dict[str, Any], week: Dict[str, Any], draft: Dict[str, Any], evidence_ids: List[int]) -> str:
    parts = []
    week_goal = _safe_text(week.get("week_goal"), "")
    if week_goal:
        parts.append(f"本次安排用于支撑本周目标：{week_goal}。")

    phase = _safe_text(week.get("phase"), "")
    load_level = _safe_text(week.get("load_level"), "")
    if phase or load_level:
        parts.append(f"当前处于 {phase or '当前阶段'}，负荷级别为 {load_level or '当前负荷'}。")

    adjustments = [_safe_text(item, "") for item in (draft.get("adjustments") or []) if _safe_text(item, "")]
    if adjustments:
        parts.append(f"本次已结合画像或约束做微调：{adjustments[0]}。")
    else:
        parts.append(f"该训练由 `{_safe_text(day.get('training_type'))}` 类型和当日主课共同定义。")

    return "".join(parts).strip() + _format_evidence_suffix(evidence_ids)


def _build_training_explanation_panel(
    structured_training_plan: Any,
    training_plan_weeks: List[Dict[str, Any]],
    evidence_base: List[Dict[str, Any]],
    audit_scores: Dict[str, Any],
) -> Dict[str, Any]:
    if not isinstance(structured_training_plan, dict):
        return {}

    raw_week_plans = structured_training_plan.get("week_plans", []) or []
    if not isinstance(raw_week_plans, list):
        return {}

    evidence_ids = _pick_evidence_ids(evidence_base)
    weeks: List[Dict[str, Any]] = []
    total_key_workouts = 0
    explained_key_workouts = 0

    for fallback_index, raw_week in enumerate(raw_week_plans, start=1):
        if not isinstance(raw_week, dict):
            continue
        normalized_week = next(
            (
                item
                for item in training_plan_weeks
                if isinstance(item, dict) and int(item.get("week_index") or 0) == int(raw_week.get("week_index") or fallback_index)
            ),
            {},
        )
        key_workouts = [str(item or "").strip() for item in (raw_week.get("key_workouts") or normalized_week.get("key_workouts") or []) if str(item or "").strip()]
        candidate_days = _pick_explanation_days(raw_week)
        expected_count = len(key_workouts) if key_workouts else len(candidate_days)
        total_key_workouts += expected_count

        items: List[Dict[str, Any]] = []
        for item_index, day in enumerate(candidate_days, start=1):
            draft = day.get("draft") if isinstance(day.get("draft"), dict) else {}
            template_id = _safe_text(draft.get("template_id"), "")
            target_labels = _build_target_labels(day, draft)
            warnings = _compact_text_list(draft.get("warnings"), limit=3)
            adjustments = _compact_text_list(draft.get("adjustments"), limit=3)
            constraints = _normalize_constraint_reports(draft)
            decision_trace = _normalize_decision_trace(draft)
            title = f"{_safe_text(day.get('day'))}｜{_safe_text(day.get('training_type'))}"
            main_set = sanitize_all_pace(_safe_text(day.get("main_set"), ""))
            if main_set:
                title = f"{title}：{main_set}"
            item = {
                "item_id": f"week{int(raw_week.get('week_index') or fallback_index)}_item{item_index}",
                "title": title,
                "day": _safe_text(day.get("day")),
                "training_type": _safe_text(day.get("training_type")),
                "why_scheduled": _build_why_scheduled(day, raw_week, draft, evidence_ids),
                "primary_target": _build_primary_target(day, draft),
                "target_labels": target_labels,
                "risk_alert": _build_risk_alert(day, raw_week, draft),
                "alternative_workout": _build_alternative_workout(day),
                "decision_summary": _build_decision_summary(draft),
                "explanation_source": _build_explanation_source(draft),
                "status": _safe_text(draft.get("status"), "ready"),
                "template_id": template_id,
                "warnings": warnings,
                "adjustments": adjustments,
                "constraints": constraints,
                "decision_trace": decision_trace,
                "evidence_ids": evidence_ids,
            }
            items.append(item)

        explained_key_workouts += len(items)
        if items:
            weeks.append(
                {
                    "week_index": int(raw_week.get("week_index") or fallback_index),
                    "phase": _safe_text(raw_week.get("phase") or normalized_week.get("phase")),
                    "load_level": _safe_text(raw_week.get("load_level") or normalized_week.get("load_level")),
                    "week_goal": _safe_text(raw_week.get("week_goal") or normalized_week.get("week_goal")),
                    "execution_reminder": _safe_text(
                        raw_week.get("execution_reminder") or normalized_week.get("execution_reminder")
                    ),
                    "item_count": len(items),
                    "items": items,
                }
            )

    if not total_key_workouts:
        return {}

    coverage_ratio = round(explained_key_workouts / total_key_workouts, 2) if total_key_workouts else 0.0
    audit_summary = (
        f"一致性 {audit_scores.get('consistency', '—')} / "
        f"安全性 {audit_scores.get('safety', '—')} / "
        f"ROI {audit_scores.get('roi', '—')}%"
    )
    return {
        "panel_version": "v2",
        "summary": "围绕关键训练补充“为什么安排、训练目标、风险提醒、替代方案”。",
        "coverage_ratio": coverage_ratio,
        "coverage_status": "full" if coverage_ratio >= 1 else "partial",
        "explained_key_workouts": explained_key_workouts,
        "total_key_workouts": total_key_workouts,
        "audit_summary": audit_summary,
        "weeks": weeks,
    }


def _build_daily_workout_cards(
    structured_training_plan: Any,
    evidence_base: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not isinstance(structured_training_plan, dict):
        return []

    hits = []
    for item in evidence_base:
        if not isinstance(item, dict):
            continue
        source_file = item.get("source") or item.get("document") or item.get("path")
        hits.append(
            {
                "source_file": source_file,
                "page": (item.get("pages") or [None])[0] if isinstance(item.get("pages"), list) else None,
                "chunk_id": str(item.get("chunk_id") or item.get("id") or ""),
                "score": item.get("score") or 0.0,
                "text": item.get("text") or "",
            }
        )

    cards: List[Dict[str, Any]] = []
    for raw_week in structured_training_plan.get("week_plans", []) or []:
        if not isinstance(raw_week, dict):
            continue
        week_index = int(raw_week.get("week_index") or len(cards) + 1)
        for day in raw_week.get("days", []) or []:
            if not isinstance(day, dict):
                continue
            workout_type = normalize_workout_type_for_template(
                training_type=_safe_text(day.get("training_type"), ""),
                main_set=_safe_text(day.get("main_set"), ""),
            )
            if not workout_type:
                continue
            card = build_daily_workout_template_card_from_hits(
                workout_type=workout_type,
                day=_safe_text(day.get("day"), ""),
                hits=hits,
            )
            card["week_index"] = week_index
            card["day"] = _safe_text(day.get("day"), "")
            cards.append(card)
    return cards


def _build_half_marathon_protocol_panel(structured_training_plan: Any) -> Dict[str, Any]:
    if not isinstance(structured_training_plan, dict):
        return {}

    protocol = structured_training_plan.get("half_marathon_protocol") or {}
    if not isinstance(protocol, dict) or not protocol.get("active"):
        return {}

    validation = structured_training_plan.get("half_marathon_protocol_validation") or {}
    if not isinstance(validation, dict):
        validation = {}

    selected = protocol.get("selected_archetype") or {}
    if not isinstance(selected, dict):
        selected = {}

    phase_sequence = []
    for phase_id in protocol.get("phase_sequence") or []:
        phase_rule = HM_PHASE_RULES.get(phase_id)
        phase_sequence.append(
            {
                "id": _safe_text(phase_id, ""),
                "label": _safe_text(phase_rule.label if phase_rule else phase_id, ""),
                "objective": _safe_text(phase_rule.objective if phase_rule else "", ""),
            }
        )

    preferred_workouts = [
        item for item in (protocol.get("preferred_workouts") or []) if isinstance(item, dict)
    ][:5]

    glossary_term_ids = ["hmp"]
    for item in phase_sequence:
        glossary_term_ids.extend(term_ids_for_phase(str(item.get("id") or "")))
    for item in preferred_workouts:
        glossary_term_ids.extend(term_ids_for_workout(str(item.get("id") or "")))

    issues = []
    for item in validation.get("issues") or []:
        if not isinstance(item, dict):
            continue
        constraint_id = _safe_text(item.get("constraint_id"), "")
        workout_type = _safe_text(item.get("workout_type"), "")
        term_ids = [
            _safe_text(term_id, "") for term_id in (item.get("term_ids") or []) if _safe_text(term_id, "")
        ]
        if not term_ids:
            term_ids = [*term_ids_for_constraint(constraint_id), *term_ids_for_workout(workout_type)]
        evidence_basis = item.get("evidence_basis") if isinstance(item.get("evidence_basis"), dict) else {}
        if not evidence_basis and constraint_id:
            evidence_basis = evidence_basis_for_constraint(constraint_id, workout_type)
        glossary_term_ids.extend(term_ids)
        issues.append(
            {
                "severity": _safe_text(item.get("severity"), "warning"),
                "constraint_id": constraint_id,
                "label": _safe_text(item.get("label"), ""),
                "message": _safe_text(item.get("message"), ""),
                "recommendation": _safe_text(item.get("recommendation"), ""),
                "week_index": item.get("week_index"),
                "day": _safe_text(item.get("day"), ""),
                "workout_type": workout_type,
                "term_ids": term_ids,
                "evidence_basis": {
                    "summary": _safe_text(evidence_basis.get("summary"), ""),
                    "source_docs": [
                        _safe_text(source, "") for source in (evidence_basis.get("source_docs") or []) if _safe_text(source, "")
                    ],
                    "term_ids": [
                        _safe_text(term_id, "") for term_id in (evidence_basis.get("term_ids") or []) if _safe_text(term_id, "")
                    ],
                } if evidence_basis else {},
            }
        )

    error_count = len(validation.get("errors") or [])
    warning_count = len(validation.get("warnings") or [])
    status = "passed"
    if error_count:
        status = "error"
    elif warning_count:
        status = "warning"

    return {
        "active": True,
        "panel_version": "hmp_v1",
        "status": status,
        "passed": bool(validation.get("passed", True)),
        "selected_archetype": {
            "archetype_id": _safe_text(selected.get("archetype_id"), ""),
            "label": _safe_text(selected.get("label"), ""),
            "score": int(selected.get("score") or 0),
            "reasons": _compact_text_list(selected.get("reasons"), limit=5),
        },
        "archetype_candidates": [
            item for item in (protocol.get("archetype_candidates") or []) if isinstance(item, dict)
        ][:4],
        "phase_sequence": phase_sequence,
        "preferred_workouts": preferred_workouts,
        "glossary_terms": get_hmp_glossary_terms(glossary_term_ids, limit=8),
        "validation_summary": {
            "status": status,
            "passed": bool(validation.get("passed", True)),
            "error_count": error_count,
            "warning_count": warning_count,
            "issue_count": len(issues),
            "checked_constraints": [
                _safe_text(item, "") for item in (validation.get("checked_constraints") or []) if _safe_text(item, "")
            ],
        },
        "issues": issues,
        "repair_applied": bool(validation.get("repair_applied")),
        "repair_log": [
            item for item in (validation.get("repair_log") or protocol.get("repair_log") or []) if isinstance(item, dict)
        ],
        "repair_suggestions": [
            item for item in (validation.get("repair_suggestions") or []) if isinstance(item, dict)
        ],
        "profile_gaps": [
            item for item in (protocol.get("profile_gaps") or []) if isinstance(item, dict)
        ],
        "pace_calibration": protocol.get("pace_calibration") if isinstance(protocol.get("pace_calibration"), dict) else {},
        "capacity_budget": protocol.get("capacity_budget") if isinstance(protocol.get("capacity_budget"), dict) else {},
        "recent_marathon": bool(protocol.get("recent_marathon")),
        "input_weekly_mileage_km": protocol.get("input_weekly_mileage_km"),
        "source_docs": [
            "Sub-70半程马拉松训练_图片OCR整理.md",
            "docs/half_marathon_hmp_protocol.md",
            "docs/half_marathon_source_audit.md",
        ],
    }


def _build_structured_report(state: IntegratedState, final_report: str) -> Dict[str, Any]:
    rag_sources = state.get("rag_sources", [])
    evidence_bundle = state.get("evidence_bundle") if isinstance(state.get("evidence_bundle"), dict) else {}
    structured_training_plan = state.get("structured_training_plan")
    adaptive_adjustment = state.get("adaptive_adjustment") or {}
    phase_summary = _normalize_phase_summary(structured_training_plan)
    training_plan_weeks, training_plan_overview = _normalize_week_sections(structured_training_plan)
    execution_steps = []
    for idx, task in enumerate(state.get("subtasks", [])[:5], start=1):
        execution_steps.append(
            {
                "task_id": task.get("task_id", f"TASK-{idx}"),
                "objective": task.get("objective", ""),
                "findings": {
                    "focus": task.get("focus", ""),
                    "result": "已纳入本轮综合输出",
                },
                "conclusion": "本子任务已被整合到最终建议中。",
            }
        )

    if not execution_steps:
        execution_steps.append(
            {
                "task_id": "TASK-1",
                "objective": "直接回复用户问题",
                "findings": {"summary": final_report[:400]},
                "conclusion": "当前轮次以直接问答形式完成。",
            }
        )

    evidence_base = evidence_base_from_bundle(evidence_bundle, limit=5)
    if not evidence_base:
        for i, src in enumerate(rag_sources[:5], start=1):
            evidence_base.append(
                {
                    "id": i,
                    "document": src.get("source", "unknown"),
                    "source": src.get("source", "unknown"),
                    "path": src.get("source_path", "") or src.get("source_file", ""),
                    "source_path": src.get("source_path", ""),
                    "pages": [int(src.get("page", 1) or 1)],
                    "text": src.get("text", ""),
                    "chunk_id": src.get("chunk_id", ""),
                    "score": src.get("score", 0.0),
                }
            )

    daily_workout_evidence_base = evidence_base_from_bundle(evidence_bundle, limit=None) or list(evidence_base)
    if len(daily_workout_evidence_base) <= len(evidence_base):
        for i, src in enumerate(rag_sources[5:], start=6):
            daily_workout_evidence_base.append(
                {
                    "id": i,
                    "document": src.get("source", "unknown"),
                    "source": src.get("source", "unknown"),
                    "path": src.get("source_path", "") or src.get("source_file", ""),
                    "source_path": src.get("source_path", ""),
                    "pages": [int(src.get("page", 1) or 1)],
                    "text": src.get("text", ""),
                    "chunk_id": src.get("chunk_id", ""),
                    "score": src.get("score", 0.0),
                }
            )

    daily_workout_cards = _build_daily_workout_cards(structured_training_plan, daily_workout_evidence_base)
    monthly_training_calendar = generate_daily_schedule(
        structured_training_plan,
        enable_kb_fallback=not bool(state.get("skip_calendar_kb_fallback")),
    ) if structured_training_plan else None
    daily_schedule_cards = [
        item.to_dict() if hasattr(item, "to_dict") else item
        for item in (monthly_training_calendar.days if monthly_training_calendar else [])
    ]
    summary = final_report if final_report and final_report.strip() else "（本轮未产生实质性回复内容）"
    audit_scores = state.get("audit_scores", {})
    workflow_trace = state.get("workflow_trace") if isinstance(state.get("workflow_trace"), dict) else {}
    if not workflow_trace:
        workflow_trace = build_workflow_trace(
            query=state.get("query", ""),
            workflow_kind=state.get("workflow_kind", "") or state.get("category", "qa"),
            intent_type=state.get("intent_type", ""),
            status="complete",
            evidence_bundle=evidence_bundle,
            structured_training_plan=structured_training_plan if isinstance(structured_training_plan, dict) else None,
            adaptive_feedback=state.get("adaptive_feedback") if isinstance(state.get("adaptive_feedback"), dict) else None,
            adaptive_adjustment=adaptive_adjustment if isinstance(adaptive_adjustment, dict) else None,
        )
    training_explanation_panel = _build_training_explanation_panel(
        structured_training_plan,
        training_plan_weeks,
        evidence_base,
        audit_scores,
    )
    half_marathon_protocol_panel = _build_half_marathon_protocol_panel(structured_training_plan)
    if training_explanation_panel and half_marathon_protocol_panel:
        training_explanation_panel["protocol_context"] = {
            "protocol": "half_marathon_hmp",
            "status": half_marathon_protocol_panel.get("status"),
            "selected_archetype": half_marathon_protocol_panel.get("selected_archetype"),
            "validation_summary": half_marathon_protocol_panel.get("validation_summary"),
        }
    wiki_context = str(state.get("wiki_context", "") or "").strip()
    findings = [
        {"key": "用户问题", "value": state.get("query", "") or "—"},
        {"key": "意图分类", "value": state.get("category", "coach")},
        {"key": "识别实体", "value": ", ".join(state.get("entities", [])) or "—"},
        {"key": "图谱关联", "value": state.get("graph_context", "")[:200] or "暂无直接关联"},
        {"key": "一致性评分", "value": str(audit_scores.get("consistency", "—"))},
        {"key": "安全性评分", "value": str(audit_scores.get("safety", "—"))},
        {"key": "知识回报率 (ROI)", "value": f"{audit_scores.get('roi', 0)}%"},
    ]
    if structured_training_plan:
        plan_meta = structured_training_plan.get("plan_meta", {})
        findings.extend(
            [
                {"key": "结构化计划类型", "value": plan_meta.get("plan_type", "—")},
                {
                    "key": "结构化计划周数",
                    "value": str(plan_meta.get("actual_weeks", len(structured_training_plan.get("week_plans", [])))),
                },
            ]
        )
        if training_plan_weeks:
            first_week = training_plan_weeks[0]
            findings.extend(
                [
                    {"key": "首周阶段", "value": first_week.get("phase", "—")},
                    {"key": "首周训练日数", "value": str(first_week.get("training_day_count", 0))},
                ]
            )
    if adaptive_adjustment:
        findings.extend(
            [
                {
                    "key": "自适应调整触发",
                    "value": "是" if adaptive_adjustment.get("adjustment_required") else "否",
                },
                {
                    "key": "自适应主原因",
                    "value": _safe_text(adaptive_adjustment.get("primary_reason_code")),
                },
                {
                    "key": "自适应原因集合",
                    "value": ", ".join(adaptive_adjustment.get("reason_codes", [])) or "—",
                },
            ]
        )
    if wiki_context:
        findings.append({"key": "Wiki补充", "value": wiki_context[:200]})
    recommendations = [
        state.get("review_feedback", "") or "当前轮次未触发额外审查反馈",
    ]
    risk_alert = state.get("risk_alert", "")
    if risk_alert:
        recommendations.append(f"⚠️ 风险提示: {risk_alert}")
    if adaptive_adjustment.get("risk_alert"):
        recommendations.append(f"⚠️ 自适应风险: {adaptive_adjustment.get('risk_alert')}")
    if adaptive_adjustment.get("next_day_adjustment"):
        recommendations.append(f"明日调整: {adaptive_adjustment.get('next_day_adjustment')}")
    if adaptive_adjustment.get("weekly_adjustment"):
        recommendations.append(f"本周微调: {adaptive_adjustment.get('weekly_adjustment')}")
    if adaptive_adjustment.get("alternative_workout"):
        recommendations.append(f"替代训练: {adaptive_adjustment.get('alternative_workout')}")

    return {
        "title": "马拉松专业分析报告",
        "summary": summary,
        "findings": findings,
        "recommendations": recommendations,
        "report_metadata": {
            "version": "2.1",
            "mode": state.get("mode", "team"),
            "title": "Marathon QA Assistant Report",
        },
        "analysis_framework": {
            "query": state.get("query", ""),
            "key_entities": state.get("entities", []),
            "graph_context": state.get("graph_context", ""),
            "wiki_context": wiki_context,
        },
        "adaptive_adjustment": adaptive_adjustment,
        "workflow_trace": workflow_trace,
        "structured_training_plan": structured_training_plan,
        "training_plan_overview": training_plan_overview,
        "training_explanation_panel": training_explanation_panel,
        "half_marathon_protocol": structured_training_plan.get("half_marathon_protocol", {}) if isinstance(structured_training_plan, dict) else {},
        "half_marathon_protocol_validation": structured_training_plan.get("half_marathon_protocol_validation", {}) if isinstance(structured_training_plan, dict) else {},
        "half_marathon_protocol_panel": half_marathon_protocol_panel,
        "daily_workout_cards": daily_workout_cards,
        "monthly_training_calendar": monthly_training_calendar.to_dict() if monthly_training_calendar else {},
        "daily_schedule_cards": daily_schedule_cards,
        "evidence_tier_map": _EVIDENCE_TIER_LABELS,
        "weekly_structure_constraints": structured_training_plan.get("weekly_structure_constraints", {}) if isinstance(structured_training_plan, dict) else {},
        "weekly_structure_validation": structured_training_plan.get("weekly_structure_validation", {}) if isinstance(structured_training_plan, dict) else {},
        "phase_summary": phase_summary,
        "training_plan_weeks": training_plan_weeks,
        "execution_steps": execution_steps,
        "audit_block": {
            "scores": audit_scores,
            "review_feedback": state.get("review_feedback", ""),
            "risk_alert": risk_alert,
        },
        "evidence_bundle": evidence_bundle,
        "evidence_base": evidence_base,
    }


async def formatter_node(state: IntegratedState, config: RunnableConfig) -> dict:
    del config
    raw_content = state.get("final_report") or state.get("draft_plan") or "当前没有可格式化的输出。"
    is_safe, cleaned_output, reason = output_guard_obj.check(raw_content)
    structured_report = _build_structured_report(state, cleaned_output)

    logs = ["[formatter] 已生成结构化报告"]
    if not is_safe:
        logs.append(f"[formatter] 输出安全清洗: {reason}")

    return {
        "final_report": cleaned_output,
        "structured_training_plan": state.get("structured_training_plan"),
        "structured_report": structured_report,
        "token_usage": ensure_usage(state.get("token_usage")),
        "reasoning_log": logs,
    }


def _safe_truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "…"


async def guided_questions_node(state: IntegratedState, config: RunnableConfig) -> dict:
    del config
    intent = state.get("intent_type", "qa")
    draft_plan = state.get("draft_plan", "")
    final_report = state.get("final_report", "")
    missing_fields = state.get("missing_fields", [])
    missing_info_status = state.get("missing_info_status", "")

    if intent == "plan" and (
        missing_info_status == "awaiting_profile" or final_report == "__FILL_FIELDS__"
    ):
        return {
            "guided_questions": [],
            "token_usage": ensure_usage(state.get("token_usage")),
            "reasoning_log": ["[guided_questions] 计划待补信息，跳过追问"],
        }

    if intent == "plan" and not missing_fields and (draft_plan or final_report):
        return {
            "guided_questions": [],
            "token_usage": ensure_usage(state.get("token_usage")),
            "reasoning_log": ["[guided_questions] 计划已生成，跳过追问"],
        }

    query = state.get("query", "")
    category = state.get("category", "coach")
    entities = state.get("entities", [])
    mode = state.get("mode", "team")
    audit_scores = state.get("audit_scores", {})
    roi = audit_scores.get("roi", 0)

    entity_hint = entities[0] if entities else "当前主题"
    query_hint = _safe_truncate(query, 12)
    iteration = state.get("iteration_count", 0)

    template_pool = [
        f"如果继续围绕「{entity_hint}」，你想看更细的分解吗？",
        f"你希望我把这次{category}建议改写成更偏执行清单的版本吗？",
        f"要不要结合你的下一个比赛目标，继续追问「{query_hint}」的后续安排？",
        f"你对「{entity_hint}」相关的运动生理机制感兴趣吗？",
        f"当前 ROI 评分为 {roi}%，要不要补充更多个人数据来提升回答精度？",
        f"需要我把「{entity_hint}」的训练建议拆成周计划吗？",
    ]

    if mode == "research":
        template_pool.append("要不要对当前结论做一次交叉验证分析？")
    if iteration >= 2:
        template_pool.append("是否需要我切换为更简洁的模式来回答？")

    seen = set()
    picked = []
    offset = (iteration * 2 + len(query_hint)) % len(template_pool)
    for i in range(len(template_pool)):
        idx = (offset + i * 3) % len(template_pool)
        q = template_pool[idx]
        if q not in seen:
            seen.add(q)
            picked.append(q)
        if len(picked) >= 3:
            break

    return {
        "guided_questions": picked,
        "token_usage": ensure_usage(state.get("token_usage")),
        "reasoning_log": ["[guided_questions] 已生成 3 个追问建议"],
    }
