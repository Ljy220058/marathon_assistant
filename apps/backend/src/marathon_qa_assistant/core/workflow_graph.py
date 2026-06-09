import logging
from typing import Any, Dict

logger = logging.getLogger("workflow_graph")

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:
    END = "__end__"
    START = "__start__"
    StateGraph = None

try:
    from langgraph.types import RetryPolicy
except ImportError:
    RetryPolicy = None  # type: ignore[assignment]

from marathon_qa_assistant.core.state_models import IntegratedState
from marathon_qa_assistant.nodes.routing import (
    after_critic_auditor_route,
    after_executor_route,
    after_nutritionist_route,
    after_planner_route,
    after_profile_update_route,
    after_router_route,
    after_therapist_route,
    entity_route_decision,
    gate_decision,
)


class FallbackIntegratedApp:
    """无 langgraph 环境下的最小执行器，保留 ainvoke/astream/astream_events 接口。"""

    def __init__(self, node_handlers):
        self.node_handlers = node_handlers

    def _route_after_executor(self, state: Dict[str, Any]) -> str:
        return after_executor_route(state)

    async def _run_node(self, name: str, state: Dict[str, Any], config=None) -> Dict[str, Any]:
        handler = self.node_handlers[name]
        # P0-1 diagnostics: trace node entry
        draft_before = str(state.get("draft_plan", ""))[:50]
        final_before = str(state.get("final_report", ""))[:50]
        token_before = {k: state.get("token_usage", {}).get(k, 0) for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
        logger.debug("[trace] ENTER %s | draft=%s | final=%s | tokens=%s", name, draft_before, final_before, token_before)
        try:
            output = await handler(state, config)
        except Exception as exc:
            logger.error("[trace] EXCEPTION in %s: %s", name, exc, exc_info=True)
            raise
        logger.debug("[trace] OUTPUT %s | type=%s | keys=%s", name, type(output).__name__, list(output.keys()) if isinstance(output, dict) else "NOT_DICT")
        if isinstance(output, dict):
            draft_out = str(output.get("draft_plan", ""))[:80]
            final_out = str(output.get("final_report", ""))[:80]
            logger.debug("[trace] OUTPUT %s | draft=%s | final=%s", name, draft_out, final_out)
            state.update(output)
        else:
            logger.warning("[trace] OUTPUT %s is not dict, skipping merge", name)
        draft_after = str(state.get("draft_plan", ""))[:50]
        final_after = str(state.get("final_report", ""))[:50]
        token_after = {k: state.get("token_usage", {}).get(k, 0) for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
        logger.debug("[trace] AFTER %s | draft=%s | final=%s | tokens=%s", name, draft_after, final_after, token_after)
        return output

    def _next_node(self, current: str, state: Dict[str, Any]) -> str:
        if current == "security_gate":
            return gate_decision(state)
        if current == "router":
            return after_router_route(state)
        if current == "profile_update":
            return after_profile_update_route(state)
        if current == "profiler":
            return "entity_extraction"
        if current == "entity_extraction":
            return "wiki_search"
        if current == "wiki_search":
            decision = entity_route_decision(state)
            # P0-4: 支持营养查询路由到 nutritionist
            if decision == "nutritionist":
                return "nutritionist"
            return decision
        if current == "planner":
            return after_planner_route(state)
        if current == "executor":
            return self._route_after_executor(state)
        if current == "coach":
            return "therapist"
        if current == "adaptive_coach":
            return "therapist"
        if current == "therapist":
            return after_therapist_route(state)
        if current == "nutritionist":
            return after_nutritionist_route(state)
        if current == "psychologist":
            return "critic_auditor"
        if current == "research_analyst":
            return "therapist"
        if current == "critic_auditor":
            return after_critic_auditor_route(state)
        if current == "missing_info_handler":
            return "formatter"
        if current == "formatter":
            return "guided_questions_generator"
        if current == "guided_questions_generator":
            return END
        return END

    async def astream(self, input_state: Dict[str, Any], config=None):
        state = input_state  # P0-1 fix: use same reference so ainvoke sees mutations
        current = "security_gate"
        visited_steps = 0
        max_steps = 50
        while current != END:
            visited_steps += 1
            if visited_steps > max_steps:
                logger.error("[trace] workflow exceeded max_steps=%s at node=%s", max_steps, current)
                raise RuntimeError(f"workflow exceeded max_steps={max_steps}")
            output = await self._run_node(current, state, config=config)
            yield {current: output}
            next_node = self._next_node(current, state)
            logger.debug("[trace] ROUTE %s -> %s | is_approved=%s iter=%s wf=%s", current, next_node, state.get("is_approved"), state.get("iteration_count"), state.get("workflow_kind"))
            current = next_node

    async def ainvoke(self, input_state: Dict[str, Any], config=None):
        state = dict(input_state)
        async for _ in self.astream(state, config=config):
            pass
        return state

    async def astream_events(self, input_state: Dict[str, Any], version="v2", config=None):
        del version
        state = dict(input_state)
        current = "security_gate"
        while current != END:
            yield {"event": "on_chain_start", "name": current, "data": {"input": state.copy()}}
            output = await self._run_node(current, state, config=config)
            yield {"event": "on_chain_end", "name": current, "data": {"output": output}}
            current = self._next_node(current, state)
        yield {"event": "on_chain_end", "name": "LangGraph", "data": {"output": state}}


def build_integrated_app(node_handlers):
    if StateGraph is None:
        return FallbackIntegratedApp(node_handlers)

    workflow = StateGraph(IntegratedState)

    # LLM-calling nodes: 120s timeout + 2 retries with exponential backoff.
    _llm_timeout = 120
    _llm_retry = RetryPolicy(max_attempts=2, initial_interval=1.0, backoff_factor=2.0, jitter=True) if RetryPolicy is not None else None
    # Lightweight nodes: no extra timeout/retry.
    _light_nodes = {
        "security_gate", "router", "entity_extraction", "wiki_search",
        "profiler", "profile_update", "formatter", "guided_questions_generator",
        "missing_info_handler",
    }

    for name, handler in node_handlers.items():
        if name in _light_nodes:
            workflow.add_node(name, handler)
        elif _llm_retry is not None:
            workflow.add_node(name, handler, timeout=_llm_timeout, retry_policy=_llm_retry)
        else:
            workflow.add_node(name, handler, timeout=_llm_timeout)

    workflow.add_edge(START, "security_gate")
    workflow.add_conditional_edges(
        "security_gate",
        gate_decision,
        {
            "formatter": "formatter",
            "router": "router",
            "research_analyst": "research_analyst",
            "adaptive_coach": "adaptive_coach",
        },
    )

    workflow.add_conditional_edges(
        "router",
        after_router_route,
        {
            "profile_update": "profile_update",
            "profiler": "profiler",
        },
    )
    workflow.add_conditional_edges(
        "profile_update",
        after_profile_update_route,
        {
            "formatter": "formatter",
            "profiler": "profiler",
        },
    )
    workflow.add_edge("profiler", "entity_extraction")
    workflow.add_edge("entity_extraction", "wiki_search")
    workflow.add_conditional_edges(
        "wiki_search",
        entity_route_decision,
        {
            "planner": "planner",
            "coach": "coach",
            "nutritionist": "nutritionist",  # P0-4: 营养查询直接路由到营养师
            "research_analyst": "research_analyst",
            "adaptive_coach": "adaptive_coach",
            "missing_info_handler": "missing_info_handler",
        },
    )

    workflow.add_edge("missing_info_handler", "formatter")
    workflow.add_conditional_edges(
        "planner",
        after_planner_route,
        {"executor": "executor", "missing_info_handler": "missing_info_handler"},
    )
    workflow.add_conditional_edges(
        "executor",
        after_executor_route,
        {"nutritionist": "nutritionist", "critic_auditor": "critic_auditor"},
    )
    workflow.add_edge("coach", "therapist")
    workflow.add_edge("research_analyst", "therapist")
    workflow.add_edge("adaptive_coach", "therapist")
    workflow.add_conditional_edges(
        "therapist",
        after_therapist_route,
        {
            "nutritionist": "nutritionist",
            "critic_auditor": "critic_auditor",
        },
    )
    workflow.add_edge("nutritionist", "psychologist")
    workflow.add_edge("psychologist", "critic_auditor")
    workflow.add_conditional_edges(
        "critic_auditor",
        after_critic_auditor_route,
        {
            "formatter": "formatter",
            "executor": "executor",
            "coach": "coach",
            "research_analyst": "research_analyst",
            "adaptive_coach": "adaptive_coach",
            "missing_info_handler": "missing_info_handler",
        },
    )
    workflow.add_edge("formatter", "guided_questions_generator")
    workflow.add_edge("guided_questions_generator", END)

    return workflow.compile()
