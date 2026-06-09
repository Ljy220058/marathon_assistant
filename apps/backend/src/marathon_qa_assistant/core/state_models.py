import operator
from datetime import date, timedelta
from typing import Annotated, Any, Dict, List, Optional, TypedDict
from uuid import uuid4

try:
    from pydantic import BaseModel, Field
except ImportError:
    class BaseModel:
        """无 pydantic 环境下的最小兜底模型。"""

        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        def model_dump(self):
            return self.__dict__.copy()

    def Field(default=None, **kwargs):
        if "default_factory" in kwargs:
            return kwargs["default_factory"]()
        return default


class TokenUsage(TypedDict):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class WorkoutFeedback(TypedDict, total=False):
    completion_status: str
    completion_quality: str
    subjective_fatigue: str
    pain_status: str
    sleep_quality: str
    notes: str


class AdaptiveReason(TypedDict):
    code: str
    label: str
    severity: str
    why: str


class AdaptiveFeedback(TypedDict, total=False):
    workout_feedback: WorkoutFeedback
    reason_codes: List[str]
    reasons: List[AdaptiveReason]
    raw_text: str
    source: str


class AdaptiveAdjustment(TypedDict, total=False):
    adjustment_required: bool
    primary_reason_code: str
    reason_codes: List[str]
    reasons: List[AdaptiveReason]
    next_day_adjustment: str
    weekly_adjustment: str
    alternative_workout: str
    risk_alert: str
    rationale: str


class RiskGateResult(TypedDict, total=False):
    status: str
    risk_level: str
    triggers: List[str]
    adjustment_action: str
    product_status: str
    decision_reason: str


class ExecutionStatusSummary(TypedDict, total=False):
    week_start: str
    week_end: str
    completion_rate: int
    planned_count: int
    completed_count: int
    partial_count: int
    skipped_count: int
    missed_feedback_count: int
    plan_deviation: Dict[str, Any]
    risk_level: str
    risk_reasons: List[str]
    recovery_status: str
    next_training_recommendation: str
    generation_status: str
    risk_rule_source: str
    current_week: int
    total_weeks: int
    cycle_completion_rate: int
    completed_weeks: List[Dict[str, Any]]
    phase_progress: List[Dict[str, Any]]


class TraceStep(TypedDict, total=False):
    """AgentDoG P0: 单个节点的执行轨迹记录。"""
    node: str                          # 节点名 (entity_extraction, planner, executor, coach, auditor, ...)
    timestamp: str                     # ISO 时间戳
    input_snapshot: Dict[str, Any]     # 入口关键字段快照 (query, category, entity_count, ...)
    output_snapshot: Dict[str, Any]    # 出口关键字段快照 (evidence_count, plan_weeks, is_approved, ...)
    decision: str                      # 本节点关键决策摘要


class WorkflowTrace(TypedDict, total=False):
    trace_version: str
    run_id: str
    workflow_kind: str
    intent_type: str
    status: str
    evidence_state: Dict[str, Any]
    protocol_state: Dict[str, Any]
    risk_state: Dict[str, Any]
    repair_state: Dict[str, Any]
    feedback_state: Dict[str, Any]
    audit_events: List[Dict[str, Any]]


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _contains_any(text: str, keywords: List[str]) -> bool:
    return any(keyword in text for keyword in keywords)


_ADAPTIVE_RULE_LIBRARY: Dict[str, Dict[str, str]] = {
    "pain_risk": {
        "next_day_adjustment": "次日暂停跑步主课，改为休息或 30-40 分钟无冲击交叉训练，并优先处理疼痛部位。",
        "weekly_adjustment": "本周取消质量课加量，长距离与强度课至少下调一个档位，先把目标切回安全完赛/安全训练。",
        "alternative_workout": "可替代为自行车、椭圆机或游泳等低冲击有氧，并配合灵活性与激活训练。Low impact options: rest, swim, bike, cycling, or elliptical only.",
        "risk_alert": "若疼痛在日常行走中仍明显、持续 48 小时以上或出现加重，暂停跑步并尽快做专业评估。",
        "principle": "先控风险，再谈训练连续性。",
    },
    "high_fatigue": {
        "next_day_adjustment": "次日改为休息，或仅保留 30-45 分钟 Z1 轻松跑，取消任何阈值、间歇或爬坡刺激。",
        "weekly_adjustment": "本周减少 1 次质量课，并把总量下调约 20%-30%，优先补回睡眠和恢复窗口。",
        "alternative_workout": "如仍想保持活动，可改为 20-30 分钟恢复慢跑、快走或拉伸放松，不追求训练刺激。",
        "risk_alert": "若高疲劳连续 2-3 天未缓解，或伴随睡眠/食欲明显变差，应继续降载并暂停质量课。",
        "principle": "先补恢复赤字，避免在疲劳高位继续堆负荷。",
    },
    "mild_fatigue": {
        "next_day_adjustment": "次日训练保留，但强度下调一级；若原计划是质量课，改为 30-40 分钟轻松跑或恢复跑。",
        "weekly_adjustment": "本周不额外加量，保留训练节奏但缩短一次主课时长，整体负荷微降约 10%-15%。",
        "alternative_workout": "可替代为 30-40 分钟轻松跑 + 10-15 分钟拉伸/泡沫轴，继续观察恢复质量。",
        "risk_alert": "若轻微疲劳叠加睡眠差或不适持续到下一次关键课前，应进一步降载而不是硬顶。",
        "principle": "先做轻量微调，尽量保留训练连续性。",
    },
    "missed_workout": {
        "next_day_adjustment": "次日不要把漏掉的关键课原样补回；优先恢复到当前周节奏，只在状态稳定时安排简化版替代。",
        "weekly_adjustment": "本周避免堆课，保留 1 次最关键主课即可，其余训练按恢复状态顺延或直接跳过。",
        "alternative_workout": "若需要补练，使用缩短版替代：20-30 分钟轻松跑 + 4-6 组轻松加速跑，替代整堂高负荷主课。",
        "risk_alert": "若连续两次以上关键课漏训，需重新评估本周时间安排与计划可执行性，而不是继续加码追赶。",
        "principle": "先防止补课堆积，再维持计划可执行性。",
    },
}


