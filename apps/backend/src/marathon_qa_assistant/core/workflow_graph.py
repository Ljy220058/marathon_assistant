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
    after_adaptive_coach_route,
    after_conditioning_route,
    after_context_fanout_route,
    after_critic_auditor_route,
    after_executor_route,
    after_planner_route,
    after_rule_checker_route,
    after_router_route,
    after_supervisor_route,
    gate_decision,
)

CIRCUIT_BREAKER_CONFIG = {
    "max_node_visits": {
        "planner": 3,
        "executor": 3,
        "conditioning_constraints": 4,
        "therapist": 2,
        "critic_auditor": 3,
        "default": 3,
    },
    "max_total_node_visits": 50,
}


def _check_node_visit_limits(state: Dict[str, Any], node_name: str) -> Dict[str, int]:
    visits = dict(state.get("node_visit_count") or {})
    visits[node_name] = int(visits.get(node_name, 0) or 0) + 1

    max_visits = CIRCUIT_BREAKER_CONFIG["max_node_visits"].get(
        node_name,
        CIRCUIT_BREAKER_CONFIG["max_node_visits"]["default"],
    )
    if visits[node_name] > max_visits:
        raise RuntimeError(
            f"Circuit breaker: {node_name} visited {visits[node_name]} times "
            f"(max {max_visits}). Possible workflow loop."
        )

    total_visits = sum(int(value or 0) for value in visits.values())
    max_total = int(CIRCUIT_BREAKER_CONFIG["max_total_node_visits"])
    if total_visits > max_total:
        raise RuntimeError(
            f"Circuit breaker: total node visits {total_visits} exceeds limit {max_total}."
        )
    return visits


def _wrap_node_handler(name: str, handler):
    async def wrapped(state: Dict[str, Any], config=None):
        visits = _check_node_visit_limits(state, name)
        output = await handler(state, config)
        if not isinstance(output, dict):
            return output
        merged = dict(output)
        merged["node_visit_count"] = visits
        return merged

    return wrapped


async def _workflow_error_node(state: Dict[str, Any], config=None):
    del config
    error = state.get("workflow_error") if isinstance(state.get("workflow_error"), dict) else {}
    error = dict(error or {})
    error.setdefault("status", "failed")
    error.setdefault("error_code", "WORKFLOW_ERROR")
    error.setdefault("node", "workflow_error")
    error.setdefault("message", "工作流终止。")
    return {
        "workflow_error": error,
        "final_report": str(error.get("message") or "工作流终止。"),
        "reasoning_log": [f"[workflow_error] {error.get('error_code')}: {error.get('message')}"],
        "token_usage": dict(state.get("token_usage") or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}),
    }


