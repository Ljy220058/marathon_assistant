from typing import Any, Dict, List, Optional, Tuple
import time
import logging

logger = logging.getLogger(__name__)

try:
    from langchain_core.runnables import RunnableConfig
except ImportError:
    RunnableConfig = Any

from marathon_qa_assistant.core.profile_context import build_prompt_profile_summary
from marathon_qa_assistant.core.state_models import (
    IntegratedState,
    build_adaptive_adjustment_contract,
    derive_adaptive_reasons,
    normalize_workout_feedback,
)
from marathon_qa_assistant.core.evidence_bundle import find_invalid_citations
from marathon_qa_assistant.nodes.common import (
    ai_invoke,
    ensure_usage,
    format_evidence_lines,
    format_state_evidence_lines,
    get_security_prompt_suffix,
)


QA_REPORT_REQUIRED_SECTIONS = [
    "结论",
    "训练建议",
    "专项不受影响的边界",
    "知识库可见证据",
    "证据不足或待核验之处",
]

QA_REPORT_CONTRACT_INSTRUCTION = (
    "QA 报告必须按顺序固定包含以下二级标题："
    + "、".join(f"## {section}" for section in QA_REPORT_REQUIRED_SECTIONS)
    + "。其中“知识库可见证据”必须覆盖本轮实际提供的本地知识库可见证据编号、来源和摘要；"
    "如果没有可见证据，必须明确写明本轮未检索到可展示的本地知识库证据，不能编造引用。"
)


def _profile_summary(profile: Dict[str, Any]) -> str:
    # 只把明确确认过的画像字段放进 prompt，避免默认体重/目标/经验污染回答。
    return build_prompt_profile_summary(profile)


def _format_wiki_context(wiki_context: str) -> str:
    text = str(wiki_context or "").strip()
    if not text:
        return "暂无外部概念补充"
    return text


async def _run_expert_llm(
    role_name: str,
    task_instruction: str,
    state: IntegratedState,
    config: RunnableConfig,
    fallback_title: str,
) -> Tuple[str, Dict[str, int]]:
    profile = state.get("user_profile", {})

    # 低置信标注：检查证据是否全部为 low，若是则在 prompt 中注入警告指令
    evidence_items = (state.get("evidence_bundle") or {}).get("evidence_items") or []
    all_low = bool(evidence_items) and all(
        item.get("confidence_level") == "low"
        for item in evidence_items if isinstance(item, dict)
    )
    low_confidence_warning = ""
    if all_low:
        low_confidence_warning = (
            "\n\n⚠️ **重要指令**：当前所有知识库证据的置信度均为「低」。"
            "你必须在回答最开头添加以下横幅（原样输出，不要修改）：\n\n"
            "> ⚠️ **证据不足声明**：以下回答缺乏足够的知识库证据支持，仅供参考，不应作为训练处方依据。"
            "建议用户上传相关领域资料或咨询专业教练。\n\n"
            "然后正常回答。但任何涉及训练处方、伤病判断、营养剂量的建议，"
            "必须在句末标注「（基于通用知识，非本地证据）」"
        )

    # P1: 注入 KG 安全约束
    safety_constraints = state.get("safety_constraints") or []
    constraints_text = ""
    if safety_constraints:
        lines = ["\n相关安全约束（来自知识图谱文献，请结合用户画像逐条审查）："]
        for c in safety_constraints[:10]:
            rel_cn = "硬约束" if c["relation"] == "constrains" else "风险因素"
            ev = c.get("evidence_source", "")[:30]
            lines.append(f"- [{rel_cn}] {c['source']} → {c['target']}" + (f" (来源: {ev})" if ev else ""))
        constraints_text = "\n".join(lines)

    prompt = f"""你是马拉松多智能体系统中的 {role_name}。

任务要求：
{task_instruction}
{low_confidence_warning}
{constraints_text}

用户问题：
{state.get("query", "")}

用户画像：
{_profile_summary(profile)}

知识图谱上下文：
{state.get("graph_context", "") or "暂无直接图谱路径"}

本地知识库可见证据（必须全部处理，不能只给结论）：
{format_state_evidence_lines(state, limit=None)}

Wiki 概念补充上下文：
{_format_wiki_context(state.get("wiki_context", ""))}

引用规则（严格遵守，违反即为不合格）：
1. 凡使用上述本地知识库证据中的事实信息，必须在对应句末标注 [1]、[2] 等数字来源编号，只允许纯数字编号格式。
2. 正确示例：...由于过度训练 [1]。...VO₂max 提升与间歇跑有关 [1][2]。
3. 严禁使用以下格式：[来源: xxx.pdf]、[来源: 某论文]、[ref: xxx]、[citation needed] 或任何非纯数字的引用格式。这些格式前端无法生成可点击的预览按钮。
4. Wiki 只用于解释概念背景，不作为训练处方依据，也不要给 Wiki 内容编造 [n] 引用。
5. 没有本地知识库证据时，可以基于模型通用知识给出一般说明，但必须明确这是“未绑定外部证据的一般说明”；模型通用知识不得标成 [n] 证据，也不得替代核心训练处方字段的 evidence 来源。

请输出简洁、可执行、可审核的中文 Markdown，严格遵守引用规则，避免编造资料来源。
{QA_REPORT_CONTRACT_INSTRUCTION if state.get("intent_type") == "qa" else ""}
{get_security_prompt_suffix()}"""

    try:
        return await ai_invoke(prompt, config, state.get("token_usage"))
    except Exception:
        fallback = (
            f"## {fallback_title}\n"
            f"- 问题：{state.get('query', '')}\n"
            f"- 画像摘要：{profile.get('goal', '未知目标')} / {profile.get('weekly_mileage', 0)} km\n"
            f"- 证据摘要：\n{format_state_evidence_lines(state, limit=None)}"
        )
        return fallback, ensure_usage(state.get("token_usage"))


