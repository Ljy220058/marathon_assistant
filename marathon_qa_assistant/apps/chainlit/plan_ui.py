from typing import Any, Dict, List, Tuple

from marathon_qa_assistant.core.state_models import (
    build_adaptive_adjustment_contract,
    derive_adaptive_reasons,
    normalize_workout_feedback,
)
from marathon_qa_assistant.core.zone_constants import sanitize_all_pace as _strip_pace


def _safe_text(value: Any, fallback: str = "—") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _safe_list(value: Any, limit: int = 5) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item or "").strip() for item in value if str(item or "").strip()][:limit]


def _format_constraint_detail(constraint: Any) -> str:
    if not isinstance(constraint, dict):
        return _safe_text(constraint, "")
    rule = _safe_text(constraint.get("rule"), "")
    status = _safe_text(constraint.get("status"), "")
    message = _safe_text(constraint.get("message"), "")
    parts = [part for part in [rule, status, message] if part]
    return " / ".join(parts)


def _format_trace_detail(trace: Any) -> str:
    if not isinstance(trace, dict):
        return _safe_text(trace, "")
    requested = _safe_text(trace.get("requested"), "")
    status = _safe_text(trace.get("status"), "")
    warnings = "；".join(_safe_list(trace.get("warnings"), limit=3))
    parts = [part for part in [requested, status, warnings] if part]
    return " / ".join(parts)


def _format_evidence_badges(evidence_ids: Any) -> str:
    normalized_ids = [int(ev_id) for ev_id in (evidence_ids or []) if str(ev_id).isdigit()]
    return " ".join(f"`[{ev_id}]`" for ev_id in normalized_ids)


def extract_entry_status_context(state: Dict[str, Any]) -> Dict[str, Any]:
    structured_report = state.get("structured_report") or {}
    if not isinstance(structured_report, dict):
        return {}

    structured_plan = structured_report.get("structured_training_plan") or {}
    if not isinstance(structured_plan, dict):
        structured_plan = {}

    plan_meta = structured_plan.get("plan_meta") or {}
    if not isinstance(plan_meta, dict):
        plan_meta = {}

    overview = structured_report.get("training_plan_overview") or {}
    if not isinstance(overview, dict):
        overview = {}

    week_sections = structured_report.get("training_plan_weeks") or []
    if not isinstance(week_sections, list):
        week_sections = []
    if not week_sections:
        raw_weeks = structured_plan.get("week_plans") or []
        if isinstance(raw_weeks, list):
            week_sections = [item for item in raw_weeks if isinstance(item, dict)]
    if not week_sections:
        return {}

    current_week = next(
        (week for week in week_sections if isinstance(week, dict) and int(week.get("week_index") or 0) == 1),
        None,
    ) or next((week for week in week_sections if isinstance(week, dict)), None)
    if not current_week:
        return {}

    days = [day for day in (current_week.get("days") or []) if isinstance(day, dict)]
    selected_day = next(
        (day for day in days if str(day.get("training_type") or "").strip() and str(day.get("training_type") or "").strip() != "休息"),
        days[0] if days else {},
    )
    day_label = _safe_text(selected_day.get("day"), "当前") if isinstance(selected_day, dict) else "当前"
    training_type = _safe_text(selected_day.get("training_type"), "待查看") if isinstance(selected_day, dict) else "待查看"
    main_set = _strip_pace(_safe_text(selected_day.get("main_set"), "查看本周卡片") if isinstance(selected_day, dict) else "查看本周卡片")
    total_km = 0.0
    if isinstance(selected_day, dict):
        for key in ("warmup_km", "main_km", "cooldown_km"):
            try:
                total_km += float(selected_day.get(key) or 0)
            except (TypeError, ValueError):
                pass

    week_index = int(current_week.get("week_index") or 1)
    total_weeks = int(plan_meta.get("actual_weeks") or plan_meta.get("requested_weeks") or len(week_sections))
    training_day_count = int(current_week.get("training_day_count") or sum(1 for day in days if str(day.get("training_type") or "").strip() != "休息"))
    phase = _safe_text(current_week.get("phase"), _safe_text(overview.get("current_phase"), "训练期"))
    load_level = _safe_text(current_week.get("load_level"), "—")

    return {
        "week_index": week_index,
        "total_weeks": total_weeks,
        "phase": phase,
        "load_level": load_level,
        "day_label": day_label,
        "training_type": training_type,
        "main_set": main_set,
        "total_km": total_km,
        "training_day_count": training_day_count,
        "week_goal": _safe_text(current_week.get("week_goal")),
    }


def render_minimal_plan_summary_md(final_state: Dict[str, Any]) -> str:
    """plan 意图下的轻量摘要，避免与 CustomElement 组件重复输出。"""
    structured_report = final_state.get("structured_report") or {}
    if not isinstance(structured_report, dict):
        structured_report = {}

    meta = (structured_report.get("structured_training_plan") or {}).get("plan_meta", {}) or {}
    overview = structured_report.get("training_plan_overview") or {}
    if not isinstance(overview, dict):
        overview = {}
    weeks = structured_report.get("training_plan_weeks") or []
    if not isinstance(weeks, list):
        weeks = []

    plan_type = _safe_text(meta.get("plan_type"), "—")
    actual_weeks = int(meta.get("actual_weeks") or len(weeks) or 0)
    goal = _safe_text(meta.get("goal"), _safe_text(overview.get("goal"), "训练计划"))
    hmp_panel = structured_report.get("half_marathon_protocol_panel") or {}
    hmp_line = ""
    if isinstance(hmp_panel, dict) and hmp_panel.get("active"):
        selected = hmp_panel.get("selected_archetype") or {}
        validation = hmp_panel.get("validation_summary") or {}
        status_label = {
            "passed": "通过",
            "warning": "有提醒",
            "error": "有错误",
        }.get(str(hmp_panel.get("status") or ""), _safe_text(hmp_panel.get("status"), "未知"))
        hmp_line = (
            f"- **HMP 协议**：{_safe_text(selected.get('label'), '半马画像已识别')} · "
            f"验证{status_label} · "
            f"{int(validation.get('error_count') or 0)} 错误 / {int(validation.get('warning_count') or 0)} 提醒"
        )

    lines = [
        "### ✅ 训练计划已生成",
        "",
        f"- **类型**：{plan_type} · **周数**：{actual_weeks} 周 · **目标**：{goal}",
    ]
    if hmp_line:
        lines.append(hmp_line)
    lines.extend(
        [
            "",
            "> 点击「📄 查看完整计划」查看原始报告。",
            "",
        ]
    )
    return "\n".join(lines).strip()


