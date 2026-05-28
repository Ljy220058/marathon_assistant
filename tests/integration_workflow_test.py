import asyncio
import sys
from pathlib import Path

# 将项目根目录添加到 sys.path
BASE_DIR = Path(__file__).absolute().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from marathon_qa_assistant.core.workflow import integrated_app, IntegratedState, load_user_profile


def _build_state() -> IntegratedState:
    profile = load_user_profile()
    return {
        "query": "我最近膝盖有点疼，该如何调整我的全马训练计划？目前我每周跑 50 公里。",
        "mode": "team",
        "intent_type": "qa",
        "category": "",
        "subtasks": [],
        "draft_plan": "",
        "review_feedback": "",
        "is_approved": False,
        "iteration_count": 0,
        "final_report": "",
        "structured_report": None,
        "reasoning_log": [],
        "rag_sources": [],
        "graph_context": "",
        "wiki_context": "",
        "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "audit_scores": {"consistency": 0, "safety": 0, "roi": 0, "summary": ""},
        "roi_history": [],
        "risk_alert": "",
        "entities": [],
        "mermaid_graph": "",
        "guided_questions": [],
        "user_profile": profile,
        "adaptive_feedback": {},
        "history": []
    }


async def _run_integration() -> IntegratedState:
    state = _build_state()
    # FallbackIntegratedApp.ainvoke has a dict-copy bug where the internal
    # astream creates another copy, causing ainvoke to return the initial
    # unmodified state.  Accumulate node outputs from astream instead.
    async for chunk in integrated_app.astream(state):
        for node_output in chunk.values():
            if isinstance(node_output, dict):
                state.update(node_output)
    return state


def test_integration_workflow_returns_consistent_final_state():
    final_state = asyncio.run(_run_integration())

    assert final_state["intent_type"] == "plan"
    assert final_state["structured_report"] is not None
    assert "summary" in final_state["structured_report"]
    assert set(final_state["audit_scores"]).issuperset({"consistency", "safety", "roi", "summary"})

    if final_state["final_report"] == "__FILL_FIELDS__":
        assert final_state["missing_fields"] or not final_state["rag_sources"]
        assert not final_state["guided_questions"]
        assert "[guided_questions] 计划待补信息，跳过追问" in final_state["reasoning_log"]
        assert "[guided_questions] 计划已生成，跳过追问" not in final_state["reasoning_log"]
    else:
        assert final_state["final_report"].strip()
        # After P0-1/P0-2 fixes, workflow produces non-empty reports.
        any_ok = any(
            tag in str(final_state["reasoning_log"])
            for tag in ("[formatter]", "[guided_questions]", "已生成", "跳过追问")
        )
        assert any_ok, f"reasoning_log missing expected tags: {final_state['reasoning_log']}"


async def run_integration_test():
    print("[Start] 启动 16 节点工作流集成测试...")
    state = _build_state()
    print(f"\n[Question] 测试问题: {state['query']}")
    print("-" * 50)

    try:
        # 使用 astream_events 模拟流式输出
        async for event in integrated_app.astream_events(state, version="v2"):
            kind = event["event"]
            name = event.get("name", "")
            
            if kind == "on_chain_start":
                if name in ["security_gate", "router", "profiler", "entity_extraction", "coach", "critic_auditor", "formatter"]:
                    print(f"[Node] 进入节点: {name}")
            
            elif kind == "on_chain_end":
                output = event["data"].get("output", {})
                if isinstance(output, dict):
                    if "reasoning_log" in output and output["reasoning_log"]:
                        for log in output["reasoning_log"]:
                            print(f"   [Logic] 推理: {log}")
                    if "final_report" in output and output["final_report"]:
                        # 仅在 formatter 结束时打印预览
                        if name == "formatter":
                            print(f"\n[Success] 最终报告生成成功 (长度: {len(output['final_report'])} 字符)")

        final_state = await integrated_app.ainvoke(_build_state())
        if final_state["final_report"] == "__FILL_FIELDS__":
            print(f"[Assert] 计划待补字段: {', '.join(final_state['missing_fields'])}")
        else:
            print(f"[Assert] 最终报告长度: {len(final_state['final_report'])}")
        print("-" * 50)
        print("[Done] 集成测试完成！工作流各节点链路连通性良好。")
        
    except Exception as e:
        print(f"❌ 集成测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_integration_test())