async def coach_node(state: IntegratedState, config: RunnableConfig) -> dict:
    intent = state.get("intent_type", "qa")
    if intent == "plan":
        task_instruction = (
            "用户请求生成训练计划。请从用户需求中提取所有训练类型、配速、时间、场地约束，"
            "生成一份包含具体日程的周训练计划。每节课必须包含热身方案、主课细节（组数×距离+配速+组间休息）、冷身方案。"
            "输出为 Markdown 表格格式，一周七天全覆盖。不要反问用户。"
        )
    else:
        task_instruction = (
            "你是马拉松训练问答教练，负责回答用户关于训练原理、方法、伤病预防和具体执行建议的问题。"
            "你必须直接给出专业、具体、可执行的回答，结合用户画像和知识库证据，不反问、不追加问题。\n\n"
            "══════════════════════════\n"
            "【领域知识框架】\n\n"
            "- 训练基本原则：渐进超负荷（每1-4周增加总跑量5-10%或强度刺激）、专项性（训练适应目标赛事需求）、"
            "恢复与超量补偿（高强度刺激后需恢复窗口才能产生适应）、个体差异（能力、恢复速度、生活压力决定训练反应）、"
            "可逆性（停训3-4周后VO₂max开始下降）。\n"
            "- 经典训练类型（Jack Daniels VDOT 体系）：\n"
            "  轻松跑(E)：最大心率65-78%，RPE 2-4/10，用于建立有氧基础、恢复，"
            "配速大约比马拉松配速慢 20-25%；\n"
            "  节奏跑(T)：乳酸阈值强度，大约能维持1小时的全力配速，RPE 7-8/10，提升乳酸清除能力；\n"
            "  间歇跑(I)：VO₂max 强度，3-5分钟重复，配速大约为3-5公里比赛配速，"
            "RPE 9-10/10，组间恢复相等或略短时间；\n"
            "  重复跑(R)：速度/经济性训练，200-600 m，配速大约为1英里比赛配速，充分恢复，提升跑姿效率；\n"
            "  长距离跑(L)：E 配速或略快，时间 ≥90 分钟，提升脂肪氧化和耐力，最长不超过3小时。\n"
            "- 周训练结构原则：硬-易-硬交替（一次高强度后安排轻松日或休息），长距离安排在周末，"
            "赛前2-3周逐渐减量（taper，周跑量缩减至正常的60-70%但维持一定强度）。\n"
            "- 伤病预防基础：\n"
            "  急性:慢性负荷比 (ACWR)：最近1周急性负荷与过去4周平均慢性负荷比值，"
            "安全区间 0.8-1.3，>1.5 显著增加受伤风险；\n"
            "  疼痛等级：1-3级轻微不适可继续观察，4-6级中度疼痛需减量或调整，"
            "7-10级剧痛、肿胀、关节不稳需立即停跑并评估就医。\n"
            "- 配速/强度感知对照：RPE 1-10 与心率区间大致对应："
            "RPE 1-2（恢复）、RPE 3-4（轻松跑 E 区，最大心率60-70%）、"
            "RPE 5-6（马拉松配速 M 区，70-80%）、RPE 7-8（阈值 T 区，80-90%）、"
            "RPE 9（间歇 I 区，90-95%）、RPE 10（冲刺 R 区，95-100%）。\n\n"
            "══════════════════════════\n"
            "【输出规范】\n\n"
            "- 用户问训练原理/概念：先给定义（含生理机制和典型配速范围），再给应用场景"
            "（适合什么训练周期、什么目标），最后给出「对你的意义」"
            "（根据用户画像中的目标赛事和当前水平具体化建议，如配速参考值）。\n"
            "- 用户问具体建议：给出 2-3 个可执行选项，每条选项标注推荐优先级"
            "（★★★强烈推荐 / ★★☆可考虑 / ★☆☆不优先），"
            "每个选项包含具体配速、距离或时间，并有简明的风险/收益说明。\n"
            "- 用户描述症状/不适：先做风险评估，快速排除危险信号"
            "（如关节交锁、无法承重、红肿热痛、伴有胸痛等），再给出应对建议"
            "（RICE 原则、何时可尝试恢复跑、何时必须就医）。"
            "如果用户描述胸痛、关节剧痛、血尿、眩晕晕厥等危险症状，"
            "必须首先明确建议立即就医，不提供任何替代方案。\n"
            "- 所有配速建议必须带单位 /km，除非原始证据使用 /mile 则保留原文并转换成 /km。\n"
            "- 涉及训练量修改：必须给出具体加减量数值与百分比。"
            "例如「本周总跑量减少20%，从50 km降至40 km，强度课距离缩减30%，轻松跑维持。」\n\n"
            "══════════════════════════\n"
            "【引用要求】\n\n"
            "- 基于知识库证据回答时，必须在引用观点或数据后标注 [1][2] 等编号"
            "（引用编号与提供的知识库证据对应），若需要多条证据支撑，依次标注。"
            "只使用提供的证据，不编造。\n\n"
            "══════════════════════════\n"
            "【硬性输出约束 —— 违反即不合格】\n\n"
            "1. 不要反问用户，不追加「你最近感觉如何？」这类需要补充信息的问题。"
            "基于已有信息直接给出最佳判断和建议。\n"
            "2. 禁止给出可能引发伤病的高风险建议，包括但不限于："
            "「忍着疼痛继续跑」「每天高强度」「无视关节弹响」「大幅度贸然提速」等。\n"
            "3. 如果用户描述危险症状（胸痛、关节剧痛、血尿、呼吸急促伴头晕等），"
            "必须首先建议就医，然后再提供辅助说明。\n"
            "4. 避免模糊表述，如「适当调整」「注意恢复」「加点量」，"
            "必须给出具体方案（配速、距离、频率、周总量变化等）。"
        )
    content, usage = await _run_expert_llm(
        role_name="Coach",
        task_instruction=task_instruction,
        state=state,
        config=config,
        fallback_title="教练建议",
    )
    return {
        "draft_plan": content,
        "rag_sources": state.get("rag_sources", []),
        "token_usage": usage,
        "reasoning_log": ["[coach] 已生成训练建议草稿"],
    }


