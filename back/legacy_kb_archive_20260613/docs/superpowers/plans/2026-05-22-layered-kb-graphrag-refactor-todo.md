# Layered KB GraphRAG Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a layered, auditable knowledge base and GraphRAG prescription evidence kernel so the app can prove why a training plan is more traceable and professionally bounded than a plain LLM answer.

**Architecture:** Keep existing public facades stable while introducing a new `services/kb/` package. The vector index finds source material, the graph layer models relationships, the action library controls core prescription fields, and the evaluation layer proves retrieval and evidence quality. Frontend UI changes are out of scope for this implementation round, but API payloads must carry future-safe metadata that the frontend can consume later.

**Tech Stack:** Python, FastAPI, Pydantic, SQLite, local vector KB, FAISS or TF-IDF existing retriever, GraphRAG-inspired graph query patterns, pytest contract tests, existing Astro frontend contract tests.

---

## Scope Decision

- This plan implements Route C: layered knowledge base, GraphRAG, action library, and evidence kernel first.
- Do not rewrite `apps/web/src/scripts/app.js` in this plan.
- Do not replace the existing vector store in one step.
- Do not remove `GraphEngine`, `generate_daily_schedule()`, `build_structured_training_plan_skeleton()`, or `marathon_qa_assistant.apps.api_app:app`.
- Do not let GraphRAG or LLM general knowledge write core prescription fields.
- Allow `llm_general_knowledge` only for general explanations when no local source exists.
- Keep all API changes additive and backward compatible.

## External Evidence Used For This Plan

- Microsoft GraphRAG query engine separates local, global, and DRIFT search. The implementation should route questions to retrieval modes instead of treating one graph query as universal.
- GraphRAG research shows graph summaries improve cross-document sensemaking, but it does not make every generated prescription field clinically or sport-science valid.
- Ragas evaluates retrieval and generation with separate metrics such as faithfulness, answer relevancy, context precision, and context recall. This project needs comparable evidence-quality gates.
- WHO health AI guidance emphasizes transparency, explainability, accountability, and caution with persuasive but wrong LLM answers.
- ACSM FITT-VP exercise prescription framing supports structured prescription fields: frequency, intensity, time, type, volume, and progression.

## Current Repo Evidence

- `apps/backend/src/marathon_qa_assistant/services/knowledge_graph.py` mixes graph IO, schema migration, entity extraction, registry data, decision execution, and Mermaid output.
- `apps/backend/src/marathon_qa_assistant/services/vector_store.py` owns document extraction, chunk metadata, query variants, retrieval, FAISS/TF-IDF concerns, and source-path inference.
- `apps/backend/src/marathon_qa_assistant/services/workout_template_retriever.py` owns action-library style training templates and evidence extraction.
- `apps/backend/src/marathon_qa_assistant/services/daily_schedule_generator.py` already protects core fields with `field_sources`, `needs_evidence`, `action_match`, `protocol_check`, `kb_fallback`, and `risk_gate`.
- `docs/quality/shared_delivery_contract.md` requires no fake source path, no fake page, no fake citation id, and no LLM-generated core prescription fields.

## Target Knowledge Layers

1. `source_registry`
   - Raw document identity, source metadata, evidence tier, freshness, applicable runners, contraindications, and source path.
2. `document_index`
   - Chunking, metadata normalization, vector retrieval, lexical retrieval, query variants, and source-path inference.
3. `domain_graph`
   - Entities, relations, graph retrieval mode, graph evidence mapping, graph confidence, and relationship trace.
4. `prescription_library`
   - Protocol rules, action library templates, core field permissions, fallback policy, and `needs_evidence` blocking.
5. `evaluation`
   - Golden questions, retrieval metrics, source coverage, core field source violations, and RAG vs base model comparison.

## Future API Metadata Contract

The first implementation round should add these fields internally and expose them only where already natural:

- `evidence_domain`: one of `protocol`, `action_library`, `sports_science_reference`, `medical_safety`, `competitor_product_reference`, `user_profile_case`, `llm_general_knowledge`.
- `knowledge_layer`: one of `source_registry`, `document_index`, `domain_graph`, `prescription_library`, `evaluation`.
- `source_registry_id`: stable id for a source record.
- `source_quality`: object with `tier`, `freshness_status`, `applicability`, `contraindications`, and `notes`.
- `retrieval_mode`: one of `vector`, `lexical`, `graph_local`, `graph_global`, `graph_drift`, `action_library`, `protocol_rule`, `none`.
- `prescription_permission`: one of `can_write_core`, `explanation_only`, `blocked_needs_evidence`.
- `rag_eval`: object with `retrieval_hit`, `context_precision_proxy`, `source_coverage`, `faithfulness_proxy`, and `needs_review`.

These fields must be additive. Existing frontend code may ignore them.

## P0 Acceptance Criteria

- The repo has a new `services/kb/` package with typed models for source registry, evidence binding, prescription permissions, and retrieval modes.
- At least one test proves no source can be registered without a stable `source_registry_id`, `evidence_domain`, and `knowledge_layer`.
- Existing `tests/test_daily_schedule_generator.py` still passes.
- Existing `tests/test_openapi_contract.py` still passes.
- No frontend UI behavior changes.

## P1 Acceptance Criteria

- Existing vector hits can be converted into normalized evidence bindings with source registry metadata.
- Existing workout template cards can expose `source_registry_id`, `evidence_domain`, and `prescription_permission`.
- Core fields still reject `llm_general_knowledge`.
- `needs_evidence` remains visible when action-library evidence is missing.

## P2 Acceptance Criteria

- `GraphEngine` still imports and works through the old facade.
- New graph submodules can be tested independently.
- Graph evidence can be mapped into the same evidence binding format as vector hits.
- Graph evidence defaults to `explanation_only` unless it maps to protocol or action-library evidence.

## P3 Acceptance Criteria

- A minimal RAG evaluation harness exists and runs without external paid APIs.
- Golden questions cover at least 10 domains: training load, plan structure, periodization, injury recovery, rehabilitation, strength, mobility, injury prevention, evidence control, and RAG vs base model.
- The output distinguishes retrieval failure, answer unsupported, and core prescription missing evidence.

