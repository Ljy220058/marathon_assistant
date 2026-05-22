from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str
    mode: str = "team"
    user_id: str = "default_user"
    stream: bool = False
    llm_provider: str = "ollama"
    llm_model: str = ""
    ds_api_key: str = ""
    response_mode: str = "full"
    timeout_sec: int = Field(default=45, ge=5, le=180)


class QueryResponse(BaseModel):
    report: str
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
    llm_provider: str = "ollama"
    llm_model: str = ""
    message: str = ""
    generation_timings: Dict[str, float] = Field(default_factory=dict)
    half_marathon_protocol_validation: Optional[Dict[str, Any]] = None
    workflow_trace: Dict[str, Any] = Field(default_factory=dict)


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


class FeedbackRequest(BaseModel):
    user_id: str = "default_user"
    plan_id: Optional[str] = None
    event_id: Optional[str] = None
    day_key: Optional[str] = None
    raw_text: str = ""
    feedback: Dict[str, Any] = Field(default_factory=dict)


class FeedbackResponse(BaseModel):
    workout_feedback: Dict[str, Any]
    risk_gate: Dict[str, Any]
    protocol_recheck: Dict[str, Any]
    adaptive_feedback: Dict[str, Any]
    adaptive_adjustment: Dict[str, Any]
    plan_diff: Dict[str, Any]
    generation_status: str
    feedback_id: Optional[str] = None
    workflow_trace: Dict[str, Any] = Field(default_factory=dict)


class PlanDetailResponse(BaseModel):
    plan: Dict[str, Any]
    structured_training_plan: Dict[str, Any]
    workflow_trace: Dict[str, Any] = Field(default_factory=dict)
    events: List[Dict[str, Any]]
    execution_status_summary: Dict[str, Any]
    adjustment_history: List[Dict[str, Any]]
    training_plan_review: Dict[str, Any] = Field(default_factory=dict)


class OpsMetricsResponse(BaseModel):
    requests_total: int
    errors_total: int
    request_route_counts: Dict[str, int] = Field(default_factory=dict)
    generation_status_counts: Dict[str, int]
    feedback_risk_reason_counts: Dict[str, int]
    llm_provider_error_counts: Dict[str, int] = Field(default_factory=dict)
    plan_generation_duration_buckets: Dict[str, int]
    medical_referral_total: int


class EventScheduleRequest(BaseModel):
    scheduled_date: str
    start_time: str
    duration_min: int = Field(default=60, ge=0, le=600)


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


class ZoneReference(BaseModel):
    zones: Dict[str, str]
    zones_detail: Dict[str, str]


class DayDetailResponse(BaseModel):
    day: Dict[str, Any]
    evidence_tier_labels: Dict[str, str]