def render_entry_status_md(context: Dict[str, Any]) -> str:
    if not context:
        return ""

    total_km = float(context.get("total_km") or 0)
    distance_text = f" · {total_km:.1f}km" if total_km > 0 else ""
    current_task = (
        f"{_safe_text(context.get('day_label'))}："
        f"{_safe_text(context.get('training_type'))}{distance_text} · {_safe_text(context.get('main_set'))}"
    )
    return "\n".join(
        [
            "### 🧭 训练入口状态",
            "",
            (
                f"第 {int(context.get('week_index') or 1)} / {int(context.get('total_weeks') or 1)} 周 · "
                f"{_safe_text(context.get('phase'))} · {_safe_text(context.get('load_level'))}"
            ),
            "",
            f"**当前建议**：{current_task}",
            f"**本周摘要**：{int(context.get('training_day_count') or 0)} 个训练日 · {_safe_text(context.get('week_goal'))}",
            "",
            "优先看当前周摘要；需要时再展开每日详情、解释和证据。",
        ]
    ).strip()



def extract_first_week_execution_context(state: Dict[str, Any]) -> Dict[str, Any]:
    structured_report = state.get("structured_report") or {}
    if not isinstance(structured_report, dict):
        return {}

    structured_plan = structured_report.get("structured_training_plan") or {}
    if not isinstance(structured_plan, dict):
        structured_plan = {}

    overview = structured_report.get("training_plan_overview") or {}
    if not isinstance(overview, dict):
        overview = {}

    week_sections = structured_report.get("training_plan_weeks") or []
    if not isinstance(week_sections, list):
        week_sections = []

    if not week_sections:
        raw_weeks = structured_plan.get("week_plans") or []
        if isinstance(raw_weeks, list):
            week_sections = [item for item in raw_weeks if isinstance(item, dict)]

    if not week_sections:
        return {}

    first_week = next(
        (
            week
            for week in week_sections
            if isinstance(week, dict) and int(week.get("week_index") or 0) == 1
        ),
        None,
    )
    if not first_week:
        first_week = next((week for week in week_sections if isinstance(week, dict)), None)
    if not first_week:
        return {}

    first_week_actions = overview.get("first_week_actions") or structured_plan.get("first_week_actions") or []
    key_workouts = first_week.get("key_workouts") or []
    action_suggestions = first_week.get("action_suggestions") or []

    normalized_actions = [_strip_pace(str(item).strip()) for item in first_week_actions if str(item or "").strip()]
    normalized_key_workouts = [_strip_pace(str(item).strip()) for item in key_workouts if str(item or "").strip()]
    normalized_action_suggestions = [_strip_pace(str(item).strip()) for item in action_suggestions if str(item or "").strip()]

    return {
        "week_index": int(first_week.get("week_index") or 1),
        "goal": _safe_text(first_week.get("week_goal")),
        "phase": _safe_text(first_week.get("phase")),
        "load_level": _safe_text(first_week.get("load_level")),
        "execution_reminder": _safe_text(first_week.get("execution_reminder")),
        "first_week_actions": normalized_actions[:3],
        "key_workouts": normalized_key_workouts[:3],
        "action_suggestions": normalized_action_suggestions[:3],
    }


def render_first_week_execution_md(context: Dict[str, Any]) -> str:
    if not context:
        return ""

    lines: List[str] = [
        "### 🚀 首周执行入口",
        "",
        f"**第 {context.get('week_index', 1)} 周阶段**：{_safe_text(context.get('phase'))} / {_safe_text(context.get('load_level'))}",
        f"**本周目标**：{_safe_text(context.get('goal'))}",
        "",
    ]

    first_week_actions = context.get("first_week_actions") or []
    if first_week_actions:
        lines.extend(["**先做什么**", ""])
        for action in first_week_actions:
            lines.append(f"- {_safe_text(action)}")
        lines.append("")

    key_workouts = context.get("key_workouts") or []
    if key_workouts:
        lines.extend(["**本周关键训练**", ""])
        for workout in key_workouts:
            lines.append(f"- {_safe_text(workout)}")
        lines.append("")

    action_suggestions = context.get("action_suggestions") or []
    if action_suggestions:
        lines.extend(["**执行提示**", ""])
        for suggestion in action_suggestions:
            lines.append(f"- {_safe_text(suggestion)}")
        lines.append("")

    lines.append(f"**执行提醒**：{_safe_text(context.get('execution_reminder'))}")
    lines.extend(["", "每日详情、解释和证据默认收起，需要时再展开。"])
    return "\n".join(lines).strip()


def extract_phase_overview_context(state: Dict[str, Any]) -> Dict[str, Any]:
    structured_plan = state.get("structured_training_plan") or {}
    if not isinstance(structured_plan, dict):
        structured_plan = {}

    phase_summary = structured_plan.get("phase_summary") or []
    if not isinstance(phase_summary, list):
        phase_summary = []

    if not phase_summary:
        return {}

    plan_meta = structured_plan.get("plan_meta") or {}
    if not isinstance(plan_meta, dict):
        plan_meta = {}

    phases = []
    for item in phase_summary:
        if not isinstance(item, dict):
            continue
        start_week = int(item.get("start_week") or 0)
        end_week = int(item.get("end_week") or 0)
        phase_name = _safe_text(item.get("phase"))
        objective = _safe_text(item.get("objective"))
        week_count = max(0, end_week - start_week + 1)
        if not phase_name or week_count <= 0:
            continue
        phases.append({
            "phase": phase_name,
            "start_week": start_week,
            "end_week": end_week,
            "week_count": week_count,
            "objective": objective,
        })

    if len(phases) < 2:
        return {}

    return {
        "actual_weeks": int(plan_meta.get("actual_weeks") or 0),
        "phases": phases,
        "phase_count": len(phases),
        "goal": _safe_text(plan_meta.get("goal")),
    }


def render_phase_overview_md(context: Dict[str, Any]) -> str:
    if not context:
        return ""

    phases = context.get("phases") or []
    actual_weeks = int(context.get("actual_weeks") or 0)
    goal = _safe_text(context.get("goal"))

    lines: List[str] = [
        "## 📊 训练周期总览",
        "",
    ]
    if actual_weeks:
        lines.append(f"**计划周期**：{actual_weeks} 周")
    if goal and goal != "—":
        lines.append(f"**训练目标**：{goal}")
    lines.extend(["", ""])

    lines.extend([
        "| 阶段 | 周数 | 目标 |",
        "|------|------|------|",
    ])

    for phase in phases:
        phase_name = _safe_text(phase.get("phase"))
        start_week = int(phase.get("start_week") or 0)
        end_week = int(phase.get("end_week") or 0)
        objective = _safe_text(phase.get("objective"))
        lines.append(f"| {phase_name} | 第{start_week}-{end_week}周 | {objective} |")

    lines.extend(["", ""])
    lines.append("请选择要生成详细课表的阶段：")
    return "\n".join(lines).strip()


_FEEDBACK_KEY_ALIASES = {
    "完成状态": "completion_status",
    "状态": "completion_status",
    "completion_status": "completion_status",
    "完成质量": "quality",
    "质量": "quality",
    "completion_quality": "quality",
    "疲劳": "fatigue",
    "主观疲劳": "fatigue",
    "fatigue": "fatigue",
    "不适": "discomfort",
    "疼痛": "discomfort",
    "疼痛/不适": "discomfort",
    "discomfort": "discomfort",
    "睡眠": "sleep_quality",
    "睡眠质量": "sleep_quality",
    "sleep": "sleep_quality",
    "sleep_quality": "sleep_quality",
    "备注": "notes",
    "说明": "notes",
    "主观记录": "notes",
    "note": "notes",
    "notes": "notes",
}

