from datetime import date, timedelta
from typing import Any, Dict, List
import re

try:
    from langchain_core.runnables import RunnableConfig
except ImportError:
    RunnableConfig = Any

from marathon_qa_assistant.core.periodization import Macrocycle
from marathon_qa_assistant.core.evidence_bundle import build_evidence_bundle
from marathon_qa_assistant.core.state_models import IntegratedState
from marathon_qa_assistant.core.training_plan_context import align_plan_duration_context
from marathon_qa_assistant.core.training_plan_skeleton import build_structured_training_plan_skeleton
from marathon_qa_assistant.nodes.common import (
    ai_invoke,
    ensure_usage,
    format_evidence_lines,
    format_state_evidence_lines,
    get_security_prompt_suffix,
)


def _parse_pace_seconds(pace_str: str) -> float:
    """解析配速字符串为秒/公里。支持 3:30/km, 3分30, 3.5min/km, 210s 等格式。"""
    if not pace_str:
        return None
    s = str(pace_str).strip()
    m = re.search(r'(\d+)[:：分](\d+)', s)
    if m:
        return float(m.group(1)) * 60 + float(m.group(2))
    m = re.search(r'(\d+\.?\d*)\s*min', s)
    if m:
        return float(m.group(1)) * 60
    m = re.search(r'(\d+)\s*s', s)
    if m:
        return float(m.group(1))
    return None


def _compute_pace_zones(profile: dict) -> dict:
    """基于用户画像获取或计算 9 区配速区间。
    
    优先级：profile['pace_zones'] > T-Pace > 目标成绩。
    """
    from marathon_qa_assistant.core.zone_constants import ZONE_LABELS
    from marathon_qa_assistant.core.physiology import calculate_pace_zones

    zones = {}
    pace_zones = profile.get("pace_zones", {})
    
    # 1. 优先使用已有的 9 区配速
    if pace_zones and isinstance(pace_zones, dict) and any(pace_zones.values()):
        for i in range(1, 10):
            key = f"Z{i}"
            val = pace_zones.get(key)
            if val and val != "—":
                label = ZONE_LABELS.get(key, key)
                zones[key] = (0, 0, f"{val}/km ({label})")
        zones['_derived_from'] = 'Profile (9-Zones)'
        return zones

    # 2. 如果没有 9 区，尝试基于 t_pace 反推
    t_pace_str = profile.get('t_pace', '')
    if not t_pace_str:
        # 尝试从目标成绩反推 t_pace
        t_pace_sec = None
        goal = str(profile.get('goal', '') or '').strip()
        race_pace_sec = None
        m_half = re.search(r'半马\s*(\d+)\s*分', goal)
        if m_half:
            total_min = int(m_half.group(1))
            race_pace_sec = total_min * 60 / 21.0975
        m_full = re.search(r'全马\s*(\d+)\s*小时\s*(\d+)\s*分', goal)
        if not m_full:
            m_full = re.search(r'全马\s*(\d+)\s*[时分]\s*(\d+)\s*[分]', goal)
        if not m_full:
            m_full = re.search(r'全马\s*(\d{3})\s*$', goal)
            if m_full:
                hour = int(m_full.group(1)[:1])
                minute = int(m_full.group(1)[1:])
                race_pace_sec = (hour * 60 + minute) * 60 / 42.195
        if m_full and not race_pace_sec:
            hour = int(m_full.group(1))
            minute = int(m_full.group(2))
            race_pace_sec = (hour * 60 + minute) * 60 / 42.195

        if race_pace_sec:
            from marathon_qa_assistant.core.physiology import seconds_to_pace
            if '半马' in goal:
                t_pace_str = seconds_to_pace(race_pace_sec - 9)
            else:
                t_pace_str = seconds_to_pace(race_pace_sec - 20)

    if t_pace_str:
        calculated = calculate_pace_zones(t_pace_str)
        for i in range(1, 10):
            key = f"Z{i}"
            val = calculated.get(key)
            if val:
                label = ZONE_LABELS.get(key, key)
                zones[key] = (0, 0, f"{val}/km ({label})")
        zones['_derived_from'] = f'T-Pace 推导 (9-Zones, {t_pace_str})'
    else:
        zones['_derived_from'] = 'unknown'

    # 用户自定义配速偏好覆盖
    pace_pref = str(profile.get('pace_preference', '') or '').strip()
    if pace_pref:
        zones['_pace_preference'] = pace_pref

    return zones


