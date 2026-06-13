from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=5000)
    mode: str = "team"
    user_id: str = "default_user"
    stream: bool = False
    llm_provider: str = "ds"
    llm_model: str = ""
    response_mode: str = "full"
    timeout_sec: int = Field(default=120, ge=5, le=600)
    resume_from_workflow_pause: Dict[str, Any] = Field(default_factory=dict)


class QueryResponse(BaseModel):
    report: str
    medical_disclaimer: str = ""
    structured_training_plan: Optional[Dict[str, Any]] = None
    structured_report: Optional[Dict[str, Any]] = None
    training_explanation_panel: Optional[Dict[str, Any]] = None
    monthly_training_calendar: Optional[Dict[str, Any]] = None
    daily_schedule_cards: Optional[List[Dict[str, Any]]] = None
    phases: List[Dict[str, Any]] = Field(default_factory=list)
    training_load_summary: Dict[str, Any] = Field(default_factory=dict)
    training_plan_review: Dict[str, Any] = Field(default_factory=dict)
    token_usage: Dict[str, int]
    audit_scores: Dict[str, Any]
    guided_questions: List[str]
    training_plan_id: Optional[str] = None
    generation_status: str = "complete"
    llm_provider: str = "ds"
    llm_model: str = ""
    message: str = ""
    generation_timings: Dict[str, float] = Field(default_factory=dict)
    half_marathon_protocol_validation: Optional[Dict[str, Any]] = None
    answer_card: Dict[str, Any] = Field(default_factory=dict)
    full_report: Dict[str, Any] = Field(default_factory=dict)
    ui_policy: Dict[str, Any] = Field(default_factory=dict)
    answer_source_mode: str = ""
    rag_health: Dict[str, Any] = Field(default_factory=dict)
    workflow_trace: Dict[str, Any] = Field(default_factory=dict)
    workflow_pause: Dict[str, Any] = Field(default_factory=dict)
    evidence_chain: Dict[str, Any] = Field(default_factory=dict)


class ProfileRequest(BaseModel):
    user_id: str = "default_user"
    profile: Dict[str, Any]


class ProfileFieldRequest(BaseModel):
    value: Any


class NluExtractRequest(BaseModel):
    text: str = ""


class SavePlanRequest(BaseModel):
    user_id: str = "default_user"
    source_query: str = ""
    structured_training_plan: Dict[str, Any]
    calendar_settings: Dict[str, Any] = Field(default_factory=dict)
    calendar_days: List[Dict[str, Any]] = Field(default_factory=list)
    lineage_id: str = ""
    parent_plan_id: str = ""
    trigger: str = "initial"
    trigger_detail: str = ""


class RollbackPlanRequest(BaseModel):
    to_version: int = Field(ge=1)
    trigger_detail: str = ""


class FeedbackRequest(BaseModel):
    user_id: str = "default_user"
    plan_id: Optional[str] = None
    event_id: Optional[str] = None
    day_key: Optional[str] = None
    raw_text: str = ""
    feedback: Dict[str, Any] = Field(default_factory=dict)
    schedule_constraints: Dict[str, Any] = Field(default_factory=dict)


class FeedbackActionRequest(BaseModel):
    action: str
    schedule_constraints: Dict[str, Any] = Field(default_factory=dict)
    note: str = ""


class FeedbackActionResponse(BaseModel):
    feedback_replan: Dict[str, Any]
    affected_events: List[Dict[str, Any]] = Field(default_factory=list)
    plan_diff: Dict[str, Any] = Field(default_factory=dict)


class FeedbackResponse(BaseModel):
    workout_feedback: Dict[str, Any]
    risk_gate: Dict[str, Any]
    protocol_recheck: Dict[str, Any]
    adaptive_feedback: Dict[str, Any]
    adaptive_adjustment: Dict[str, Any]
    plan_diff: Dict[str, Any]
    generation_status: str
    affected_events: List[Dict[str, Any]] = Field(default_factory=list)
    feedback_id: Optional[str] = None
    feedback_replan: Dict[str, Any] = Field(default_factory=dict)
    workflow_trace: Dict[str, Any] = Field(default_factory=dict)