_STATUS_ALIASES = {
    "已完成": ("completed", True, "已完成"),
    "完成": ("completed", True, "已完成"),
    "completed": ("completed", True, "已完成"),
    "部分完成": ("partial", True, "部分完成"),
    "partial": ("partial", True, "部分完成"),
    "未完成": ("missed", False, "未完成"),
    "漏训": ("missed", False, "未完成"),
    "missed": ("missed", False, "未完成"),
}

_QUALITY_ALIASES = {
    "好": ("good", "好"),
    "good": ("good", "好"),
    "顺利": ("good", "好"),
    "一般": ("ok", "一般"),
    "中": ("ok", "一般"),
    "ok": ("ok", "一般"),
    "还行": ("ok", "一般"),
    "差": ("poor", "差"),
    "poor": ("poor", "差"),
    "吃力": ("poor", "差"),
}

_FATIGUE_ALIASES = {
    "低": ("low", "低"),
    "low": ("low", "低"),
    "轻": ("mild", "中"),
    "中": ("mild", "中"),
    "一般": ("mild", "中"),
    "mild": ("mild", "中"),
    "高": ("high", "高"),
    "high": ("high", "高"),
    "很累": ("high", "高"),
}

_DISCOMFORT_ALIASES = {
    "无": ("none", "无"),
    "none": ("none", "无"),
    "没有": ("none", "无"),
    "轻微": ("watch", "轻微"),
    "轻": ("watch", "轻微"),
    "watch": ("watch", "轻微"),
    "明显": ("risk", "明显"),
    "风险": ("risk", "明显"),
    "risk": ("risk", "明显"),
}

_SLEEP_ALIASES = {
    "好": ("good", "好"),
    "good": ("good", "好"),
    "一般": ("ok", "一般"),
    "中": ("ok", "一般"),
    "ok": ("ok", "一般"),
    "差": ("poor", "差"),
    "poor": ("poor", "差"),
    "不好": ("poor", "差"),
}


def _find_alias_value(raw_value: Any, aliases: Dict[str, tuple[str, str]], default_code: str, default_label: str) -> tuple[str, str]:
    text = str(raw_value or "").strip().lower()
    if not text:
        return default_code, default_label
    if text in aliases:
        return aliases[text]
    for alias, normalized in aliases.items():
        if alias in text:
            return normalized
    return default_code, default_label


def _parse_feedback_fields(raw_text: str) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    for raw_line in str(raw_text or "").splitlines():
        line = raw_line.strip().lstrip("-").strip()
        if not line:
            continue
        delimiter = "：" if "：" in line else ":" if ":" in line else None
        if not delimiter:
            continue
        key, value = line.split(delimiter, 1)
        normalized_key = _FEEDBACK_KEY_ALIASES.get(key.strip().lower()) or _FEEDBACK_KEY_ALIASES.get(key.strip())
        if not normalized_key:
            continue
        fields[normalized_key] = value.strip()
    return fields


def render_training_feedback_input_md(context: Dict[str, Any], completed: bool = True) -> str:
    workout = _safe_text((context.get("key_workouts") or ["首周训练"])[0], "首周训练")
    status_text = "已完成" if completed else "未完成"
    lines = [
        "### 📝 快速训练反馈",
        "",
        f"**本次训练**：{workout}",
        f"**反馈状态**：{status_text}",
        "",
        "请复制下面模板，按实际情况修改后直接发送：",
        "",
        "```text",
        f"完成状态：{status_text}",
        "完成质量：一般",
        "疲劳：中",
        "不适：无",
        "睡眠：一般",
        "备注：例如 周二主课完成，但小腿有点紧，昨晚睡眠一般",
        "```",
        "",
        "可只修改你想改的项；未填写项会按中性默认值处理。",
    ]
    return "\n".join(lines).strip()


def build_training_feedback_bundle(
    context: Dict[str, Any],
    raw_text: str = "",
    default_completed: bool = True,
) -> Dict[str, Any]:
    fields = _parse_feedback_fields(raw_text)
    default_status = "已完成" if default_completed else "未完成"
    status_code, completed, status_label = _find_alias_value(
        fields.get("completion_status", default_status),
        _STATUS_ALIASES,
        "completed" if default_completed else "missed",
        default_status,
    )
    quality_code, quality_label = _find_alias_value(fields.get("quality"), _QUALITY_ALIASES, "ok", "一般")
    fatigue_code, fatigue_label = _find_alias_value(fields.get("fatigue"), _FATIGUE_ALIASES, "mild", "中")
    discomfort_code, discomfort_label = _find_alias_value(fields.get("discomfort"), _DISCOMFORT_ALIASES, "none", "无")
    sleep_code, sleep_label = _find_alias_value(fields.get("sleep_quality"), _SLEEP_ALIASES, "ok", "一般")

    raw_note = str(fields.get("notes") or "").strip()
    if raw_note:
        note_text = raw_note
    elif str(raw_text or "").strip() and not fields:
        note_text = str(raw_text).strip()
    elif completed:
        note_text = "本次已按快速反馈模板提交。"
    else:
        note_text = "本次训练未完成，已按快速反馈模板提交。"

    synthesized_raw_text = "\n".join(
        [
            f"完成状态：{status_label}",
            f"完成质量：{quality_label}",
            f"疲劳：{fatigue_label}",
            f"不适：{discomfort_label}",
            f"睡眠：{sleep_label}",
            f"备注：{note_text}",
        ]
    ).strip()

    workout_feedback = normalize_workout_feedback(
        {
            "completion_status": status_code,
            "completion_quality": quality_code,
            "subjective_fatigue": fatigue_code,
            "pain_status": discomfort_code,
            "sleep_quality": sleep_code,
            "notes": note_text,
        },
        raw_text=synthesized_raw_text,
    )
    reasons = derive_adaptive_reasons(workout_feedback, raw_text=synthesized_raw_text)
    adaptive_adjustment = build_adaptive_adjustment_contract(workout_feedback, raw_text=synthesized_raw_text)
    card = build_training_feedback_card(
        context,
        {
            "completed": completed,
            "completion_status_code": status_code,
            "completion_status": status_label,
            "quality": quality_label,
            "fatigue": fatigue_label,
            "discomfort": discomfort_label,
            "sleep_quality": sleep_label,
            "subjective_note": note_text,
        },
    )
    return {
        "card": card,
        "workout_feedback": workout_feedback,
        "adaptive_feedback": {
            "workout_feedback": workout_feedback,
            "reason_codes": [reason["code"] for reason in reasons],
            "reasons": reasons,
            "raw_text": synthesized_raw_text,
            "source": "training_feedback_form",
        },
        "adaptive_adjustment": adaptive_adjustment,
    }



