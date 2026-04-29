from marathon_qa_assistant.core.kb_provider import KB_CHUNKS, clear_kb_data, set_kb_data
from marathon_qa_assistant.core.profile_store import load_user_profile, save_user_profile
from marathon_qa_assistant.core.state_models import (
    AuditScores,
    EntityList,
    EvidenceSource,
    IntegratedState,
    ProfessionalReport,
    ReportTaskResult,
    TokenUsage,
)
from marathon_qa_assistant.core.workflow_graph import build_integrated_app
from marathon_qa_assistant.nodes.expert_nodes import (
    adaptive_coach_node,
    auditor_node,
    coach_node,
    nutritionist_node,
    research_analyst_node,
    therapist_node,
)
from marathon_qa_assistant.nodes.output_nodes import formatter_node, guided_questions_node
from marathon_qa_assistant.nodes.plan_nodes import executor_node, planner_node
from marathon_qa_assistant.nodes.profile_and_retrieval import (
    entity_extraction_node,
    missing_info_handler_node,
    profiler_node,
    wiki_search_node,
)
from marathon_qa_assistant.nodes.profile_update import profile_update_node
from marathon_qa_assistant.nodes.router import router_node
from marathon_qa_assistant.nodes.security import security_gate_node

integrated_app = build_integrated_app(
    {
        "security_gate": security_gate_node,
        "router": router_node,
        "entity_extraction": entity_extraction_node,
        "wiki_search": wiki_search_node,
        "profiler": profiler_node,
        "profile_update": profile_update_node,
        "planner": planner_node,
        "executor": executor_node,
        "coach": coach_node,
        "nutritionist": nutritionist_node,
        "therapist": therapist_node,
        "auditor": auditor_node,
        "formatter": formatter_node,
        "guided_questions_generator": guided_questions_node,
        "research_analyst": research_analyst_node,
        "adaptive_coach": adaptive_coach_node,
        "missing_info_handler": missing_info_handler_node,
    }
)

__all__ = [
    "AuditScores",
    "KB_CHUNKS",
    "EntityList",
    "EvidenceSource",
    "IntegratedState",
    "ProfessionalReport",
    "ReportTaskResult",
    "TokenUsage",
    "clear_kb_data",
    "integrated_app",
    "load_user_profile",
    "save_user_profile",
    "set_kb_data",
]