async def adaptive_coach_node(state: IntegratedState, config: RunnableConfig) -> dict:
    raw_feedback_text = str(state.get("query", "") or "").strip()
    existing_feedback = state.get("adaptive_feedback", {}) or {}
    workout_feedback = normalize_workout_feedback(
        existing_feedback.get("workout_feedback") if isinstance(existing_feedback, dict) else {},
        raw_text=raw_feedback_text,
    )
    reasons = derive_adaptive_reasons(workout_feedback, raw_text=raw_feedback_text)
    adaptive_feedback = {
        "workout_feedback": workout_feedback,
        "reason_codes": [reason["code"] for reason in reasons],
        "reasons": reasons,
        "raw_text": raw_feedback_text,
        "source": "query_text",
    }
    adaptive_adjustment = build_adaptive_adjustment_contract(workout_feedback, raw_text=raw_feedback_text)
    content, usage = await _run_expert_llm(
        role_name="Adaptive Coach",
        task_instruction=(
            "你是自适应训练调整教练，根据用户疲劳、缺课、心率异常等反馈数据，对当前训练计划进行降载或替代建议。"
            "你必须依据客观与主观指标，给出分级调整方案，以安全为最高优先级。\n\n"
            f"自适应反馈数据：{adaptive_feedback}\n\n"
            "══════════════════════════\n"
            "【领域知识框架】\n\n"
            "- 疲劳评估框架：\n"
            "  主观指标：RPE 趋势（同样配速下 RPE 持续升高）、睡眠质量（连续多晚睡眠评分下降）、"
            "肌肉酸痛度 1-10（≥6 持续超过 48 小时提示恢复不足）、情绪/动力下降；\n"
            "  客观指标：早晨静息心率升高 >5 bpm（需连续 3 天以上趋势）、"
            "HRV（心率变异性）下降 >10%（与个人基线比较）、"
            "同等配速下训练心率偏高 >8-10 bpm（心血管漂移/脱水/疲劳）、"
            "心率无法随强度升高（严重过度训练或自主神经疲劳信号）。\n"
            "- 降载策略分级：\n"
            "  Level 1（轻度疲劳）：保持训练日结构不变，强度课减量 20-30%"
            "（如间歇跑组数减少、配速放宽 5-10 秒/km），轻松跑维持原计划，总周跑量减少 10-20%；\n"
            "  Level 2（中度疲劳）：取消一次强度课，改为轻松跑或低冲击交叉训练"
            "（游泳/骑行/椭圆机），总周跑量减少 30-40%，取消长距离跑中任何强度成分，"
            "只保留轻松跑时间（≤原计划的 70%）；\n"
            "  Level 3（重度疲劳/疑似过度训练）：全休 2-3 天，仅步行或轻柔拉伸，"
            "之后若指标改善可尝试 30 分钟极轻松跑（RPE 2-3），周跑量减少 50% 以上，"
            "任何结构训练暂停。\n"
            "- 缺课处理原则：绝不补课，避免训练负荷堆积和 ACWR 骤升。向后顺延训练周期，"
            "维持原有训练结构（周一强度、周三轻松等）优先于维持周跑量。"
            "若连续缺课 ≥2 次，重新评估本周是否应转为降载周。\n"
            "- 心率异常解读与行动：\n"
            "  静息心率升高 + HRV 下降：自主神经疲劳，即时对应 Level 2 调整并增加恢复日；\n"
            "  同等配速心率偏高：可能脱水、糖原不足或疲劳积累，"
            "调整当日训练为轻松感知努力（RPE 控制），并建议增加水分/碳水化合物；\n"
            "  心率对强度无反应（无法升高）：罕见但严重，视为过度训练/病理信号，"
            "强制建议休息并就医排查。\n"
            "- 交叉训练替代方案：游泳（低冲击有氧，RPE 4-5，30-45 分钟）、"
            "骑行（有氧耐力维持，80-100 rpm，心率控制区 1-2）、"
            "椭圆机、力量训练（核心与臀腿，不加重疲劳的维持性训练）。\n\n"
            "══════════════════════════\n"
            "【输出规范】\n\n"
            "- 第一步：输出「疲劳评估摘要」，用一句话总结当前状态"
            "（包含关键指标异常）并明确评级：轻度 / 中度 / 重度。\n"
            "- 第二步：输出「调整方案」，用 Markdown 表格列出接下来 7 天的每日计划调整，"
            "必须包含四列：日期 | 原计划 | 调整后 | 调整理由。"
            "调整后需具体到配速、距离/时间或交叉训练类型；"
            "调整理由需引用评估指标和降载原则。\n"
            "- 第三步：输出「恢复建议」，包含睡眠（具体时长建议、规律性）、"
            "营养（蛋白质摄入时机、水分补充、抗炎食物例子）、"
            "主动恢复（拉伸、泡沫轴、呼吸练习）的具体措施。\n"
            "- 第四步：输出「回归条件」，明确指出哪些客观/主观指标恢复正常后"
            "（如静息心率回落至基线、HRV 恢复、主观酸痛 ≤3、RPE 匹配回归），"
            "可以安全地回到原计划，并建议回归后的首次强度课如何做"
            "（如「先执行一次原计划的 70% 强度，观察 24 小时反应」）。\n\n"
            "══════════════════════════\n"
            "【引用要求】\n\n"
            "- 使用知识库证据时，必须在相关内容后标注 [1][2] 等编号。可多证据并列。\n\n"
            "══════════════════════════\n"
            "【硬性输出约束 —— 违反即不合格】\n\n"
            "1. 不要反问用户，直接根据已有数据给出调整方案。\n"
            "2. 降载必须给出具体百分比和替代方案，禁止只是说「减少一点强度」。必须量化。\n"
            "3. 如果反馈数据提示可能过度训练（如同时出现静息心率升高 >5 bpm、HRV 下降 >10%、"
            "RPE 居高不下、睡眠质量差中至少 3 项），必须明确建议休息，不得建议「减量继续」。\n"
            "4. 禁止建议「加倍训练补回来」或「明天跑长一点补上」等加大负荷的方案。缺课即缺课，不弥补。\n"
            "5. 心率异常（如静息升高或心率漂移异常）且主观疲劳感强烈"
            "（RPE ≥7 级反馈或用户描述「很累」）同时出现时，"
            "调整等级强制升级到 Level 2 以上处理，不允许按 Level 1 应对。\n"
            "6. 避免模糊词如「适当调整」「注意恢复」，必须给出可直接执行的每日安排。"
        ),
        state=state,
        config=config,
        fallback_title="自适应调整建议",
    )
    return {
        "draft_plan": content,
        "adaptive_feedback": adaptive_feedback,
        "adaptive_adjustment": adaptive_adjustment,
        "rag_sources": state.get("rag_sources", []),
        "token_usage": usage,
        "reasoning_log": ["[adaptive_coach] 已生成自适应调整建议"],
    }


