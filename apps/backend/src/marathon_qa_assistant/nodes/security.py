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
    ("chest_pain", ["胸痛", "胸口疼", "胸闷", "胸紧", "chest pain", "chest tightness"], "胸痛/胸闷"),
    ("dyspnea", ["呼吸困难", "喘不上气", "气短", "呼吸急促", "difficulty breathing", "short of breath"], "呼吸困难"),
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


def _scan_medical_risk(query: str) -> Tuple[bool, Optional[str], Optional[str], List[str], List[str]]:
    """P1-4: 扫描查询文本中的医疗风险。

    Returns:
        (should_intercept, risk_level, reason, matched_labels, matched_codes)
        - should_intercept: True 表示需要立即拦截
        - risk_level: "medical" / "high_risk" / None
        - reason: 拦截/警告原因，None 表示通过
        - matched_labels: 命中的标签列表（中文）
        - matched_codes: 命中的代码列表（如 "chest_pain"）
    """
    text = str(query or "")
    matched_labels: List[str] = []
    matched_codes: List[str] = []
    matched_severe: List[str] = []

    # 1. 扫描严重红旗
    for code, keywords, label in _SEVERE_MEDICAL_RED_FLAGS:
        for kw in keywords:
            if kw.lower() in text.lower():
                matched_severe.append(label)
                matched_codes.append(code)
                break
    if matched_severe:
        matched_labels.extend(matched_severe)
        reason = (
            f"检测到医疗风险信号：{'、'.join(matched_severe)}。"
            "这些症状属于需要立即就医的健康红旗，系统不能生成训练建议。"
            "请先寻求专业医疗评估，在获得医生许可后再恢复训练。"
        )
        return True, "medical", reason, matched_labels, matched_codes

    # 2. 扫描高风险行为
    for code, pattern, label in _HIGH_RISK_BEHAVIOR_PATTERNS:
        if pattern.search(text):
            matched_labels.append(label)
            matched_codes.append(code)

    if matched_labels:
        reason = (
            f"检测到高风险训练行为：{'、'.join(matched_labels)}。"
            "系统将就此发出安全提醒，在计划中嵌入风险警告。"
        )
        return False, "high_risk", reason, matched_labels, matched_codes

    return False, None, None, [], []


_scan_query_medical_risk = _scan_medical_risk  # 兼容别名


# ── P1 增强：按红旗类型定制的安全拦截报告 ──