## P4 Acceptance Criteria

- Shared delivery contract is updated with the metadata fields above.
- Frontend owner is told not to display raw metadata in normal mode.
- Expert mode can later show these fields without needing another backend schema redesign.

## File Structure

### Create

- `apps/backend/src/marathon_qa_assistant/services/kb/__init__.py`
- `apps/backend/src/marathon_qa_assistant/services/kb/models.py`
- `apps/backend/src/marathon_qa_assistant/services/kb/source_registry.py`
- `apps/backend/src/marathon_qa_assistant/services/kb/evidence_binding.py`
- `apps/backend/src/marathon_qa_assistant/services/kb/prescription_permissions.py`
- `apps/backend/src/marathon_qa_assistant/services/kb/graph_store.py`
- `apps/backend/src/marathon_qa_assistant/services/kb/graph_registry.py`
- `apps/backend/src/marathon_qa_assistant/services/kb/graph_evidence.py`
- `apps/backend/src/marathon_qa_assistant/services/kb/evaluation.py`
- `tests/test_kb_source_registry.py`
- `tests/test_kb_evidence_binding.py`
- `tests/test_kb_graph_evidence.py`
- `tests/test_kb_evaluation.py`

### Modify

- `apps/backend/src/marathon_qa_assistant/services/vector_store.py`
- `apps/backend/src/marathon_qa_assistant/services/workout_template_retriever.py`
- `apps/backend/src/marathon_qa_assistant/services/daily_schedule_generator.py`
- `apps/backend/src/marathon_qa_assistant/services/knowledge_graph.py`
- `apps/backend/src/marathon_qa_assistant/services/training_plan_review.py`
- `docs/quality/shared_delivery_contract.md`
- `docs/architecture/backend_technical_overview.md`

### Do Not Modify In This Plan

- `apps/web/src/scripts/app.js`
- `apps/web/src/pages/index.astro`
- `apps/web/src/styles/*.css`
- `data/vector_kb/default/user_profile.json`
- `data/vector_kb/default/knowledge_graph.json`

---

## P0: Establish KB Data Contracts

### Task 1: Create KB model vocabulary

**Files:**
- Create: `apps/backend/src/marathon_qa_assistant/services/kb/__init__.py`
- Create: `apps/backend/src/marathon_qa_assistant/services/kb/models.py`
- Test: `tests/test_kb_source_registry.py`

- [ ] **Step 1: Write the failing test**

```python
from marathon_qa_assistant.services.kb.models import (
    EvidenceDomain,
    KnowledgeLayer,
    PrescriptionPermission,
    RetrievalMode,
    SourceQuality,
)


def test_kb_model_enums_are_stable_for_frontend_and_reviewers():
    assert EvidenceDomain.PROTOCOL.value == "protocol"
    assert EvidenceDomain.ACTION_LIBRARY.value == "action_library"
    assert EvidenceDomain.LLM_GENERAL_KNOWLEDGE.value == "llm_general_knowledge"
    assert KnowledgeLayer.SOURCE_REGISTRY.value == "source_registry"
    assert RetrievalMode.GRAPH_LOCAL.value == "graph_local"
    assert PrescriptionPermission.CAN_WRITE_CORE.value == "can_write_core"


def test_source_quality_has_required_review_fields():
    quality = SourceQuality(
        tier="protocol",
        freshness_status="current",
        applicability=["half_marathon", "advanced_runner"],
        contraindications=["acute_pain", "medical_red_flag"],
        notes="Internal HMP protocol source.",
    )

    assert quality.tier == "protocol"
    assert "acute_pain" in quality.contraindications
```

- [ ] **Step 2: Run the test and verify failure**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_source_registry.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'marathon_qa_assistant.services.kb'
```

- [ ] **Step 3: Implement the model module**

Create `apps/backend/src/marathon_qa_assistant/services/kb/__init__.py`:

```python
"""Layered knowledge-base primitives for auditable training prescriptions."""
```

Create `apps/backend/src/marathon_qa_assistant/services/kb/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EvidenceDomain(str, Enum):
    PROTOCOL = "protocol"
    ACTION_LIBRARY = "action_library"
    SPORTS_SCIENCE_REFERENCE = "sports_science_reference"
    MEDICAL_SAFETY = "medical_safety"
    COMPETITOR_PRODUCT_REFERENCE = "competitor_product_reference"
    USER_PROFILE_CASE = "user_profile_case"
    LLM_GENERAL_KNOWLEDGE = "llm_general_knowledge"


class KnowledgeLayer(str, Enum):
    SOURCE_REGISTRY = "source_registry"
    DOCUMENT_INDEX = "document_index"
    DOMAIN_GRAPH = "domain_graph"
    PRESCRIPTION_LIBRARY = "prescription_library"
    EVALUATION = "evaluation"


class RetrievalMode(str, Enum):
    VECTOR = "vector"
    LEXICAL = "lexical"
    GRAPH_LOCAL = "graph_local"
    GRAPH_GLOBAL = "graph_global"
    GRAPH_DRIFT = "graph_drift"
    ACTION_LIBRARY = "action_library"
    PROTOCOL_RULE = "protocol_rule"
    NONE = "none"


class PrescriptionPermission(str, Enum):
    CAN_WRITE_CORE = "can_write_core"
    EXPLANATION_ONLY = "explanation_only"
    BLOCKED_NEEDS_EVIDENCE = "blocked_needs_evidence"


@dataclass(frozen=True)
class SourceQuality:
    tier: str
    freshness_status: str
    applicability: List[str] = field(default_factory=list)
    contraindications: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class SourceRecord:
    source_registry_id: str
    title: str
    evidence_domain: EvidenceDomain
    knowledge_layer: KnowledgeLayer
    source_file: str = ""
    source_path: str = ""
    published_at: str = ""
    updated_at: str = ""
    quality: Optional[SourceQuality] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceBinding:
    evidence_id: str
    source_registry_id: str
    evidence_domain: EvidenceDomain
    knowledge_layer: KnowledgeLayer
    retrieval_mode: RetrievalMode
    prescription_permission: PrescriptionPermission
    source_file: str = ""
    source_path: str = ""
    page: Optional[int] = None
    chunk_id: str = ""
    snippet: str = ""
    score: float = 0.0
    trace: Dict[str, Any] = field(default_factory=dict)
