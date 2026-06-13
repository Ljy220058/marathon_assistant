import asyncio
import sys
from pathlib import Path


root = Path(__file__).parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from marathon_qa_assistant.nodes.expert_nodes import _format_wiki_context, _run_expert_llm
from marathon_qa_assistant.nodes.output_nodes import _build_structured_report
from marathon_qa_assistant.nodes.profile_and_retrieval import (
    context_fanout_node,
    evidence_retriever_node,
    missing_info_handler_node,
)
from marathon_qa_assistant.ui.legacy_ui import UIHelper


def test_evidence_retriever_node_is_kb_rag_first_external_fallback_disabled():
    """evidence_retriever 是真实链路节点；当前只使用本地 KB/RAG，不直接启用外部 Wiki。"""
    result = asyncio.run(
        evidence_retriever_node(
            {
                "query": "什么是乳酸阈？",
                "intent_type": "qa",
                "mode": "team",
                "selected_entities": ["乳酸阈"],
            },
            {},
        )
    )

    assert result["wiki_context"] == ""
    assert "KB/RAG 优先" in result["reasoning_log"][0]
    assert "未启用外部知识" in result["reasoning_log"][0]


def test_entity_extraction_and_evidence_retriever_have_separate_responsibilities(monkeypatch):
    from marathon_qa_assistant.nodes import profile_and_retrieval as profile_module

    async def fake_get_context(*_args, **_kwargs):
        return [{"chunk_id": "p1", "text": "周训练计划包含轻松跑和长距离", "score": 0.9, "evidence_domain": "protocol"}]

    monkeypatch.setattr(profile_module, "infer_entities", lambda *_args, **_kwargs: ["训练计划"])
    monkeypatch.setattr(profile_module, "semantic_match_entities", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(profile_module, "expand_entities_for_kg", lambda entities: entities)
    monkeypatch.setattr(profile_module, "graph_fusion_runtime_enabled", lambda: False)
    monkeypatch.setattr(profile_module, "get_context", fake_get_context)
    monkeypatch.setattr(profile_module, "build_rag_sources", lambda hits: hits)
    monkeypatch.setattr(profile_module, "build_ranked_evidence", lambda **kwargs: kwargs["vector_hits"])
    monkeypatch.setattr(profile_module, "build_evidence_bundle", lambda **_kwargs: {"evidence_items": [{"id": "p1"}], "health": {}})

    extraction = asyncio.run(
        profile_module.entity_extraction_node(
            {"query": "给我训练计划", "selected_entities": [], "intent_type": "plan", "category": "coach", "token_usage": {}},
            {},
        )
    )
    retrieval = asyncio.run(
        evidence_retriever_node(
            {**extraction, "query": "给我训练计划", "intent_type": "plan", "category": "coach", "token_usage": {}},
            {},
        )
    )

    assert extraction["entities"] == ["训练计划"]
    assert "gate_hits" not in extraction
    assert retrieval["gate_hits"]
    assert retrieval["evidence_bundle"]["evidence_items"]


def test_context_fanout_runs_profiler_and_entity_extraction_in_parallel(monkeypatch):
    from marathon_qa_assistant.nodes import profile_and_retrieval as profile_module

    started = set()
    release = asyncio.Event()

    async def fake_profiler(*_args, **_kwargs):
        started.add("profiler")
        if "entity" in started:
            release.set()
        await asyncio.wait_for(release.wait(), timeout=1)
        return {
            "user_profile": {"weekly_mileage": 50},
            "reasoning_log": ["[profiler] done"],
            "execution_trace": [{"node": "profiler"}],
            "token_usage": {"prompt_tokens": 1, "completion_tokens": 0, "total_tokens": 1},
        }

    async def fake_entity_extraction(*_args, **_kwargs):
        started.add("entity")
        if "profiler" in started:
            release.set()
        await asyncio.wait_for(release.wait(), timeout=1)
        return {
            "entities": ["marathon"],
            "selected_entities": ["marathon"],
            "reasoning_log": ["[entity_extraction] done"],
            "execution_trace": [{"node": "entity_extraction"}],
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }

    monkeypatch.setattr(profile_module, "profiler_node", fake_profiler)
    monkeypatch.setattr(profile_module, "entity_extraction_node", fake_entity_extraction)

    output = asyncio.run(
        context_fanout_node(
            {"query": "build marathon plan", "intent_type": "plan", "token_usage": {}},
            {},
        )
    )

    assert started == {"profiler", "entity"}
    assert output["context_fanout_done"] is True
    assert output["user_profile"]["weekly_mileage"] == 50
    assert output["selected_entities"] == ["marathon"]
    assert [step["node"] for step in output["execution_trace"]] == ["profiler", "entity_extraction", "context_fanout"]
    assert any("[context_fanout]" in line for line in output["reasoning_log"])


def test_missing_info_handler_exposes_resume_contract_for_plan_profile_gaps():
    result = asyncio.run(
        missing_info_handler_node(
            {
                "query": "帮我生成全马计划",
                "intent_type": "plan",
                "missing_fields": ["weekly_mileage", "available_days"],
                "token_usage": {},
            },
            {},
        )
    )

    assert result["missing_info_status"] == "awaiting_profile"
    assert result["workflow_pause"]["status"] == "awaiting_user_input"
    assert result["workflow_pause"]["resume_target"] == "router"
    assert result["workflow_pause"]["pending_query"] == "帮我生成全马计划"
    assert result["final_report"] == "__FILL_FIELDS__"


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
    assert "没有本地知识库证据时，可以基于模型通用知识给出一般说明" in captured["prompt"]
    assert "模型通用知识不得标成 [n] 证据" in captured["prompt"]


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