# 每种严重红旗类型的具体就医指导
_RED_FLAG_DETAILED_REPORTS: Dict[str, str] = {
    "chest_pain": (
        "### 胸痛/胸闷\n\n"
        "**风险说明**：跑步中或跑步后出现胸痛、胸闷、压迫感或烧灼感，"
        "可能提示运动性哮喘、心肌缺血、心包炎或冠状动脉异常。"
        "这些症状在跑者中容易被误判为「训练过度」或「岔气」，"
        "但实际可能涉及心脏问题，自行判断风险极高。\n\n"
        "**建议行动**：\n"
        "- **立即停止运动**，不要尝试「慢跑缓解」或「再坚持看看」。\n"
        "- 尽早就医（**心内科**），建议做心电图（ECG）和心脏超声检查。\n"
        "- 在医生明确排除心脏问题并获得书面许可前，**不要恢复任何强度的跑步训练**。\n"
        "- **不要自行判断为「训练过度」或「呼吸方式不对」**，心脏问题需要专业检查才能排除。"
    ),
    "achilles_rupture": (
        "### 跟腱弹响/撕裂感\n\n"
        "**风险说明**：跑步中突然听到或感觉到跟腱处「啪」的一声弹响，"
        "伴随剧烈疼痛和无法踮脚站立，这是**跟腱断裂的典型三联征**。"
        "跟腱断裂是运动医学急症，完全断裂后肌腱会回缩，"
        "延误治疗将导致手术难度增加和康复期显著延长。\n\n"
        "**建议行动**：\n"
        "- **立即停止一切负重活动**，患侧脚不要着地承重。\n"
        "- 立即就医（**骨科/运动医学科**），告知医生弹响史和受伤机制。\n"
        "- **跟腱断裂需在 48 小时内手术**，超过 48 小时断端回缩将增加手术复杂度，影响康复预后。\n"
        "- 就医前可冰敷跟腱部位（每次 15-20 分钟），抬高患肢，**不要自行按摩或拉伸**。"
    ),
    "fracture": (
        "### 骨折/骨裂\n\n"
        "**风险说明**：跑步中或跑步后出现特定部位的**点压痛**（手指按压某一点时剧烈疼痛）"
        "和**负重痛**（站立或行走时疼痛明显加重），可能提示应力性骨折或急性骨折。"
        "常见部位包括胫骨、跖骨、腓骨和股骨颈。"
        "继续负重训练可导致不完全骨折发展为完全骨折，甚至需要手术内固定。\n\n"
        "**建议行动**：\n"
        "- **立即停止跑步和一切高冲击活动**。\n"
        "- 尽早就医（**骨科/运动医学科**），建议做 **X 光检查**，必要时做 **MRI**（X 光对应力性骨折早期不敏感）。\n"
        "- 在影像学确认骨折愈合前，禁止跑步、跳跃等高冲击运动。\n"
        "- 可转为游泳等非负重交叉训练（需在医生许可后进行）。"
    ),
    "stress_fracture": (
        "### 应力性骨折\n\n"
        "**风险说明**：特定部位的点压痛（按压时剧痛）和负重痛是应力性骨折的典型信号。"
        "应力性骨折是骨骼在反复应力下出现的微骨折，"
        "继续跑步训练可能发展为完全骨折或骨不连，显著延长恢复周期。\n\n"
        "**建议行动**：\n"
        "- **立即停止跑步和一切高冲击活动**。\n"
        "- 尽早就医（**骨科/运动医学科**），建议做 **MRI**（X 光在早期可能显示正常）。\n"
        "- 恢复期通常需要 6-12 周，具体取决于骨折部位和严重程度。\n"
        "- 在医生确认愈合前禁止跑步和跳跃训练。"
    ),
    "rhabdomyolysis": (
        "### 横纹肌溶解\n\n"
        "**风险说明**：横纹肌溶解是肌肉细胞大量破坏后释放肌红蛋白进入血液的急症，"
        "典型症状包括**酱油色/茶色尿、肌肉极度酸痛僵硬（远超正常延迟性肌肉酸痛）、全身乏力、恶心**。"
        "严重时可导致急性肾衰竭，是运动医学中最危险的急症之一，**需要急诊处理**。\n\n"
        "**建议行动**：\n"
        "- **立即前往急诊就医**，告知医生近期有高强度/超长距离运动史。\n"
        "- **不要自行补水「观察看看」**——横纹肌溶解需要静脉补液和住院监测肾功能。\n"
        "- 就医时主动说明尿液颜色变化和运动史，帮助医生快速判断。\n"
        "- 预防：避免突然大幅增加训练量、避免高温高湿环境下极限运动、运动后充分补水。"
    ),
    "dyspnea": (
        "### 呼吸困难\n\n"
        "**风险说明**：运动中出现与强度不相称的严重呼吸困难、喘不上气、无法完整说话，"
        "可能提示运动诱发哮喘、心源性呼吸困难或肺栓塞等。"
        "如伴有口唇发紫、胸痛、头晕或意识模糊，属于**医疗急症**。\n\n"
        "**建议行动**：\n"
        "- **立即停止运动**，保持坐位或半卧位，松开紧身衣物。\n"
        "- 如症状在停止运动后 5-10 分钟内不缓解，或伴有胸痛、头晕，**立即拨打急救电话或前往急诊**。\n"
        "- 即使症状自行缓解，也应就医（**呼吸内科/心内科**）查明原因后再恢复训练。\n"
        "- 不要在未查明原因的情况下尝试「调整呼吸方式」继续跑。"
    ),
    "syncope": (
        "### 晕厥\n\n"
        "**风险说明**：运动中或运动后出现晕厥（短暂意识丧失）、眼前发黑、头晕欲倒，"
        "可能提示心源性晕厥、严重脱水、低血糖或脑血管问题。"
        "运动相关性晕厥是需要**急诊评估**的危险信号，不应简单归因于「太累了」或「低血糖」。\n\n"
        "**建议行动**：\n"
        "- **立即停止运动并平卧**，抬高双腿促进回心血量。\n"
        "- 如意识未在 1-2 分钟内完全恢复，或反复发作，**立即拨打急救电话或前往急诊**。\n"
        "- 即使症状自行缓解，也应在 24 小时内就医（**心内科/神经内科**），做心电图和必要的进一步检查。\n"
        "- 在医生明确排除心源性原因前，禁止独自进行高强度运动。"
    ),
    # 以下为次要红旗类型的通用详细指导
    "ligament_tear": (
        "### 韧带损伤\n\n"
        "**风险说明**：膝关节韧带（如前交叉韧带 ACL）损伤常见于急停、变向或落地不稳时。"
        "典型症状包括受伤时听到/感觉到「啪」声、关节迅速肿胀、关节不稳感。"
        "韧带损伤若未正确治疗，可能导致关节长期不稳定和早期骨关节炎。\n\n"
        "**建议行动**：\n"
        "- **立即停止运动**，受伤关节制动。\n"
        "- 尽早就医（**骨科/运动医学科**），需要 MRI 明确韧带损伤程度。\n"
        "- 在医生指导下进行康复，完全断裂可能需要手术重建。\n"
        "- 急性期遵循 RICE 原则（休息、冰敷、加压、抬高）。"
    ),
    "hematemesis": (
        "### 呕血/内出血\n\n"
        "**风险说明**：运动后出现呕血、咳血或黑便，可能提示消化道出血或运动诱发内脏损伤。"
        "这是需要**急诊评估**的严重信号，不可自行观察等待。\n\n"
        "**建议行动**：\n"
        "- **立即前往急诊就医**，告知医生运动史和出血情况。\n"
        "- 就医前禁食禁水，以便可能的急诊内镜检查。\n"
        "- 不要自行服用止血药或止痛药。"
    ),
    "plantar_fasciitis": (
        "### 足底筋膜炎\n\n"
        "**风险说明**：足跟或足底疼痛，尤其晨起第一步时最明显，可能提示足底筋膜炎。"
        "虽然通常不会威胁健康，但若伴随剧烈疼痛或足底出现淤青/肿胀，需排除足底筋膜撕裂。\n\n"
        "**建议行动**：\n"
        "- 减少跑量，暂停高强度训练。\n"
        "- 就医（**骨科/运动医学科/康复科**）明确诊断。\n"
        "- 可尝试足底筋膜拉伸、滚网球按摩、换用支撑性更好的跑鞋。\n"
        "- 如疼痛持续超过 2 周无改善，需做 MRI 排除撕裂。"
    ),
    "severe_swelling": (
        "### 严重肿胀/关节积液\n\n"
        "**风险说明**：关节或肢体出现明显肿胀、发热、活动受限，"
        "可能提示关节内结构损伤（半月板、韧带、软骨）或感染性关节炎。"
        "严重肿胀伴剧痛需紧急评估，排除骨筋膜室综合征等急症。\n\n"
        "**建议行动**：\n"
        "- **立即停止运动**，抬高患肢，冰敷消肿。\n"
        "- 尽早就医（**骨科/运动医学科**），可能需要关节穿刺或 MRI 检查。\n"
        "- 如肿胀迅速加重或伴发热/发红，应前往急诊排除感染。"
    ),
}