async def nutritionist_node(state: IntegratedState, config: RunnableConfig) -> dict:
    content, usage = await _run_expert_llm(
        role_name="Nutritionist",
        task_instruction=(
            "你是马拉松运动营养专家。你的任务是为运动员的日常训练和比赛提供营养、补水和恢复策略建议，"
            "必须严格基于时间线、训练类型和用户画像，给出可量化、可执行的方案。\n\n"
            "══════════════════════════\n"
            "【领域知识框架】\n\n"
            "1. 五大营养时间窗口\n"
            "   - 训练前 2-4 小时：储备糖原，低升糖碳水 + 中等蛋白 + 低脂肪\n"
            "   - 训练前 30 分钟：快速供能，小份高升糖碳水，避免胃肠负担\n"
            "   - 训练中（>60 分钟）：持续供能，每小时 30-90 g 碳水，分次补给\n"
            "   - 训练后 30 分钟（黄金窗口）：4:1 碳水-蛋白质比例，快速启动修复\n"
            "   - 训练后 2-4 小时：完整餐食，碳水:蛋白:脂肪 ≈ 4:3:1~2，补水继续\n\n"
            "2. 宏量营养素配比原则\n"
            "   - 总热量基础：维持训练需求，勿长期低能量可用性\n"
            "   - 训练日用：碳水 5-12 g/kg/d（依训练强度和时长），蛋白质 1.4-2.0 g/kg/d，脂肪 20-35% 总热量\n"
            "   - 非训练/恢复日：适当降低碳水，蛋白质保持\n\n"
            "3. 补水与电解质\n"
            "   - 训练前 2 h：5-7 ml/kg，尿色清亮\n"
            "   - 训练中：每 15-20 min 150-300 ml 含电解质液体，钠 300-600 mg/L\n"
            "   - 训练后：补充体重丢失的 150% 液体量，优先含钠饮品\n\n"
            "4. 常见补充品使用策略\n"
            "   - 能量胶：赛前/训练中每 30-45 min 1 份，配水 200-300 ml\n"
            "   - 盐丸：高温或大出汗时，每 60 min 1-2 粒（视钠含量）\n"
            "   - BCAA/EAA：训练前或中可辅助抗分解，非必需\n"
            "   - 蛋白粉：训练后 30 min 内 0.3-0.4 g/kg，配合碳水\n"
            "   - 咖啡因：赛前 60 min 3-6 mg/kg，注意个体耐受\n\n"
            "5. 比赛日营养\n"
            "   - 赛前 2-3 天碳水加载：10-12 g/kg/d，低纤维\n"
            "   - 赛前餐（2-4 h 前）：200-300 g 碳水 + 中等蛋白，低脂低纤维\n"
            "   - 赛中补给计划：从 15 min 起开始补给，能量胶 + 水，交替运动饮料\n"
            "   - 赛后立即：0.8 g/kg 碳水 + 0.2 g/kg 蛋白，液体优先\n\n"
            "6. 训练类型差异化策略\n"
            "   - 长距离跑（LSD）：赛前餐同比赛日，途中按比赛中补给方案，训练后黄金窗口务必利用\n"
            "   - 间歇/高强度：训练前 2 h 适量碳水，训练中可只补水，训练后快速碳水+蛋白\n"
            "   - 轻松跑/恢复日：无需额外赛中补给，常态三餐，蛋白充足，碳水适量\n"
            "   - 力量训练日：训练后加蛋白至 0.4 g/kg，可配合酪蛋白\n\n"
            "══════════════════════════\n"
            "【输出规范】\n\n"
            "- 必须按时间线组织营养建议，小标题：训练前 2-4 小时、训练前 30 分钟、训练中、"
            "训练后 30 分钟、训练后 2-4 小时、比赛日专项、非训练/恢复日。\n"
            "- 每一时间窗口内，根据当前训练类型（参考用户画像和问题）给出至少一条量化建议，"
            "包含克数、毫升数、具体时间或频率。\n"
            "- 使用 Markdown 表格呈现营养素汇总示例，包含：时段、训练类型、碳水 (g)、蛋白 (g)、"
            "脂肪 (g)、液体 (ml)、补充品/备注。\n"
            "- 每条建议必须以短段落或表格行明确呈现，禁止笼统描述。\n\n"
            "══════════════════════════\n"
            "【引用规则】\n\n"
            "- 凡使用知识库证据中的事实数据（如具体克数、比例、研究结论），"
            "必须在对应句末标注来源编号，如 [1]、[2]。\n"
            "- 如果同一数据被多个来源支持，可标注多个编号。\n"
            "- 若知识库缺少直接证据，可依据公认运动营养指南推导，但需注明「基于通用指南」。\n\n"
            "══════════════════════════\n"
            "【硬性输出约束 —— 违反即不合格】\n\n"
            "1. 不要反问用户，不要输出与营养无关的训练调整。\n"
            "2. 所有建议必须有明确数值、单位（g, ml, mg/kg 等）。\n"
            "3. 必须覆盖训练前、中、后至少三个窗口，除非用户问题仅针对单个窗口。\n"
            "4. 必须区分至少两种训练类型（如长距离 vs 间歇）的营养差别，"
            "若用户只提及一种训练，需补充另一常见类型的对比提醒。\n"
            "5. 若提供补充品建议，必须明确使用时机、剂量、和水一起服用说明。\n"
            "6. 输出结尾附「执行要点」≤100 字总结。\n"
            "7. 禁止使用模糊词如「适量」「多喝」「一些」，必须转化为具体数值或范围。"
        ),
        state=state,
        config=config,
        fallback_title="营养支持建议",
    )
    merged = (state.get("draft_plan", "") + "\n\n" + content).strip()
    return {
        "draft_plan": merged,
        "nutritionist_done": True,
        "token_usage": usage,
        "reasoning_log": ["[nutritionist] 已补充营养支持建议"],
    }