def build_training_feedback_card(
    context: Dict[str, Any],
    completion: Dict[str, Any] | None = None,
):
    completion = completion or {}
    key_workouts = context.get("key_workouts") or []
    action_suggestions = context.get("action_suggestions") or []
    first_workout = _safe_text(completion.get("workout") or (key_workouts[0] if key_workouts else "首周训练"))
    status_code = _safe_text(completion.get("completion_status_code"), "completed").lower()
    completed = bool(completion.get("completed", status_code != "missed"))
    completion_status = _safe_text(
        completion.get("completion_status"),
        "部分完成" if status_code == "partial" else ("已完成" if completed else "未完成"),
    )
    quality = _safe_text(completion.get("quality"), "已完成，质量待补充")
    fatigue = _safe_text(completion.get("fatigue"), "待补充")
    discomfort = _safe_text(completion.get("discomfort"), "无明显不适")
    sleep_quality = _safe_text(completion.get("sleep_quality"), "一般")
    subjective_note = _safe_text(completion.get("subjective_note"), "本次已记录为完成训练。")
    next_hint = _safe_text(
        completion.get("next_hint") or (action_suggestions[0] if action_suggestions else context.get("execution_reminder")),
        "优先完成下一次计划内训练，并观察恢复状态。",
    )
    recovery_advice = _safe_text(
        completion.get("recovery_advice"),
        "完成后 24 小时内优先补水、补碳水和保证睡眠；如疲劳或不适升高，下一次训练先降强度。",
    )

    return {
        "card_type": "training_feedback_card",
        "week_index": int(context.get("week_index") or 1),
        "phase": _safe_text(context.get("phase")),
        "workout": first_workout,
        "completed": completed,
        "completion_status": completion_status,
        "quality": quality,
        "fatigue": fatigue,
        "discomfort": discomfort,
        "sleep_quality": sleep_quality,
        "subjective_note": subjective_note,
        "recovery_advice": recovery_advice,
        "next_training_hint": next_hint,
    }



def render_training_feedback_card_md(card: Dict[str, Any]) -> str:
    if not card:
        return ""

    lines: List[str] = [
        "### ✅ 训练反馈卡",
        "",
        f"**周次 / 阶段**：第 {int(card.get('week_index') or 1)} 周 / {_safe_text(card.get('phase'))}",
        f"**本次训练**：{_safe_text(card.get('workout'))}",
        f"**完成状态**：{_safe_text(card.get('completion_status'))}",
        f"**完成质量**：{_safe_text(card.get('quality'))}",
        f"**主观疲劳**：{_safe_text(card.get('fatigue'))}",
        f"**疼痛/不适**：{_safe_text(card.get('discomfort'))}",
        f"**睡眠质量**：{_safe_text(card.get('sleep_quality'))}",
        "",
        f"**主观记录**：{_safe_text(card.get('subjective_note'))}",
        f"**恢复建议**：{_safe_text(card.get('recovery_advice'))}",
        f"**下一次训练提醒**：{_safe_text(card.get('next_training_hint'))}",
    ]
    return "\n".join(lines).strip()


def _safe_reason_labels(adaptive_adjustment: Dict[str, Any]) -> List[str]:
    labels = []
    for reason in adaptive_adjustment.get("reasons", []) or []:
        if not isinstance(reason, dict):
            continue
        label = str(reason.get("label") or "").strip()
        if label and label not in labels:
            labels.append(label)
    if labels:
        return labels

    for code in adaptive_adjustment.get("reason_codes", []) or []:
        normalized = str(code or "").strip()
        if normalized and normalized not in labels:
            labels.append(normalized)
    return labels


def extract_adaptive_adjustment_context(state: Dict[str, Any]) -> Dict[str, Any]:
    structured_report = state.get("structured_report") or {}
    if not isinstance(structured_report, dict):
        structured_report = {}

    adaptive_adjustment = structured_report.get("adaptive_adjustment") or state.get("adaptive_adjustment") or {}
    if not isinstance(adaptive_adjustment, dict) or not adaptive_adjustment:
        return {}

    reason_labels = _safe_reason_labels(adaptive_adjustment)
    reasons_text = "、".join(reason_labels) if reason_labels else "未触发"
    return {
        "adjustment_required": bool(adaptive_adjustment.get("adjustment_required")),
        "primary_reason_code": _safe_text(adaptive_adjustment.get("primary_reason_code"), ""),
        "reason_labels": reason_labels,
        "reasons_text": reasons_text,
        "next_day_adjustment": _safe_text(adaptive_adjustment.get("next_day_adjustment")),
        "weekly_adjustment": _safe_text(adaptive_adjustment.get("weekly_adjustment")),
        "alternative_workout": _safe_text(adaptive_adjustment.get("alternative_workout")),
        "risk_alert": _safe_text(adaptive_adjustment.get("risk_alert"), ""),
        "rationale": _safe_text(adaptive_adjustment.get("rationale")),
    }


def build_adaptive_adjustment_card(context: Dict[str, Any]) -> Dict[str, Any]:
    if not context:
        return {}

    adjustment_required = bool(context.get("adjustment_required"))
    reason_labels = context.get("reason_labels") or []
    badge = "已触发" if adjustment_required else "无需调整"
    headline = "建议优先执行下列调整，再决定是否回到原计划。" if adjustment_required else "当前可按原计划推进，继续观察恢复状态。"
    next_step_hint = (
        "如果下一次训练后仍有疲劳、疼痛或漏训，请继续补充反馈，我会再做一轮调整。"
        if adjustment_required
        else "若后续出现疲劳、疼痛或漏训，再次点击自适应调整并补充反馈即可。"
    )

    return {
        "card_type": "adaptive_adjustment_card",
        "badge": badge,
        "headline": headline,
        "adjustment_required": adjustment_required,
        "primary_reason_code": _safe_text(context.get("primary_reason_code"), ""),
        "reason_labels": reason_labels,
        "reasons_text": _safe_text(context.get("reasons_text"), "未触发"),
        "next_day_adjustment": _safe_text(context.get("next_day_adjustment")),
        "weekly_adjustment": _safe_text(context.get("weekly_adjustment")),
        "alternative_workout": _safe_text(context.get("alternative_workout")),
        "risk_alert": _safe_text(context.get("risk_alert"), ""),
        "rationale": _safe_text(context.get("rationale")),
        "next_step_hint": next_step_hint,
    }


def render_adaptive_adjustment_card_md(card: Dict[str, Any]) -> str:
    if not card:
        return ""

    lines: List[str] = [
        "### 🔁 自适应调整卡",
        "",
        f"**状态**：{_safe_text(card.get('badge'))}",
        f"**触发原因**：{_safe_text(card.get('reasons_text'))}",
        f"**处理结论**：{_safe_text(card.get('headline'))}",
        "",
        "**明日调整**",
        "",
        f"- {_safe_text(card.get('next_day_adjustment'))}",
        "",
        "**本周微调**",
        "",
        f"- {_safe_text(card.get('weekly_adjustment'))}",
        "",
        "**替代训练**",
        "",
        f"- {_safe_text(card.get('alternative_workout'))}",
    ]

    risk_alert = str(card.get("risk_alert") or "").strip()
    if risk_alert:
        lines.extend(["", "**风险提示**", "", f"- {risk_alert}"])

    lines.extend(
        [
            "",
            "**为什么这么调**",
            "",
            f"- {_safe_text(card.get('rationale'))}",
            "",
            f"**下一步**：{_safe_text(card.get('next_step_hint'))}",
        ]
    )
    return "\n".join(lines).strip()