def _fmt_pace(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"


def _build_cycle_phase_summary(total_weeks: int) -> str:
    macrocycle = Macrocycle.from_race_date(
        race_date=date.today() + timedelta(weeks=max(1, total_weeks)),
        total_weeks=total_weeks,
    )
    lines = []
    for mesocycle in macrocycle.mesocycles:
        lines.append(
            f"- {mesocycle.name}：第{mesocycle.start_week}-{mesocycle.end_week}周，"
            f"{mesocycle.goal}（周跑量系数≈{mesocycle.weekly_mileage_ratio:.2f}）"
        )
    return "\n".join(lines)


def _resolve_weeks_source_label(source: str) -> str:
    return {
        "query": "用户显式请求",
        "target_race_date": "比赛倒计时",
        "profile": "画像存量字段",
        "default": "系统默认值",
    }.get(source, source)


def _build_plan_prompt(state: IntegratedState) -> str:
    plan_context = align_plan_duration_context(state.get("query", ""), state.get("user_profile", {}))
    profile = plan_context["aligned_profile"]
    evidence_lines = format_state_evidence_lines(state, limit=5)
    graph_context = state.get("graph_context", "")
    requested_weeks = state.get("requested_weeks")
    if requested_weeks is None:
        requested_weeks = plan_context["requested_weeks"]
    requested_weeks_text = f"{requested_weeks} 周" if requested_weeks else "未显式指定"
    target_race_weeks = plan_context["target_race_weeks"]
    target_race_weeks_text = f"{target_race_weeks} 周" if target_race_weeks else "未换算"
    resolved_plan_weeks = plan_context["resolved_plan_weeks"]
    weeks_source_label = _resolve_weeks_source_label(plan_context["resolved_from"])
    cycle_phase_summary = _build_cycle_phase_summary(resolved_plan_weeks)

    zones = _compute_pace_zones(profile)
    derived = zones.get('_derived_from', 'unknown')
    pace_pref = zones.get('_pace_preference', '')

    pace_table_lines = []
    for i in range(1, 10):
        key = f"Z{i}"
        if key in zones:
            lo, hi, disp = zones[key]
            pace_table_lines.append(f"| {key} | {disp} |")

    pace_table = "\n".join(pace_table_lines) if pace_table_lines else "（无可用配速数据，请根据用户描述推导）"

    prompt = f"""你是马拉松训练计划教练。你必须先按给定训练周期理解当前阶段，再生成严谨、结构完整的训练计划输出。

══════════════════════════
【用户需求】
{state.get("query", "")}

══════════════════════════
【运动员画像】
- 目标：{profile.get('goal', '未设置')}
- 当前周跑量：{profile.get('weekly_mileage', 0)} km
- T-Pace（乳酸阈配速）：{profile.get('t_pace', '') or '未设置'}
- 经验水平：{profile.get('experience_level', '未知')}
- 可用训练日：{profile.get('available_days', '未指定')}
- 单次最长训练：{profile.get('max_session_minutes', '未指定')} 分钟
- 场地偏好：{profile.get('terrain_preference', '未指定')}
- VO₂max：{profile.get('vo2max', '未设置')}
- 用户配速偏好：{pace_pref or '未设置'}

"""

    enhancement_missing = state.get("enhancement_missing_fields", [])
    if enhancement_missing:
        from marathon_qa_assistant.nodes.profile_and_retrieval import ENHANCEMENT_FIELD_LABELS
        enhancement_hints = "\n".join(
            f"- {ENHANCEMENT_FIELD_LABELS.get(f, f)}：未设置（使用默认估算值）"
            for f in enhancement_missing
        )
        prompt += f"""═══════════════════════════
【可补强精度字段】（以下字段缺失，当前使用默认估算值，补充后可获得更个性化训练计划）
{enhancement_hints}

"""

    prompt += f"""═══════════════════════════
【训练周期上下文】（后续训练负荷递进必须严格参考这里，不得回退为默认 12 周或"第一周计划"心智模型）
- 本次显式请求周数：{requested_weeks_text}
- 比赛倒计时换算周数：{target_race_weeks_text}
- 当前对齐后的训练周期：{resolved_plan_weeks} 周（来源：{weeks_source_label}）
- 周期阶段摘要：
{cycle_phase_summary}

══════════════════════════
【生理学配速映射】（推导来源: {derived}，你必须在对应训练类型中严格使用这些配速区间）

| 训练类型 | 配速区间 |
|----------|----------|
{pace_table}

如果用户显式指定了某个类型的配速（如'强度课2:50-3:00/km'），则以用户指定的配速优先。

══════════════════════════
【训练术语精确释义】
- 重复跑 (Repetition)：200m-600m 极短距离极高强度冲刺，组间完全恢复（慢走或站立 2-3 分钟）
- 摄氧量 (VO₂max)：400m-1200m 间歇跑，接近 3K-5K 比赛配速，组间慢跑恢复
- 无氧阈 (Anaerobic Threshold)：800m-2000m 间歇跑，稍慢于 VO₂max 配速，组间慢跑或原地恢复
- 节奏跑 (Tempo Run / Lactate Threshold)：20-40 分钟持续跑，稳定在乳酸阈配速附近
- 有氧阈 (Aerobic Threshold)：30-60 分钟中等强度持续跑，比节奏跑慢 15-25 秒/公里
- 长距离 (Long Run)：60-120 分钟耐力跑，以轻松配速完成
- 轻松跑 (Easy Run)：30-60 分钟恢复性慢跑，非常舒适的配速

══════════════════════════
【知识库证据】
{evidence_lines}

【引用规则】
凡使用上述证据中的事实信息，必须在对应句末或表格单元格内标注 [1]、[2] 等来源编号（例如：...由于过度训练 [1]）。

══════════════════════════
【图谱上下文】
{graph_context or '暂无'}

══════════════════════════
【硬性输出约束 —— 违反任何一条即为不合格】

1. 一周 7 天全覆盖（周一至周日），一天不能少
2. 用户指定的训练日必须严格安排，不可擅自改动
3. 用户指定的训练类型必须逐一覆盖，不可遗漏

★ 主课格式强制要求（这是本次审核的核心）：
  A. 间歇/重复类：必须写成「N×距离，配速X:XX/km，组间慢跑Ym/站立Zm」
     示例：8×400m，配速2:52/km，组间慢跑200m
  B. 节奏跑：必须写成「T分钟，配速X:XX/km（标准阈值配速）」
     示例：30分钟，配速3:07/km
  C. 有氧阈：必须写成「T分钟，配速X:XX/km」
  D. 长距离：必须写成「T分钟，配速X:XX-X:XX/km」
  E. 轻松跑：必须写成「T分钟，配速X:XX/km 或更慢」
  F. 配速必须带单位 /km，不可省略

★ 热身格式：写具体时长+动作类型
   示例：「慢跑10分钟 + 动态拉伸（开合跳、高抬腿、踢腿各30次）」

★ 冷身格式：写具体时长+动作类型
   示例：「慢跑10分钟 + 静态拉伸（股四头肌、腘绳肌、小腿各30秒×2）」

★ 表格列：日期 | 训练类型 | 热身 | 主课（含组数/配速/休息） | 冷身 | 场地 | 备注

★ 表格之后附 ≤100 字的执行提醒

4. 不要反问用户，不要追加需要补充的信息
5. 配速标注必须统一使用「分:秒/km」格式（如 3:07/km），不使用「分 秒」中间加汉字的格式

{get_security_prompt_suffix()}"""
    return prompt


def _build_plan_subtasks(state: IntegratedState) -> List[Dict[str, Any]]:
    query = state.get("query", "")
    entities = state.get("entities", [])[:3]
    focus_text = "\u3001".join(entities) if entities else "训练目标"
    plan_context = align_plan_duration_context(query, state.get("user_profile", {}))
    resolved_plan_weeks = plan_context["resolved_plan_weeks"]

    return [
        {
            "task_id": "TASK-1",
            "objective": "明确训练目标与约束",
            "focus": f"基于问题\u201c{query}\u201d提炼目标、风险与 {resolved_plan_weeks} 周周期范围",
        },
        {
            "task_id": "TASK-2",
            "objective": "生成训练结构",
            "focus": f"围绕 {focus_text} 设计 {resolved_plan_weeks} 周周期下的训练日结构与强度分配",
        },
        {
            "task_id": "TASK-3",
            "objective": "补充执行提醒",
            "focus": "增加恢复、补给与安全监控提示",
        },
    ]


async def planner_node(state: IntegratedState, config: RunnableConfig) -> dict:
    del config
    if state.get("missing_fields"):
        return {
            "subtasks": [],
            "token_usage": ensure_usage(state.get("token_usage")),
            "reasoning_log": ["[planner] 缺少关键画像指标，停止拆解"],
        }

    subtasks = _build_plan_subtasks(state)
    return {
        "subtasks": subtasks,
        "token_usage": ensure_usage(state.get("token_usage")),
        "reasoning_log": [f"[planner] 已拆解 {len(subtasks)} 个子任务"],
    }


def _static_executor_fallback(state: IntegratedState, profile: dict, evidence_lines: str) -> str:
    sections = [
        "## 训练计划草案（LLM 不可用，生成模板）",
        f"- 目标：{profile.get('goal', '未设置')}",
        f"- 当前周跑量：{profile.get('weekly_mileage', 0)} km",
        f"- 参考实体：{', '.join(state.get('entities', [])) or '未识别'}",
        "",
        "### TASK-1 明确训练目标与约束",
        "请重新提交需求，或检查 Ollama 服务是否正常运行。",
        "",
        "### 证据摘要",
        evidence_lines,
    ]
    return "\n".join(sections)


async def executor_node(state: IntegratedState, config: RunnableConfig) -> dict:
    subtasks = state.get("subtasks", [])
    if not subtasks:
        return {
            "draft_plan": "",
            "structured_training_plan": None,
            "reasoning_log": ["[executor] 没有可执行的子任务"],
            "token_usage": ensure_usage(state.get("token_usage")),
        }

    rag_sources = state.get("rag_sources", [])
    prompt = _build_plan_prompt(state)
    structured_training_plan = build_structured_training_plan_skeleton(
        query=state.get("query", ""),
        profile=state.get("user_profile", {}),
        requested_weeks=state.get("requested_weeks"),
    )
    validation_result = structured_training_plan.get("half_marathon_protocol_validation", {}) if isinstance(structured_training_plan, dict) else {}
    evidence_bundle = build_evidence_bundle(
        query=state.get("query", ""),
        rag_sources=rag_sources,
        ranked_evidence=state.get("ranked_evidence", []),
        structured_training_plan=structured_training_plan,
        health=(state.get("evidence_bundle") or {}).get("health") if isinstance(state.get("evidence_bundle"), dict) else None,
    )

    try:
        content, usage = await ai_invoke(prompt, config, state.get("token_usage"))
        fallback_reason = ""
    except Exception as exc:
        fallback_reason = f"[executor] LLM 调用失败，已使用静态模板兜底: {exc}"
        profile = state.get("user_profile", {})
        evidence_lines = format_evidence_lines(rag_sources, limit=3)
        content = _static_executor_fallback(state, profile, evidence_lines)
        usage = ensure_usage(state.get("token_usage"))

    logs = [
        f"[executor] 已生成 {structured_training_plan.get('plan_meta', {}).get('actual_weeks', 0)} 周结构化训练骨架",
        "[executor] 已通过 LLM 生成完整周训练计划",
    ]
    if fallback_reason:
        logs.append(fallback_reason)

    return {
        "draft_plan": content,
        "draft_ready": True,
        "structured_training_plan": structured_training_plan,
        "validation_result": validation_result,
        "repair_suggestions": validation_result.get("repair_suggestions", []) if isinstance(validation_result, dict) else [],
        "fallback_reason": fallback_reason,
        "used_fallback": bool(fallback_reason),
        "evidence_bundle": evidence_bundle,
        "rag_sources": rag_sources,
        "token_usage": usage,
        "reasoning_log": logs,
    }