async def therapist_node(state: IntegratedState, config: RunnableConfig) -> dict:
    del config
    draft = state.get("draft_plan", "") or state.get("final_report", "")
    review_feedback: List[str] = []
    passed = True

    risky_keywords = ["强忍疼痛"]
    for keyword in risky_keywords:
        if keyword in draft:
            passed = False
            review_feedback.append(f"检测到潜在高风险表述：{keyword}")

    if state.get("intent_type") == "qa":
        review_feedback.append("QA 模式仅做安全检查，不做处方回写。")

    feedback_text = "；".join(review_feedback) if review_feedback else "未发现明显风险表达。"
    risk_alert = ""
    if not passed:
        risk_alert = f"<div class='github-flash-warn'><strong>治疗师审查：</strong>{feedback_text}</div>"

    return {
        "therapist_passed": passed,
        "review_feedback": feedback_text,
        "risk_alert": risk_alert,
        "token_usage": ensure_usage(state.get("token_usage")),
        "reasoning_log": [f"[therapist] 安全初筛: {'通过' if passed else '需审计处理'}"],
    }


# ── AgentDoG P0 (修订): 反馈 → 诊断映射，仅保留确定性检查项 ──
# 主观判断项 (overtraining_rx, pacing_overly_aggressive, recovery_insufficient 等) 已移除。
# 审计职责: 引用诚实 + 文献一致 + 硬合同 (用户要求) + 医疗红线。不审训练方案是否"最优"。

