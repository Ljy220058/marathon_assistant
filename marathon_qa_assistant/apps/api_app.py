import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 将项目根目录添加到 sys.path
current_file = Path(__file__).absolute()
BASE_DIR = current_file.parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from marathon_qa_assistant.core.workflow import integrated_app, IntegratedState, load_user_profile
from marathon_qa_assistant.services.daily_schedule_generator import generate_daily_schedule
from marathon_qa_assistant.services.workout_template_retriever import (
    WORKOUT_TEMPLATE_REGISTRY,
    ZONE_LABELS,
    ZONE_LABELS_DETAIL,
    EVIDENCE_TIER_LABELS,
)

DEFAULT_API_USER_ID = "default_user"

app = FastAPI(title="Marathon QA Assistant API", version="1.0.0")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # Browsers reject "*" + credentials, so keep the API permissive but stateless.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str
    mode: str = "team"  # team (coach) or research
    user_id: str = DEFAULT_API_USER_ID
    stream: bool = False

class QueryResponse(BaseModel):
    report: str
    structured_training_plan: Optional[Dict[str, Any]] = None
    structured_report: Optional[Dict[str, Any]] = None
    training_explanation_panel: Optional[Dict[str, Any]] = None
    monthly_training_calendar: Optional[Dict[str, Any]] = None
    daily_schedule_cards: Optional[List[Dict[str, Any]]] = None
    token_usage: Dict[str, int]
    audit_scores: Dict[str, Any]
    guided_questions: List[str]

class TrainingCalendarResponse(BaseModel):
    year: int
    month: int
    start_week_index: int
    end_week_index: int
    total_days: int
    days: List[Dict[str, Any]]
    phases: List[Dict[str, Any]]
    evidence_summary: Dict[str, int]

class ZoneReference(BaseModel):
    zones: Dict[str, str]  # Z1-Z9 -> label mapping
    zones_detail: Dict[str, str]  # Z1-Z9 -> detail label mapping

class DayDetailResponse(BaseModel):
    day: Dict[str, Any]
    evidence_tier_labels: Dict[str, str]

@app.get("/health")
async def health_check():
    return {"status": "healthy", "model": os.getenv("OLLAMA_MODEL", "qwen2.5:latest")}

@app.post("/query", response_model=QueryResponse)
async def execute_query(request: QueryRequest):
    """同步查询接口"""
    if request.user_id != DEFAULT_API_USER_ID:
        raise HTTPException(
            status_code=400,
            detail=f"当前 API 仅支持单用户画像，user_id 必须为 {DEFAULT_API_USER_ID!r}。",
        )

    profile = load_user_profile()
    
    initial_state: IntegratedState = {
        "query": request.query,
        "mode": request.mode,
        "intent_type": "qa",
        "category": "",
        "subtasks": [],
        "draft_plan": "",
        "review_feedback": "",
        "is_approved": False,
        "iteration_count": 0,
        "final_report": "",
        "structured_training_plan": None,
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
        "adaptive_adjustment": {},
        "missing_info_status": "",
        "enhancement_missing_fields": [],
        "history": []
    }

    try:
        # 使用 ainvoke 进行同步调用
        result = await integrated_app.ainvoke(initial_state)
        structured_report = result.get("structured_report")
        training_explanation_panel = None
        monthly_training_calendar = None
        daily_schedule_cards = None
        if isinstance(structured_report, dict):
            training_explanation_panel = structured_report.get("training_explanation_panel")
            monthly_training_calendar = structured_report.get("monthly_training_calendar")
            daily_schedule_cards = structured_report.get("daily_schedule_cards")
        
        return QueryResponse(
            report=result.get("final_report", ""),
            structured_training_plan=result.get("structured_training_plan"),
            structured_report=structured_report,
            training_explanation_panel=training_explanation_panel,
            monthly_training_calendar=monthly_training_calendar,
            daily_schedule_cards=daily_schedule_cards,
            token_usage=result.get("token_usage", {}),
            audit_scores=result.get("audit_scores", {}),
            guided_questions=result.get("guided_questions", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/zone-reference", response_model=ZoneReference)
async def get_zone_reference():
    """返回 Z1-Z9 强度区间中文术语参考表"""
    return ZoneReference(
        zones=ZONE_LABELS,
        zones_detail=ZONE_LABELS_DETAIL,
    )


@app.get("/evidence-tier-reference")
async def get_evidence_tier_reference():
    """返回证据分层标记的中文映射"""
    return {
        "evidence_tiers": EVIDENCE_TIER_LABELS,
        "descriptions": {
            "action_library": "课表数据来自动作库直接证据，训练方案经过验证。",
            "kb_fallback": "动作库中未找到该训练类型的直接证据，已基于其他知识库内容生成参考课表。",
            "plan_only": "当前训练类型在知识库中暂无充分证据支撑，基于训练计划骨架生成。",
        },
    }


@app.post("/training-calendar", response_model=TrainingCalendarResponse)
async def get_training_calendar(request: QueryRequest):
    """生成并返回训练日历（月历视图数据）"""
    if request.user_id != DEFAULT_API_USER_ID:
        raise HTTPException(
            status_code=400,
            detail=f"当前 API 仅支持单用户画像，user_id 必须为 {DEFAULT_API_USER_ID!r}。",
        )

    profile = load_user_profile()
    initial_state: IntegratedState = {
        "query": request.query,
        "mode": request.mode,
        "intent_type": "qa",
        "category": "",
        "subtasks": [],
        "draft_plan": "",
        "review_feedback": "",
        "is_approved": False,
        "iteration_count": 0,
        "final_report": "",
        "structured_training_plan": None,
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
        "adaptive_adjustment": {},
        "missing_info_status": "",
        "enhancement_missing_fields": [],
        "history": [],
    }

    try:
        result = await integrated_app.ainvoke(initial_state)
        structured_training_plan = result.get("structured_training_plan")
        if not structured_training_plan:
            raise HTTPException(status_code=404, detail="未生成训练计划，请先使用 /query 接口生成训练计划。")

        calendar = generate_daily_schedule(structured_training_plan)
        if not calendar or not calendar.days:
            raise HTTPException(status_code=404, detail="训练日历生成失败，计划数据不完整。")

        return TrainingCalendarResponse(
            year=calendar.year,
            month=calendar.month,
            start_week_index=calendar.start_week_index,
            end_week_index=calendar.end_week_index,
            total_days=calendar.total_days,
            days=[d.to_dict() for d in calendar.days],
            phases=calendar.phases,
            evidence_summary=calendar.evidence_summary,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/training-calendar/day-detail/{day_index}", response_model=DayDetailResponse)
async def get_day_detail(day_index: int):
    """返回训练日历中某一天的详情（从会话提取或历史缓存的日历数据）"""
    return DayDetailResponse(
        day={"day_index": day_index, "note": "请通过 /training-calendar 接口获取完整日历后在客户端侧查找。"},
        evidence_tier_labels=EVIDENCE_TIER_LABELS,
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
