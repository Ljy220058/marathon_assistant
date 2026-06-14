"""CRAG 纠正节点（crag_corrector）单测。

覆盖：三档分档、知识精炼写入/降级、incorrect 降权不删除、top-N 限制、异常兜底、NoOp web search。
"""
import asyncio

from marathon_qa_assistant.nodes import crag_corrector


def _ev(eid, score, text="正文内容", kind="vector", snippet=None, **extra):
    return {
        "evidence_id": eid,
        "kind": kind,
        "text": text,
        "snippet": snippet if snippet is not None else text[:50],
        "relevance_score": score,
        "hybrid_score": score,
        "vector_score": score,
        "retrieval_score": score,
        "citation_label": "",
        "trace": {},
        **extra,
    }


def _usage():
    return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


# ── classify_tier ────────────────────────────────────────────────────────────

def test_classify_tier_three_buckets():
    assert crag_corrector.classify_tier(_ev("a", 0.80)) == "correct"
    assert crag_corrector.classify_tier(_ev("b", 0.50)) == "correct"   # 边界 ≥0.50
    assert crag_corrector.classify_tier(_ev("c", 0.49)) == "ambiguous"
    assert crag_corrector.classify_tier(_ev("d", 0.30)) == "ambiguous"
    assert crag_corrector.classify_tier(_ev("d2", 0.28)) == "ambiguous"  # 边界 ≥0.28
    assert crag_corrector.classify_tier(_ev("e", 0.27)) == "incorrect"
    assert crag_corrector.classify_tier(_ev("f", 0.0)) == "incorrect"


def test_classify_tier_decision_gate_pinned():
    # decision_gate 的 relevance_score 被刻意置 0（build_ranked_evidence:1060），
    # 但仍判 correct 以免被降权到末位、破坏置顶优先级。
    ev = _ev("gate", 0.0, kind="decision_gate")
    assert crag_corrector.classify_tier(ev) == "correct"


def test_classify_tier_falls_back_to_hybrid_score():
    ev = _ev("a", 0.0)
    ev.pop("relevance_score")
    ev["hybrid_score"] = 0.6
    assert crag_corrector.classify_tier(ev) == "correct"


# ── refine_evidence ──────────────────────────────────────────────────────────

def test_refine_writes_refined_text_without_overwriting_original(monkeypatch):
    async def fake_invoke(prompt, config, usage):
        return ("精炼后的关键片段", {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2})

    monkeypatch.setattr(crag_corrector, "ai_invoke", fake_invoke)

    ev = _ev("x", 0.6, text="原始正文，包含一些与问题相关的信息和冗余内容。")
    original_text = ev["text"]
    ev, usage = asyncio.run(crag_corrector.refine_evidence("半马配速", ev, None, _usage()))

    assert ev["refined_text"] == "精炼后的关键片段"
    assert ev["text"] == original_text  # 原文未被覆盖（保护引用回溯）
    assert ev["refinement_meta"]["refined"] is True
    assert ev["refinement_meta"]["refine_model"] == "ai_invoke"
    assert ev["refinement_meta"]["original_relevance_score"] == 0.6
    assert usage["total_tokens"] == 2


def test_refine_fallback_on_llm_failure(monkeypatch):
    async def failing_invoke(prompt, config, usage):
        raise RuntimeError("LLM 不可用")

    monkeypatch.setattr(crag_corrector, "ai_invoke", failing_invoke)

    ev = _ev("x", 0.6, text="原始正文内容。", snippet="原始正文")
    ev, usage = asyncio.run(crag_corrector.refine_evidence("query", ev, None, _usage()))

    assert ev["refined_text"] == "原始正文"  # 降级为 snippet
    assert ev["text"] == "原始正文内容。"    # 原文未变
    assert ev["refinement_meta"]["refined"] is False
    assert "RuntimeError" in ev["refinement_meta"]["refine_skipped_reason"]


# ── crag_corrector_node ──────────────────────────────────────────────────────

def test_node_empty_evidence_passthrough():
    state = {"query": "q", "ranked_evidence": [], "token_usage": _usage()}
    result = asyncio.run(crag_corrector.crag_corrector_node(state, None))
    assert result["ranked_evidence"] == []
    assert any("跳过" in line for line in result["reasoning_log"])


def test_node_assigns_tiers_and_refines_correct(monkeypatch):
    async def fake_invoke(prompt, config, usage):
        return ("精炼", _usage())

    monkeypatch.setattr(crag_corrector, "ai_invoke", fake_invoke)

    state = {
        "query": "半马配速",
        "ranked_evidence": [
            _ev("correct1", 0.80, text="高质量正文"),
            _ev("correct2", 0.60, text="相关正文"),
            _ev("amb", 0.40, text="部分相关"),
            _ev("inc", 0.20, text="无关片段"),
        ],
        "token_usage": _usage(),
    }
    result = asyncio.run(crag_corrector.crag_corrector_node(state, None))
    evs = result["ranked_evidence"]

    tiers = {ev["evidence_id"]: ev["refinement_meta"]["tier"] for ev in evs}
    assert tiers == {"correct1": "correct", "correct2": "correct", "amb": "ambiguous", "inc": "incorrect"}

    # 仅 correct 档被精炼为 "精炼"；ambiguous/incorrect 未被精炼
    refined_ids = {ev["evidence_id"] for ev in evs if ev.get("refined_text") == "精炼"}
    assert refined_ids == {"correct1", "correct2"}