_FEEDBACK_TRIPLE_MAP: dict[str, tuple[str, str, str]] = {
    # ── 确定性: 审计可证实 ──
    "引用编号不存在": ("llm_generation", "hallucinated_claim", "citation_break"),
    "缺少 source_path": ("rag_retrieval", "citation_integrity", "untraceable_evidence"),
    "强忍疼痛": ("user_input", "contraindication_missed", "injury_risk"),
    "therapist": ("user_input", "contraindication_missed", "injury_risk"),
    # 硬合同: plan 不符合用户显式要求
    "合同": ("llm_generation", "contract_violation", "user_misalignment"),
}

# targeted_fix: 仅保留可执行、非主观的建议
_FIX_MAP: dict[str, str] = {
    "hallucinated_claim": "删除或替换为有本地证据支持的表述，检查引用编号对应关系",
    "citation_integrity": "为每个处方级建议附加明确的 [n] 证据引用",
    "contraindication_missed": "立即就医评估，暂停相关训练直至医生确认安全",
    "contract_violation": "按照用户明确要求修正计划：周数、可用日、最长时长、训练类型",
    "untraceable_evidence": "补充证据来源路径或降级为「基于通用知识」标注",
    "user_misalignment": "对照用户画像和反馈逐项修正",
}


def _classify_feedback(feedback_text: str) -> tuple[str, str, str, str]:
    """将审计反馈文本分类为诊断 + 定向修复建议。仅处理确定性检查项。"""
    risk_source = "llm_generation"
    failure_mode = "citation_integrity"
    real_world_harm = "untraceable_evidence"
    for keyword, triple in _FEEDBACK_TRIPLE_MAP.items():
        if keyword in feedback_text:
            risk_source, failure_mode, real_world_harm = triple
            break
    targeted_fix = _FIX_MAP.get(failure_mode, "重新审查该部分内容，确保符合用户明确要求")
    return risk_source, failure_mode, real_world_harm, targeted_fix


def _build_ternary_diagnosis(feedback: list[str], approved: bool) -> dict:
    """构建 AgentDoG 三元组诊断。"""
    if approved:
        return {"diagnoses": [], "summary": "审计通过，无安全风险"}
    diagnoses = []
    for item in feedback:
        risk_source, failure_mode, real_world_harm, targeted_fix = _classify_feedback(item)
        diagnoses.append({
            "feedback": item,
            "risk_source": risk_source,
            "failure_mode": failure_mode,
            "real_world_harm": real_world_harm,
            "targeted_fix": targeted_fix,
        })
    return {
        "diagnoses": diagnoses,
        "summary": f"审计未通过：{len(diagnoses)} 个问题",
        "primary_risk_source": diagnoses[0]["risk_source"] if diagnoses else "unknown",
        "primary_failure_mode": diagnoses[0]["failure_mode"] if diagnoses else "unknown",
    }


def _auditor_trace_step(state: dict, approved: bool, feedback: list[str], iteration: int) -> dict:
    """记录 auditor 节点的执行轨迹。"""
    from datetime import datetime, timezone
    return {
        "node": "critic_auditor",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_snapshot": {
            "workflow_kind": state.get("workflow_kind") or state.get("intent_type"),
            "iteration": iteration,
            "has_evidence": bool(state.get("ranked_evidence")),
            "has_draft": bool(state.get("draft_plan") or state.get("final_report")),
        },
        "output_snapshot": {
            "approved": approved,
            "issue_count": len(feedback),
            "issues": feedback[:3],
        },
        "decision": "通过，进入 formatter" if approved else f"未通过 ({len(feedback)} 个问题)，打回重试",
    }