# 通用严重红旗模板（用于未在 _RED_FLAG_DETAILED_REPORTS 中定义的红旗类型）
_GENERIC_SEVERE_TEMPLATE = (
    "### {label}\n\n"
    "**风险说明**：检测到需要医疗关注的症状或情况。跑步训练中忽视这些信号可能导致伤情加重或出现严重并发症。\n\n"
    "**建议行动**：\n"
    "- **先休息**，暂停跑步训练直至症状明确。\n"
    "- 尽早就医，由专业医生进行评估和诊断。\n"
    "- 在获得医生许可前，不要恢复跑步训练。\n"
    "- 可将检查结果与教练沟通，制定安全的恢复计划。"
)

# 医疗免责声明
_MEDICAL_DISCLAIMER = "\n> 本建议不能替代专业医疗诊断，如有严重症状请立即就医。"


def _build_safety_intercept_report(matched_codes: List[str], matched_labels: List[str]) -> str:
    """根据命中的红旗代码，生成定制化的安全拦截报告。"""
    sections: List[str] = []
    title_parts = [label for label in matched_labels if label]
    title = f"## ⚠️ 安全提醒：{'、'.join(title_parts)}" if title_parts else "## ⚠️ 安全提醒"
    sections.append(title)

    reported_codes: set = set()
    for code in matched_codes:
        if code in reported_codes:
            continue
        if code in _RED_FLAG_DETAILED_REPORTS:
            sections.append(_RED_FLAG_DETAILED_REPORTS[code])
        else:
            # 用通用模板兜底
            label = next(
                (lbl for c, lbl in zip(matched_codes, matched_labels) if c == code),
                "未知医疗风险",
            )
            sections.append(_GENERIC_SEVERE_TEMPLATE.format(label=label))
        reported_codes.add(code)

    sections.append(_MEDICAL_DISCLAIMER)
    return "\n\n".join(sections)