def test_node_incorrect_demoted_to_tail_not_deleted(monkeypatch):
    async def fake_invoke(prompt, config, usage):
        return ("精炼", _usage())

    monkeypatch.setattr(crag_corrector, "ai_invoke", fake_invoke)

    state = {
        "query": "query",
        "ranked_evidence": [
            _ev("inc_low", 0.10),
            _ev("correct_high", 0.90),
            _ev("inc2", 0.20),
        ],
        "token_usage": _usage(),
    }
    result = asyncio.run(crag_corrector.crag_corrector_node(state, None))
    evs = result["ranked_evidence"]

    assert len(evs) == 3  # 未删除
    ids = [ev["evidence_id"] for ev in evs]
    assert ids[0] == "correct_high"          # correct 保持在前
    assert set(ids[1:]) == {"inc_low", "inc2"}  # 两个 incorrect 沉底
    assert all(evs[i]["refinement_meta"]["tier"] == "incorrect" for i in (1, 2))


def test_node_refine_top_n_limits_llm_calls(monkeypatch):
    call_count = {"n": 0}

    async def counting_invoke(prompt, config, usage):
        call_count["n"] += 1
        return (f"精炼{call_count['n']}", _usage())

    monkeypatch.setattr(crag_corrector, "ai_invoke", counting_invoke)
    monkeypatch.setattr(crag_corrector, "CRAG_REFINE_TOP_N", 2)

    state = {
        "query": "query",
        "ranked_evidence": [_ev(f"c{i}", 0.80 - i * 0.01, text=f"正文{i}") for i in range(5)],
        "token_usage": _usage(),
    }
    asyncio.run(crag_corrector.crag_corrector_node(state, None))
    assert call_count["n"] == 2  # 只精炼 top-2


def test_node_exception_fallback(monkeypatch):
    async def fake_invoke(prompt, config, usage):
        return ("精炼", _usage())

    monkeypatch.setattr(crag_corrector, "ai_invoke", fake_invoke)
    # 让重排抛异常，触发节点级兜底
    def boom(evs):
        raise RuntimeError("rerank 挂了")
    monkeypatch.setattr(crag_corrector, "_rerank_with_tier_demotion", boom)

    state = {
        "query": "query",
        "ranked_evidence": [_ev("a", 0.80, text="正文A"), _ev("b", 0.20, text="正文B")],
        "token_usage": _usage(),
    }
    result = asyncio.run(crag_corrector.crag_corrector_node(state, None))

    # 兜底：返回入口快照，核心证据未丢失、顺序保持
    assert [ev["evidence_id"] for ev in result["ranked_evidence"]] == ["a", "b"]
    assert any("异常回退" in line for line in result["reasoning_log"])


def test_node_decision_gate_not_demoted(monkeypatch):
    async def fake_invoke(prompt, config, usage):
        return ("精炼", _usage())

    monkeypatch.setattr(crag_corrector, "ai_invoke", fake_invoke)

    gate = _ev("gate", 0.0, kind="decision_gate", text="")  # relevance=0 但应判 correct，不降权
    state = {
        "query": "query",
        "ranked_evidence": [gate, _ev("normal", 0.20, text="低相关正文")],
        "token_usage": _usage(),
    }
    result = asyncio.run(crag_corrector.crag_corrector_node(state, None))
    evs = result["ranked_evidence"]

    # gate 判 correct（不被降权），normal(0.20) 判 incorrect 沉底
    assert evs[0]["evidence_id"] == "gate"
    assert evs[0]["refinement_meta"]["tier"] == "correct"
    assert evs[-1]["evidence_id"] == "normal"


# ── WebSearchProvider ────────────────────────────────────────────────────────

def test_node_rebuilds_evidence_bundle_with_refined_text(monkeypatch):
    """精炼后重建 evidence_bundle，让 refined_text 流到下游 item.text。"""
    async def fake_invoke(prompt, config, usage):
        return ("精炼后的关键片段", _usage())

    monkeypatch.setattr(crag_corrector, "ai_invoke", fake_invoke)

    state = {
        "query": "半马配速",
        "ranked_evidence": [_ev("c1", 0.80, text="原始带噪声的正文内容", source_file="training_guide.pdf")],
        "rag_sources": [],
        "token_usage": _usage(),
    }
    result = asyncio.run(crag_corrector.crag_corrector_node(state, None))

    bundle = result["evidence_bundle"]
    items = bundle["evidence_items"]
    assert items
    # bundle item 的 text 用了精炼版（非原始带噪声正文）
    assert items[0]["text"] == "精炼后的关键片段"
    # ranked_evidence 原文仍保留（引用回溯用）
    assert result["ranked_evidence"][0]["text"] == "原始带噪声的正文内容"


def test_noop_web_search_returns_empty():
    provider = crag_corrector.NoOpWebSearch()
    assert asyncio.run(provider.search("query")) == []