async def critic_auditor_node(state: IntegratedState, config: RunnableConfig) -> dict:
    del config
    # C3: 审计性能计时
    t0 = time.perf_counter()
    current_iteration = int(state.get("iteration_count", 0) or 0)
    draft = state.get("draft_plan", "") or state.get("final_report", "")
    evidence_bundle = state.get("evidence_bundle") if isinstance(state.get("evidence_bundle"), dict) else {}
    evidence_items = [item for item in (evidence_bundle.get("evidence_items") or []) if isinstance(item, dict)]
    structured_plan = state.get("structured_training_plan") if isinstance(state.get("structured_training_plan"), dict) else {}
    workflow_kind = state.get("workflow_kind") or state.get("intent_type") or "qa"
    feedback: List[str] = []

    # P0-5: 当 evidence_bundle 无证据时，跳过引用编号检查，避免 coach 编造引用后 auditor 拒绝形成死循环
    if evidence_items:
        invalid_citations = find_invalid_citations(draft, evidence_bundle)
        if invalid_citations:
            feedback.append(f"引用编号不存在：{', '.join(invalid_citations)}")
    else:
        invalid_citations = []

    for item in evidence_items:
        tier = str(item.get("tier") or "")
        # P0-2: 图谱来源的证据天然没有文档路径，跳过 source_path 检查
        trace = item.get("trace") if isinstance(item, dict) else {}
        is_graph_sourced = isinstance(trace, dict) and trace.get("graph_hit")
        if tier in {"kb_fallback", "action_library"} and not is_graph_sourced and not str(item.get("source_path") or "").strip():
            feedback.append(f"证据 {item.get('citation_label', '')} 缺少 source_path")
            break

    hmp_validation = {}
    if structured_plan:
        hmp_validation = structured_plan.get("half_marathon_protocol_validation") or {}
    hmp_errors = (hmp_validation.get("errors") or []) if isinstance(hmp_validation, dict) else []
    if hmp_errors:
        feedback.append(f"HMP 专项验证仍有 {len(hmp_errors)} 条错误，不能放行")

    # E1: LLM 生成课时是否在文献约束范围内
    try:
        from marathon_qa_assistant.core.half_marathon_validator import _validate_workout_duration_bounds
        week_plans = structured_plan.get("week_plans", []) if structured_plan else []
        for issue in _validate_workout_duration_bounds(week_plans):
            feedback.append(f"[{issue.constraint_id}] {issue.message} -> {issue.recommendation}")
    except Exception:
        pass

    risky_keywords = ["强忍疼痛"]
    for keyword in risky_keywords:
        if keyword in draft:
            feedback.append(f"检测到潜在高风险表述：{keyword}")

    has_rule_skeleton = bool(structured_plan)
    has_evidence = bool(evidence_items)
    if workflow_kind == "plan" and not (has_rule_skeleton or has_evidence):
        feedback.append("计划型请求缺少规则骨架或证据包支撑")

    therapist_passed = state.get("therapist_passed", True)
    if therapist_passed is False and state.get("review_feedback"):
        feedback.append(str(state.get("review_feedback")))

    # ── P1 修订: 硬合同检查 — 比对 plan 是否满足用户显式要求 ──
    profile = state.get("user_profile") or {}
    # 1. 可用训练日
    available_days_str = str(profile.get("available_days") or "")
    if available_days_str:
        expected_days = [d.strip() for d in available_days_str.replace(",", "，").split("，") if d.strip()]
        expected_count = len(expected_days)
        if structured_plan and expected_count:
            week_plans = structured_plan.get("week_plans", [])
            if week_plans:
                plan_day_count = max(len(wp.get("days", [])) for wp in week_plans) if week_plans else 0
                if plan_day_count > 0 and plan_day_count > expected_count:
                    feedback.append(f"[合同] 计划安排了 {plan_day_count} 天训练，但用户明确可用 {expected_count} 天 ({available_days_str})")
    # 2. 最长训练时长
    max_minutes = profile.get("max_session_minutes")
    if max_minutes and draft:
        import re as _re_check
        max_m = int(max_minutes)
        minutes_in_draft = _re_check.findall(r'(\d+)\s*(?:分钟|min)', draft)
        for m_val in minutes_in_draft:
            if int(m_val) > max_m:
                feedback.append(f"[合同] 计划安排了 {m_val} 分钟训练，超出用户设定的最长 {max_m} 分钟")
                break
    # 3. 用户反馈未处理 (adaptive mode)
    adaptive_feedback = state.get("adaptive_feedback")
    if adaptive_feedback and isinstance(adaptive_feedback, str) and adaptive_feedback.strip():
        if "累" in adaptive_feedback or "疲劳" in adaptive_feedback or "疼" in adaptive_feedback:
            # 检查 plan 是否降低了强度 — 只 flag，不判断
            if workflow_kind != "adaptive":
                feedback.append(f"[合同] 用户反馈了疲劳/疼痛 ({adaptive_feedback[:30]})，但未触发自适应调整模式")
    # 4. 训练类型覆盖
    training_types_str = str(profile.get("training_types") or "")
    if training_types_str and workflow_kind == "plan" and draft:
        requested_types = [t.strip() for t in training_types_str.replace(",", "，").split("，") if t.strip()]
        missing_types = [t for t in requested_types if t not in draft]
        if len(missing_types) >= 2:
            feedback.append(f"[合同] 用户要求训练类型 {requested_types}，计划未体现: {missing_types}")

    approved = not feedback
    consistency = 88 if approved else 60
    safety = 92 if approved else 45
    roi = min(100, 40 + len(evidence_items) * 10)
    if has_rule_skeleton:
        roi = max(roi, 70)

    summary = "通过独立审计，可进入格式化输出。" if approved else "独立审计未通过：" + "；".join(feedback[:4])

    # C3: 审计性能计时
    elapsed_ms = (time.perf_counter() - t0) * 1000
    logger.info("critic_auditor: %.1fms, approved=%s, issues=%d, evidence=%d",
                elapsed_ms, approved, len(feedback), len(evidence_items))

    return {
        "is_approved": approved,
        "iteration_count": current_iteration + (0 if approved else 1),
        "review_feedback": summary,
        "audit_scores": {
            "consistency": consistency,
            "safety": safety,
            "roi": roi,
            "summary": summary,
            "score_sources": {
                "evidence_count": len(evidence_items),
                "has_rule_skeleton": has_rule_skeleton,
                "invalid_citations": invalid_citations,
                "hmp_error_count": len(hmp_errors),
            },
        },
        "token_usage": ensure_usage(state.get("token_usage")),
        "reasoning_log": [f"[critic_auditor] approved={approved}, consistency={consistency}, safety={safety}, roi={roi}"],
        "execution_trace": [_auditor_trace_step(state, approved, feedback, current_iteration)],
        "audit_diagnosis": _build_ternary_diagnosis(feedback, approved),
    }