```

- [ ] **Step 4: Run the test and verify pass**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_source_registry.py -q
```

Expected:

```text
2 passed
```

### Task 2: Add source registry normalization

**Files:**
- Create: `apps/backend/src/marathon_qa_assistant/services/kb/source_registry.py`
- Modify: `tests/test_kb_source_registry.py`

- [ ] **Step 1: Extend the failing test**

Append to `tests/test_kb_source_registry.py`:

```python
from marathon_qa_assistant.services.kb.models import SourceRecord
from marathon_qa_assistant.services.kb.source_registry import (
    build_source_registry_id,
    normalize_source_record,
)


def test_source_record_requires_stable_id_and_domain():
    record = normalize_source_record(
        {
            "title": "Half Marathon HMP Protocol",
            "source_file": "docs/product/half_marathon_hmp_protocol.md",
            "evidence_domain": "protocol",
            "knowledge_layer": "source_registry",
            "source_path": "docs/product/half_marathon_hmp_protocol.md",
        }
    )

    assert isinstance(record, SourceRecord)
    assert record.source_registry_id == build_source_registry_id("docs/product/half_marathon_hmp_protocol.md")
    assert record.evidence_domain.value == "protocol"
    assert record.knowledge_layer.value == "source_registry"


def test_source_record_rejects_fake_empty_source():
    try:
        normalize_source_record({"title": "No source", "evidence_domain": "protocol"})
    except ValueError as exc:
        assert "source_file or source_path is required" in str(exc)
    else:
        raise AssertionError("source without path should fail")
```

- [ ] **Step 2: Run the test and verify failure**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_source_registry.py -q
```

Expected:

```text
ImportError: cannot import name 'normalize_source_record'
```

- [ ] **Step 3: Implement source registry helpers**

Create `apps/backend/src/marathon_qa_assistant/services/kb/source_registry.py`:

```python
from __future__ import annotations

import hashlib
from typing import Any, Dict

from marathon_qa_assistant.services.kb.models import (
    EvidenceDomain,
    KnowledgeLayer,
    SourceQuality,
    SourceRecord,
)


def build_source_registry_id(source: str) -> str:
    normalized = " ".join(str(source or "").replace("\\", "/").split()).strip().lower()
    if not normalized:
        raise ValueError("source is required")
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]
    return f"src_{digest}"


def _quality_from_dict(value: Any) -> SourceQuality | None:
    if not isinstance(value, dict):
        return None
    return SourceQuality(
        tier=str(value.get("tier") or "unknown"),
        freshness_status=str(value.get("freshness_status") or "unknown"),
        applicability=[str(item) for item in value.get("applicability") or []],
        contraindications=[str(item) for item in value.get("contraindications") or []],
        notes=str(value.get("notes") or ""),
    )


def normalize_source_record(payload: Dict[str, Any]) -> SourceRecord:
    source_file = str(payload.get("source_file") or "").strip()
    source_path = str(payload.get("source_path") or "").strip()
    source_key = source_path or source_file
    if not source_key:
        raise ValueError("source_file or source_path is required")

    evidence_domain = EvidenceDomain(str(payload.get("evidence_domain") or EvidenceDomain.SPORTS_SCIENCE_REFERENCE.value))
    knowledge_layer = KnowledgeLayer(str(payload.get("knowledge_layer") or KnowledgeLayer.SOURCE_REGISTRY.value))
    source_registry_id = str(payload.get("source_registry_id") or build_source_registry_id(source_key))

    return SourceRecord(
        source_registry_id=source_registry_id,
        title=str(payload.get("title") or source_file or source_path),
        evidence_domain=evidence_domain,
        knowledge_layer=knowledge_layer,
        source_file=source_file,
        source_path=source_path,
        published_at=str(payload.get("published_at") or ""),
        updated_at=str(payload.get("updated_at") or ""),
        quality=_quality_from_dict(payload.get("quality")),
        metadata=dict(payload.get("metadata") or {}),
    )
```

- [ ] **Step 4: Run the test and verify pass**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_source_registry.py -q
```

Expected:

```text
4 passed
```

## P1: Normalize Evidence Bindings

### Task 3: Convert vector hits into evidence bindings

**Files:**
- Create: `apps/backend/src/marathon_qa_assistant/services/kb/evidence_binding.py`
- Create: `tests/test_kb_evidence_binding.py`

- [ ] **Step 1: Write the failing test**

```python
from marathon_qa_assistant.services.kb.evidence_binding import evidence_from_vector_hit


def test_vector_hit_becomes_explanation_only_evidence_binding():
    binding = evidence_from_vector_hit(
        {
            "source_file": "马拉松训练原理.pdf",
            "source_path": "C:/kb/马拉松训练原理.pdf",
            "page": 12,
            "chunk_id": "chunk_12",
            "text": "Long run should be placed with recovery around it.",
            "score": 0.82,
        },
        evidence_domain="sports_science_reference",
    )

    assert binding.evidence_id == "chunk_12"
    assert binding.evidence_domain.value == "sports_science_reference"
    assert binding.knowledge_layer.value == "document_index"
    assert binding.retrieval_mode.value == "vector"
    assert binding.prescription_permission.value == "explanation_only"
    assert binding.page == 12
    assert binding.score == 0.82
```

- [ ] **Step 2: Run the test and verify failure**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_evidence_binding.py -q
```

Expected:

```text
ModuleNotFoundError or ImportError for evidence_binding
```

- [ ] **Step 3: Implement evidence binding conversion**

Create `apps/backend/src/marathon_qa_assistant/services/kb/evidence_binding.py`:

```python
from __future__ import annotations

from typing import Any, Dict

