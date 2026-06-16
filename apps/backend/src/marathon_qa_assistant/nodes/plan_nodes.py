from datetime import date, timedelta
from typing import Any, Dict, List
import asyncio
import logging
import re

_logger = logging.getLogger("workflow_engine")

try:
    from langchain_core.runnables import RunnableConfig
except ImportError:
    RunnableConfig = Any

from marathon_qa_assistant.core.periodization import Macrocycle
from marathon_qa_assistant.core.evidence_bundle import build_evidence_bundle
from marathon_qa_assistant.core.state_models import IntegratedState
from marathon_qa_assistant.core.training_plan_context import align_plan_duration_context
from marathon_qa_assistant.core.training_plan_skeleton import build_structured_training_plan_skeleton
from marathon_qa_assistant.core.prompt_kit import (
    CITATION_RULES_PLAN,
    PLAN_COACH_IDENTITY,
    PLAN_GLOSSARY,
)
from marathon_qa_assistant.nodes.common import (
    ai_invoke,
    ensure_usage,
    format_evidence_lines,
    format_state_evidence_lines,
    get_security_prompt_suffix,
)


def _safe_llm_fallback_summary(exc: Exception) -> str:
    provider = str(getattr(exc, "provider", "") or "").strip()
    error_code = str(getattr(exc, "error_code", "") or "").strip()
    if provider and error_code:
        return f"{provider}/{error_code}"
    return exc.__class__.__name__


def _executor_llm_timeout_sec(config: RunnableConfig) -> float:
    """Keep executor under the LangGraph node timeout so structured plans survive LLM stalls."""
    configured = 90.0
    try:
        cfg = config.get("configurable", {}) if isinstance(config, dict) else {}
        configured = float(cfg.get("executor_llm_timeout_sec") or cfg.get("llm_timeout_sec") or configured)
    except Exception:
        configured = 90.0
    return max(10.0, min(configured, 90.0))