def _build_no_adjustment_contract() -> AdaptiveAdjustment:
    return {
        "adjustment_required": False,
        "primary_reason_code": "",
        "reason_codes": [],
        "reasons": [],
        "next_day_adjustment": "次日按原计划执行，并保持常规热身、补水与恢复安排。",
        "weekly_adjustment": "本周维持既定训练节奏，不额外加量，也无需主动降载。",
        "alternative_workout": "当前无需替代训练，按原课表推进即可。",
        "risk_alert": "",
        "rationale": "当前反馈未识别出需要触发自适应调整的明确信号。",
    }


def _compose_adaptive_field(reason_codes: List[str], field: str) -> str:
    segments: List[str] = []
    for code in reason_codes:
        rule = _ADAPTIVE_RULE_LIBRARY.get(code, {})
        text = _normalize_text(rule.get(field))
        if not text or text in segments:
            continue
        segments.append(text)
    return "；".join(segments)


def _build_adaptive_rationale(reason_codes: List[str], reasons: List[AdaptiveReason]) -> str:
    if not reason_codes:
        return "当前反馈未识别出需要触发自适应调整的明确信号。"

    labels = [reason["label"] for reason in reasons if _normalize_text(reason.get("label"))]
    principles: List[str] = []
    for code in reason_codes:
        principle = _normalize_text(_ADAPTIVE_RULE_LIBRARY.get(code, {}).get("principle"))
        if principle and principle not in principles:
            principles.append(principle)

    reason_summary = "、".join(labels) if labels else "当前反馈"
    principle_summary = "；".join(principles)
    return f"本次调整由{reason_summary}触发；处理原则是{principle_summary}"


def build_feedback_risk_gate(feedback: Optional[Dict[str, Any]] = None, raw_text: str = "") -> RiskGateResult:
    normalized = normalize_workout_feedback(feedback, raw_text=raw_text)
    combined_text = f"{raw_text} {normalized.get('notes', '')}".lower()
    triggers: List[str] = []

    # P1-6: \u6269\u5c55\u4e25\u91cd\u7ea2\u65d7\u5173\u952e\u8bcd\u5e93\uff0c\u8986\u76d6\u8dd1\u6b65\u4e13\u9879\u4f24\u75c5
    severe_keywords = {
        "chest_pain": ["\u80f8\u75db", "\u80f8\u75db", "\u80f8\u95f7", "chest pain", "chest tightness"],
        "dizziness_or_syncope": ["\u5934\u6655", "\u7729\u6655", "\u6655\u53a5", "\u6655\u5012", "dizzy", "faint"],
        "heat_illness": ["\u4e2d\u6691", "\u70ed\u75c5", "\u70ed\u5c04\u75c5", "\u9ad8\u6e29\u5f02\u5e38", "heat illness", "heatstroke"],
        "difculty_breathing": ["\u547c\u5438\u56f0\u96be", "\u5598\u4e0d\u4e0a\u6c14", "\u6c14\u77ed", "\u77ed\u6c14"],
        "fracture": ["\u9aa8\u6298", "bone break", "fracture"],
        # P1-6 \u65b0\u589e\u8dd1\u6b65\u4e13\u9879\u4f24\u75c5
        "achilles_rupture": ["\u8ddf\u8171\u65ad\u88c2", "\u8ddf\u8171\u6495\u88c2", "\u5f39\u54cd", "achilles rupture", "achilles tear"],
        "stress_fracture": ["\u5e94\u529b\u6027\u9aa8\u6298", "\u70b9\u538b\u75db", "\u8d1f\u91cd\u75db", "stress fracture", "\u9aa8\u88c2"],
        "plantar_fasciitis": ["\u8db3\u5e95\u7b4b\u819c\u708e", "\u8db3\u8ddf\u75db", "plantar fasciitis"],
        "severe_swelling": ["\u4e25\u91cd\u80bf\u80c0", "\u65e0\u6cd5\u627f\u91cd", "\u5173\u8282\u79ef\u6db2"],
        "rhabdomyolysis": ["\u6a2a\u7eb9\u808c\u6eb6\u89e3", "\u9171\u6cb9\u5c3f", "\u8336\u8272\u5c3f", "rhabdomyolysis"],
    }
    for code, keywords in severe_keywords.items():
        if _contains_any(combined_text, keywords):
            triggers.append(code)

    if normalized.get("pain_status") == "risk":
        triggers.append("pain_risk")
    if normalized.get("subjective_fatigue") == "high":
        triggers.append("high_fatigue")
    if normalized.get("sleep_quality") == "poor":
        triggers.append("poor_sleep")

    triggers = list(dict.fromkeys(triggers))
    # P1-6: 扩展严重红旗集合
    _SEVERE_CODES = {
        "chest_pain", "dizziness_or_syncope", "heat_illness",
        "difculty_breathing", "fracture",
        "achilles_rupture", "stress_fracture", "plantar_fasciitis",
        "severe_swelling", "rhabdomyolysis",
    }
    severe = any(code in triggers for code in _SEVERE_CODES)
    if severe:
        return {
            "status": "blocked",
            "risk_level": "medical",
            "triggers": triggers,
            "adjustment_action": "deescalate_or_refuse",
            "product_status": "medical_referral",
            "decision_reason": "出现胸痛、头晕/晕厥或中暑迹象时，系统不继续生成训练调整，先建议停止训练并寻求专业评估。",
        }
    if triggers:
        return {
            "status": "needs_protocol_recheck",
            "risk_level": "high" if {"pain_risk", "high_fatigue"} & set(triggers) else "medium",
            "triggers": triggers,
            "adjustment_action": "deescalate_or_refuse" if "pain_risk" in triggers else "deescalate",
            "product_status": "risk_refused" if "pain_risk" in triggers else "partial_generated",
            "decision_reason": "反馈触发风险门，必须先降级并重查协议容量，再给训练调整建议。",
        }
    return {
        "status": "passed",
        "risk_level": "low",
        "triggers": [],
        "adjustment_action": "none",
        "product_status": "generated",
        "decision_reason": "未识别到需要阻断或降级的风险信号。",
    }


