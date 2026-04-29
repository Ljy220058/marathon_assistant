import asyncio
import sys
from pathlib import Path

# 将项目根目录添加到 sys.path
BASE_DIR = Path(__file__).absolute().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from marathon_qa_assistant.core.workflow import integrated_app, IntegratedState, load_user_profile

async def run_integration_test():
    print("[Start] 启动 16 节点工作流集成测试...")
    
    # 初始化状态
    profile = load_user_profile()
    state: IntegratedState = {
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

    print(f"\n[Question] 测试问题: {state['query']}")
    print("-" * 50)

    try:
        # 使用 astream_events 模拟流式输出
        async for event in integrated_app.astream_events(state, version="v2"):
            kind = event["event"]
            name = event.get("name", "")
            
            if kind == "on_chain_start":
                if name in ["security_gate", "router", "profiler", "entity_extraction", "coach", "auditor", "formatter"]:
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

        print("-" * 50)
        print("[Done] 集成测试完成！工作流各节点链路连通性良好。")
        
    except Exception as e:
        print(f"❌ 集成测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_integration_test())
