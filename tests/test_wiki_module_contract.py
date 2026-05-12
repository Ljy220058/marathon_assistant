import asyncio
import sys
from pathlib import Path


root = Path(__file__).parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from marathon_qa_assistant.nodes.expert_nodes import _format_wiki_context, _run_expert_llm
from marathon_qa_assistant.nodes.output_nodes import _build_structured_report
from marathon_qa_assistant.nodes.profile_and_retrieval import _should_use_wiki_context, wiki_search_node
from marathon_qa_assistant.ui.legacy_ui import UIHelper


def test_should_use_wiki_context_only_for_concept_or_research_queries():
    assert _should_use_wiki_context("什么是乳酸阈？", "qa", "team", ["乳酸阈"])
    assert _should_use_wiki_context("分析乳酸阈机制", "qa", "research", ["乳酸阈"])
    assert not _should_use_wiki_context("帮我制定下周训练计划", "plan", "team", ["训练计划"])
    assert not _should_use_wiki_context("帮我看看今天怎么练", "qa", "team", ["训练"])
    assert not _should_use_wiki_context("什么是乳酸阈？", "qa", "team", [])


def test_wiki_search_node_uses_wiki_agent_for_concept_queries(monkeypatch):
    from marathon_qa_assistant.nodes import profile_and_retrieval as profile_module

    calls = []

    class _FakeWikiAgent:
        async def search(self, entities, lang="zh"):
            calls.append({"entities": entities, "lang": lang})
            return "【维基百科 - 乳酸阈】\n乳酸阈是耐力训练中的重要概念。"

    monkeypatch.setattr(profile_module, "wiki_agent", _FakeWikiAgent())

    result = asyncio.run(
        wiki_search_node(
            {
                "query": "什么是乳酸阈？",
                "intent_type": "qa",
                "mode": "team",
                "selected_entities": ["乳酸阈"],
            },
            {},
        )
    )

    assert calls == [{"entities": ["乳酸阈"], "lang": "zh"}]
    assert "乳酸阈" in result["wiki_context"]
    assert "已补充" in result["reasoning_log"][0]


def test_wiki_search_node_skips_plan_queries(monkeypatch):
    from marathon_qa_assistant.nodes import profile_and_retrieval as profile_module

    class _FailingWikiAgent:
        async def search(self, entities, lang="zh"):
            raise AssertionError("计划类问题不应调用 Wiki")

    monkeypatch.setattr(profile_module, "wiki_agent", _FailingWikiAgent())

    result = asyncio.run(
        wiki_search_node(
            {
                "query": "帮我制定下周半马训练计划",
                "intent_type": "plan",
                "mode": "team",
                "selected_entities": ["半马"],
            },
            {},
        )
    )

    assert result["wiki_context"] == ""
    assert "不需要外部概念补充" in result["reasoning_log"][0]


def test_expert_prompt_includes_wiki_context_without_treating_it_as_numbered_evidence(monkeypatch):
    from marathon_qa_assistant.nodes import expert_nodes

    captured = {}

    async def _fake_ai_invoke(prompt, config, current_usage):
        captured["prompt"] = prompt
        return "ok", {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}

    monkeypatch.setattr(expert_nodes, "ai_invoke", _fake_ai_invoke)

    content, usage = asyncio.run(
        _run_expert_llm(
            "Coach",
            "给出概念解释。",
            {
                "query": "什么是乳酸阈？",
                "wiki_context": "【维基百科 - Lactate threshold】\n乳酸阈是运动生理概念。",
                "rag_sources": [],
                "user_profile": {},
                "graph_context": "",
                "token_usage": {},
            },
            {},
            "教练建议",
        )
    )

    assert content == "ok"
    assert usage["total_tokens"] == 2
    assert "Wiki 概念补充上下文" in captured["prompt"]
    assert "乳酸阈是运动生理概念" in captured["prompt"]
    assert "不要给 Wiki 内容编造 [n] 引用" in captured["prompt"]


def test_structured_report_keeps_wiki_context_for_audit():
    report = _build_structured_report(
        {
            "query": "什么是 VO2max？",
            "category": "coach",
            "entities": ["VO2max"],
            "graph_context": "",
            "wiki_context": "【维基百科 - VO2 max】\n最大摄氧量用于描述有氧能力。",
            "audit_scores": {"consistency": 90, "safety": 95, "roi": 70},
            "rag_sources": [],
        },
        "VO2max 是衡量有氧能力的指标。",
    )

    assert report["analysis_framework"]["wiki_context"].startswith("【维基百科")
    assert any(item["key"] == "Wiki补充" for item in report["findings"])


def test_wiki_panel_renders_only_when_context_exists():
    report = _build_structured_report(
        {
            "query": "什么是 VO2max？",
            "category": "coach",
            "entities": ["VO2max"],
            "graph_context": "",
            "wiki_context": "【维基百科 - VO2 max】\n最大摄氧量用于描述有氧能力。",
            "audit_scores": {"consistency": 90, "safety": 95, "roi": 70},
            "rag_sources": [],
        },
        "VO2max 是衡量有氧能力的指标。",
    )

    wiki_md = UIHelper.render_wiki_context_md(report)

    assert "Wiki补充" in wiki_md
    assert "概念背景解释" in wiki_md
    assert "最大摄氧量用于描述有氧能力" in wiki_md
    assert UIHelper.render_wiki_context_md({"analysis_framework": {"wiki_context": ""}}) == ""


def test_format_wiki_context_has_empty_fallback():
    assert _format_wiki_context("") == "暂无外部概念补充"
    assert _format_wiki_context("  Wiki内容  ") == "Wiki内容"
