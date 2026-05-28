import re
from typing import Any, Dict, List, Optional, Tuple

try:
    from langchain_core.runnables import RunnableConfig
except ImportError:
    RunnableConfig = Any

from marathon_qa_assistant.core.state_models import IntegratedState
from marathon_qa_assistant.nodes.common import ensure_usage, input_guard


# ── P1-4 / P1-6: 医疗风险关键词库 ──

# 严重红旗关键词：命中后立即拦截并建议就医
_SEVERE_MEDICAL_RED_FLAGS: List[Tuple[str, List[str], str]] = [
    ("chest_pain", ["胸痛", "胸痛", "胸口疼", "胸闷", "胸紧", "chest pain", "chest tightness"], "胸痛/胸闷"),
    ("dyspnea", ["呼吸困难", "喘不上气", "气短", "呼吸急促", "defculty breathing", "short of breath"], "呼吸困难"),
    ("syncope", ["晕厥", "晕倒", "眼前发黑", "突然晕", "faint", "blackout", "pass out"], "晕厥"),
    ("fracture", ["骨折", "骨裂", "stress fracture", "应力性骨折"], "骨折/骨裂"),
    ("ligament_tear", ["韧带断裂", "韧带撕裂", "ligament tear", "ligament rupture", "前交叉韧带", "ACL"], "韧带损伤"),
    ("hematemesis", ["呕血", "咳血", "出血", "blood vomit"], "呕血/内出血"),
    ("achilles_rupture", ["跟腱断裂", "跟腱撕裂", "achilles tear", "achilles rupture", "弹响"], "跟腱断裂"),  # P1-6
    ("rhabdomyolysis", ["横纹肌溶解", "酱油尿", "茶色尿", "rhabdomyolysis"], "横纹肌溶解"),  # P1-6
    ("stress_fracture", ["应力性骨折", "点压痛", "负重痛", "stress fracture", "骨裂"], "应力性骨折"),  # P1-6
    ("plantar_fasciitis", ["足底筋膜炎", "足跟痛", "plantar fasciitis"], "足底筋膜炎"),  # P1-6
    ("severe_swelling", ["严重肿胀", "无法承重", "关节积液"], "严重肿胀/关节积液"),  # P1-6
]

# 高风险行为关键词：警告但不拦截
_HIGH_RISK_BEHAVIOR_PATTERNS: List[Tuple[str, re.Pattern, str]] = [
    ("ignore_pain", re.compile(r'忽略.*(?:疼痛|不适|疼).*(?:继续|训练|跑)'), "忽略疼痛继续训练"),
    ("ignore_doctor", re.compile(r'(?:无视|不听|不管).*(?:医生|医嘱|建议)'), "无视医生建议"),
    ("run_with_injury", re.compile(r'(?:带伤|有伤|受伤).*(?:比赛|跑|训练)'), "带伤训练/比赛"),
    ("overtrain_risk", re.compile(r'(?:每天跑|天天跑|加练|超级加倍|double.*train)'), "过度训练风险"),
    ("pain_while_running", re.compile(r'(?:跑步时|跑的时候).*(?:疼|痛)'), "跑步时疼痛"),
]

# P1-6: 疼痛关键词扩展（用于 normalize_workout_feedback 等）
_PAIN_KEYWORDS_WATCH_PLUS: List[str] = [
    "跟腱疼", "跟腱不适", "跟腱酸", "跟腱痛",
    "膝盖疼", "膝盖痛", "膝痛",
    "足底筋膜炎", "足跟痛", "plantar fasciitis", "足底疼",
    "脚踝疼", "脚踝痛", "ankle pain",
]