def extract_training_explanation_context(state: Dict[str, Any], week_index: int = 1) -> Dict[str, Any]:
    structured_report = state.get("structured_report") or {}
    if not isinstance(structured_report, dict):
        structured_report = {}

    panel = structured_report.get("training_explanation_panel") or {}
    if not isinstance(panel, dict) or not panel:
        return {}

    weeks = [item for item in (panel.get("weeks") or []) if isinstance(item, dict)]
    if not weeks:
        return {}

    target_week = next(
        (item for item in weeks if int(item.get("week_index") or 0) == int(week_index or 1)),
        None,
    )
    if not target_week:
        target_week = weeks[0]
    if not target_week:
        return {}

    return {
        "week_index": int(target_week.get("week_index") or week_index or 1),
        "phase": _safe_text(target_week.get("phase")),
        "load_level": _safe_text(target_week.get("load_level")),
        "total_weeks": len(weeks),
        "available_week_indexes": [
            int(item.get("week_index") or 0)
            for item in weeks
            if int(item.get("week_index") or 0) > 0
        ],
        "coverage_ratio": float(panel.get("coverage_ratio") or 0),
        "audit_summary": _safe_text(panel.get("audit_summary")),
        "summary": _safe_text(panel.get("summary")),
        "items": [
            {
                "title": _safe_text(item.get("title")),
                "why_scheduled": _safe_text(item.get("why_scheduled")),
                "primary_target": _safe_text(item.get("primary_target")),
                "risk_alert": _safe_text(item.get("risk_alert")),
                "alternative_workout": _safe_text(item.get("alternative_workout")),
                "decision_summary": _safe_text(item.get("decision_summary")),
                "template_id": _safe_text(item.get("template_id"), ""),
                "status": _safe_text(item.get("status"), ""),
                "explanation_source": _safe_text(item.get("explanation_source"), ""),
                "target_labels": _safe_list(item.get("target_labels"), limit=5),
                "warnings": _safe_list(item.get("warnings"), limit=3),
                "adjustments": _safe_list(item.get("adjustments"), limit=3),
                "constraints": [
                    constraint
                    for constraint in (item.get("constraints") or [])
                    if isinstance(constraint, dict) or str(constraint or "").strip()
                ][:3],
                "decision_trace": [
                    trace
                    for trace in (item.get("decision_trace") or [])
                    if isinstance(trace, dict) or str(trace or "").strip()
                ][:4],
                "evidence_ids": [
                    int(ev_id)
                    for ev_id in (item.get("evidence_ids") or [])
                    if str(ev_id).isdigit()
                ],
            }
            for item in (target_week.get("items") or [])
            if isinstance(item, dict)
        ],
    }


def build_training_explanation_card(context: Dict[str, Any]) -> Dict[str, Any]:
    if not context:
        return {}

    coverage_ratio = int(float(context.get("coverage_ratio") or 0) * 100)
    return {
        "card_type": "training_explanation_card",
        "week_index": int(context.get("week_index") or 1),
        "phase": _safe_text(context.get("phase")),
        "load_level": _safe_text(context.get("load_level")),
        "total_weeks": int(context.get("total_weeks") or 1),
        "available_week_indexes": context.get("available_week_indexes") or [],
        "coverage_ratio": coverage_ratio,
        "audit_summary": _safe_text(context.get("audit_summary")),
        "summary": _safe_text(context.get("summary")),
        "items": context.get("items") or [],
    }


def render_training_explanation_card_md(card: Dict[str, Any]) -> str:
    if not card:
        return ""

    lines: List[str] = [
        "### 🔍 关键训练解释",
        "",
        f"**周次 / 阶段**：第 {int(card.get('week_index') or 1)} 周 / {_safe_text(card.get('phase'))} / {_safe_text(card.get('load_level'))}",
        f"**解释覆盖率**：{int(card.get('coverage_ratio') or 0)}%",
        f"**审计摘要**：{_safe_text(card.get('audit_summary'))}",
        "",
        f"{_safe_text(card.get('summary'))}",
        "",
    ]

    total_weeks = int(card.get("total_weeks") or 1)
    available_week_indexes = [
        int(week_idx)
        for week_idx in (card.get("available_week_indexes") or [])
        if str(week_idx).isdigit() and int(week_idx) > 0
    ]
    if total_weeks > 1 and available_week_indexes:
        weeks_text = " / ".join(f"第 {week_idx} 周" for week_idx in available_week_indexes[:8])
        lines.extend(
            [
                f"**多周说明**：当前仅展示第 {int(card.get('week_index') or 1)} 周关键解释；完整解释覆盖 {weeks_text}，其余周请以上方共享报告为准。",
                "",
            ]
        )

    items = [item for item in (card.get("items") or []) if isinstance(item, dict)]
    if not items:
        lines.extend(
            [
                "> 当前周暂无可展示的关键训练解释项。",
                "> 如本次请求生成了多周计划，请以上方共享报告中的周级解释区块为准。",
            ]
        )
        return "\n".join(lines).strip()

    for item in items:
        evidence_ids = [int(ev_id) for ev_id in (item.get("evidence_ids") or []) if str(ev_id).isdigit()]
        evidence_suffix = _format_evidence_badges(evidence_ids)
        lines.extend(
            [
                f"**{_strip_pace(_safe_text(item.get('title')))}**",
                f"- 为什么安排：{_safe_text(item.get('why_scheduled'))}",
                f"- 主要训练目标：{_safe_text(item.get('primary_target'))}",
                f"- 风险提醒：{_safe_text(item.get('risk_alert'))}",
                f"- 状态不佳时替代：{_safe_text(item.get('alternative_workout'))}",
                f"- 决策摘要：{_safe_text(item.get('decision_summary'))}",
            ]
        )
        template_id = _safe_text(item.get("template_id"), "")
        status = _safe_text(item.get("status"), "")
        explanation_source = _safe_text(item.get("explanation_source"), "")
        target_labels = _safe_list(item.get("target_labels"), limit=5)
        warnings = _safe_list(item.get("warnings"), limit=3)
        adjustments = _safe_list(item.get("adjustments"), limit=3)
        constraints = [_format_constraint_detail(constraint) for constraint in (item.get("constraints") or [])]
        constraints = [constraint for constraint in constraints if constraint]
        decision_trace = [_format_trace_detail(trace) for trace in (item.get("decision_trace") or [])]
        decision_trace = [trace for trace in decision_trace if trace]
        detail_lines: List[str] = []
        if target_labels:
            detail_lines.append(f"- 目标标签：{'、'.join(target_labels)}")
        if explanation_source:
            detail_lines.append(f"- 解释来源：{explanation_source}")
        if status:
            detail_lines.append(f"- 决策状态：{status}")
        if warnings:
            detail_lines.extend(["- 约束告警：", *[f"  - {warning}" for warning in warnings]])
        if adjustments:
            detail_lines.extend(["- 自动调整：", *[f"  - {adjustment}" for adjustment in adjustments]])
        if constraints:
            detail_lines.extend(["- 约束检查：", *[f"  - {constraint}" for constraint in constraints]])
        if decision_trace:
            detail_lines.extend(["- 决策轨迹：", *[f"  - {trace}" for trace in decision_trace]])
        if template_id:
            detail_lines.append(f"- 模板标识：{template_id}")
        if evidence_suffix:
            detail_lines.append(f"- 关联证据：{evidence_suffix}")
            detail_lines.append("- 预览提示：可在下方“查看证据”中点击同编号按钮打开原文。")
        else:
            detail_lines.append("- 关联证据：当前未提取到编号，请以下方“参考来源 / 查看证据（同号按钮）”区块为准。")
        if detail_lines:
            lines.extend(["", "<details>", "<summary>打开解释抽屉：决策细节与证据</summary>", "", *detail_lines, "", "</details>"])
        lines.append("")

    return "\n".join(lines).strip()