def _build_high_risk_warning_report(matched_codes: List[str], matched_labels: List[str]) -> str:
    """为高风险训练行为生成安全提醒。"""

    has_ignore_pain = "ignore_pain" in matched_codes or "pain_while_running" in matched_codes
    has_ignore_doctor = "ignore_doctor" in matched_codes
    has_run_with_injury = "run_with_injury" in matched_codes
    has_overtrain = "overtrain_risk" in matched_codes

    lines: List[str] = [f"## ⚠️ 训练安全提醒\n"]

    if has_ignore_pain:
        lines.append(
            "**关于忽略疼痛**：疼痛是身体保护机制的一部分，不是需要「克服」的障碍。"
            "跑步中出现疼痛意味着身体某个部位正在承受超出其当前能力的应力。"
            "持续忽视疼痛信号可能导致急性损伤转为慢性劳损，使恢复周期从数周延长至数月。"
        )
    if has_ignore_doctor:
        lines.append(
            "**关于无视医嘱**：医生和物理治疗师给出的建议基于专业评估。"
            "自行判断「感觉不疼了」就恢复训练，可能在损伤尚未完全愈合时造成二次伤害。"
            "请在获得医生书面许可后再恢复跑步训练。"
        )
    if has_run_with_injury:
        lines.append(
            "**关于带伤训练/比赛**：带伤跑步会改变跑姿以代偿疼痛部位，"
            "进而可能导致身体其他部位出现新的损伤（代偿性损伤）。"
            "一场比赛的成绩不应该以延长数月的康复期为代价。"
        )
    if has_overtrain:
        lines.append(
            "**关于过度训练**：跑量过快增长或连续高强度训练会超过身体的适应和修复能力。"
            "过度训练不仅增加受伤风险，还可能导致免疫力下降、睡眠质量变差和运动表现下降。"
        )

    lines.append(
        "### 建议\n"
        "- **倾听身体信号**：疼痛是身体的保护机制，不是需要「克服」的障碍。\n"
        "- **渐进原则**：跑量周增幅建议不超过 10%，强度提升应在适应 2-3 周后进行。\n"
        "- **听从医嘱**：专业评估不可替代，不要自行判断「感觉还好」就恢复训练。\n"
        "- **交叉训练**：受伤期间可选择游泳、骑行等非负重运动保持体能（需在医生许可下进行）。\n"
        "- **跑休结合**：每周至少安排 1-2 天完全休息或低强度恢复日，给身体修复时间。"
    )
    lines.append(_MEDICAL_DISCLAIMER)

    return "\n\n".join(lines)


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
    should_intercept, risk_level, medical_reason, matched_labels, matched_codes = _scan_medical_risk(query)

    if should_intercept:
        # P1 增强：生成定制化安全报告，替代原来的通用模板
        intercept_report = _build_safety_intercept_report(matched_codes, matched_labels)
        return {
            "mode": "intercepted",
            "final_report": intercept_report,
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
        risk_report = _build_high_risk_warning_report(matched_codes, matched_labels)
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
            "medical_risk_report": risk_report,
        }

    return {"reasoning_log": ["[security] 输入与近期历史通过检查"]}


# ── 轨迹级安全扫描：在 formatter 输出前审计完整节点链路 ──

