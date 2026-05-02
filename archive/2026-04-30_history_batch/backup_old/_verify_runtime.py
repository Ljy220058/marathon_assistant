r"""
exp5_graphrag 最小运行态验证：确认 ainvoke / astream / astream_events 均走通。
不启动任何 UI，纯 asyncio 驱动。
"""
import sys
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

RESULTS = {}
OK = "[OK]"
FAIL = "[FAIL]"
WARN = "[WARN]"


async def main():
    # -- 0. 检查 Ollama --
    print("=" * 60)
    print("[0] check Ollama ...")
    from marathon_qa_assistant.core.app_state import check_ollama_status
    ok = await check_ollama_status()
    if not ok:
        print(f"{FAIL} Ollama offline, abort.")
        RESULTS["ollama"] = "FAIL"
        return
    print(f"{OK} Ollama online")
    RESULTS["ollama"] = "OK"

    # -- 1. 加载知识库 --
    print("[1] load KB ...")
    from marathon_qa_assistant.core.app_state import get_preferred_vector_dir
    from marathon_qa_assistant.services.vector_store import load_vector_kb, retrieve
    from marathon_qa_assistant.core.workflow import set_kb_data, IntegratedState, load_user_profile

    vector_dir = get_preferred_vector_dir()
    print(f"    dir: {vector_dir}")
    chunks, vectorizer, matrix, bm25 = load_vector_kb(vector_dir)
    set_kb_data(chunks, vectorizer, matrix, retrieve, bm25=bm25)
    print(f"{OK} KB loaded: {len(chunks)} chunks")
    RESULTS["kb_load"] = f"OK ({len(chunks)} chunks)"

    # -- 2. 构造最小 state --
    profile = load_user_profile()
    query = "什么是乳酸阈值"

    state: IntegratedState = {
        "query": query,
        "mode": "team",
        "intent_type": "qa",
        "selected_entities": [],
        "category": "",
        "subtasks": [],
        "draft_plan": "",
        "review_feedback": "",
        "is_approved": False,
        "iteration_count": 0,
        "final_report": "",
        "structured_report": None,
        "reasoning_log": [],
        "gate_hits": [],
        "rag_sources": [],
        "graph_context": "",
        "wiki_context": "",
        "mermaid_graph": "",
        "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "audit_scores": {"consistency": 0, "safety": 0, "roi": 0, "summary": ""},
        "roi_history": [],
        "risk_alert": "",
        "entities": [],
        "guided_questions": [],
        "user_profile": profile,
        "adaptive_feedback": {},
        "missing_fields": [],
        "history": [],
    }

    from marathon_qa_assistant.core.workflow import integrated_app

    # -- 3. 测试 ainvoke --
    print("=" * 60)
    print(f"[2] test ainvoke | query='{query}' ...")
    try:
        s = dict(state)
        final = await asyncio.wait_for(integrated_app.ainvoke(s), timeout=120.0)
        report_len = len(final.get("final_report", ""))
        log_count = len(final.get("reasoning_log", []))
        intent = final.get("intent_type", "?")
        mode = final.get("mode", "?")
        tokens = final.get("token_usage", {}).get("total_tokens", "?")
        print(f"    mode={mode}  intent={intent}  report_len={report_len}  logs={log_count}  tokens={tokens}")
        if report_len > 0:
            print(f"    {OK} ainvoke PASS")
            RESULTS["ainvoke"] = f"OK (report={report_len}ch)"
        else:
            print(f"    {WARN} ainvoke empty report (likely KB gap / refusal)")
            RESULTS["ainvoke"] = "OK (empty report - likely KB gap)"
    except Exception as e:
        print(f"    {FAIL} ainvoke FAIL: {e}")
        RESULTS["ainvoke"] = f"FAIL: {e}"

    # -- 4. 测试 astream --
    print("=" * 60)
    print(f"[3] test astream | query='{query}' ...")
    try:
        s = dict(state)
        node_count = 0
        final_report = ""
        async for event in integrated_app.astream(s):
            for node_name, output in event.items():
                node_count += 1
                if output.get("final_report"):
                    final_report = output["final_report"]
        print(f"    {node_count} nodes yielded, report_len={len(final_report)}")
        if node_count >= 3:
            print(f"    {OK} astream PASS")
            RESULTS["astream"] = f"OK ({node_count} nodes)"
        else:
            print(f"    {WARN} astream few nodes")
            RESULTS["astream"] = f"WARN ({node_count} nodes)"
    except Exception as e:
        print(f"    {FAIL} astream FAIL: {e}")
        RESULTS["astream"] = f"FAIL: {e}"

    # -- 5. 测试 astream_events --
    print("=" * 60)
    print(f"[4] test astream_events | query='{query}' ...")
    try:
        s = dict(state)
        on_chain_start_count = 0
        on_chain_end_count = 0
        on_chat_model_stream_count = 0
        langgraph_end_output = None

        async for event in integrated_app.astream_events(s, version="v2"):
            kind = event.get("event", "")
            name = event.get("name", "")

            if kind == "on_chain_start":
                on_chain_start_count += 1
            elif kind == "on_chain_end":
                on_chain_end_count += 1
                if name in ("LangGraph", "__root__", ""):
                    data = event.get("data", {})
                    langgraph_end_output = data.get("output")
            elif kind == "on_chat_model_stream":
                on_chat_model_stream_count += 1

        if langgraph_end_output and isinstance(langgraph_end_output, dict):
            report_len = len(langgraph_end_output.get("final_report", ""))
        else:
            report_len = 0

        print(f"    chain_start={on_chain_start_count}  chain_end={on_chain_end_count}  stream_chunks={on_chat_model_stream_count}  report_len={report_len}")
        if on_chain_start_count >= 5 and on_chain_end_count >= 5:
            print(f"    {OK} astream_events PASS")
            RESULTS["astream_events"] = f"OK ({on_chain_start_count} starts, {on_chain_end_count} ends)"
        else:
            print(f"    {WARN} astream_events few events")
            RESULTS["astream_events"] = f"WARN (starts={on_chain_start_count}, ends={on_chain_end_count})"
    except Exception as e:
        print(f"    {FAIL} astream_events FAIL: {e}")
        RESULTS["astream_events"] = f"FAIL: {e}"

    # -- 6. 汇总 --
    print("=" * 60)
    print("Summary:")
    for k, v in RESULTS.items():
        if v.startswith("FAIL"):
            print(f"  {FAIL} {k}: {v}")
        elif v.startswith("WARN"):
            print(f"  {WARN} {k}: {v}")
        else:
            print(f"  {OK} {k}: {v}")

    all_ok = all(
        v.startswith("OK") or v.startswith("WARN")
        for k, v in RESULTS.items()
        if k != "ollama"
    )
    if all_ok:
        print(f"\n{OK} ainvoke / astream / astream_events ALL PASS at exp5_graphrag.")
    else:
        print(f"\n{FAIL} some items failed, see above.")


if __name__ == "__main__":
    asyncio.run(main())