def render_plan_retry_md(query: str, error_text: str = "") -> str:

    normalized_query = str(query or "").strip() or "请基于当前训练画像重新生成训练计划。"
    lines = [
        "### ⚠️ 计划生成暂未完成",
        "",
        "",
        f"**原始请求**：{normalized_query}",
        "",
        "👉 **下一步**：点击下方「重试计划生成」，或先检查训练画像后再重试。",
    ]
    if str(error_text or "").strip():
        lines.extend(["", f"**错误摘要**：{str(error_text).strip()}"])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CustomElement props 构建函数 (用于 cl.CustomElement 替代 Markdown)
# ---------------------------------------------------------------------------


def build_entry_status_bar_props(context: Dict[str, Any]) -> Dict[str, Any]:
    """将入口状态上下文转换为 EntryStatusBar CustomElement 的 props"""
    if not context:
        return {}
    return {
        "week_index": int(context.get("week_index") or 1),
        "total_weeks": int(context.get("total_weeks") or 1),
        "phase": _safe_text(context.get("phase"), "训练期"),
        "load_level": _safe_text(context.get("load_level"), "—"),
        "day_label": _safe_text(context.get("day_label"), "当前"),
        "training_type": _safe_text(context.get("training_type"), "待查看"),
        "main_set": _safe_text(context.get("main_set"), "查看本周卡片"),
        "total_km": float(context.get("total_km") or 0),
        "training_day_count": int(context.get("training_day_count") or 0),
        "week_goal": _safe_text(context.get("week_goal")),
    }


def extract_current_week_context(state: Dict[str, Any]) -> Dict[str, Any]:
    """从 structured_report 提取当前周数据，供 WeekTrainingCard 使用"""
    structured_report = state.get("structured_report") or {}
    if not isinstance(structured_report, dict):
        return {}

    structured_plan = structured_report.get("structured_training_plan") or {}
    if not isinstance(structured_plan, dict):
        structured_plan = {}

    overview = structured_report.get("training_plan_overview") or {}
    if not isinstance(overview, dict):
        overview = {}

    week_sections = structured_report.get("training_plan_weeks") or []
    if not isinstance(week_sections, list):
        week_sections = []
    if not week_sections:
        raw_weeks = structured_plan.get("week_plans") or []
        if isinstance(raw_weeks, list):
            week_sections = [item for item in raw_weeks if isinstance(item, dict)]
    if not week_sections:
        return {}

    current_week = next(
        (week for week in week_sections if isinstance(week, dict) and int(week.get("week_index") or 0) == 1),
        None,
    ) or next((week for week in week_sections if isinstance(week, dict)), None)
    if not current_week:
        return {}

    days_data = []
    schedule_zone_map: Dict[Tuple[int, int], Dict[str, Any]] = {}
    daily_schedule_cards = structured_report.get("daily_schedule_cards") or []
    if isinstance(daily_schedule_cards, list):
        for sc in daily_schedule_cards:
            if not isinstance(sc, dict):
                continue
            sc_week = int(sc.get("week_index") or 0)
            sc_day = int(sc.get("day_index") or 0)
            if sc_week and sc_day:
                schedule_zone_map[(sc_week, sc_day)] = sc

    for day_idx, day in enumerate((current_week.get("days") or []) or [], start=1):
        if not isinstance(day, dict):
            continue
        sc_match = schedule_zone_map.get((int(current_week.get("week_index") or 1), day_idx), {})
        zone_range = _safe_text(sc_match.get("zone_range"), "")
        zone_label = _safe_text(sc_match.get("zone_label"), "")
        intensity_target = _safe_text(sc_match.get("intensity_target"), "")
        evidence_tier = _safe_text(sc_match.get("evidence_tier"), "")
        evidence_tier_label = _safe_text(sc_match.get("evidence_tier_label"), "")
        days_data.append({
            "day": _safe_text(day.get("day"), ""),
            "training_type": _safe_text(day.get("training_type"), "未安排"),
            "warmup": _safe_text(day.get("warmup"), ""),
            "warmup_km": float(day.get("warmup_km") or 0),
            "main_set": _strip_pace(_safe_text(day.get("main_set"), "")),
            "main_km": float(day.get("main_km") or 0),
            "cooldown": _safe_text(day.get("cooldown"), ""),
            "cooldown_km": float(day.get("cooldown_km") or 0),
            "venue": _safe_text(day.get("venue"), ""),
            "notes": _safe_text(day.get("notes"), ""),
            "heart_rate_zone": _safe_text(day.get("heart_rate_zone"), ""),
            "pace_range": _safe_text(day.get("pace_range"), ""),
            "key_workout": bool(day.get("key_workout")),
            "zone_range": zone_range or _safe_text(day.get("zone_range"), ""),
            "zone_label": zone_label or _safe_text(day.get("zone_label"), ""),
            "intensity_target": intensity_target or _safe_text(day.get("intensity_target"), ""),
            "evidence_tier": evidence_tier,
            "evidence_tier_label": evidence_tier_label,
        })

    other_weeks = []
    for week in week_sections:
        if not isinstance(week, dict):
            continue
        week_idx = int(week.get("week_index") or 0)
        if week_idx == int(current_week.get("week_index") or 1):
            continue
        other_weeks.append({
            "week_index": week_idx,
            "phase": _safe_text(week.get("phase"), ""),
            "load_level": _safe_text(week.get("load_level"), ""),
            "week_goal": _safe_text(week.get("week_goal"), ""),
        })

    return {
        "week_index": int(current_week.get("week_index") or 1),
        "phase": _safe_text(current_week.get("phase"), _safe_text(overview.get("current_phase"), "训练期")),
        "load_level": _safe_text(current_week.get("load_level"), "—"),
        "week_goal": _safe_text(current_week.get("week_goal"), ""),
        "load_progression_note": _safe_text(current_week.get("load_progression_note"), ""),
        "days": days_data,
        "key_workouts": [_strip_pace(str(kw)) for kw in (current_week.get("key_workouts") or []) if str(kw).strip()],
        "action_suggestions": [_strip_pace(str(s)) for s in (current_week.get("action_suggestions") or []) if str(s).strip()],
        "execution_reminder": _safe_text(current_week.get("execution_reminder"), ""),
        "other_weeks": other_weeks,
    }


