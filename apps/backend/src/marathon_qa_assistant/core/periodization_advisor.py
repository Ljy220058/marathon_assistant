"""周期化阶段模型选择顾问：RAG 检索 + LLM 决策。

阶段模型的周数分配公式是固定的，但「选哪个模型、要不要导入期、
按跑者画像怎么调整阶段侧重」由 RAG 证据 + LLM 做出。

LLM 不可用时，自动降级到确定性规则。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from marathon_qa_assistant.core.settings import get_settings

logger = logging.getLogger("periodization_advisor")

# B1: 精英来源过滤关键词 — 业余跑者 (新手/初级/中级) 检索时自动排除匹配项
# 新增偏精英来源只需追加 tuple, 不改变过滤逻辑
ELITE_SOURCE_FILTER_KEYWORDS: Tuple[str, ...] = (
    "Norway", "The Norway", "elite", "professional",
    "Olympic", "national team", "世界纪录",
)

# ── 结构化输出 ────────────────────────────────────────────────────────────


@dataclass
class PeriodizationAdvisory:
    """LLM 输出的阶段模型选择建议。"""

    model_tier: str = ""
    # 半马: "compact" | "medium" | "standard" | "long"
    # 全马: "short" | "medium" | "long"

    needs_introductory: bool = False
    intro_weeks: int = 0
    # 各阶段周数偏移 (e.g. {"base": 2, "specific": -1})
    phase_adjustments: Dict[str, int] = field(default_factory=dict)
    reasoning: str = ""
    evidence_sources: List[str] = field(default_factory=list)
    # 标记是否来自 LLM (False = 降级到确定性规则)
    llm_generated: bool = False


# ── 精英来源过滤 ──────────────────────────────────────────────────────────

def _is_elite_source(chunk: Dict[str, Any]) -> bool:
    """检查检索结果是否来自精英运动员来源（业余跑者应过滤）。

    B1: 将硬编码字符串匹配提取为可配置检查。
    新增精英来源关键词只需追加 ELITE_SOURCE_FILTER_KEYWORDS。
    """
    source_file = str(chunk.get("source_file", ""))
    text_prefix = str(chunk.get("text", ""))[:200]
    combined = f"{source_file} {text_prefix}"
    return any(kw in combined for kw in ELITE_SOURCE_FILTER_KEYWORDS)


# ── RAG 检索 ──────────────────────────────────────────────────────────────


def _build_periodization_rag_query(profile: Dict[str, Any], total_weeks: int) -> str:
    """从跑者画像构建周期化检索查询。"""
    parts: List[str] = []

    race_type = profile.get("goal", "")
    experience = profile.get("experience_level", "")
    mileage = profile.get("weekly_mileage", 40)
    recent_marathon = profile.get("recent_marathon", False)
    background = profile.get("training_background", "")

    parts.append(f"跑者准备{total_weeks}周训练")
    if race_type:
        parts.append(f"目标：{race_type}")
    if experience:
        parts.append(f"水平：{experience}")
    parts.append(f"周跑量约{mileage}km")
    if recent_marathon:
        parts.append("近期完成过全马比赛，可能需要恢复导入期")
    if background:
        parts.append(f"训练背景：{background}")

    query = "马拉松训练周期化阶段划分依据 " + " ".join(parts)
    return query


def _retrieve_periodization_evidence(profile: Dict[str, Any], total_weeks: int) -> List[Dict[str, Any]]:
    """从训练协议 KB 检索周期化阶段选择相关证据。

    优先检索 HMP 协议和训练学文献中与阶段划分、导入期、减量期相关的内容。
    FAISS 不可用时从 JSONL 后备检索。
    """
    chunks: List[Dict[str, Any]] = []
    query = _build_periodization_rag_query(profile, total_weeks)

    # 尝试 FAISS 向量检索
    try:
        from marathon_qa_assistant.services.vector_store import retrieve  # noqa: E402
        hits = retrieve(query, top_k=6)
        if hits:
            # B1: 业余跑者过滤精英来源 (FAISS 路径)
            experience = str(profile.get("experience_level") or "").strip()
            if experience in ("新手", "初级", "中级", "beginner", "intermediate"):
                hits = [h for h in hits if not _is_elite_source(h)]
            chunks.extend(hits)
    except Exception as exc:
        logger.debug("periodization RAG: FAISS 检索失败 (%s)，使用 JSONL 后备", exc)

    # JSONL 后备：从 training_protocol chunks 中按关键词匹配
    if not chunks:
        try:
            from marathon_qa_assistant.core.app_state import DATA_DIR  # noqa: E402
            jsonl_path = DATA_DIR / "vector_kb" / "v2_sharded" / "training_protocol" / "chunks.jsonl"
            if jsonl_path.exists():
                keywords = ["阶段", "周期", "导入", "基础期", "比赛专项", "减量", "taper",
                            "periodization", "phase", "peaking", "introductory", "build phase",
                            "Seiler", "Stoggl", "Gabbett", "80/20", "极化训练", "ACWR",
                            "强度分布", "训练负荷", "10%", "递增"]
                with open(jsonl_path, encoding="utf-8") as f:
                    for line in f:
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        text = str(obj.get("text") or "")
                        if any(kw in text.lower() for kw in keywords):
                            chunks.append({
                                "text": text[:800],
                                "source_file": str(obj.get("source_file") or ""),
                                "chunk_id": str(obj.get("chunk_id") or ""),
                                "score": 0.5,
                            })
                        if len(chunks) >= 8:
                            break
                logger.debug("periodization RAG: JSONL 后备检索到 %d 个 chunks", len(chunks))
        except Exception as exc:
            logger.warning("periodization RAG: JSONL 后备检索失败: %s", exc)

    # B1: 业余跑者过滤精英来源 (JSONL 后备路径)
    experience = str(profile.get("experience_level") or "").strip()
    if experience in ("新手", "初级", "中级", "beginner", "intermediate"):
        chunks = [c for c in chunks if not _is_elite_source(c)]

    # 总是追加 HMP 协议阶段规则作为基础证据
    hmp_chunk = _extract_hmp_phase_rules()
    if hmp_chunk:
        chunks.insert(0, hmp_chunk)

    return chunks[:8]


def _extract_hmp_phase_rules() -> Optional[Dict[str, Any]]:
    """提取 HMP 协议中的阶段选择规则作为 RAG 证据。"""
    try:
        from marathon_qa_assistant.core.half_marathon_protocol import (  # noqa: E402
            HM_PHASE_RULES, select_phase_sequence,
        )
        rules_text = "半马 HMP 协议阶段规则：\n"
        for phase_id, rule in HM_PHASE_RULES.items():
            rules_text += (
                f"- {rule.label} ({phase_id})：{rule.objective}\n"
                f"  典型训练：{', '.join(rule.typical_workouts)}\n"
            )
        # 添加阶段序列选择逻辑
        rules_text += "\n阶段序列选择规则：\n"
        rules_text += "- 刚比完全马（recent_marathon=True）：无论如何都从导入期开始\n"
        rules_text += "- 短周期 <=4周：只有比赛专项阶段\n"
        rules_text += "- 5-8周：专项构建+比赛专项（无独立基础阶段）\n"
        rules_text += "- 9-14周：基础阶段+专项构建+比赛专项\n"
        rules_text += "- 15-20周：基础阶段+专项构建+比赛专项+赛前减量\n"
        rules_text += "- 21-26周：基础阶段-1/-2+专项构建+比赛专项+赛前减量\n"
        return {
            "text": rules_text,
            "source_file": "half_marathon_hmp_protocol.md",
            "chunk_id": "hmp_phase_rules",
            "score": 1.0,
        }
    except Exception:
        return None


# ── LLM 调用 ──────────────────────────────────────────────────────────────


def _build_advisor_prompt(
    profile: Dict[str, Any],
    total_weeks: int,
    race_type: str,
    evidence_text: str,
    total_sessions: int = 5,
    phase_family: str = "general",
) -> str:
    """构建 LLM 周期化顾问提示词。"""
    # 计算当前强度课约束范围
    try:
        from marathon_qa_assistant.core.half_marathon_capacity_budget import (
            _compute_intensity_bounds,
        )
        intensity_lower, intensity_upper = _compute_intensity_bounds(
            total_sessions, phase_family, profile,
        )
    except Exception:
        intensity_lower, intensity_upper = 1, 2

    parts = [
        "你是一位运动训练学专家，负责为马拉松跑者选择最优的周期化阶段模型。",
        "",
        "## 跑者信息",
        f"- 目标赛事类型：{race_type}",
        f"- 训练目标：{profile.get('goal', '未设置')}",
        f"- 经验水平：{profile.get('experience_level', '未知')}",
        f"- 当前周跑量(km)：{profile.get('weekly_mileage', 40)}",
        f"- 可用训练周数：{total_weeks} 周",
        f"- 近期是否完赛全马：{'是' if profile.get('recent_marathon') else '否'}",
        f"- 训练背景：{profile.get('training_background', '未知')}",
        f"- 最大单次训练时长(分钟)：{profile.get('max_session_minutes', 90)}",
        "",
        "## 参考证据（来自训练学文献和协议）",
        evidence_text[:3000],
        "",
        "## 强度课数量约束（不可超出）",
        f"- 每周训练总课次: {total_sessions} 次",
        f"- 允许强度课范围: {intensity_lower}-{intensity_upper} 节/周",
        f"- 当前阶段: {phase_family}",
        "",
        "## 决策任务",
        "请基于跑者信息和参考证据，输出 JSON 格式的阶段模型选择决策。",
        "注意：周数分配公式是正确的，你不需要改变各阶段的绝对周数。",
        "你需要决策的是：",
        "1. 选哪个模型层级",
        f"   - 注意：当前总周数 {total_weeks} 周，可选 model_tier 范围见证据中的约束表，超出范围会被自动驳回",
        "2. 是否需要导入期（introductory phase）—— 仅在刚比完全马或有明显训练中断时启用",
        "3. 是否需要按跑者画像微调阶段权重（如速度弱则专项构建+1周、比赛专项-1周），不做大幅调整",
        "",
        "## 输出格式（严格 JSON，不要有其他文字）",
        "{",
        '  "model_tier": "standard",',
        '  "needs_introductory": false,',
        '  "intro_weeks": 2,',
        '  "phase_adjustments": {"base": 0, "support": 1, "specific": -1},',
        '  "reasoning": "基于跑者全马背景和中等周跑量...",',
        '  "evidence_sources": ["half_marathon_hmp_protocol.md"]',
        "}",
        "",
        "JSON:",
    ]
    return "\n".join(parts)


def _parse_advisor_response(raw: str) -> Optional[PeriodizationAdvisory]:
    """从 LLM 响应中解析 PeriodizationAdvisory。"""
    if not raw:
        return None
    # 尝试提取 JSON 块
    text = raw.strip()
    # 去掉可能的 markdown 代码块包裹
    if "```" in text:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start:end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("periodization advisor: LLM 响应不是有效 JSON")
        return None

    return PeriodizationAdvisory(
        model_tier=str(data.get("model_tier") or ""),
        needs_introductory=bool(data.get("needs_introductory", False)),
        intro_weeks=max(0, int(data.get("intro_weeks") or 0)),
        phase_adjustments={
            str(k): int(v)
            for k, v in (data.get("phase_adjustments") or {}).items()
        },
        reasoning=str(data.get("reasoning") or ""),
        evidence_sources=[
            str(s) for s in (data.get("evidence_sources") or [])
        ],
        llm_generated=True,
    )


# ── 同步 LLM 调用 ─────────────────────────────────────────────────────────


def _call_llm_sync(prompt: str, timeout_sec: float = 60.0) -> Optional[str]:
    """同步调用 DeepSeek API（骨架生成器是 sync 的，不能用 ai_invoke）。

    调用失败时静默返回 None，由上层降级到确定性规则。
    """
    import os
    try:
        import requests  # noqa: E402
    except ImportError:
        logger.warning("periodization advisor: requests 库不可用")
        return None

    settings = get_settings()
    api_key = settings.deepseek_api_key
    if not api_key:
        logger.info("periodization advisor: DEEPSEEK_API_KEY 未设置——使用确定性规则生成训练计划")
        return None

    base_url = settings.deepseek_base_url.rstrip("/")
    # 对齐全局配置（默认 v4-pro），避免此处另用 deepseek-chat 造成同一链路模型质量不一致
    model = settings.deepseek_model

    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 800,
                # 强制 JSON 输出，避免 LLM 返回非 JSON 导致 archetype/periodization 解析失败降级
                "response_format": {"type": "json_object"},
            },
            timeout=timeout_sec,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices", [])
        if choices:
            content = str(choices[0].get("message", {}).get("content", "") or "")
            logger.debug("periodization advisor: LLM 返回 %d chars", len(content))
            return content
    except Exception as exc:
        logger.warning("periodization advisor: LLM 调用失败 (%s)，降级到确定性规则", exc)

    return None


# ── 主入口 ────────────────────────────────────────────────────────────────


def get_periodization_advisory(
    profile: Dict[str, Any],
    total_weeks: int,
    race_type: str = "general",
    enable_llm: bool = True,
    total_sessions: int = 5,
    phase_family: str = "general",
) -> PeriodizationAdvisory:
    """获取周期化阶段模型选择建议。

    LLM 可用时：RAG 检索 → LLM 决策 → 结构化建议。
    LLM 不可用时：降级到确定性规则（返回空 advisory，由 periodization.py 走原有分支）。

    Args:
        profile: 跑者画像
        total_weeks: 训练总周数
        race_type: 赛事类型（half_marathon / marathon / general）
        enable_llm: 是否启用 LLM（测试环境可关）

    Returns:
        PeriodizationAdvisory（llm_generated 标记来源）
    """
    if not enable_llm:
        return PeriodizationAdvisory()

    # Step 1: RAG 检索
    evidence = _retrieve_periodization_evidence(profile, total_weeks)
    evidence_text = "\n\n---\n\n".join(
        f"[{e.get('source_file', '?')}] {e.get('text', '')[:600]}"
        for e in evidence[:6]
    )
    if len(evidence_text) < 100:
        logger.debug("periodization advisor: RAG 证据不足，降级到确定性规则")
        return PeriodizationAdvisory()

    # Step 2: LLM 决策
    prompt = _build_advisor_prompt(profile, total_weeks, race_type, evidence_text,
                                   total_sessions=total_sessions, phase_family=phase_family)
    raw = _call_llm_sync(prompt)
    if not raw:
        return PeriodizationAdvisory()

    # Step 3: 解析
    advisory = _parse_advisor_response(raw)
    if advisory is None:
        return PeriodizationAdvisory()

    logger.info(
        "periodization advisor: LLM 建议 model_tier=%s intro=%s adjustments=%s",
        advisory.model_tier, advisory.needs_introductory, advisory.phase_adjustments,
    )
    return advisory