from marathon_qa_assistant.services.kb.models import (
    EvidenceBinding,
    EvidenceDomain,
    KnowledgeLayer,
    PrescriptionPermission,
    RetrievalMode,
)
from marathon_qa_assistant.services.kb.source_registry import build_source_registry_id


def _domain(value: str) -> EvidenceDomain:
    try:
        return EvidenceDomain(value)
    except ValueError:
        return EvidenceDomain.SPORTS_SCIENCE_REFERENCE


def evidence_from_vector_hit(hit: Dict[str, Any], evidence_domain: str = "sports_science_reference") -> EvidenceBinding:
    source_path = str(hit.get("source_path") or "")
    source_file = str(hit.get("source_file") or "")
    source_key = source_path or source_file or "unknown_vector_source"
    chunk_id = str(hit.get("chunk_id") or "")
    evidence_id = chunk_id or build_source_registry_id(source_key)

    return EvidenceBinding(
        evidence_id=evidence_id,
        source_registry_id=build_source_registry_id(source_key),
        evidence_domain=_domain(evidence_domain),
        knowledge_layer=KnowledgeLayer.DOCUMENT_INDEX,
        retrieval_mode=RetrievalMode.VECTOR,
        prescription_permission=PrescriptionPermission.EXPLANATION_ONLY,
        source_file=source_file,
        source_path=source_path,
        page=hit.get("page"),
        chunk_id=chunk_id,
        snippet=str(hit.get("text") or hit.get("snippet") or ""),
        score=float(hit.get("score") or 0.0),
        trace={"source": "vector_hit"},
    )
```

- [ ] **Step 4: Run the test and verify pass**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_evidence_binding.py -q
```

Expected:

```text
1 passed
```

### Task 4: Add prescription permission guard

**Files:**
- Create: `apps/backend/src/marathon_qa_assistant/services/kb/prescription_permissions.py`
- Modify: `tests/test_kb_evidence_binding.py`

- [ ] **Step 1: Extend failing tests**

Append:

```python
from marathon_qa_assistant.services.kb.models import EvidenceDomain
from marathon_qa_assistant.services.kb.prescription_permissions import permission_for_domain


def test_only_protocol_and_action_library_can_write_core_fields():
    assert permission_for_domain(EvidenceDomain.PROTOCOL).value == "can_write_core"
    assert permission_for_domain(EvidenceDomain.ACTION_LIBRARY).value == "can_write_core"
    assert permission_for_domain(EvidenceDomain.SPORTS_SCIENCE_REFERENCE).value == "explanation_only"
    assert permission_for_domain(EvidenceDomain.LLM_GENERAL_KNOWLEDGE).value == "blocked_needs_evidence"
```

- [ ] **Step 2: Run and verify failure**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_evidence_binding.py -q
```

Expected:

```text
ImportError: cannot import name 'permission_for_domain'
```

- [ ] **Step 3: Implement permission guard**

Create `apps/backend/src/marathon_qa_assistant/services/kb/prescription_permissions.py`:

```python
from __future__ import annotations

from marathon_qa_assistant.services.kb.models import EvidenceDomain, PrescriptionPermission


CORE_ALLOWED_DOMAINS = {
    EvidenceDomain.PROTOCOL,
    EvidenceDomain.ACTION_LIBRARY,
}


def permission_for_domain(domain: EvidenceDomain) -> PrescriptionPermission:
    if domain in CORE_ALLOWED_DOMAINS:
        return PrescriptionPermission.CAN_WRITE_CORE
    if domain == EvidenceDomain.LLM_GENERAL_KNOWLEDGE:
        return PrescriptionPermission.BLOCKED_NEEDS_EVIDENCE
    return PrescriptionPermission.EXPLANATION_ONLY
```

- [ ] **Step 4: Run and verify pass**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_evidence_binding.py -q
```

Expected:

```text
2 passed
```

## P2: Connect Action Library Metadata

### Task 5: Add metadata to workout template cards without changing old fields

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/services/workout_template_retriever.py`
- Test: `tests/test_workout_template_retriever.py`

- [ ] **Step 1: Write a failing contract test**

Add a test near existing card tests:

```python
def test_workout_template_card_exposes_layered_kb_metadata():
    card = retrieve_workout_template("轻松跑")

    assert card["kb_metadata"]["knowledge_layer"] == "prescription_library"
    assert card["kb_metadata"]["evidence_domain"] == "action_library"
    assert card["kb_metadata"]["prescription_permission"] == "can_write_core"
    assert card["kb_metadata"]["retrieval_mode"] == "action_library"
    assert card["kb_metadata"]["source_registry_id"].startswith("src_")
```

- [ ] **Step 2: Run and verify failure**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_workout_template_retriever.py::test_workout_template_card_exposes_layered_kb_metadata -q
```

Expected:

```text
KeyError: 'kb_metadata'
```

- [ ] **Step 3: Implement additive metadata**

In `DailyWorkoutTemplateCard.to_dict()`, keep `asdict(self)` and add a `kb_metadata` object before returning:

```python
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        primary_source = self.source[0] if self.source else self.title
        data["kb_metadata"] = {
            "knowledge_layer": "prescription_library",
            "evidence_domain": "action_library" if self.evidence_tier == "action_library" else self.evidence_tier,
            "retrieval_mode": "action_library",
            "prescription_permission": "can_write_core" if self.evidence_tier == "action_library" else "blocked_needs_evidence",
            "source_registry_id": build_source_registry_id(primary_source),
        }
        return data
```

Also import:

```python
from marathon_qa_assistant.services.kb.source_registry import build_source_registry_id
```

- [ ] **Step 4: Run targeted tests**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_workout_template_retriever.py -q
```

Expected:

```text
all tests pass
```

## P3: Keep Daily Schedule Core Fields Guarded

### Task 6: Carry KB metadata into daily cards

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/services/daily_schedule_generator.py`
- Test: `tests/test_daily_schedule_generator.py`

- [ ] **Step 1: Add a failing daily card test**

Add:

```python
def test_daily_card_preserves_layered_kb_metadata_for_action_library():
    structured_plan = {
        "week_plans": [
            {
                "week_index": 1,
                "days": [
                    {
                        "day_index": 1,
                        "weekday": "周二",
                        "training_type": "轻松跑",
                        "workout_type": "easy_run",
                        "main_set": "40分钟轻松跑",
                    }
                ],
            }
        ]
    }

    calendar = generate_daily_schedule(structured_plan, enable_kb_fallback=False)
    card = calendar.daily_schedule_cards[0].to_dict()

    assert card["kb_metadata"]["knowledge_layer"] in {"prescription_library", "source_registry"}
    assert card["kb_metadata"]["prescription_permission"] in {"can_write_core", "blocked_needs_evidence"}
    assert card["field_sources"]["main_set"]["source_type"] != "llm_general_knowledge"
```

- [ ] **Step 2: Run and verify failure**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_daily_schedule_generator.py::test_daily_card_preserves_layered_kb_metadata_for_action_library -q
```

Expected:

```text
KeyError: 'kb_metadata'
```

- [ ] **Step 3: Extend `DailyScheduleItem`**

Add field:

```python
kb_metadata: Dict[str, Any] = field(default_factory=dict)
```

When building an item from an action-library card, set:

```python
kb_metadata=card.get("kb_metadata") or {
    "knowledge_layer": "prescription_library",
    "evidence_domain": evidence_tier,
    "retrieval_mode": "action_library" if evidence_tier == "action_library" else "none",
    "prescription_permission": "can_write_core" if evidence_tier == "action_library" else "blocked_needs_evidence",
}
```

For `needs_evidence` cards, set:

```python
kb_metadata={
    "knowledge_layer": "prescription_library",
    "evidence_domain": "llm_general_knowledge" if evidence_tier == "llm_general_knowledge" else "sports_science_reference",
    "retrieval_mode": "none",
    "prescription_permission": "blocked_needs_evidence",
}
```

- [ ] **Step 4: Run daily schedule tests**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_daily_schedule_generator.py -q
```

Expected:

```text
all tests pass
```

## P4: Split Graph Evidence Mapping

### Task 7: Add graph evidence mapper module

**Files:**
- Create: `apps/backend/src/marathon_qa_assistant/services/kb/graph_evidence.py`
- Create: `tests/test_kb_graph_evidence.py`
- Modify later: `apps/backend/src/marathon_qa_assistant/services/knowledge_graph.py`

- [ ] **Step 1: Write failing test**

```python
from marathon_qa_assistant.services.kb.graph_evidence import graph_edge_to_evidence_binding


def test_graph_edge_defaults_to_explanation_only():
    binding = graph_edge_to_evidence_binding(
        {
            "source_file": "training-principles.pdf",
            "source_path": "C:/kb/training-principles.pdf",
            "chunk_id": "g-1",
            "source": "long_run",
            "target": "endurance",
            "relation": "targets",
            "confidence": 0.76,
            "snippet": "Long runs target endurance adaptations.",
        }
    )

    assert binding.knowledge_layer.value == "domain_graph"
    assert binding.retrieval_mode.value == "graph_local"
    assert binding.prescription_permission.value == "explanation_only"
    assert binding.trace["relation"] == "targets"
```

- [ ] **Step 2: Run and verify failure**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_graph_evidence.py -q
```

Expected:

```text
ModuleNotFoundError or ImportError for graph_evidence
```

- [ ] **Step 3: Implement graph evidence mapper**

Create `apps/backend/src/marathon_qa_assistant/services/kb/graph_evidence.py`:

```python
from __future__ import annotations

from typing import Any, Dict

from marathon_qa_assistant.services.kb.models import (
    EvidenceBinding,
    EvidenceDomain,
    KnowledgeLayer,
    PrescriptionPermission,
    RetrievalMode,
)
from marathon_qa_assistant.services.kb.source_registry import build_source_registry_id


def graph_edge_to_evidence_binding(edge: Dict[str, Any]) -> EvidenceBinding:
    source_path = str(edge.get("source_path") or "")
    source_file = str(edge.get("source_file") or "")
    source_key = source_path or source_file or str(edge.get("source") or "graph_edge")
    chunk_id = str(edge.get("chunk_id") or "")
    relation = str(edge.get("relation") or "")

    return EvidenceBinding(
        evidence_id=chunk_id or build_source_registry_id(f"{source_key}:{relation}"),
        source_registry_id=build_source_registry_id(source_key),
        evidence_domain=EvidenceDomain.SPORTS_SCIENCE_REFERENCE,
        knowledge_layer=KnowledgeLayer.DOMAIN_GRAPH,
        retrieval_mode=RetrievalMode.GRAPH_LOCAL,
        prescription_permission=PrescriptionPermission.EXPLANATION_ONLY,
        source_file=source_file,
        source_path=source_path,
        page=edge.get("page"),
        chunk_id=chunk_id,
        snippet=str(edge.get("snippet") or edge.get("text") or ""),
        score=float(edge.get("confidence") or 0.0),
        trace={
            "source": edge.get("source"),
            "target": edge.get("target"),
            "relation": relation,
            "graph_confidence": edge.get("confidence"),
        },
    )
```

- [ ] **Step 4: Run graph evidence test**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_graph_evidence.py -q
```

Expected:

```text
1 passed
```

### Task 8: Preserve old `GraphEngine` facade while delegating evidence mapping

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/services/knowledge_graph.py`
- Test: existing graph and retrieval tests

- [ ] **Step 1: Add characterization test if one exists for `map_edge_to_evidence`**

If `tests/test_vector_store_query_fusion.py` or a related test already covers graph evidence, extend it to assert:

```python
assert mapped["knowledge_layer"] == "domain_graph"
assert mapped["retrieval_mode"] in {"graph_local", "graph_global", "graph_drift"}
assert mapped["prescription_permission"] == "explanation_only"
```

If no direct test exists, add `tests/test_kb_graph_evidence.py` coverage for the public `GraphEngine` method:

```python
def test_graph_engine_map_edge_keeps_layered_metadata():
    engine = GraphEngine.__new__(GraphEngine)
    mapped = engine.map_edge_to_evidence(
        {
            "source_file": "source.pdf",
            "chunk_id": "edge-1",
            "source": "tempo",
            "target": "lactate_threshold",
            "relation": "targets",
            "confidence": 0.7,
        }
    )

    assert mapped["knowledge_layer"] == "domain_graph"
    assert mapped["prescription_permission"] == "explanation_only"
