# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Start API server (FastAPI on port 8000)
python marathon_qa_assistant/apps/api_app.py

# Run all tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_security_guards.py -v

# Verify core module compiles
python -m py_compile marathon_qa_assistant/core/workflow.py

# Build vector KB from domain_docs/
python marathon_qa_assistant/services/vector_store.py --mode build --vector-dir vector_kb

# Run retrieval test
python marathon_qa_assistant/services/vector_store.py --mode test --vector-dir vector_kb --query "马拉松训练"
```

## Architecture

This is a **marathon training AI coach** built on LangGraph. The system ingests sports science PDFs into a FAISS vector store + knowledge graph, then runs a multi-agent LangGraph workflow for RAG-augmented Q&A, training plan generation, and safety auditing.

### LangGraph Workflow

17 nodes connected in a StateGraph with conditional routing. The full path:

```
START → security_gate → router → [profile_sync] → profiler → entity_extraction
  → wiki_search → [planner → executor → auditor] | [coach → therapist → nutritionist → auditor] | [missing_info_handler]
  → formatter → guided_questions → END
```

**Modes** (set in `IntegratedState.mode`):
- `team` — multi-expert Q&A (coach + nutritionist + therapist + auditor), with iteration loop on audit rejection
- `subagent` — training plan generation (planner → executor → auditor), with iteration loop
- `research` — cross-document analysis via `research_analyst_node`
- `adaptive` — adaptive plan adjustment via `adaptive_coach_node`
- `intercepted` — security gate blocked, terminates immediately

**Key routing decisions** (in `nodes/routing/__init__.py`):
- `gate_decision` — after security: intercepted→blocked, else→router
- `after_supervisor_route` — missing fields→missing_info_handler, adaptive→adaptive_coach, plan→planner, else→coach
- `after_critic_auditor_route` — approved→safety_out, retry→supervisor, retry budget exhausted→workflow_error

### RAG Pipeline

**Ingestion**: PDF/DOCX/TXT/images → text extraction (PyMuPDF/pypdf/python-docx/PaddleOCR) → 500-char chunks with 50-char overlap → `nomic-embed-text` via Ollama → FAISS vector DB + `chunks.jsonl`

**Retrieval** (core fusion logic in `profile_and_retrieval.py::build_ranked_evidence`):
1. Entity extraction (regex, ≤5 domain entities)
2. Dense vector search (FAISS similarity, query enhanced with `QUERY_HINTS` keyword expansion)
3. Knowledge graph BFS search (2-hop, `services/knowledge_graph.py::search_graph`)
4. Fusion: dedup by `chunk_id`, upgrade vector+graph overlap to `kind="fusion"`
5. Hybrid scoring: `vector_score×0.4 + graph_confidence×0.3 + entity_overlap×0.2 + fusion_bonus×0.1 - penalty`
6. Top-5 with stable citation labels `[1]`-`[5]`

**Knowledge Graph** (`services/knowledge_graph.py::GraphEngine`):
- Pre-built decision registry: 5 constraints (quality gap, weekly caps) + 8 workout templates (easy run through repetition)
- `STRICT_MODE = True` in production — blocks LLM triple extraction, graph runs on registry only
- `plan_week_drafts()` — constraint-based week planner that steps through days with state tracking, auto-downgrading blocked workouts

### Module Layout

| Layer | Location | Role |
|-------|----------|------|
| Assembly | `core/workflow.py` + `workflow_graph.py` | Node registry → compiled `integrated_app` |
| State | `core/state_models.py` | `IntegratedState` TypedDict (~40 fields) |
| Nodes | `nodes/` | One async function per node, all share `IntegratedState` |
| Routing | `nodes/routing/__init__.py` | All conditional edge functions + evidence gate |
| Services | `services/vector_store.py`, `knowledge_graph.py`, `multimodal.py`, `wiki_agent.py` | KB, graph, OCR/VLM, external wiki |
| Core libs | `core/kb_runtime.py`, `kb_provider.py`, `app_state.py`, `profile_store.py`, `physiology.py` | Global KB state, path config, 9-zone calculations |

### State Model

The central `IntegratedState` (TypedDict) carries all state through the graph. Key fields:
- `query`, `mode`, `intent_type`, `category` — routing inputs
- `user_profile` — athlete data (lthr, t_pace, goal, weekly_mileage, pace_zones, etc.)
- `ranked_evidence` — `List[Evidence]` from the fusion pipeline
- `draft_plan`, `review_feedback`, `is_approved`, `iteration_count` — audit loop state
- `reasoning_log` — `Annotated[List[str], operator.add]` for append-only logging
- `token_usage`, `audit_scores`, `risk_alert` — observability

### Fallback Design

Every import is wrapped in `try/except ImportError` with local stubs. `workflow_graph.py` provides `FallbackIntegratedApp` when `langgraph` is unavailable — it implements the same `ainvoke/astream/astream_events` interface by chaining node calls sequentially with the same routing logic in `_next_node()`. This means the core QA/plan logic works even without LangGraph installed.

### Security

Two-layer guard in `nodes/security.py`:
- **InputGuard**: compiled regex patterns detect prompt injection, jailbreak, API key leaks, system prompt probing. Also checks last 6 history turns.
- **OutputGuard**: scans LLM output for sensitive leaks (auto-redacts) and harmful content (blocks).

Additionally, retrieved context is sanitized via `scan_and_clean_context()` before prompt injection, and prompts include a security suffix to prevent instruction-following from retrieved content.