class FallbackIntegratedApp:
    """Minimal executor when langgraph is unavailable."""

    def __init__(self, node_handlers):
        self.node_handlers = node_handlers

    def _route_after_executor(self, state: Dict[str, Any]) -> str:
        return after_executor_route(state)

    async def _run_node(self, name: str, state: Dict[str, Any], config=None) -> Dict[str, Any]:
        handler = self.node_handlers[name]
        draft_before = str(state.get("draft_plan", ""))[:50]
        final_before = str(state.get("final_report", ""))[:50]
        token_before = {k: state.get("token_usage", {}).get(k, 0) for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
        logger.debug("[trace] ENTER %s | draft=%s | final=%s | tokens=%s", name, draft_before, final_before, token_before)
        output = await handler(state, config)
        logger.debug("[trace] OUTPUT %s | type=%s | keys=%s", name, type(output).__name__, list(output.keys()) if isinstance(output, dict) else "NOT_DICT")
        if isinstance(output, dict):
            state.update(output)
        return output

    def _next_node(self, current: str, state: Dict[str, Any]) -> str:
        if current == "security_gate":
            decision = gate_decision(state)
            return END if decision == "blocked" else decision
        if current == "router":
            return after_router_route(state)
        if current == "context_fanout":
            return after_context_fanout_route(state)
        if current == "evidence_retriever":
            return "conditioning_constraints"
        if current == "conditioning_constraints":
            return after_conditioning_route(state)
        if current == "supervisor":
            return after_supervisor_route(state)
        if current == "planner":
            return after_planner_route(state)
        if current == "executor":
            return self._route_after_executor(state)
        if current == "coach":
            return "rule_checker"
        if current == "adaptive_coach":
            return after_adaptive_coach_route(state)
        if current == "therapist":
            return "conditioning_constraints"
        if current == "nutritionist":
            return "psychologist"
        if current == "psychologist":
            return "rule_checker"
        if current == "rule_checker":
            return "workflow_error" if after_rule_checker_route(state) == "workflow_error" else "critic_auditor"
        if current == "critic_auditor":
            return after_critic_auditor_route(state)
        if current == "safety_out":
            return "formatter"
        if current == "missing_info_handler":
            return END
        if current == "workflow_error":
            return END
        if current == "formatter":
            return "guided_questions_generator"
        if current == "guided_questions_generator":
            return END
        return END

    async def astream(self, input_state: Dict[str, Any], config=None):
        state = input_state
        current = "security_gate"
        visited_steps = 0
        max_steps = 50
        while current != END:
            visited_steps += 1
            if visited_steps > max_steps:
                raise RuntimeError(f"workflow exceeded max_steps={max_steps}")
            output = await self._run_node(current, state, config=config)
            yield {current: output}
            current = self._next_node(current, state)

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
    if "workflow_error" not in node_handlers:
        node_handlers = {**node_handlers, "workflow_error": _workflow_error_node}
    node_handlers = {name: _wrap_node_handler(name, handler) for name, handler in node_handlers.items()}

    if StateGraph is None:
        return FallbackIntegratedApp(node_handlers)

    workflow = StateGraph(IntegratedState)

    _llm_timeout = 120
    _llm_retry = RetryPolicy(max_attempts=2, initial_interval=1.0, backoff_factor=2.0, jitter=True) if RetryPolicy is not None else None
    _light_nodes = {
        "security_gate",
        "router",
        "context_fanout",
        "evidence_retriever",
        "conditioning_constraints",
        "supervisor",
        "formatter",
        "guided_questions_generator",
        "missing_info_handler",
        "safety_out",
        "rule_checker",
        "workflow_error",
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
            "blocked": END,
            "router": "router",
        },
    )

    workflow.add_conditional_edges(
        "router",
        after_router_route,
        {
            "context_fanout": "context_fanout",
        },
    )
    workflow.add_conditional_edges(
        "context_fanout",
        after_context_fanout_route,
        {
            "evidence_retriever": "evidence_retriever",
        },
    )
    workflow.add_edge("evidence_retriever", "conditioning_constraints")
    workflow.add_conditional_edges(
        "conditioning_constraints",
        after_conditioning_route,
        {
            "supervisor": "supervisor",
            "planner": "planner",
        },
    )
    workflow.add_conditional_edges(
        "supervisor",
        after_supervisor_route,
        {
            "planner": "planner",
            "coach": "coach",
            "adaptive_coach": "adaptive_coach",
            "missing_info_handler": "missing_info_handler",
        },
    )
    workflow.add_edge("missing_info_handler", END)
    workflow.add_conditional_edges(
        "planner",
        after_planner_route,
        {"executor": "executor"},
    )
    workflow.add_edge("executor", "nutritionist")
    workflow.add_edge("coach", "rule_checker")
    workflow.add_conditional_edges(
        "rule_checker",
        after_rule_checker_route,
        {
            "critic_auditor": "critic_auditor",
            "workflow_error": "workflow_error",
        },
    )
    workflow.add_conditional_edges(
        "adaptive_coach",
        after_adaptive_coach_route,
        {
            "therapist": "therapist",
            "conditioning_constraints": "conditioning_constraints",
        },
    )
    workflow.add_edge("therapist", "conditioning_constraints")
    workflow.add_edge("nutritionist", "psychologist")
    workflow.add_edge("psychologist", "rule_checker")
    workflow.add_conditional_edges(
        "critic_auditor",
        after_critic_auditor_route,
        {
            "safety_out": "safety_out",
            "supervisor": "supervisor",
            "workflow_error": "workflow_error",
        },
    )
    workflow.add_edge("safety_out", "formatter")
    workflow.add_edge("workflow_error", END)
    workflow.add_edge("formatter", "guided_questions_generator")
    workflow.add_edge("guided_questions_generator", END)

    return workflow.compile()