def _scan_medical_risk(query: str) -> Tuple[bool, Optional[str], Optional[str], List[str]]:
    """P1-4: 扫描查询文本中的医疗风险。

    Returns:
        (should_intercept, risk_level, reason, matched_labels)
        - should_intercept: True 表示需要立即拦截
        - risk_level: "medical" / "high_risk" / None
        - reason: 拦截/警告原因，None 表示通过
        - matched_labels: 命中的标签列表
    """
    text = str(query or "")
    matched_labels: List[str] = []
    matched_severe: List[str] = []

    # 1. 扫描严重红旗
    for code, keywords, label in _SEVERE_MEDICAL_RED_FLAGS:
        for kw in keywords:
            if kw.lower() in text.lower():
                matched_severe.append(label)
                break
    if matched_severe:
        matched_labels.extend(matched_severe)
        reason = (
            f"检测到医疗风险信号：{'、'.join(matched_severe)}。"
            "这些症状属于需要立即就医的健康红旗，系统不能生成训练建议。"
            "请先寻求专业医疗评估，在获得医生许可后再恢复训练。"
        )
        return True, "medical", reason, matched_labels

    # 2. 扫描高风险行为
    for code, pattern, label in _HIGH_RISK_BEHAVIOR_PATTERNS:
        if pattern.search(text):
            matched_labels.append(label)

    if matched_labels:
        reason = (
            f"检测到高风险训练行为：{'、'.join(matched_labels)}。"
            "系统将就此发出安全提醒，在计划中嵌入风险警告。"
        )
        return False, "high_risk", reason, matched_labels

    return False, None, None, []


_scan_query_medical_risk = _scan_medical_risk  # 兼容别名


async def security_gate_node(state: IntegratedState, config: RunnableConfig) -> dict:
    del config
    query = state.get("query", "")

    # ── 第 1 层：提示注入/越狱检查 ──
    is_safe, reason = input_guard.check(query, input_type="query")
    if not is_safe:
        return {
            "mode": "intercepted",
            "final_report": (
                "## 安全拦截\n"
                f"当前请求被系统安全护栏拦截，原因：{reason}\n\n"
                "请去掉越权、注入或敏感探测相关内容后重试。"
            ),
            "risk_alert": f"<div class='github-flash-error'><strong>安全拦截：</strong>{reason}</div>",
            "reasoning_log": [f"[security] 已拦截输入: {reason}"],
            "token_usage": ensure_usage(state.get("token_usage")),
        }

    for item in state.get("history", [])[-6:]:
        content = str(item.get("content", ""))
        history_safe, history_reason = input_guard.check(content, input_type="history")
        if not history_safe:
            return {
                "mode": "intercepted",
                "final_report": (
                    "## 会话已重置\n"
                    f"最近对话中检测到不安全内容：{history_reason}\n\n"
                    "请重新发起一个安全、明确的问题。"
                ),
                "risk_alert": f"<div class='github-flash-error'><strong>历史风险：</strong>{history_reason}</div>",
                "reasoning_log": [f"[security] 已拦截历史上下文: {history_reason}"],
                "token_usage": ensure_usage(state.get("token_usage")),
            }

    # ── 第 2 层：P1-4 医疗风险扫描 ──
    should_intercept, risk_level, medical_reason, matched_labels = _scan_medical_risk(query)

    if should_intercept:
        return {
            "mode": "intercepted",
            "final_report": (
                "## 安全提醒\n\n"
                f"{medical_reason}\n\n"
                "### 建议步骤\n"
                "1. 立即停止训练并前往医疗机构进行评估。\n"
                "2. 在获得专业医疗许可前，不要恢复跑步训练。\n"
                "3. 可将检查结果反馈给教练后，再重新制定安全训练计划。\n\n"
                "### 紧急情况\n"
                "如症状加重或持续不缓解，请直接前往急诊。"
            ),
            "risk_alert": (
                '<div class="github-flash-error">'
                f'<strong>医疗安全提醒：</strong>{medical_reason}'
                '</div>'
            ),
            "reasoning_log": [
                f"[security] 医疗风险拦截: {medical_reason}",
                f"[medical_scan] 命中标签: {matched_labels}",
            ],
            "token_usage": ensure_usage(state.get("token_usage")),
        }

    if risk_level == "high_risk":
        return {
            "reasoning_log": [
                f"[security] 输入与近期历史通过检查",
                f"[medical_scan] 高风险行为提醒: {medical_reason}",
            ],
            "risk_alert": (
                '<div class="github-flash-warn">'
                f'<strong>训练安全提醒：</strong>{medical_reason}'
                '</div>'
            ),
        }

    return {"reasoning_log": ["[security] 输入与近期历史通过检查"]}
