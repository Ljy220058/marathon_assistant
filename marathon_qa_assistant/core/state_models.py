import operator
from typing import Annotated, Any, Dict, List, Optional, TypedDict

try:
    from pydantic import BaseModel, Field
except ImportError:
    class BaseModel:
        """无 pydantic 环境下的最小兜底模型。"""

        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        def model_dump(self):
            return self.__dict__.copy()

    def Field(default=None, **kwargs):
        if "default_factory" in kwargs:
            return kwargs["default_factory"]()
        return default


class TokenUsage(TypedDict):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class AdaptiveFeedback(TypedDict):
    fatigue_level: int
    missed_workouts: bool
    abnormal_hr: bool
    notes: str


class UserProfile(TypedDict):
    experience_level: str
    weekly_mileage: float
    goal: str
    injury_history: List[str]
    last_race_time: str
    pb_800m: Optional[str]
    pb_1500m: Optional[str]
    pb_5k: Optional[str]
    pb_10k: Optional[str]
    pb_half: Optional[str]
    pb_full: Optional[str]
    lthr: Optional[int]
    t_pace: Optional[str]
    hr_zones: Optional[Dict[str, str]]
    pace_zones: Optional[Dict[str, str]]
    target_race_date: Optional[str]
    plan_duration_weeks: Optional[int]
    long_term_memory: Optional[List[str]]
    verified_facts: Optional[Dict[str, Any]]


class AuditScores(TypedDict):
    consistency: int
    safety: int
    roi: int
    summary: str
    score_sources: Dict[str, Any]


class ReportTaskResult(BaseModel):
    task_id: str
    objective: str
    findings: Dict[str, Any]
    mechanisms: Optional[List[Dict[str, str]]] = None
    conclusion: Optional[str] = None


class EvidenceSource(BaseModel):
    document: str
    pages: List[int]


class Evidence(TypedDict):
    """统一证据数据结构"""
    evidence_id: str
    kind: str  # vector | graph | fusion
    source_file: str
    page: int
    chunk_id: str
    snippet: str
    text: str
    vector_score: float
    retrieval_score: float
    graph_confidence: float
    entity_overlap: float
    fusion_bonus: float
    hybrid_score: float
    citation_label: str  # [1], [2] 等
    trace: Dict[str, Any]


class ProfessionalReport(BaseModel):
    report_metadata: Dict[str, str] = Field(default_factory=lambda: {"version": "2.0", "mode": "SUBAGENT"})
    analysis_framework: Dict[str, Any]
    execution_steps: List[ReportTaskResult]
    audit_block: Dict[str, Any]
    evidence_base: List[EvidenceSource]


class EntityList(BaseModel):
    entities: List[str] = Field(description="核心实体名词列表")


class IntegratedState(TypedDict):
    query: str
    mode: str
    intent_type: str
    selected_entities: List[str]
    category: str
    subtasks: List[Dict[str, Any]]
    draft_plan: str
    review_feedback: str
    is_approved: bool
    iteration_count: int
    final_report: str
    structured_report: Optional[Dict[str, Any]]
    reasoning_log: Annotated[List[str], operator.add]
    gate_hits: List[Dict[str, Any]]
    rag_sources: List[Dict[str, Any]]
    ranked_evidence: List[Evidence]
    graph_context: str
    wiki_context: str
    mermaid_graph: str
    token_usage: TokenUsage
    audit_scores: AuditScores
    roi_history: List[float]
    risk_alert: str
    entities: List[str]
    guided_questions: List[str]
    user_profile: UserProfile
    adaptive_feedback: AdaptiveFeedback
    missing_fields: List[str]
    history: List[Dict[str, str]]
    used_fallback: bool
    fallback_reason: str
