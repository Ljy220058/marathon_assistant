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
    structured_report: Optional[Dict[str, Any]] = None
    token_usage: Dict[str, int]
    audit_scores: Dict[str, Any]
    guided_questions: List[str]

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
        "history": []
    }

    try:
        # 使用 ainvoke 进行同步调用
        result = await integrated_app.ainvoke(initial_state)
        
        return QueryResponse(
            report=result.get("final_report", ""),
            structured_report=result.get("structured_report"),
            token_usage=result.get("token_usage", {}),
            audit_scores=result.get("audit_scores", {}),
            guided_questions=result.get("guided_questions", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