```

- [ ] **Step 2: Run and verify failure**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_graph_evidence.py -q
```

Expected:

```text
AssertionError or missing metadata fields
```

- [ ] **Step 3: Delegate mapping in `knowledge_graph.py`**

Import:

```python
from marathon_qa_assistant.services.kb.graph_evidence import graph_edge_to_evidence_binding
```

Inside the existing edge mapping method, convert the dataclass to a dict and keep old keys:

```python
binding = graph_edge_to_evidence_binding(edge)
mapped = {
    "evidence_id": binding.evidence_id,
    "kind": "graph",
    "chunk_id": binding.chunk_id,
    "source_file": binding.source_file,
    "source_path": binding.source_path,
    "page": binding.page,
    "snippet": binding.snippet,
    "hybrid_score": binding.score,
    "knowledge_layer": binding.knowledge_layer.value,
    "evidence_domain": binding.evidence_domain.value,
    "retrieval_mode": binding.retrieval_mode.value,
    "prescription_permission": binding.prescription_permission.value,
    "source_registry_id": binding.source_registry_id,
    "trace": binding.trace,
}
```

- [ ] **Step 4: Run graph and retrieval tests**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_vector_store_query_fusion.py tests/test_kb_graph_evidence.py -q
```

Expected:

```text
all tests pass
```

## P5: Add Evaluation Layer

### Task 9: Build minimal KB evaluation contracts

**Files:**
- Create: `apps/backend/src/marathon_qa_assistant/services/kb/evaluation.py`
- Create: `tests/test_kb_evaluation.py`

- [ ] **Step 1: Write failing tests**

```python
from marathon_qa_assistant.services.kb.evaluation import evaluate_evidence_answer


def test_evaluation_marks_missing_context():
    result = evaluate_evidence_answer(
        question="如何安排疼痛后的训练？",
        answer="继续高强度间歇。",
        evidence_bindings=[],
        core_fields={"main_set": "继续高强度间歇"},
    )

    assert result["retrieval_hit"] is False
    assert result["source_coverage"] == 0.0
    assert result["needs_review"] is True
    assert result["core_prescription_supported"] is False


def test_evaluation_accepts_action_library_core_field():
    result = evaluate_evidence_answer(
        question="今天轻松跑怎么安排？",
        answer="40分钟轻松跑。",
        evidence_bindings=[
            {
                "evidence_domain": "action_library",
                "prescription_permission": "can_write_core",
                "snippet": "轻松跑 30-60 分钟。",
            }
        ],
        core_fields={"main_set": "40分钟轻松跑"},
    )

    assert result["retrieval_hit"] is True
    assert result["core_prescription_supported"] is True
    assert result["needs_review"] is False
```

- [ ] **Step 2: Run and verify failure**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_evaluation.py -q
```

Expected:

```text
ModuleNotFoundError or ImportError for evaluation
```

- [ ] **Step 3: Implement minimal local evaluation**

Create `apps/backend/src/marathon_qa_assistant/services/kb/evaluation.py`:

```python
from __future__ import annotations

from typing import Any, Dict, List


CORE_ALLOWED_PERMISSIONS = {"can_write_core"}


def evaluate_evidence_answer(
    question: str,
    answer: str,
    evidence_bindings: List[Dict[str, Any]],
    core_fields: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    core_fields = core_fields or {}
    retrieval_hit = len(evidence_bindings) > 0
    source_coverage = 0.0 if not retrieval_hit else min(1.0, len(evidence_bindings) / 3.0)
    core_prescription_supported = not core_fields or any(
        str(binding.get("prescription_permission") or "") in CORE_ALLOWED_PERMISSIONS
        for binding in evidence_bindings
    )

    answer_lower = str(answer or "").lower()
    faithfulness_proxy = 1.0 if retrieval_hit and any(
        str(binding.get("snippet") or "").lower()[:20] in answer_lower
        for binding in evidence_bindings
        if str(binding.get("snippet") or "").strip()
    ) else 0.0

    return {
        "question": question,
        "retrieval_hit": retrieval_hit,
        "context_precision_proxy": source_coverage,
        "source_coverage": source_coverage,
        "faithfulness_proxy": faithfulness_proxy,
        "core_prescription_supported": core_prescription_supported,
        "needs_review": (not retrieval_hit) or (not core_prescription_supported),
    }
```

- [ ] **Step 4: Run evaluation tests**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_evaluation.py -q
```

Expected:

```text
2 passed
```

## P6: Feed Evaluation Into Plan Review

### Task 10: Add KB metadata summary to training plan review

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/services/training_plan_review.py`
- Modify: `tests/test_training_plan_review.py`

- [ ] **Step 1: Add failing assertions**

In `test_training_plan_review_covers_commercial_quality_dimensions`, add:

```python
    assert "layered_kb" in review["dimensions"]
    assert review["dimensions"]["layered_kb"]["status"] in {"traceable", "partial_traceable", "gap"}
    assert "prescription_permission_counts" in review["dimensions"]["layered_kb"]
```

- [ ] **Step 2: Run and verify failure**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_training_plan_review.py::test_training_plan_review_covers_commercial_quality_dimensions -q
```

Expected:

```text
KeyError or AssertionError for layered_kb
```

- [ ] **Step 3: Implement review summarizer**

Inside `build_training_plan_review`, count daily card `kb_metadata`:

```python
permission_counts = {}
layer_counts = {}
for card in daily_schedule_cards or []:
    metadata = card.get("kb_metadata") or {}
    permission = str(metadata.get("prescription_permission") or "unknown")
    layer = str(metadata.get("knowledge_layer") or "unknown")
    permission_counts[permission] = permission_counts.get(permission, 0) + 1
    layer_counts[layer] = layer_counts.get(layer, 0) + 1