def build_feedback_protocol_recheck(risk_gate: RiskGateResult) -> Dict[str, Any]:
    blocked = risk_gate.get("status") == "blocked"
    return {
        "allowed": not blocked,
        "risk_gate_status": risk_gate.get("status", ""),
        "adjustment_action": risk_gate.get("adjustment_action", "none"),
        "violations": list(risk_gate.get("triggers") or []),
        "decision_reason": "风险门阻断，拒绝继续生成训练负荷调整。" if blocked else "风险门通过或已要求降级，允许进入受控调整。",
    }


def _parse_iso_date(value: Any) -> Optional[date]:
    try:
        return date.fromisoformat(str(value or "").strip()[:10])
    except ValueError:
        return None


def _week_bounds(today: Optional[Any] = None) -> tuple[date, date]:
    base = _parse_iso_date(today) if today is not None else None
    base = base or date.today()
    start = base - timedelta(days=base.weekday())
    return start, start + timedelta(days=6)


def _is_execution_rest_event(event: Dict[str, Any]) -> bool:
    haystack = " ".join(
        str(event.get(key) or "")
        for key in ("workout_type", "training_type", "training_type_label", "title", "main_set")
    ).lower()
    return bool(event.get("is_rest")) or "rest" in haystack or "recovery" in haystack


def _feedback_for_event(event: Dict[str, Any]) -> Dict[str, Any]:
    feedback = event.get("latest_feedback") or event.get("feedback") or {}
    return feedback if isinstance(feedback, dict) else {}


def _event_risk_reasons(feedback: Dict[str, Any]) -> List[str]:
    reasons: List[str] = []
    for code in feedback.get("reason_codes") or []:
        if code:
            reasons.append(str(code))
    risk_gate = feedback.get("risk_gate") or {}
    if isinstance(risk_gate, dict):
        for code in risk_gate.get("triggers") or []:
            if code:
                reasons.append(str(code))
        product_status = str(risk_gate.get("product_status") or "")
        if product_status == "medical_referral":
            reasons.append("medical_referral")
    return list(dict.fromkeys(reasons))


def _risk_level_from_reasons(reasons: List[str]) -> tuple[str, str, str]:
    reason_set = set(reasons)
    if {"medical_referral", "chest_pain", "dizziness_or_syncope", "heat_illness"} & reason_set:
        return (
            "medical_referral",
            "medical_referral",
            "停止训练，并在进行任何训练调整前先接受专业医疗评估。",
        )
    if "pain_risk" in reason_set:
        return (
            "deescalate",
            "risk_refused",
            "下一次训练降级为休息或低冲击活动，直到疼痛风险重新评估。",
        )
    if "high_fatigue" in reason_set:
        return (
            "deescalate",
            "partial_generated",
            "Reduce the next workout intensity and prioritize recovery before quality sessions.",
        )
    if "poor_sleep" in reason_set or "missed_workout" in reason_set:
        return (
            "attention",
            "partial_generated",
            "Keep the plan conservative and avoid stacking missed or low-recovery workouts.",
        )
    return ("normal", "generated", "Continue with the planned next workout and keep routine recovery checks.")


def _week_number(event: Dict[str, Any]) -> int:
    try:
        return max(1, int(event.get("week_no") or event.get("week_index") or 1))
    except (TypeError, ValueError):
        return 1