class PlanDetailResponse(BaseModel):
    plan: Dict[str, Any]
    structured_training_plan: Dict[str, Any]
    workflow_trace: Dict[str, Any] = Field(default_factory=dict)
    events: List[Dict[str, Any]]
    versions: List[Dict[str, Any]] = Field(default_factory=list)
    execution_status_summary: Dict[str, Any]
    adjustment_history: List[Dict[str, Any]]
    training_plan_review: Dict[str, Any] = Field(default_factory=dict)
    evidence_chain: Dict[str, Any] = Field(default_factory=dict)


class OpsMetricsResponse(BaseModel):
    requests_total: int
    errors_total: int
    request_route_counts: Dict[str, int] = Field(default_factory=dict)
    generation_status_counts: Dict[str, int]
    feedback_risk_reason_counts: Dict[str, int]
    plan_persist_status_counts: Dict[str, int] = Field(default_factory=dict)
    llm_provider_error_counts: Dict[str, int] = Field(default_factory=dict)
    plan_generation_duration_buckets: Dict[str, int]
    medical_referral_total: int


class EventScheduleRequest(BaseModel):
    scheduled_date: str
    start_time: str
    duration_min: int = Field(default=60, ge=0, le=600)

    @field_validator("scheduled_date")
    @classmethod
    def validate_scheduled_date(cls, value: str) -> str:
        text = str(value or "").strip()
        try:
            date.fromisoformat(text)
        except ValueError as exc:
            raise ValueError("scheduled_date must be a valid ISO date (YYYY-MM-DD).") from exc
        return text

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, value: str) -> str:
        text = str(value or "").strip()
        if len(text) != 5 or text[2] != ":":
            raise ValueError("start_time must use HH:MM format.")
        hour_text, minute_text = text.split(":", 1)
        if not (hour_text.isdigit() and minute_text.isdigit()):
            raise ValueError("start_time must use HH:MM format.")
        hour = int(hour_text)
        minute = int(minute_text)
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("start_time must be a real 24-hour time.")
        return text


class TrainingCalendarResponse(BaseModel):
    year: int
    month: int
    start_week_index: int
    end_week_index: int
    total_days: int
    days: List[Dict[str, Any]]
    phases: List[Dict[str, Any]]
    evidence_summary: Dict[str, int]
    monthly_training_calendar: Dict[str, Any]
    daily_schedule_cards: List[Dict[str, Any]]
    training_load_summary: Dict[str, Any]
    training_plan_review: Dict[str, Any] = Field(default_factory=dict)
    evidence_chain: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeSourceSummary(BaseModel):
    source_registry_id: str = ""
    source_file: str = ""
    source_label: str = ""
    domain_pack: str = ""
    source_status: str = "missing_text"
    has_full_text: bool = False
    evidence_policy: str = "not_answerable"
    chunk_count: int = 0
    body_chunk_count: int = 0
    registry_chunk_count: int = 0
    sections: Dict[str, int] = Field(default_factory=dict)
    sample_text: str = ""


class KnowledgeSourcesResponse(BaseModel):
    total_sources: int = 0
    total_chunks: int = 0
    ready_sources: int = 0
    registry_only_sources: int = 0
    missing_text_sources: int = 0
    status_counts: Dict[str, int] = Field(default_factory=dict)
    domain_pack_counts: Dict[str, int] = Field(default_factory=dict)
    sources: List[KnowledgeSourceSummary] = Field(default_factory=list)


class ZoneReference(BaseModel):
    zones: Dict[str, str]
    zones_detail: Dict[str, str]


class DayDetailResponse(BaseModel):
    day: Dict[str, Any]
    evidence_tier_labels: Dict[str, str]


class AdminCreateUserRequest(BaseModel):
    display_name: str = "新用户"
    birth_year: Optional[int] = None
    age_confirmed: bool = False


class UserConsentRequest(BaseModel):
    privacy_consent: bool = False
    health_data_consent: bool = False
    terms_accepted: bool = False


class UserComplianceResponse(BaseModel):
    user_id: str
    age_gate_passed: bool
    privacy_consented: bool
    health_data_consented: bool
    terms_accepted: bool
    compliance_complete: bool
    missing: List[str] = Field(default_factory=list)
