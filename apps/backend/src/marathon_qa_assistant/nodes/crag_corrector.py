"""CRAG（Corrective RAG）纠正节点。

接入位置：evidence_retriever → crag_corrector → conditioning_constraints。
对 ranked_evidence 做：
  1. 文档级三档分档（correct / ambiguous / incorrect）——复用 build_ranked_evidence
     已写入的 relevance_score，零额外计算。
  2. correct 档 top-N 知识精炼——复用 nodes.common.ai_invoke，写 refined_text
     （绝不覆盖原 text/snippet/citation_label，保护 security.py:483 引用回溯）。
  3. incorrect 降权置末位——不删除，保留引用完整性。
  4. 低置信占比高时触发 web search——本期 WebSearchProvider 为 NoOp，仅留接入点。

全程 try/except 兜底：任何异常回退原 ranked_evidence，绝不阻断检索链路。
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from marathon_qa_assistant.core.evidence_bundle import build_evidence_bundle
from marathon_qa_assistant.core.state_models import Evidence, IntegratedState
from marathon_qa_assistant.nodes.common import ai_invoke, ensure_usage

try:
    from langchain_core.runnables import RunnableConfig
except ImportError:  # pragma: no cover
    RunnableConfig = Any  # type: ignore[assignment]

logger = logging.getLogger("crag_corrector")

# ── 三档阈值（基于 relevance_score；build_ranked_evidence 已写入该字段）──
CRAG_TIER_THRESHOLDS: Dict[str, float] = {
    "correct": 0.50,   # ≈ confidence_level high+medium
    "ambiguous": 0.28,  # low 的上半；<0.28 为 incorrect（放宽，避免内容相关证据卡边界归零）
}

# 精炼 top-N：只对 correct 档最高分若干条调 LLM，控制成本/延迟
CRAG_REFINE_TOP_N = int(os.environ.get("CRAG_REFINE_TOP_N", "3") or "3")

# 触发 web search 的低置信占比门槛（ambiguous+incorrect 占比超过此值才调）
CRAG_LOW_CONFIDENCE_RATIO = 0.50


def classify_tier(evidence: Dict[str, Any]) -> str:
    """根据 relevance_score 判定 CRAG 三档：correct / ambiguous / incorrect。

    decision_gate 类证据维持 build_ranked_evidence 的置顶优先级（其 relevance_score
    被刻意置 0 但排序 priority=1），这里统一判 correct 以免被降权到末位。
    """
    if evidence.get("kind") == "decision_gate":
        return "correct"
    score = float(evidence.get("relevance_score", evidence.get("hybrid_score", 0.0)) or 0.0)
    if score >= CRAG_TIER_THRESHOLDS["correct"]:
        return "correct"
    if score >= CRAG_TIER_THRESHOLDS["ambiguous"]:
        return "ambiguous"
    return "incorrect"


def _is_refinable(evidence: Dict[str, Any], tier: str) -> bool:
    """仅 correct 档、且有正文、且非 decision_gate/conflict 的证据才参与精炼。"""
    if tier != "correct":
        return False
    if evidence.get("kind") == "decision_gate":
        return False
    if evidence.get("conflict_detected"):
        return False
    return bool(str(evidence.get("text") or "").strip())


async def refine_evidence(
    query: str,
    evidence: Dict[str, Any],
    config: Optional[RunnableConfig],
    usage: Dict[str, int],
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """对单条 correct 证据调 LLM 精炼，写 refined_text（不覆盖原 text）。

    失败降级：refined_text = 原 snippet，refinement_meta.refine_skipped_reason 记异常。
    """
    original_text = str(evidence.get("text") or "")
    snippet = str(evidence.get("snippet") or original_text[:300])
    refined_text = snippet
    refine_skipped: Optional[str] = None
    refine_model = ""

    try:
        prompt = (
            "你是马拉松训练知识库的证据精炼器。从下面检索片段中抽取与用户问题最相关、最关键的信息，"
            "去除冗余与无关句子。\n要求：\n"
            "1. 输出不超过 300 字的精炼片段，保留事实、数值、动作要点。\n"
            "2. 不要编造、不要补充原文没有的内容。\n"
            "3. 若片段与问题无关，输出空字符串。\n\n"
            f"用户问题：{query[:500]}\n\n"
            f'检索片段：\n"""\n{original_text[:1500]}\n"""\n\n'
            "精炼片段："
        )
        content, new_usage = await ai_invoke(prompt, config, usage)
        refined_text = (content or "").strip() or snippet
        refine_model = "ai_invoke"
        usage = new_usage
    except Exception as exc:  # 精炼失败不阻断
        refine_skipped = f"{type(exc).__name__}: {exc}"
        logger.warning("[crag_corrector] refine_evidence 降级: %s", refine_skipped)

    meta = dict(evidence.get("refinement_meta") or {})
    meta.update({
        "refined": refine_skipped is None,
        "original_relevance_score": float(evidence.get("relevance_score", 0.0) or 0.0),
        "refine_model": refine_model,
        "refine_skipped_reason": refine_skipped or "",
    })
    evidence["refined_text"] = refined_text
    evidence["refinement_meta"] = meta
    return evidence, usage


class WebSearchProvider:
    """web search 抽象接口。本期默认 NoOp；后续接入 Tavily / 火山引擎 DeepSeek 联网版时实现。"""

    async def search(self, query: str) -> List[Dict[str, Any]]:  # pragma: no cover
        raise NotImplementedError


class NoOpWebSearch(WebSearchProvider):
    """默认实现：返回空 + 记日志。留接入点，无副作用。"""

    async def search(self, query: str) -> List[Dict[str, Any]]:
        logger.debug("[crag_corrector] WebSearchProvider 未配置（NoOp），跳过 web search: %s", query[:60])
        return []


# 模块级默认 provider（后续可被配置注入替换）
_default_web_search = NoOpWebSearch()


def _low_confidence_ratio(evidence_list: List[Dict[str, Any]]) -> float:
    if not evidence_list:
        return 0.0
    low = sum(1 for ev in evidence_list if classify_tier(ev) in {"ambiguous", "incorrect"})
    return low / len(evidence_list)


def _rerank_with_tier_demotion(evidence_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """incorrect 降权置末位；correct/ambiguous（含 decision_gate）保持原相对顺序（稳定）。"""
    kept: List[Dict[str, Any]] = []
    demoted: List[Dict[str, Any]] = []
    for ev in evidence_list:
        tier = ev.get("refinement_meta", {}).get("tier", "correct")
        if tier == "incorrect":
            demoted.append(ev)
        else:
            kept.append(ev)
    return kept + demoted


async def crag_corrector_node(state: IntegratedState, config: RunnableConfig) -> Dict[str, Any]:
    """CRAG 纠正节点：分档 → correct 精炼 → incorrect 降权 → （可选）web search。"""
    query = str(state.get("query", "") or "")
    raw_evidence: List[Evidence] = list(state.get("ranked_evidence") or [])
    usage = ensure_usage(state.get("token_usage"))

    # 空证据或无 query：直接透传，不做纠正
    if not raw_evidence or not query.strip():
        return {
            "ranked_evidence": raw_evidence,
            "token_usage": usage,
            "reasoning_log": ["[crag_corrector] 无证据或无 query，跳过纠正"],
        }

    # 入口快照：异常时返回未经 CRAG 处理的副本，保证兜底"原证据不变"
    original_snapshot = [dict(ev) for ev in raw_evidence]

    try:
        # 1. 全量打 tier 标签（写 refinement_meta.tier，不改变 evidence 正文内容）
        for ev in raw_evidence:
            tier = classify_tier(ev)
            meta = dict(ev.get("refinement_meta") or {})
            meta["tier"] = tier
            ev["refinement_meta"] = meta

        # 2. correct 档 top-N 精炼（按 relevance_score 降序取前 N 条 refinable）
        refinable = [
            ev for ev in raw_evidence
            if _is_refinable(ev, str(ev.get("refinement_meta", {}).get("tier", "")))
        ]
        refinable.sort(key=lambda x: float(x.get("relevance_score", 0.0) or 0.0), reverse=True)
        refined_count = 0
        for ev in refinable[:CRAG_REFINE_TOP_N]:
            _, usage = await refine_evidence(query, ev, config, usage)
            refined_count += 1

        # 3. incorrect 降权：置末位（不删除，保护引用回溯）
        corrected = _rerank_with_tier_demotion(raw_evidence)

        # 4. 低置信占比高时触发 web search（NoOp 下无副作用）
        web_triggered = _low_confidence_ratio(corrected) > CRAG_LOW_CONFIDENCE_RATIO
        web_used = False
        if web_triggered:
            web_results = await _default_web_search.search(query)
            web_used = bool(web_results)

        tier_counts = {
            t: sum(1 for ev in corrected if ev.get("refinement_meta", {}).get("tier") == t)
            for t in ("correct", "ambiguous", "incorrect")
        }
        # 重建 evidence_bundle：_item_from_ranked_evidence 优先读 refined_text，
        # 让精炼后的片段流到下游 LLM 上下文（原 text 仍在 ranked_evidence 供引用回溯）。
        evidence_bundle = build_evidence_bundle(
            query=query,
            rag_sources=state.get("rag_sources") or [],
            ranked_evidence=corrected,
            structured_training_plan=state.get("structured_training_plan"),
            health=(state.get("evidence_bundle") or {}).get("health")
            if isinstance(state.get("evidence_bundle"), dict)
            else None,
        )
        return {
            "ranked_evidence": corrected,
            "evidence_bundle": evidence_bundle,
            "token_usage": usage,
            "reasoning_log": [
                f"[crag_corrector] 分档 correct={tier_counts['correct']} "
                f"ambiguous={tier_counts['ambiguous']} incorrect={tier_counts['incorrect']}",
                f"[crag_corrector] 精炼 {refined_count} 条 correct 证据（top-{CRAG_REFINE_TOP_N}）",
                f"[crag_corrector] web_search={'触发(NoOp)' if web_triggered else '未触发'}"
                + (" 有结果" if web_used else ""),
            ],
        }
    except Exception as exc:
        # 兜底：任何异常回退入口快照（未经 CRAG 处理的副本），绝不阻断检索链路
        logger.exception("[crag_corrector] 纠正失败，回退原证据: %s", exc)
        return {
            "ranked_evidence": original_snapshot,
            "token_usage": usage,
            "reasoning_log": [f"[crag_corrector] 纠正异常回退: {type(exc).__name__}: {exc}"],
        }


__all__ = [
    "CRAG_TIER_THRESHOLDS",
    "CRAG_REFINE_TOP_N",
    "classify_tier",
    "refine_evidence",
    "crag_corrector_node",
    "WebSearchProvider",
    "NoOpWebSearch",
]