dimensions["layered_kb"] = {
    "status": "traceable" if permission_counts.get("can_write_core") else "gap",
    "knowledge_layer_counts": layer_counts,
    "prescription_permission_counts": permission_counts,
    "normal_user_copy": "核心训练处方必须来自协议或动作库；普通知识库和模型常识只用于解释。",
}
```

- [ ] **Step 4: Run plan review tests**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_training_plan_review.py -q
```

Expected:

```text
all tests pass
```

## P7: Add Golden Question Set

### Task 11: Create local golden questions for KB evaluation

**Files:**
- Create: `tests/fixtures/kb_golden_questions.json`
- Modify: `tests/test_kb_evaluation.py`

- [ ] **Step 1: Add fixture**

Create `tests/fixtures/kb_golden_questions.json`:

```json
[
  {"id": "kb-load-001", "domain": "training_load", "question": "这个计划的训练负荷为什么只能叫计划代理负荷？"},
  {"id": "kb-structure-001", "domain": "plan_structure", "question": "半马训练为什么不能每周安排三次高强度？"},
  {"id": "kb-period-001", "domain": "periodization", "question": "16周半马计划为什么要分基础期、建设期、专项期和减量期？"},
  {"id": "kb-injury-001", "domain": "injury_recovery", "question": "膝痛后为什么不能直接安排间歇跑？"},
  {"id": "kb-rehab-001", "domain": "rehabilitation", "question": "康复训练和普通恢复跑有什么区别？"},
  {"id": "kb-strength-001", "domain": "strength_conditioning", "question": "半马计划中力量训练应该解决什么问题？"},
  {"id": "kb-mobility-001", "domain": "mobility_recovery", "question": "为什么冷身和拉伸不能只写一句放松？"},
  {"id": "kb-prevent-001", "domain": "injury_prevention", "question": "哪些信号提示训练计划需要降级？"},
  {"id": "kb-evidence-001", "domain": "evidence_control", "question": "无本地证据时系统应该如何回答？"},
  {"id": "kb-rag-001", "domain": "rag_vs_base_model", "question": "如何证明RAG计划比裸模型计划更可复查？"}
]
```

- [ ] **Step 2: Add fixture test**

Append:

```python
import json
from pathlib import Path


def test_kb_golden_questions_cover_required_domains():
    questions = json.loads(Path("tests/fixtures/kb_golden_questions.json").read_text(encoding="utf-8"))
    domains = {item["domain"] for item in questions}

    assert len(questions) >= 10
    assert {
        "training_load",
        "plan_structure",
        "periodization",
        "injury_recovery",
        "rehabilitation",
        "strength_conditioning",
        "mobility_recovery",
        "injury_prevention",
        "evidence_control",
        "rag_vs_base_model",
    }.issubset(domains)
```

- [ ] **Step 3: Run fixture test**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_evaluation.py::test_kb_golden_questions_cover_required_domains -q
```

Expected:

```text
1 passed
```

## P8: Add KB Health Check

### Task 12: Build source and evidence health checks

**Files:**
- Create: `apps/backend/src/marathon_qa_assistant/services/kb/health.py`
- Create: `tests/test_kb_health.py`

- [ ] **Step 1: Write failing tests**

```python
from marathon_qa_assistant.services.kb.health import check_evidence_bindings_health


def test_health_check_flags_fake_sources():
    result = check_evidence_bindings_health(
        [
            {"source_path": "", "source_file": "", "page": None, "evidence_domain": "protocol"},
            {"source_path": "C:/kb/source.pdf", "source_file": "source.pdf", "page": 3, "evidence_domain": "action_library"},
        ]
    )

    assert result["total"] == 2
    assert result["missing_source_count"] == 1
    assert result["missing_page_count"] == 1
    assert result["status"] == "needs_review"
```

- [ ] **Step 2: Run and verify failure**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_health.py -q
```

Expected:

```text
ModuleNotFoundError or ImportError for health
```

- [ ] **Step 3: Implement health check**

Create `apps/backend/src/marathon_qa_assistant/services/kb/health.py`:

```python
from __future__ import annotations

from typing import Any, Dict, List


def check_evidence_bindings_health(bindings: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(bindings)
    missing_source_count = sum(
        1 for item in bindings if not (item.get("source_path") or item.get("source_file"))
    )
    missing_page_count = sum(1 for item in bindings if item.get("page") in {None, "", 0})
    status = "ok" if total and missing_source_count == 0 else "needs_review"
    if total == 0:
        status = "empty"
    return {
        "total": total,
        "missing_source_count": missing_source_count,
        "missing_page_count": missing_page_count,
        "status": status,
    }
```

- [ ] **Step 4: Run health tests**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_health.py -q
```

Expected:

```text
1 passed
```

## P9: Documentation and Shared Contract

### Task 13: Update backend technical overview

**Files:**
- Modify: `docs/architecture/backend_technical_overview.md`

- [ ] **Step 1: Add section after current Graph Retrieval section**

Add:

```markdown
### Layered KB and GraphRAG Evidence Kernel

The knowledge base is split into five layers: source registry, document index, domain graph, prescription library, and evaluation. Vector and graph retrieval can support explanations and evidence discovery, but core prescription fields are only writable by protocol or action-library sources. General LLM knowledge remains allowed for ordinary explanations when local evidence is missing, but it cannot write `main_set`, `intensity`, `duration`, `progression`, or `risk_downgrade`.
```

- [ ] **Step 2: Verify terminology**

Run:

```powershell
rg -n "Layered KB|GraphRAG Evidence Kernel|llm_general_knowledge|can_write_core" docs/architecture/backend_technical_overview.md
```

Expected:

```text
matching lines are printed
```

### Task 14: Update shared delivery contract

**Files:**
- Modify: `docs/quality/shared_delivery_contract.md`

- [ ] **Step 1: Add section under Evidence / LLM General Knowledge**

Add:

```markdown
### Layered KB / GraphRAG Contract