async def _invoke_executor_llm(prompt: str, config: RunnableConfig, token_usage: dict):
    task = asyncio.create_task(ai_invoke(prompt, config, token_usage))
    done, pending = await asyncio.wait({task}, timeout=_executor_llm_timeout_sec(config))
    if task in done:
        return await task
    task.cancel()
    return None


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
        race_type = None  # "full" | "half"

        # ── P0-3: 时间在前、赛事在后的模式 ──
        # "3小时30分全马" / "3小时30分 马拉松"
        m_time_first_full = re.search(r'(\d+)\s*小时\s*(\d+)\s*分[^a-z0-9]*(?:全马|马拉松|marathon|全马)', goal, re.I)
        if m_time_first_full:
            hour = int(m_time_first_full.group(1))
            minute = int(m_time_first_full.group(2))
            race_pace_sec = (hour * 60 + minute) * 60 / 42.195
            race_type = "full"
        else:
            # "1小时30分半马" / "1小时30分 半程"
            m_time_first_half = re.search(r'(\d+)\s*小时\s*(\d+)\s*分[^a-z0-9]*(?:半马|半程|half)', goal, re.I)
            if m_time_first_half:
                hour = int(m_time_first_half.group(1))
                minute = int(m_time_first_half.group(2))
                race_pace_sec = (hour * 60 + minute) * 60 / 21.0975
                race_type = "half"

        # ── 赛事在前、时间在后的模式（原有）──
        if race_pace_sec is None:
            m_half = re.search(r'半马\s*(\d+)\s*分', goal)
            if m_half:
                total_min = int(m_half.group(1))
                race_pace_sec = total_min * 60 / 21.0975
                race_type = "half"
        if race_pace_sec is None:
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
            if m_full:
                race_type = "full"

        if race_pace_sec:
            from marathon_qa_assistant.core.physiology import seconds_to_pace
            if race_type == "half":
                t_pace_str = seconds_to_pace(race_pace_sec - 9)
            else:
                t_pace_str = seconds_to_pace(race_pace_sec - 20)

    # L3 Critical Speed 兜底：无 T-Pace 且无法从目标成绩反推时，从 PB 拟合 CS 作为阈值配速代理。
    _cs_derived = False
    if not t_pace_str:
        try:
            from marathon_qa_assistant.core.physiology import collect_pb_distance_time, calculate_critical_speed
            cs_result = calculate_critical_speed(collect_pb_distance_time(profile))
            if cs_result:
                t_pace_str = cs_result["cs_pace_str"]
                _cs_derived = True
        except Exception:
            pass

    if t_pace_str:
        calculated = calculate_pace_zones(t_pace_str)
        for i in range(1, 10):
            key = f"Z{i}"
            val = calculated.get(key)
            if val:
                label = ZONE_LABELS.get(key, key)
                zones[key] = (0, 0, f"{val}/km ({label})")
        zones['_derived_from'] = (
            f'Critical Speed 拟合 (9-Zones, {t_pace_str}/km, R²={cs_result["r_squared"] if _cs_derived else 0})'
            if _cs_derived else f'T-Pace 推导 (9-Zones, {t_pace_str})'
        )
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
    from marathon_qa_assistant.core.training_plan_context import merge_plan_profile_overrides
    query = state.get("query", "")
    plan_context = align_plan_duration_context(query, state.get("user_profile", {}))
    # 用 query 中显式提到的目标、PB、周跑量等覆盖 DB 中可能过时的字段，
    # 确保配速区间推导基于本次请求语境而非历史画像。
    profile = merge_plan_profile_overrides(query, plan_context["aligned_profile"])

    # Step 2: 构建文献约束表上下文 (替代硬编码分钟值)
    try:
        from marathon_qa_assistant.core.workout_constraints import build_constraints_context
        constraint_table = build_constraints_context("auto")
    except Exception:
        constraint_table = "(约束表暂不可用，请使用典型训练时长 30-60min 范围)"
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

    pb_half = profile.get('pb_half') or profile.get('current_half_time') or '未设置'
    pb_full = profile.get('pb_full') or '未设置'
    target_half = profile.get('target_half_time') or '未设置'

    prompt = f"""你是马拉松训练计划教练。{PLAN_COACH_IDENTITY}
你必须先按给定训练周期理解当前阶段，再生成严谨、结构完整的训练计划输出。

══════════════════════════
【用户需求】
{state.get("query", "")}

══════════════════════════
【运动员画像】
- 目标：{profile.get('goal', '未设置')}
- 半马 PB（当前成绩）：{pb_half}
- 半马目标成绩：{target_half}
- 全马 PB：{pb_full}
- 当前周跑量：{profile.get('weekly_mileage', 0)} km
- T-Pace（乳酸阈配速）：{profile.get('t_pace', '') or '未设置'}
- 经验水平：{profile.get('experience_level', '未知')}
- 可用训练日：{profile.get('available_days', '未指定')}
- 单次最长训练：{profile.get('max_session_minutes', '未指定')} 分钟
- 场地偏好：{profile.get('terrain_preference', '未指定')}
- VO₂max：{profile.get('vo2max', '未设置')}
- 用户配速偏好：{pace_pref or '未设置'}

"""

    # 营养画像
    nutrition = (profile.get("nutrition_profile") or {})
    if isinstance(nutrition, dict) and nutrition.get("weight_kg"):
        prompt += f"""- 体重：{nutrition.get('weight_kg', 0)} kg
- 饮食偏好：{nutrition.get('diet_preference', '无偏好')}
- 过敏食物：{', '.join(nutrition.get('allergies') or []) or '无'}

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

{PLAN_GLOSSARY}

══════════════════════════
【补给与营养约束】（必须嵌入到对应训练日备注中）
- 训练时长 > 60 分钟的课表应在备注中标明：训练中每 30-40 分钟补充 30-60g 碳水（凝胶/运动饮料/香蕉）。
- 训练后 30 分钟内需补充碳水+蛋白（比例 3:1），2 小时内完成正餐。
- 补水策略：{nutrition.get('hydration_strategy', '运动中每 20 分钟饮水 150-250ml') if isinstance(nutrition, dict) else '运动中每 20 分钟饮水 150-250ml'}。
- 饮食偏好：{nutrition.get('diet_preference', '无偏好') if isinstance(nutrition, dict) else '无偏好'}。如为素食/低碳水，需在备注中给出替代补给方案。
- 高温/高湿环境下每额外流失 1L 汗液需补充 1.5L 含电解质液体。

    【知识库证据】
{evidence_lines}

{CITATION_RULES_PLAN}

══════════════════════════
【图谱上下文】
{graph_context or '暂无'}

══════════════════════════
【硬性输出约束 —— 违反任何一条即为不合格】

1. 一周 7 天全覆盖（周一至周日），一天不能少
2. 用户指定的训练日必须严格安排，不可擅自改动
3. 用户指定的训练类型必须逐一覆盖，不可遗漏

★ 每节课的时长必须遵守以下文献约束范围。不可超出 min-max，典型值作为默认参考：
{constraint_table}

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
    # P5: 注入上一轮审核反馈，让 executor 做定向修正而非盲重试
    review_feedback = state.get("review_feedback", "")
    rag_feedback = state.get("rag_audit_feedback", "")
    if review_feedback or rag_feedback:
        correction = "\n\n## 上一轮审核未通过，请修正以下问题后重新生成\n"
        if rag_feedback:
            correction += f"\n[RAG 文献审核反馈]\n{rag_feedback}\n"
        if review_feedback:
            correction += f"\n[规则审核反馈]\n{review_feedback}\n"
        correction += "\n请针对性修正上述问题，保留其余正确的部分不变。"
        prompt += correction
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
    missing = state.get("missing_fields") or []
    _logger.info("[planner] missing_fields=%s", missing)
    if missing:
        return {
            "subtasks": [],
            "token_usage": ensure_usage(state.get("token_usage")),
            "reasoning_log": ["[planner] 缺少关键画像指标，停止拆解"],
        }

    subtasks = _build_plan_subtasks(state)
    trace = _planning_role_trace(state, role_key="planner", note=f"Planner decomposed the request into {len(subtasks)} executable subtasks.")
    return {
        "subtasks": subtasks,
        "expert_evidence_trace": _merge_plan_role_trace(state, "planner", trace),
        "token_usage": ensure_usage(state.get("token_usage")),
        "reasoning_log": [f"[planner] 已拆解 {len(subtasks)} 个子任务"],
    }


def _trace_refs_from_bundle(bundle: Any, limit: int = 5) -> list[dict]:
    if not isinstance(bundle, dict):
        return []
    refs = []
    for item in bundle.get("evidence_items") or []:
        if not isinstance(item, dict):
            continue
        retrieval_mode = str(item.get("retrieval_mode") or "")
        refs.append(
            {
                "citation_label": item.get("citation_label") or "",
                "source_file": item.get("source_file") or item.get("source") or "",
                "source_path": item.get("source_path") or item.get("path") or "",
                "page": item.get("page"),
                "chunk_id": item.get("chunk_id") or "",
                "evidence_domain": item.get("evidence_domain") or item.get("domain_pack") or _domain_from_retrieval_mode(retrieval_mode),
                "retrieval_mode": retrieval_mode,
            }
        )
        if len(refs) >= limit:
            break
    return refs


def _domain_from_retrieval_mode(retrieval_mode: str) -> str:
    text = str(retrieval_mode or "")
    for prefix in ("sharded:", "bm25:", "role_shard_jsonl:"):
        if prefix not in text:
            continue
        tail = text.split(prefix, 1)[1]
        domain = re.split(r"[+:]", tail, maxsplit=1)[0].strip()
        if domain:
            return domain
    return ""


def _planning_role_trace(state: IntegratedState, *, role_key: str, note: str) -> dict:
    refs = _trace_refs_from_bundle(state.get("evidence_bundle"), limit=5)
    if not refs and isinstance(state.get("s_and_c_constraints"), dict):
        refs = [
            {
                "citation_label": ref,
                "source_file": "training_capacity_envelope",
                "evidence_domain": "strength_conditioning",
            }
            for ref in (state.get("s_and_c_constraints") or {}).get("evidence_refs", [])[:5]
        ]
    return {
        "role": role_key,
        "status": "verified" if refs else "needs_evidence",
        "evidence_refs": refs,
        "note": note if refs else f"{note} No KB evidence was visible to this role.",
    }


def _merge_plan_role_trace(state: IntegratedState, role_key: str, trace: dict) -> dict:
    existing = state.get("expert_evidence_trace") if isinstance(state.get("expert_evidence_trace"), dict) else {}
    merged = dict(existing)
    merged[role_key] = trace
    return merged


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
    _logger.info("[executor] start: subtask_count=%d", len(subtasks) if subtasks else 0)
    if not subtasks:
        return {
            "draft_plan": "",
            "structured_training_plan": None,
            "expert_evidence_trace": _merge_plan_role_trace(
                state,
                "executor",
                {
                    "role": "executor",
                    "status": "needs_evidence",
                    "evidence_refs": [],
                    "note": "Executor had no subtasks to execute.",
                },
            ),
            "reasoning_log": ["[executor] 没有可执行的子任务"],
            "token_usage": ensure_usage(state.get("token_usage")),
        }

    rag_sources = state.get("rag_sources", [])
    prompt = _build_plan_prompt(state)
    # build_structured_training_plan_skeleton 是同步函数（内部 _call_llm_sync 用 requests），
    # 在 async executor 节点里直接调会阻塞 event loop，用 to_thread 放到线程池执行。
    structured_training_plan = await asyncio.to_thread(
        build_structured_training_plan_skeleton,
        query=state.get("query", ""),
        profile=state.get("user_profile", {}),
        requested_weeks=state.get("requested_weeks"),
        training_capacity_envelope=state.get("training_capacity_envelope") or state.get("s_and_c_constraints") or None,
        framework=state.get("framework"),
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
        llm_result = await _invoke_executor_llm(prompt, config, state.get("token_usage"))
        if llm_result is None:
            raise TimeoutError("executor_llm_timeout")
        content, usage = llm_result
        fallback_reason = ""
    except (Exception, asyncio.CancelledError) as exc:
        fallback_reason = f"[executor] LLM 调用失败，已使用静态模板兜底: {_safe_llm_fallback_summary(exc)}"
        profile = state.get("user_profile", {})
        evidence_lines = format_evidence_lines(rag_sources, limit=3)
        content = _static_executor_fallback(state, profile, evidence_lines)
        usage = ensure_usage(state.get("token_usage"))

    logs = [
        f"[executor] 已生成 {structured_training_plan.get('plan_meta', {}).get('actual_weeks', 0)} 周结构化训练骨架",
    ]
    if fallback_reason:
        logs.append(fallback_reason)
    else:
        logs.append("[executor] 已通过 LLM 生成完整周训练计划")

    # 多周计划需要营养标注；单周计划则在出现长时间训练日时触发营养师节点。
    needs_nutrition = False
    if isinstance(structured_training_plan, dict):
        plan_meta = structured_training_plan.get("plan_meta") if isinstance(structured_training_plan.get("plan_meta"), dict) else {}
        actual_weeks = int(plan_meta.get("actual_weeks") or 0)
        if actual_weeks > 1:
            needs_nutrition = True
        for week in (structured_training_plan.get("week_plans") or []):
            for day in (week.get("days") or []):
                duration = int(day.get("duration_min") or 0)
                if duration >= 90:
                    needs_nutrition = True
                    break
            if needs_nutrition:
                break

    _logger.info(
        "[executor] skeleton result: type=%s has_week_plans=%s week_count=%s",
        type(structured_training_plan).__name__,
        bool(isinstance(structured_training_plan, dict) and structured_training_plan.get("week_plans")),
        len((structured_training_plan or {}).get("week_plans") or []) if isinstance(structured_training_plan, dict) else 0,
    )
    return {
        "draft_plan": content,
        "draft_ready": True,
        "structured_training_plan": structured_training_plan,
        "nutritionist_done": False,
        "psychologist_done": False,
        "expert_evidence_trace": _merge_plan_role_trace(
            state,
            "executor",
            _planning_role_trace(
                {**state, "evidence_bundle": evidence_bundle},
                role_key="executor",
                note=f"Executor generated a {structured_training_plan.get('plan_meta', {}).get('actual_weeks', 0)}-week structured training plan.",
            ),
        ),
        "validation_result": validation_result,
        "repair_suggestions": validation_result.get("repair_suggestions", []) if isinstance(validation_result, dict) else [],
        "fallback_reason": fallback_reason,
        "used_fallback": bool(fallback_reason),
        "evidence_bundle": evidence_bundle,
        "rag_sources": rag_sources,
        "token_usage": usage,
        "reasoning_log": logs + (['[executor] 多周计划或长距离训练触发营养师复核'] if needs_nutrition else []),
        "needs_nutrition_review": needs_nutrition,
    }
