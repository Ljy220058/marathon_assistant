import operator
from typing import Annotated, Any, Dict, List, Optional, TypedDict

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


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _contains_any(text: str, keywords: List[str]) -> bool:
    return any(keyword in text for keyword in keywords)


_ADAPTIVE_RULE_LIBRARY: Dict[str, Dict[str, str]] = {
    "pain_risk": {
        "next_day_adjustment": "次日暂停跑步主课，改为休息或 30-40 分钟无冲击交叉训练，并优先处理疼痛部位。",
        "weekly_adjustment": "本周取消质量课加量，长距离与强度课至少下调一个档位，先把目标切回安全完赛/安全训练。",
        "alternative_workout": "可替代为自行车、椭圆机或游泳等低冲击有氧，并配合灵活性与激活训练。",
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

    severe_keywords = {
        "chest_pain": ["\u80f8\u75db", "\u80f8\u95f7", "chest pain", "chest tightness"],
        "dizziness_or_syncope": ["\u5934\u6655", "\u7729\u6655", "\u6655\u53a5", "\u6655\u5012", "dizzy", "faint"],
        "heat_illness": ["\u4e2d\u6691", "\u70ed\u5c04\u75c5", "\u9ad8\u6e29\u5f02\u5e38", "heat illness", "heatstroke"],
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
    severe = any(code in triggers for code in {"chest_pain", "dizziness_or_syncope", "heat_illness"})
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
        if _contains_any(combined_text, ["疼痛", "痛感明显", "刺痛", "膝盖疼", "脚踝疼", "pain", "injury"]):
            pain_status = "risk"
        elif _contains_any(combined_text, ["有点不适", "轻微不适", "酸痛", "发紧"]):
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
    final_report: str
    structured_training_plan: Optional[Dict[str, Any]]
    structured_report: Optional[Dict[str, Any]]
    reasoning_log: Annotated[List[str], operator.add]
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


WorkingState = IntegratedState