- Backend owner may add additive metadata fields: `knowledge_layer`, `evidence_domain`, `source_registry_id`, `source_quality`, `retrieval_mode`, `prescription_permission`, and `rag_eval`.
- Frontend owner must not expose raw metadata in normal mode. Normal mode may show short labels such as "动作库", "协议依据", "知识库解释", or "模型常识说明".
- `prescription_permission=can_write_core` is required before evidence can populate core prescription fields.
- `llm_general_knowledge` and graph-only evidence default to explanation-only or needs-evidence status.
```

- [ ] **Step 2: Verify shared contract lines**

Run:

```powershell
rg -n "Layered KB|prescription_permission|source_registry_id|rag_eval" docs/quality/shared_delivery_contract.md
```

Expected:

```text
matching lines are printed
```

## P10: Cross-Test Matrix

### Task 15: Run targeted backend test matrix

**Files:**
- No file change.

- [ ] **Step 1: Run new KB tests**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest `
  tests/test_kb_source_registry.py `
  tests/test_kb_evidence_binding.py `
  tests/test_kb_graph_evidence.py `
  tests/test_kb_evaluation.py `
  tests/test_kb_health.py -q
```

Expected:

```text
all tests pass
```

- [ ] **Step 2: Run protected existing tests**

Run:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest `
  tests/test_daily_schedule_generator.py `
  tests/test_workout_template_retriever.py `
  tests/test_training_plan_review.py `
  tests/test_openapi_contract.py `
  tests/test_api_app.py -q
```

Expected:

```text
all tests pass
```

- [ ] **Step 3: Run repository hygiene checks**

Run:

```powershell
git diff --check
python tools/dev/check_repo.py --scope hygiene
git status --short --branch
```

Expected:

```text
git diff --check exits 0
check_repo exits 0 or only known warnings
git status shows only intended files for this version unit
```

### Task 16: Version boundary checklist

**Files:**
- No file change unless a review document is required.

- [ ] **Step 1: Confirm intended file list**

Allowed for this version unit:

```text
apps/backend/src/marathon_qa_assistant/services/kb/*.py
apps/backend/src/marathon_qa_assistant/services/vector_store.py
apps/backend/src/marathon_qa_assistant/services/workout_template_retriever.py
apps/backend/src/marathon_qa_assistant/services/daily_schedule_generator.py
apps/backend/src/marathon_qa_assistant/services/knowledge_graph.py
apps/backend/src/marathon_qa_assistant/services/training_plan_review.py
tests/test_kb_*.py
tests/test_daily_schedule_generator.py
tests/test_workout_template_retriever.py
tests/test_training_plan_review.py
docs/architecture/backend_technical_overview.md
docs/quality/shared_delivery_contract.md
docs/superpowers/plans/2026-05-22-layered-kb-graphrag-refactor-todo.md
```

- [ ] **Step 2: Confirm excluded files are not staged**

Do not stage:

```text
data/vector_kb/default/user_profile.json
data/vector_kb/default/knowledge_graph.json
apps/web/dist/
.pytest_cache/
tests/__pycache__/
apps/**/__pycache__/
```

- [ ] **Step 3: Use explicit staging only**

Run only after verification passes:

```powershell
git add `
  apps/backend/src/marathon_qa_assistant/services/kb `
  apps/backend/src/marathon_qa_assistant/services/vector_store.py `
  apps/backend/src/marathon_qa_assistant/services/workout_template_retriever.py `
  apps/backend/src/marathon_qa_assistant/services/daily_schedule_generator.py `
  apps/backend/src/marathon_qa_assistant/services/knowledge_graph.py `
  apps/backend/src/marathon_qa_assistant/services/training_plan_review.py `
  tests/test_kb_source_registry.py `
  tests/test_kb_evidence_binding.py `
  tests/test_kb_graph_evidence.py `
  tests/test_kb_evaluation.py `
  tests/test_kb_health.py `
  tests/test_daily_schedule_generator.py `
  tests/test_workout_template_retriever.py `
  tests/test_training_plan_review.py `
  docs/architecture/backend_technical_overview.md `
  docs/quality/shared_delivery_contract.md `
  docs/superpowers/plans/2026-05-22-layered-kb-graphrag-refactor-todo.md
```

Expected:

```text
Only intended files are staged.
```

## Frontend Owner Notification

- Backend may add `kb_metadata` to daily cards and `layered_kb` to `training_plan_review.dimensions`.
- Frontend normal mode should not show raw values like `source_registry_id`, `prescription_permission`, or `retrieval_mode`.
- Frontend can later map:
  - `protocol` to `协议依据`
  - `action_library` to `动作库`
  - `sports_science_reference` to `知识库解释`
  - `medical_safety` to `安全边界`
  - `llm_general_knowledge` to `模型常识说明`
- If `prescription_permission` is not `can_write_core`, frontend must not display "权威处方已验证".
- This plan does not require frontend code changes in the first implementation round.

## Review Checklist

- [ ] No core prescription field is written from `llm_general_knowledge`.
- [ ] Graph-only evidence is explanation-only unless explicitly mapped to protocol or action library.
- [ ] Source registry ids are stable across runs.
- [ ] Source path and page are never fabricated.
- [ ] `needs_evidence` remains visible for missing action-library matches.
- [ ] RAG evaluation distinguishes retrieval miss from unsupported answer.
- [ ] Existing API response fields remain backward compatible.
- [ ] Existing frontend contract tests are not weakened.
- [ ] Dirty worktree is handled with explicit staging only.
- [ ] Shared delivery contract is updated before implementation is claimed complete.

## Self-Review

- Spec coverage: The plan covers source registry, document index metadata, domain graph evidence, prescription permission, evaluation, plan review, shared contract, and verification.
- Placeholder scan: No step depends on an unspecified placeholder or future invention.
- Type consistency: `EvidenceDomain`, `KnowledgeLayer`, `RetrievalMode`, `PrescriptionPermission`, `SourceRecord`, `SourceQuality`, and `EvidenceBinding` are defined before use.
- Scope check: The plan intentionally excludes frontend UI refactor and keeps the first implementation round backend-only.