def build_week_training_card_props(context: Dict[str, Any]) -> Dict[str, Any]:
    """将当前周上下文转换为 WeekTrainingCard CustomElement 的 props"""
    if not context:
        return {}
    return {
        "week_index": int(context.get("week_index") or 1),
        "phase": _safe_text(context.get("phase"), "训练期"),
        "load_level": _safe_text(context.get("load_level"), "—"),
        "week_goal": _safe_text(context.get("week_goal"), ""),
        "load_progression_note": _safe_text(context.get("load_progression_note"), ""),
        "days": context.get("days") or [],
        "key_workouts": context.get("key_workouts") or [],
        "action_suggestions": context.get("action_suggestions") or [],
        "execution_reminder": _safe_text(context.get("execution_reminder"), ""),
        "other_weeks": context.get("other_weeks") or [],
    }


def build_explanation_drawer_props(card: Dict[str, Any]) -> Dict[str, Any]:
    """将训练解释卡片转换为 ExplanationDrawer CustomElement 的 props"""
    if not card:
        return {}

    items = [item for item in (card.get("items") or []) if isinstance(item, dict)]
    first_item = items[0] if items else {}

    detail_lines: List[str] = []
    for item in items:
        template_id = _safe_text(item.get("template_id"), "")
        status = _safe_text(item.get("status"), "")
        explanation_source = _safe_text(item.get("explanation_source"), "")
        target_labels = _safe_list(item.get("target_labels"), limit=5)
        warnings = _safe_list(item.get("warnings"), limit=3)
        adjustments = _safe_list(item.get("adjustments"), limit=3)
        constraints = [_format_constraint_detail(c) for c in (item.get("constraints") or [])]
        constraints = [c for c in constraints if c]
        decision_trace = [_format_trace_detail(t) for t in (item.get("decision_trace") or [])]
        decision_trace = [t for t in decision_trace if t]
        evidence_ids = [int(ev_id) for ev_id in (item.get("evidence_ids") or []) if str(ev_id).isdigit()]
        if target_labels:
            detail_lines.append(f"目标标签：{'、'.join(target_labels)}")
        if explanation_source:
            detail_lines.append(f"解释来源：{explanation_source}")
        if status:
            detail_lines.append(f"决策状态：{status}")
        if warnings:
            detail_lines.extend(["约束告警："] + [f"  {w}" for w in warnings])
        if adjustments:
            detail_lines.extend(["自动调整："] + [f"  {a}" for a in adjustments])
        if constraints:
            detail_lines.extend(["约束检查："] + [f"  {c}" for c in constraints])
        if decision_trace:
            detail_lines.extend(["决策轨迹："] + [f"  {t}" for t in decision_trace])
        if template_id:
            detail_lines.append(f"模板标识：{template_id}")
        evidence_suffix = _format_evidence_badges(evidence_ids)
        if evidence_suffix:
            detail_lines.append(f"关联证据：{evidence_suffix}")

    evidence_ids = first_item.get("evidence_ids") or []
    if not isinstance(evidence_ids, list):
        evidence_ids = []
    normalized_evidence_ids = [int(ev_id) for ev_id in evidence_ids if str(ev_id).isdigit()]

    return {
        "training_name": _safe_text(first_item.get("title"), ""),
        "day": _safe_text(first_item.get("day"), ""),
        "phase": _safe_text(card.get("phase"), ""),
        "why_scheduled": _safe_text(first_item.get("why_scheduled"), ""),
        "primary_target": _safe_text(first_item.get("primary_target"), ""),
        "risk_alert": _safe_text(first_item.get("risk_alert"), ""),
        "alternative_workout": _safe_text(first_item.get("alternative_workout"), ""),
        "decision_summary": _safe_text(first_item.get("decision_summary"), ""),
        "evidence_ids": normalized_evidence_ids,
        "detail_lines": detail_lines,
        "summary": _safe_text(card.get("summary"), ""),
        "coverage_ratio": int(card.get("coverage_ratio") or 0),
    }


def build_monthly_calendar_props(state: Dict[str, Any]) -> Dict[str, Any]:
    """从 structured_report 提取训练日历数据，供 MonthlyTrainingCalendar CustomElement 使用"""
    from datetime import date, timedelta

    structured_report = state.get("structured_report") or {}
    if not isinstance(structured_report, dict):
        return {}

    calendar = structured_report.get("monthly_training_calendar") or {}
    if not isinstance(calendar, dict):
        return {}

    days = calendar.get("days") or []
    if not isinstance(days, list) or not days:
        return {}

    plan_start = _derive_plan_start_date(state)
    _DAY_NAME_TO_NUM = {"周一": 1, "周二": 2, "周三": 3, "周四": 4, "周五": 5, "周六": 6, "周日": 7}

    month_set = set()
    for day in days:
        if not isinstance(day, dict):
            continue
        wi = int(day.get("week_index") or 1)
        dl = str(day.get("day_label") or "")
        dn = _DAY_NAME_TO_NUM.get(dl, 1)
        offset_days = (wi - 1) * 7 + (dn - 1)
        actual_date = plan_start + timedelta(days=offset_days)
        day["month_num"] = actual_date.month
        day["year_num"] = actual_date.year
        day["date_str"] = actual_date.isoformat()
        month_set.add((actual_date.year, actual_date.month))

    sorted_months = sorted(month_set, key=lambda m: (m[0], m[1]))
    available_months = [{"year": m[0], "month": m[1]} for m in sorted_months]
    default_month = sorted_months[0] if sorted_months else (2026, 5)

    monthly_aggregates = {}
    for day in days:
        if not isinstance(day, dict):
            continue
        key = (day.get("year_num", 2026), day.get("month_num", 5))
        if key not in monthly_aggregates:
            monthly_aggregates[key] = {"total": 0, "action_library": 0, "kb_fallback": 0, "plan_only": 0, "zone_counts": {}}
        agg = monthly_aggregates[key]
        agg["total"] += 1
        et = str(day.get("evidence_tier") or "plan_only")
        if et in ("action_library", "kb_fallback", "plan_only"):
            agg[et] = agg.get(et, 0) + 1
        zr = str(day.get("zone_range") or "")
        if zr:
            agg["zone_counts"][zr] = agg["zone_counts"].get(zr, 0) + 1

    month_summaries = []
    for m in sorted_months:
        agg = monthly_aggregates.get(m, {"total": 0, "action_library": 0, "kb_fallback": 0, "plan_only": 0, "zone_counts": {}})
        month_summaries.append({
            "year": m[0],
            "month": m[1],
            "total_days": agg["total"],
            "action_library": agg.get("action_library", 0),
            "kb_fallback": agg.get("kb_fallback", 0),
            "plan_only": agg.get("plan_only", 0),
            "zone_counts": agg.get("zone_counts", {}),
        })

    evidence_tier_map = structured_report.get("evidence_tier_map") or {}

    return {
        "year": default_month[0],
        "month": default_month[1],
        "start_week_index": int(calendar.get("start_week_index") or 1),
        "end_week_index": int(calendar.get("end_week_index") or 4),
        "days": days,
        "phases": calendar.get("phases") or [],
        "evidence_summary": calendar.get("evidence_summary") or {},
        "evidence_tier_map": evidence_tier_map,
        "available_months": available_months,
        "month_summaries": month_summaries,
    }


