import operator
import asyncio
import json
import os
from typing import List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# 导入统一引擎
from workflow_engine import IntegratedState, integrated_app, set_kb_data

try:
    from build_vector_kb import load_vector_kb, retrieve
    VECTOR_KB_AVAILABLE = True
except ImportError:
    VECTOR_KB_AVAILABLE = False

app = FastAPI(title="LangGraph RAG API", version="1.0.0")

# ==========================================
# 1. 安全加固 (Task 1)
# ==========================================
API_KEY_NAME = "X-API-Key"
API_KEY = os.getenv("GRAPHRAG_API_KEY", "default_secret_key")
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if not api_key or api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Could not validate API Key")
    return api_key

# CORS 策略限制 (Task 1)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 2. 配置解耦 (Task 2)
# ==========================================
DEFAULT_VECTOR_DIR = Path(__file__).parent / "vector_kb"
KB_CHUNKS = []

class ChatRequest(BaseModel):
    question: str
    enable_rag: bool = True

def load_kb(vector_dir: str):
    try:
        path = Path(vector_dir).expanduser().resolve()
        if not VECTOR_KB_AVAILABLE:
            return "向量库模块不可用", {}
        
        chunks, vectorizer, matrix, bm25 = load_vector_kb(path)
        global KB_CHUNKS
        KB_CHUNKS = chunks
        
        # 同步更新引擎中的知识库数据
        set_kb_data(chunks, vectorizer, matrix, retrieve, bm25=bm25)
        
        # 兼容性处理： matrix 现在是 Chroma 实例
        db_info = "ChromaDB"
        
        return "已加载知识库", {"vector_dir": str(path), "chunks": len(chunks), "db_info": db_info}
    except Exception as e:
        global KB_MATRIX, KB_VECTORIZER
        set_kb_data([], None, None, None)
        return f"加载失败：{e}", {}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "kb_loaded": len(KB_CHUNKS) > 0}

@app.post("/api/load-kb", dependencies=[Depends(verify_api_key)])
async def api_load_kb(vector_dir: str = None):
    if vector_dir is None:
        vector_dir = str(DEFAULT_VECTOR_DIR)
    status, meta = load_kb(vector_dir)
    return {"status": status, "meta": meta}

@app.post("/api/chat", dependencies=[Depends(verify_api_key)])
async def chat_stream(request: ChatRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    state: IntegratedState = {
        "query": request.question,
        "mode": "team", # 默认模式，由 router 动态改写
        "category": "",
        "subtasks": [],
        "draft_plan": "",
        "review_feedback": "",
        "is_approved": False,
        "iteration_count": 0,
        "final_report": "",
        "reasoning_log": [],
        "rag_sources": [],
        "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    }

    async def event_generator():
        reasoning_set = set()
        rag_sources_seen = set()

        try:
            async for event in integrated_app.astream(state):
                for node_name, output in event.items():
                    # 推送 Token 使用情况 (v2.0 Schema)
                    if "token_usage" in output:
                        yield f"data: {json.dumps({'type': 'usage', 'usage': output['token_usage']}, ensure_ascii=False)}\n\n"

                    # 推送工作模式 (v2.0 Schema)
                    if "mode" in output:
                        yield f"data: {json.dumps({'type': 'mode_switch', 'mode': output['mode']}, ensure_ascii=False)}\n\n"

                    if "reasoning_log" in output:
                        for log in output["reasoning_log"]:
                            if log not in reasoning_set:
                                reasoning_set.add(log)
                                data = {
                                    "type": "reasoning",
                                    "node": node_name,
                                    "log": log,
                                    "count": len(reasoning_set)
                                }
                                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

                    if "rag_sources" in output and output["rag_sources"]:
                        for src in output["rag_sources"]:
                            src_id = src.get("source", src.get("title"))
                            if src_id not in rag_sources_seen:
                                rag_sources_seen.add(src_id)
                                data = {
                                    "type": "rag_source",
                                    "source": src
                                }
                                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

                    if "final_report" in output:
                        data = {
                            "type": "final",
                            "report": output["final_report"]
                        }
                        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                        return

        except Exception as e:
            error_data = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

if __name__ == "__main__":
    import uvicorn
    host = "0.0.0.0"
    port = int(os.getenv("API_PORT", 8000))
    print(f"Starting API server at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