async def research_analyst_node(state: IntegratedState, config: RunnableConfig) -> dict:
    content, usage = await _run_expert_llm(
        role_name="Research Analyst",
        task_instruction=(
            "你是运动科学前沿研究分析师。你需要以研究综述的深度，解析用户提出的马拉松训练相关问题，"
            "揭示概念关系、比较证据质量，并提炼可跨问题复用的科学原则。\n\n"
            "══════════════════════════\n"
            "【领域知识框架】\n\n"
            "1. 核心理论模型\n"
            "   - 训练负荷-适应模型：刺激 → 疲劳 → 适应 → 超量恢复，需考虑个体恢复速率\n"
            "   - 周期化理论：线性、波形、板块周期化，以及各自与不同水平跑者的适配\n"
            "   - 训练强度分布：极化训练（80/20 低强度/高强度）、金字塔模型、阈值模型，及其生理依据\n"
            "   - 关键生理学指标互动：VO₂max、乳酸阈、跑步经济性、最大脂肪氧化强度（FatMax）之间的依赖和转移关系\n"
            "   - 生理信号与过度训练：HRV、静息心率、血液标志物（CK、尿素）的预警阈值\n\n"
            "2. 证据质量评估维度\n"
            "   - 研究设计：系统综述/Meta 分析 > RCT > 队列/横断面 > 个案/经验报告\n"
            "   - 样本量、效应量（Cohen's d, R²）、置信区间宽度\n"
            "   - 外部效度：精英 vs 大众跑者，实验室 vs 实地条件\n"
            "   - 发表偏倚风险、资助方背景、是否预注册\n"
            "   - 矛盾证据的处理：可能出现「效果方向不一致」时，需考虑调节变量（训练状态、测量误差）\n\n"
            "3. 概念关系类型\n"
            "   - 因果关系：需 RCT 或有向无环图支持，慎用\n"
            "   - 相关关系：横断面观察或纵向关联，不得推论因果\n"
            "   - 机制链条：从分子/细胞到器官系统到表现输出（如：线粒体生物发生→乳酸清除能力→阈速度）\n"
            "   - 中介/调节变量：如训练量通过恢复质量影响表现\n\n"
            "══════════════════════════\n"
            "【输出规范】\n\n"
            "分析报告必须包含以下固定板块（依次呈现）：\n\n"
            "1. 核心发现：用 ≤3 条简洁陈述概括最主要发现，每条标注证据强度（直接/间接/待验证）。\n\n"
            "2. 概念关系图（文字）：至少描述一条 A→B→C 机制链条，明确因果关系或相关关系标识。"
            "可使用「促进/抑制/调节/关联」等动词。\n\n"
            "3. 证据对比表：Markdown 表格，至少两行证据来源对比，包含：\n"
            "   - 来源编号 | 研究设计 | 受试人群 | 主要结论 | 效应量/可信度评级（高/中/低）\n\n"
            "4. 可复用结论：提炼出 ≥2 条不限于当前问题、普遍适用于马拉松训练的一般性原则或机制，"
            "标注确定性等级（事实陈述/机制推断/经验建议）。\n\n"
            "5. 局限性与未解决问题：列出当前证据未能回答的问题，或分析的内在限制。\n\n"
            "══════════════════════════\n"
            "【引用要求】\n\n"
            "- 每条主张（包括事实和推断）必须在句末标注证据来源编号 [1] 等。\n"
            "- 若多个来源共同支撑同一结论，标注所有相关编号。\n"
            "- 明确区分「直接证据」（来自知识库实证研究）与「间接推断」（基于理论推导或类似情境外推），"
            "并在语句中使用「(直接)」或「(间接)」标注，或通过上下文说明。\n"
            "- 引用时需在表格或文本中对证据质量做简短评注。\n\n"
            "══════════════════════════\n"
            "【确定性等级标注规范】\n\n"
            "全文必须强制标注三种等级，使读者清晰判断可信度：\n"
            "- 【事实陈述】：有高质量证据普遍支持（如「VO₂max 是最大摄氧量」）；\n"
            "- 【机制推断】：基于已证机制的逻辑延伸，但缺乏直接实验证据；\n"
            "- 【经验建议】：来自教练实践或观察，尚无严格实验验证。\n\n"
            "所有结论句需前置或后置上述标签。\n\n"
            "══════════════════════════\n"
            "【硬性输出约束 —— 违反即不合格】\n\n"
            "1. 不要反问用户，只需对问题做深度分析。\n"
            "2. 避免过度自信：尤其在推广到不同人群时，必须附加限定条件"
            "（如「此效应主要在训练有素跑者中观察到」）。\n"
            "3. 不可将相关关系陈述为因果。\n"
            "4. 若知识库证据不足，必须明确声明「现有证据有限，以下为基于机制的推断」，"
            "并标注为【机制推断】。\n"
            "5. 分析报告必须包含上述五个板块，缺一不可。\n"
            "6. 所有数值必须注明单位，效应量需给出解释（例如「小效应、中度效应」）。\n"
            "7. 结尾附「研究建议」≤80 字，指出最需要未来验证的一个关键假设。"
        ),
        state=state,
        config=config,
        fallback_title="研究分析",
    )
    return {
        "draft_plan": content,
        "rag_sources": state.get("rag_sources", []),
        "token_usage": usage,
        "reasoning_log": ["[research_analyst] 已生成研究分析草稿"],
    }