def _derive_plan_start_date(state: Dict[str, Any]):
    from datetime import date

    structured_report = state.get("structured_report") or {}
    if not isinstance(structured_report, dict):
        return date.today()

    structured_plan = structured_report.get("structured_training_plan") or {}
    if not isinstance(structured_plan, dict):
        return date.today()

    plan_meta = structured_plan.get("plan_meta") or {}
    if not isinstance(plan_meta, dict):
        return date.today()

    start_str = str(plan_meta.get("start_date") or plan_meta.get("target_race_date") or "").strip()
    if start_str:
        try:
            return date.fromisoformat(start_str[:10])
        except (ValueError, TypeError):
            pass
    return date.today()


def build_calendar_props_with_explanations(state: Dict[str, Any]) -> Dict[str, Any]:
    """与 build_monthly_calendar_props 相同，但额外将 training_explanation_panel 中的解释合并到每个 day 的 explanation 字段"""
    props = build_monthly_calendar_props(state)
    if not props:
        return {}

    structured_report = state.get("structured_report") or {}
    if not isinstance(structured_report, dict):
        return props

    panel = structured_report.get("training_explanation_panel") or {}
    if not isinstance(panel, dict) or not panel:
        return props

    panel_weeks = panel.get("weeks") or []
    if not isinstance(panel_weeks, list):
        return props

    explanation_map = {}
    for pw in panel_weeks:
        if not isinstance(pw, dict):
            continue
        wi = int(pw.get("week_index") or 0)
        for item in pw.get("items") or []:
            if not isinstance(item, dict):
                continue
            day_label = _safe_text(item.get("day"), "").strip()
            if not day_label:
                continue
            explanation_map[(wi, day_label)] = {
                "why_scheduled": _safe_text(item.get("why_scheduled")),
                "primary_target": _safe_text(item.get("primary_target")),
                "risk_alert": _safe_text(item.get("risk_alert")),
                "alternative_workout": _safe_text(item.get("alternative_workout")),
                "decision_summary": _safe_text(item.get("decision_summary")),
                "target_labels": _safe_list(item.get("target_labels"), limit=5),
                "explanation_source": _safe_text(item.get("explanation_source"), ""),
                "status": _safe_text(item.get("status"), ""),
                "evidence_ids": [
                    int(ev_id)
                    for ev_id in (item.get("evidence_ids") or [])
                    if str(ev_id).isdigit()
                ],
            }

    days = props.get("days") or []
    for day in days:
        if not isinstance(day, dict):
            continue
        wi = int(day.get("week_index") or 0)
        dl = str(day.get("day_label") or "").strip()
        explanation = explanation_map.get((wi, dl))
        if explanation:
            day["explanation"] = explanation

    return props


def build_calendar_props_from_db(plan_id: str) -> Dict[str, Any]:
    """从 SQLite training_calendar_events 构建 MonthlyTrainingCalendar 所需 props"""
    from marathon_qa_assistant.services.database import get_db

    db = get_db()
    plan = db.get_plan(plan_id)
    events = db.list_events(plan_id)

    if not plan or not events:
        return {}

    first_date = sorted(e["scheduled_date"] for e in events)[0] if events else ""
    year = int(first_date[:4]) if first_date else 2026
    month = int(first_date[5:7]) if len(first_date) >= 7 else 5
    week_nos = sorted({int(e["week_no"]) for e in events})

    _WO_TYPE_TO_CN = {
        "easy": "轻松跑",
        "long_run": "长距离",
        "interval": "间歇跑",
        "tempo": "节奏跑",
        "threshold": "节奏跑",
        "fartlek": "法特莱克",
        "hill": "坡道跑",
        "recovery": "恢复跑",
        "progression": "渐进跑",
        "race_sim": "比赛模拟",
        "rest": "休息",
    }

    def _extract_training_type(event: dict) -> str:
        title = str(event.get("title") or "")
        if "｜" in title:
            return title.split("｜", 1)[-1].strip()
        wo_type = str(event.get("workout_type") or "").lower()
        return _WO_TYPE_TO_CN.get(wo_type, "训练")

    phase_map = {}
    for e in events:
        w = int(e["week_no"])
        p = str(e.get("phase") or "")
        if w and p and w not in phase_map:
            phase_map[w] = p

    phases = []
    phase_entries = sorted(phase_map.items())
    if phase_entries:
        cur_name = phase_entries[0][1]
        cur_start = phase_entries[0][0]
        cur_end = cur_start
        for w, p in phase_entries[1:]:
            if p == cur_name:
                cur_end = w
            else:
                phases.append({"phase": cur_name, "start_week": cur_start, "end_week": cur_end})
                cur_name = p
                cur_start = w
                cur_end = w
        phases.append({"phase": cur_name, "start_week": cur_start, "end_week": cur_end})

    days = []
    month_set = set()
    for e in events:
        wo_type = str(e.get("workout_type") or "").lower()
        training_type = _extract_training_type(e)
        is_rest = wo_type == "rest"
        sched = str(e.get("scheduled_date") or "")
        year_num = 2026
        month_num = 5
        if sched:
            try:
                year_num = int(sched[:4])
                month_num = int(sched[5:7])
            except (ValueError, IndexError):
                pass
            month_set.add((year_num, month_num))
        days.append({
            "week_index": int(e["week_no"]),
            "day_index": int(e["day_no"]),
            "day_label": str(e.get("day_label") or ""),
            "date_str": sched,
            "month_num": month_num,
            "year_num": year_num,
            "workout_title": str(e.get("title") or "训练"),
            "training_type": training_type,
            "training_type_label": training_type,
            "workout_type": wo_type,
            "is_rest": is_rest,
            "zone_range": str(e.get("intensity_zone") or ""),
            "intensity_target": str(e.get("intensity_zone") or ""),
            "warmup": str(e.get("warmup") or ""),
            "main_set": _strip_pace(str(e.get("main_set") or "")),
            "cooldown": str(e.get("cooldown") or ""),
            "venue": str(e.get("venue") or ""),
            "notes": str(e.get("notes") or ""),
            "total_km": float(e.get("total_km") or 0),
            "phase": str(e.get("phase") or ""),
            "evidence_tier": "plan_only",
            "evidence_tier_label": "基础计划",
        })

    sorted_months = sorted(month_set, key=lambda m: (m[0], m[1]))
    available_months = [{"year": m[0], "month": m[1]} for m in sorted_months]
    default_month = sorted_months[0] if sorted_months else (year, month)

    return {
        "year": default_month[0],
        "month": default_month[1],
        "start_week_index": week_nos[0] if week_nos else 1,
        "end_week_index": week_nos[-1] if week_nos else 1,
        "days": days,
        "phases": phases,
        "evidence_summary": {},
        "evidence_tier_map": {},
        "available_months": available_months,
        "month_summaries": [],
    }
