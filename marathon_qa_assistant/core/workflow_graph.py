from typing import Any, Dict

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:
    END = "__end__"
    START = "__start__"
    StateGraph = None

from marathon_qa_assistant.core.state_models import IntegratedState
from marathon_qa_assistant.nodes.routing import (
    after_critic_auditor_route,
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

    async def _run_node(self, name: str, state: Dict[str, Any], config=None) -> Dict[str, Any]:
        handler = self.node_handlers[name]
        output = await handler(state, config)
        if isinstance(output, dict):
            state.update(output)
            return output
        return {}

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
            return entity_route_decision(state)
        if current == "planner":
            return after_planner_route(state)
        if current == "executor":
            return "critic_auditor"
        if current == "coach":
            return "therapist"
        if current == "adaptive_coach":
            return "therapist"
        if current == "therapist":
            return after_therapist_route(state)
        if current == "nutritionist":
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
        state = dict(input_state)
        current = "security_gate"
        while current != END:
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
    if StateGraph is None:
        return FallbackIntegratedApp(node_handlers)

    workflow = StateGraph(IntegratedState)
    for name, handler in node_handlers.items():
        workflow.add_node(name, handler)

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
    workflow.add_edge("executor", "critic_auditor")
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
    workflow.add_edge("nutritionist", "critic_auditor")
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