def _completion_points(feedback: Dict[str, Any]) -> float:
    status = str(feedback.get("completion_status") or "").strip().lower()
    if status == "completed":
        return 1.0
    if status == "partial":
        return 0.5
    return 0.0


def _completed_weeks(events: List[Dict[str, Any]], today_date: date) -> List[Dict[str, Any]]:
    grouped: Dict[int, List[Dict[str, Any]]] = {}
    for event in events or []:
        if _is_execution_rest_event(event):
            continue
        grouped.setdefault(_week_number(event), []).append(event)

    rows: List[Dict[str, Any]] = []
    for week_no in sorted(grouped):
        week_events = grouped[week_no]
        planned = len(week_events)
        completed = 0.0
        missing = 0
        for event in week_events:
            feedback = _feedback_for_event(event)
            if feedback:
                completed += _completion_points(feedback)
                continue
            event_date = _parse_iso_date(event.get("scheduled_date"))
            if event_date is None or event_date <= today_date:
                missing += 1
        rows.append(
            {
                "week_no": week_no,
                "planned_count": planned,
                "completion_rate": int(round((completed / planned) * 100)) if planned else 0,
                "missed_feedback_count": missing,
            }
        )
    return rows


def _phase_progress(events: List[Dict[str, Any]], current_week: int) -> List[Dict[str, Any]]:
    phases: Dict[str, Dict[str, Any]] = {}
    for event in events or []:
        phase = str(event.get("phase") or event.get("phase_label") or "base").strip() or "base"
        week_no = _week_number(event)
        entry = phases.setdefault(
            phase,
            {"phase": phase, "start_week": week_no, "end_week": week_no, "state": "upcoming"},
        )
        entry["start_week"] = min(int(entry["start_week"]), week_no)
        entry["end_week"] = max(int(entry["end_week"]), week_no)
    for entry in phases.values():
        if int(entry["end_week"]) < current_week:
            entry["state"] = "complete"
        elif int(entry["start_week"]) <= current_week <= int(entry["end_week"]):
            entry["state"] = "current"
        else:
            entry["state"] = "upcoming"
    return sorted(phases.values(), key=lambda item: int(item["start_week"]))


def build_execution_status_summary(
    events: List[Dict[str, Any]],
    *,
    plan: Optional[Dict[str, Any]] = None,
    today: Optional[Any] = None,
) -> ExecutionStatusSummary:
    week_start, week_end = _week_bounds(today)
    current_week_events: List[Dict[str, Any]] = []
    for event in events or []:
        event_date = _parse_iso_date(event.get("scheduled_date"))
        if event_date is None or week_start <= event_date <= week_end:
            current_week_events.append(event)

    planned_events = [event for event in current_week_events if not _is_execution_rest_event(event)]
    planned_count = len(planned_events)
    completed_count = 0
    partial_count = 0
    skipped_count = 0
    missed_feedback_count = 0
    risk_reasons: List[str] = []

    today_date = _parse_iso_date(today) if today is not None else date.today()
    for event in planned_events:
        feedback = _feedback_for_event(event)
        event_date = _parse_iso_date(event.get("scheduled_date"))
        if not feedback:
            if event_date is None or event_date <= today_date:
                missed_feedback_count += 1
            continue

        status = str(feedback.get("completion_status") or "").strip().lower()
        if status == "completed":
            completed_count += 1
        elif status == "partial":
            partial_count += 1
        elif status in {"missed", "skipped"}:
            skipped_count += 1
        risk_reasons.extend(_event_risk_reasons(feedback))

    risk_reasons = list(dict.fromkeys(risk_reasons))
    risk_level, generation_status, recommendation = _risk_level_from_reasons(risk_reasons)
    completion_points = completed_count + partial_count * 0.5
    completion_rate = int(round((completion_points / planned_count) * 100)) if planned_count else 0
    total_weeks = int((plan or {}).get("actual_weeks") or (plan or {}).get("total_weeks") or 0)
    event_weeks = [_week_number(event) for event in events or []]
    current_week = max((_week_number(event) for event in current_week_events), default=1)
    if event_weeks:
        current_week = min(current_week, max(event_weeks))
    total_weeks = total_weeks or max(event_weeks, default=0)
    cycle_completion_rate = int(round((current_week / total_weeks) * 100)) if total_weeks else 0
    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "completion_rate": completion_rate,
        "planned_count": planned_count,
        "completed_count": completed_count,
        "partial_count": partial_count,
        "skipped_count": skipped_count,
        "missed_feedback_count": missed_feedback_count,
        "plan_deviation": {
            "not_completed_count": skipped_count + missed_feedback_count,
            "partial_count": partial_count,
            "completion_points": completion_points,
            "total_weeks": total_weeks,
        },
        "risk_level": risk_level,
        "risk_reasons": risk_reasons,
        "recovery_status": "medical_referral" if risk_level == "medical_referral" else risk_level,
        "next_training_recommendation": recommendation,
        "generation_status": generation_status,
        "risk_rule_source": "deterministic_feedback_rules",
        "current_week": current_week,
        "total_weeks": total_weeks,
        "cycle_completion_rate": cycle_completion_rate,
        "completed_weeks": _completed_weeks(events or [], today_date),
        "phase_progress": _phase_progress(events or [], current_week),
    }


