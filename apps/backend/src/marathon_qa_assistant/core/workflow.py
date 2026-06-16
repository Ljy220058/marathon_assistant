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
from marathon_qa_assistant.nodes.conditioning import conditioning_constraints_node
from marathon_qa_assistant.nodes.expert_nodes import (
    adaptive_coach_node,
    coach_node,
    critic_auditor_node,
    nutritionist_node,
    psychologist_node,
    rule_checker_node,
    therapist_node,
)
from marathon_qa_assistant.nodes.output_nodes import formatter_node, guided_questions_node
from marathon_qa_assistant.nodes.plan_nodes import executor_node, planner_node
from marathon_qa_assistant.nodes.profile_and_retrieval import (
    context_fanout_node,
    evidence_retriever_node,
    missing_info_handler_node,
)
from marathon_qa_assistant.nodes.crag_corrector import crag_corrector_node
from marathon_qa_assistant.nodes.router import router_node
from marathon_qa_assistant.nodes.routing import supervisor_node
from marathon_qa_assistant.nodes.security import safety_out_node, security_gate_node

integrated_app = build_integrated_app(
    {
        "security_gate": security_gate_node,
        "router": router_node,
        "supervisor": supervisor_node,
        "context_fanout": context_fanout_node,
        "evidence_retriever": evidence_retriever_node,
        "crag_corrector": crag_corrector_node,
        "conditioning_constraints": conditioning_constraints_node,
        "planner": planner_node,
        "executor": executor_node,
        "coach": coach_node,
        "nutritionist": nutritionist_node,
        "psychologist": psychologist_node,
        "therapist": therapist_node,
        "rule_checker": rule_checker_node,
        "critic_auditor": critic_auditor_node,
        "safety_out": safety_out_node,
        "formatter": formatter_node,
        "guided_questions_generator": guided_questions_node,
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