def scan_execution_trace(state: IntegratedState) -> dict:
    """扫描完整执行轨迹，检测跨节点的安全风险。

    AgentDoG 风格：不只审最终文本，而是审查"每一步调用了什么、收到什么反馈、依据什么决策"。
    在 formatter 生成 final_report 后、output_guard 检查前调用。

    Returns:
        {"safe": bool, "alerts": list[str], "risk_level": "none"|"low"|"medium"|"high"}
    """
    reasoning_log: list = state.get("reasoning_log") or []
    log_text = "\n".join(str(item) for item in reasoning_log)
    alerts: list[str] = []

    # AgentDoG P0: 优先使用结构化 execution_trace，回退到 reasoning_log 字符串匹配
    execution_trace: list = state.get("execution_trace") or []
    trace_nodes = [step.get("node", "") for step in execution_trace if isinstance(step, dict)]

    # 1. 计划漂移：planner 生成被 safety_gate 拦截的内容
    if "[security] 已拦截" in log_text and "[planner]" in log_text:
        alerts.append("[plan_drift] 安全门拦截后 planner 仍生成了内容")

    # 2. 证据覆盖：auditor 拒绝但最终仍通过（优先用结构化 trace）
    audit_steps = [s for s in execution_trace if isinstance(s, dict) and s.get("node") == "critic_auditor"]
    audit_rejections = sum(1 for s in audit_steps if not s.get("output_snapshot", {}).get("approved", True))
    if not audit_steps:
        audit_rejections = sum(1 for line in reasoning_log
                             if "[auditor]" in str(line) and ("未通过" in str(line) or "拒绝" in str(line) or "rejected" in str(line).lower()))
    final_approved = any("[auditor]" in str(line) and ("通过" in str(line) or "approved" in str(line).lower())
                        for line in reasoning_log)
    if audit_rejections >= 2 and not final_approved:
        alerts.append(f"[evidence_override] auditor 拒绝 {audit_rejections} 次但未收到最终通过信号")

    # 3. 迭代异常：audit loop 超过 3 次
    iteration_count = state.get("iteration_count", 0)
    if iteration_count > 3:
        alerts.append(f"[loop_anomaly] 审核迭代 {iteration_count} 次仍未收敛")

    # 4. 跨域泄露：coach 节点使用了 nutrition/therapist 专属证据
    category = str(state.get("category") or "")
    if category == "coach":
        evidence_items = (state.get("evidence_bundle") or {}).get("evidence_items") or []
        leaked_domains = set()
        for item in (evidence_items or []):
            ed = item.get("expert_domain", "")
            if ed in ("nutrition", "rehab_safety") and item.get("confidence_level") == "high":
                leaked_domains.add(ed)
        if leaked_domains:
            alerts.append(f"[domain_leak] coach 节点使用了非教练域证据: {leaked_domains}")

    # 5. 引用断裂：final_report 中的 [n] 引用是否能回溯到 ranked_evidence
    final_report = str(state.get("final_report") or "")
    ranked_evidence = state.get("ranked_evidence") or []
    import re as _re
    cited_nums = set(int(m) for m in _re.findall(r'\[(\d+)\]', final_report))
    max_evidence = len(ranked_evidence)
    if cited_nums and max(cited_nums, default=0) > max_evidence:
        bad_cites = [n for n in cited_nums if n > max_evidence]
        alerts.append(f"[citation_break] 引用了不存在的证据编号: {bad_cites} (最大 {max_evidence})")

    # 6. 证据全低置信：所有证据都是 low
    evidence_items = (state.get("evidence_bundle") or {}).get("evidence_items") or []
    if evidence_items and all(
        item.get("confidence_level") == "low"
        for item in evidence_items if isinstance(item, dict)
    ):
        alerts.append("[low_confidence] 所有证据置信度为 low，回答应标注「证据不足」")

    # AgentDoG P0: 结构化执行轨迹摘要
    trace_summary = " → ".join(trace_nodes) if trace_nodes else "(无结构化 trace)"
    audit_diagnosis = state.get("audit_diagnosis") or {}
    if audit_diagnosis.get("diagnoses"):
        diag_items = audit_diagnosis["diagnoses"]
        alerts.append(
            f"[ternary_diagnosis] {len(diag_items)} 个问题: "
            + "; ".join(f"{d['failure_mode']}→{d['real_world_harm']}" for d in diag_items[:3])
        )

    # 确定风险等级
    if not alerts:
        risk_level = "none"
    elif any("plan_drift" in a or "evidence_override" in a for a in alerts):
        risk_level = "high"
    elif any("citation_break" in a or "domain_leak" in a for a in alerts):
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "safe": risk_level in ("none", "low"),
        "alerts": alerts,
        "risk_level": risk_level,
        "trace_nodes": trace_nodes,
        "trace_summary": trace_summary,
    }