WORKFLOW_TRACE_VERSION = "workflow_trace.v1"


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _tier_counts(items: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in items:
        tier = str(item.get("tier") or "unknown")
        counts[tier] = counts.get(tier, 0) + 1
    return counts


def _workflow_evidence_state(evidence_bundle: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    bundle = _safe_dict(evidence_bundle)
    health = _safe_dict(bundle.get("health"))
    items = [item for item in _safe_list(bundle.get("evidence_items")) if isinstance(item, dict)]
    missing_evidence: List[str] = []
    kb_ready = bool(health.get("kb_ready") or health.get("ready") or health.get("ok"))
    if not kb_ready:
        missing_evidence.append("kb_not_ready")
    if not items:
        missing_evidence.append("no_evidence_items")
    citation_labels = [
        str(item.get("citation_label") or "").strip()
        for item in items
        if str(item.get("citation_label") or "").strip()
    ]
    return {
        "status": "ok" if not missing_evidence else "missing_or_partial",
        "kb_ready": kb_ready,
        "chunks_count": int(health.get("chunks_count") or 0),
        "faiss_ready": bool(health.get("faiss_ready")),
        "evidence_count": len(items),
        "tier_counts": _tier_counts(items),
        "citation_labels": citation_labels,
        "evidence_ids": [str(item.get("evidence_id") or "") for item in items if item.get("evidence_id")],
        "missing_evidence": missing_evidence,
    }


def _workflow_protocol_state(structured_training_plan: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    plan = _safe_dict(structured_training_plan)
    protocol = _safe_dict(plan.get("half_marathon_protocol"))
    validation = _safe_dict(plan.get("half_marathon_protocol_validation"))
    active = bool(protocol.get("active"))
    errors = [item for item in _safe_list(validation.get("errors")) if isinstance(item, dict)]
    warnings = [item for item in _safe_list(validation.get("warnings")) if isinstance(item, dict)]
    issues = [item for item in _safe_list(validation.get("issues")) if isinstance(item, dict)]
    if not active:
        status = "inactive"
    elif errors:
        status = "failed"
    elif validation.get("passed", True):
        status = "passed"
    else:
        status = "needs_review"

    selected = protocol.get("selected_archetype")
    if isinstance(selected, dict):
        selected_archetype = str(selected.get("archetype_id") or selected.get("id") or "")
    else:
        selected_archetype = str(selected or "")

    return {
        "active": active,
        "status": status,
        "selected_archetype": selected_archetype,
        "passed": bool(validation.get("passed", not errors)),
        "issue_count": len(issues) + len(errors),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "checked_constraints": list(validation.get("checked_constraints") or []),
        "capacity_budget": _safe_dict(protocol.get("capacity_budget")),
        "source_docs": list(protocol.get("source_docs") or [
            "Sub-70半程马拉松训练_图片OCR整理.md",
            "docs/half_marathon_hmp_protocol.md",
            "docs/product/half_marathon_hmp_protocol.md",
            "docs/half_marathon_source_audit.md",
            "docs/audits/half_marathon_source_audit.md",
        ]),
    }


def _workflow_repair_state(structured_training_plan: Optional[Dict[str, Any]], protocol_state: Dict[str, Any]) -> Dict[str, Any]:
    plan = _safe_dict(structured_training_plan)
    protocol = _safe_dict(plan.get("half_marathon_protocol"))
    validation = _safe_dict(plan.get("half_marathon_protocol_validation"))
    repair_log = [
        item
        for item in (_safe_list(validation.get("repair_log")) or _safe_list(protocol.get("repair_log")))
        if isinstance(item, dict)
    ]
    repair_suggestions = [item for item in _safe_list(validation.get("repair_suggestions")) if isinstance(item, dict)]
    return {
        "repair_applied": bool(validation.get("repair_applied") or repair_log),
        "repair_attempts": len(repair_log),
        "repair_log": repair_log,
        "repair_suggestions": repair_suggestions,
        "recheck_status": protocol_state.get("status", "inactive"),
    }


def _workflow_risk_state(
    risk_gate: Optional[Dict[str, Any]],
    protocol_recheck: Optional[Dict[str, Any]],
    status: str,
) -> Dict[str, Any]:
    gate = _safe_dict(risk_gate)
    recheck = _safe_dict(protocol_recheck)
    product_status = str(gate.get("product_status") or status or "not_evaluated")
    fail_closed = (
        gate.get("status") == "blocked"
        or product_status == "medical_referral"
        or recheck.get("allowed") is False
    )
    return {
        "status": str(gate.get("status") or "not_evaluated"),
        "risk_level": str(gate.get("risk_level") or "unknown"),
        "triggers": list(gate.get("triggers") or []),
        "adjustment_action": str(gate.get("adjustment_action") or "none"),
        "product_status": product_status,
        "decision_reason": str(gate.get("decision_reason") or ""),
        "fail_closed": bool(fail_closed),
    }


def _workflow_feedback_state(
    adaptive_feedback: Optional[Dict[str, Any]],
    adaptive_adjustment: Optional[Dict[str, Any]],
    risk_gate: Optional[Dict[str, Any]],
    protocol_recheck: Optional[Dict[str, Any]],
    feedback_id: Optional[str],
    feedback_persisted: bool,
) -> Dict[str, Any]:
    feedback = _safe_dict(adaptive_feedback)
    adjustment = _safe_dict(adaptive_adjustment)
    reason_codes = list(feedback.get("reason_codes") or adjustment.get("reason_codes") or [])
    has_feedback = bool(feedback or reason_codes or feedback_id)
    return {
        "has_feedback": has_feedback,
        "feedback_id": str(feedback_id or ""),
        "persisted": bool(feedback_persisted or feedback_id),
        "source": str(feedback.get("source") or ""),
        "reason_codes": reason_codes,
        "risk_gate": _safe_dict(risk_gate),
        "protocol_recheck": _safe_dict(protocol_recheck),
    }


def _workflow_audit_events(
    *,
    evidence_state: Dict[str, Any],
    protocol_state: Dict[str, Any],
    risk_state: Dict[str, Any],
    repair_state: Dict[str, Any],
    feedback_state: Dict[str, Any],
) -> List[Dict[str, Any]]:
    events = [
        {"event": "evidence_state", "status": evidence_state.get("status", "unknown")},
        {"event": "protocol_state", "status": protocol_state.get("status", "inactive")},
        {"event": "repair_state", "status": "applied" if repair_state.get("repair_applied") else "not_applied"},
        {"event": "risk_state", "status": risk_state.get("status", "not_evaluated")},
    ]
    if feedback_state.get("has_feedback"):
        events.append({
            "event": "feedback_state",
            "status": "persisted" if feedback_state.get("persisted") else "computed_only",
        })
    return events


def build_workflow_trace(
    *,
    query: str = "",
    workflow_kind: str = "",
    intent_type: str = "",
    status: str = "generated",
    evidence_bundle: Optional[Dict[str, Any]] = None,
    structured_training_plan: Optional[Dict[str, Any]] = None,
    risk_gate: Optional[Dict[str, Any]] = None,
    protocol_recheck: Optional[Dict[str, Any]] = None,
    adaptive_feedback: Optional[Dict[str, Any]] = None,
    adaptive_adjustment: Optional[Dict[str, Any]] = None,
    feedback_id: Optional[str] = None,
    feedback_persisted: bool = False,
    run_id: Optional[str] = None,
) -> WorkflowTrace:
    del query
    evidence_state = _workflow_evidence_state(evidence_bundle)
    protocol_state = _workflow_protocol_state(structured_training_plan)
    repair_state = _workflow_repair_state(structured_training_plan, protocol_state)
    risk_state = _workflow_risk_state(risk_gate, protocol_recheck, status)
    feedback_state = _workflow_feedback_state(
        adaptive_feedback,
        adaptive_adjustment,
        risk_gate,
        protocol_recheck,
        feedback_id,
        feedback_persisted,
    )
    return {
        "trace_version": WORKFLOW_TRACE_VERSION,
        "run_id": str(run_id or f"workflow-{uuid4().hex}"),
        "workflow_kind": str(workflow_kind or "qa"),
        "intent_type": str(intent_type or "qa"),
        "status": str(status or "generated"),
        "evidence_state": evidence_state,
        "protocol_state": protocol_state,
        "risk_state": risk_state,
        "repair_state": repair_state,
        "feedback_state": feedback_state,
        "audit_events": _workflow_audit_events(
            evidence_state=evidence_state,
            protocol_state=protocol_state,
            risk_state=risk_state,
            repair_state=repair_state,
            feedback_state=feedback_state,
        ),
    }


def normalize_workout_feedback(payload: Optional[Dict[str, Any]] = None, raw_text: str = "") -> WorkoutFeedback:
    payload = payload or {}
    raw_text = _normalize_text(raw_text)
    note_text = _normalize_text(payload.get("notes"))
    combined_text = f"{raw_text} {note_text}".lower()

    completion_status = _normalize_text(payload.get("completion_status")).lower()
    if completion_status not in {"completed", "partial", "missed"}:
        if _contains_any(combined_text, ["漏训", "未完成", "没完成", "skip", "missed"]):
            completion_status = "missed"
        elif _contains_any(combined_text, ["部分完成", "只完成", "完成了一半", "partial"]):
            completion_status = "partial"
        else:
            completion_status = "completed"

    completion_quality = _normalize_text(payload.get("completion_quality")).lower()
    if completion_quality not in {"good", "ok", "poor"}:
        if _contains_any(combined_text, ["状态很好", "感觉很好", "good", "顺利完成"]):
            completion_quality = "good"
        elif _contains_any(combined_text, ["状态差", "很吃力", "poor", "勉强完成"]):
            completion_quality = "poor"
        else:
            completion_quality = "ok"

    subjective_fatigue = _normalize_text(payload.get("subjective_fatigue")).lower()
    if subjective_fatigue not in {"low", "mild", "high"}:
        if _contains_any(combined_text, ["非常累", "很累", "疲劳很高", "高疲劳", "疲劳明显", "累爆了", "high fatigue"]):
            subjective_fatigue = "high"
        elif _contains_any(combined_text, ["有点累", "有些累", "轻微疲劳", "略累", "mild fatigue"]):
            subjective_fatigue = "mild"
        else:
            subjective_fatigue = "low"

    pain_status = _normalize_text(payload.get("pain_status")).lower()
    if pain_status not in {"none", "watch", "risk"}:
        # P1-6: 扩展疼痛关键词库，覆盖跑步专项伤病
        if _contains_any(combined_text, [
            "疼痛", "痛感明显", "刺痛", "膝盖疼", "膝盖痛", "脚踝疼",
            "跟腱疼", "跟腱痛", "跟腱不适",  # P1-6 新增
            "足底筋膜炎", "足跟痛", "plantar fasciitis",  # P1-6 新增
            "应力性骨折", "点压痛", "负重痛", "stress fracture", "骨裂",  # P1-6 新增
            "严重肿胀", "无法承重", "关节积液",  # P1-6 新增
            "pain", "injury",
        ]):
            pain_status = "risk"
        elif _contains_any(combined_text, [
            "有点不适", "轻微不适", "酸痛", "发紧",
            "跟腱酸", "膝盖酸",  # P1-6 新增：轻微的跟腱/膝盖不适
        ]):
            pain_status = "watch"
        else:
            pain_status = "none"

    sleep_quality = _normalize_text(payload.get("sleep_quality")).lower()
    if sleep_quality not in {"good", "ok", "poor"}:
        if _contains_any(combined_text, ["没睡好", "失眠", "睡眠差", "睡不好", "poor sleep"]):
            sleep_quality = "poor"
        elif _contains_any(combined_text, ["睡得不错", "睡得很好", "good sleep"]):
            sleep_quality = "good"
        else:
            sleep_quality = "ok"

    return {
        "completion_status": completion_status,
        "completion_quality": completion_quality,
        "subjective_fatigue": subjective_fatigue,
        "pain_status": pain_status,
        "sleep_quality": sleep_quality,
        "notes": note_text or raw_text,
    }


def derive_adaptive_reasons(feedback: Optional[Dict[str, Any]] = None, raw_text: str = "") -> List[AdaptiveReason]:
    normalized = normalize_workout_feedback(feedback, raw_text=raw_text)
    reasons: List[AdaptiveReason] = []

    if normalized.get("pain_status") == "risk":
        reasons.append(
            {
                "code": "pain_risk",
                "label": "疼痛风险",
                "severity": "high",
                "why": "反馈中出现疼痛或明显不适，当前更需要先控风险而不是继续堆训练量。",
            }
        )
    if normalized.get("subjective_fatigue") == "high":
        reasons.append(
            {
                "code": "high_fatigue",
                "label": "明显疲劳",
                "severity": "high",
                "why": "主观疲劳已到高位，继续按原计划执行容易放大恢复赤字。",
            }
        )
    elif (
        normalized.get("subjective_fatigue") == "mild"
        or normalized.get("completion_status") == "partial"
        or normalized.get("completion_quality") == "poor"
        or normalized.get("sleep_quality") == "poor"
        or normalized.get("pain_status") == "watch"
    ):
        reasons.append(
            {
                "code": "mild_fatigue",
                "label": "轻微疲劳",
                "severity": "medium",
                "why": "反馈显示训练完成度或恢复质量开始下降，适合先做轻量微调而不是硬顶。",
            }
        )
    if normalized.get("completion_status") == "missed":
        reasons.append(
            {
                "code": "missed_workout",
                "label": "漏训",
                "severity": "medium",
                "why": "本次关键课未完成，需要决定是顺延、替代还是直接跳过，避免后续堆课。",
            }
        )

    deduped: List[AdaptiveReason] = []
    seen_codes = set()
    for reason in reasons:
        code = reason["code"]
        if code in seen_codes:
            continue
        deduped.append(reason)
        seen_codes.add(code)
    return deduped


def build_adaptive_adjustment_contract(feedback: Optional[Dict[str, Any]] = None, raw_text: str = "") -> AdaptiveAdjustment:
    reasons = derive_adaptive_reasons(feedback, raw_text=raw_text)
    reason_codes = [reason["code"] for reason in reasons]
    if not reason_codes:
        return _build_no_adjustment_contract()

    primary_reason_code = reason_codes[0] if reason_codes else ""
    return {
        "adjustment_required": bool(reason_codes),
        "primary_reason_code": primary_reason_code,
        "reason_codes": reason_codes,
        "reasons": reasons,
        "next_day_adjustment": _compose_adaptive_field(reason_codes, "next_day_adjustment"),
        "weekly_adjustment": _compose_adaptive_field(reason_codes, "weekly_adjustment"),
        "alternative_workout": _compose_adaptive_field(reason_codes, "alternative_workout"),
        "risk_alert": _compose_adaptive_field(reason_codes, "risk_alert"),
        "rationale": _build_adaptive_rationale(reason_codes, reasons),
    }


class NutritionProfile(TypedDict):
    weight_kg: float
    sex: str                      # P1-8: "男" / "女" / "未提供"
    diet_preference: str          # "无偏好" / "素食" / "低碳水" / "高蛋白" / etc.
    allergies: List[str]          # 过敏食物列表
    daily_calories: int           # 日均目标摄入 (kcal)
    hydration_strategy: str       # 补水策略偏好
    sweat_rate: str               # P1-8: 出汗率 "少" / "中等" / "多"
    gi_sensitivity: str           # P1-8: 胃肠敏感度 "低" / "中等" / "高"
    diet_type: str                # P1-8: 饮食类型 "均衡" / "素食" / "生酮" / etc.


class UserProfile(TypedDict):
    experience_level: str
    weekly_mileage: float
    goal: str
    injury_history: List[str]
    last_race_time: str
    pb_800m: Optional[str]
    pb_1500m: Optional[str]
    pb_5k: Optional[str]
    pb_10k: Optional[str]
    pb_half: Optional[str]
    pb_full: Optional[str]
    lthr: Optional[int]
    t_pace: Optional[str]
    hr_zones: Optional[Dict[str, str]]
    pace_zones: Optional[Dict[str, str]]
    target_race_date: Optional[str]
    plan_duration_weeks: Optional[int]
    sex: Optional[str]            # P1-8: 性别 "男" / "女"
    weight_kg: Optional[float]    # P1-8: 体重 (kg)
    nutrition_profile: Optional[NutritionProfile]
    long_term_memory: Optional[List[str]]
    verified_facts: Optional[Dict[str, Any]]


class AuditScores(TypedDict):
    consistency: int
    safety: int
    roi: int
    summary: str
    score_sources: Dict[str, Any]


class ReportTaskResult(BaseModel):
    task_id: str
    objective: str
    findings: Dict[str, Any]
    mechanisms: Optional[List[Dict[str, str]]] = None
    conclusion: Optional[str] = None


class EvidenceSource(BaseModel):
    document: str
    pages: List[int]


class Evidence(TypedDict):
    """统一证据数据结构"""
    evidence_id: str
    kind: str  # vector | graph | fusion
    source_file: str
    page: int
    chunk_id: str
    snippet: str
    text: str
    vector_score: float
    retrieval_score: float
    graph_confidence: float
    entity_overlap: float
    fusion_bonus: float
    hybrid_score: float
    citation_label: str  # [1], [2] 等
    trace: Dict[str, Any]


class EvidenceBundleItem(TypedDict, total=False):
    evidence_id: str
    citation_label: str
    tier: str
    source_file: str
    source_path: str
    page: Optional[int]
    chunk_id: str
    snippet: str
    text: str
    score: float
    trace: Dict[str, Any]


class EvidenceBundle(TypedDict, total=False):
    query: str
    evidence_items: List[EvidenceBundleItem]
    health: Dict[str, Any]


class ProfessionalReport(BaseModel):
    report_metadata: Dict[str, str] = Field(default_factory=lambda: {"version": "2.0", "mode": "SUBAGENT"})
    analysis_framework: Dict[str, Any]
    execution_steps: List[ReportTaskResult]
    audit_block: Dict[str, Any]
    evidence_base: List[EvidenceSource]


class EntityList(BaseModel):
    entities: List[str] = Field(description="核心实体名词列表")


class IntegratedState(TypedDict):
    query: str
    mode: str
    intent_type: str
    workflow_kind: str
    selected_entities: List[str]
    category: str
    subtasks: List[Dict[str, Any]]
    draft_plan: str
    review_feedback: str
    is_approved: bool
    iteration_count: int
    hard_rule_retry_count: int  # P6: 硬规则打回上限 1
    rag_audit_retry_count: int  # P6: RAG 审核打回上限 2
    final_report: str
    structured_training_plan: Optional[Dict[str, Any]]
    structured_report: Optional[Dict[str, Any]]
    reasoning_log: Annotated[List[str], operator.add]
    execution_trace: Annotated[List[TraceStep], operator.add]  # AgentDoG P0: 结构化节点执行轨迹
    audit_diagnosis: Optional[Dict[str, Any]]  # AgentDoG P0: 三元组诊断 {risk_source, failure_mode, real_world_harm, targeted_fix}
    safety_constraints: List[Dict[str, Any]]  # P1: KG constrains/risks 边
    gate_hits: List[Dict[str, Any]]
    rag_sources: List[Dict[str, Any]]
    ranked_evidence: List[Evidence]
    evidence_bundle: EvidenceBundle
    graph_context: str
    wiki_context: str
    mermaid_graph: str
    token_usage: TokenUsage
    audit_scores: AuditScores
    roi_history: List[float]
    risk_alert: str
    entities: List[str]
    guided_questions: List[str]
    user_profile: UserProfile
    adaptive_feedback: AdaptiveFeedback
    adaptive_adjustment: AdaptiveAdjustment
    workflow_trace: WorkflowTrace
    requested_weeks: Optional[int]
    missing_fields: List[str]
    enhancement_missing_fields: List[str]
    missing_info_status: str
    history: List[Dict[str, str]]
    used_fallback: bool
    fallback_reason: str
    draft_ready: bool
    validation_result: Dict[str, Any]
    repair_suggestions: List[Dict[str, Any]]
    repair_attempts: int
    nutritionist_done: bool
    needs_nutrition_review: bool
    psychologist_done: bool


WorkingState = IntegratedState
