# NotebookLM 式 RAG 知识源治理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把当前“所有 chunk 混搜”的 RAG 升级为 NotebookLM 式知识源透明治理：先判断 source 是否真的有正文，再做 source-aware 检索、证据链展示和前端可视化。

**Architecture:** 新增后端 `source_inventory` 服务作为知识源事实层，统一从 `data/vector_kb/v2/chunks.jsonl` 聚合 source 状态；检索层读取 source 状态，把 `registry_only` 降级为线索，把 `ready` 正文证据优先进入报告；前端智能文档页展示知识源健康概览、证据类型和命中 source 状态。三个并行 agent 分别负责：知识源审计/API、检索证据治理、前端 NotebookLM 体验。

**Tech Stack:** Python 3、FastAPI、Pydantic、FAISS/LangChain、vanilla JavaScript、Astro、pytest。

---

## 当前已确认事实

- 当前运行时 v2 索引：`data/vector_kb/v2/chunks.jsonl`。
- 当前 v2 chunk 数：`14306`。
- 当前 source 数：`770`。
- `731` 个 source 只有 `registry_preview` 或 `expert_source_registry`，没有正文 chunk。
- 只有 `39` 个 source 有 `document_paragraph` 或 `pdf_paragraph_candidate` 正文候选。
- FAISS 本身可加载，`index.ntotal == chunks.jsonl 行数 == 14306`，所以根因不是 FAISS 全坏，而是 source 治理和检索策略不透明。

---

## 并行执行分工

### Agent A：知识源审计与 API

负责 Task 1、Task 2。

目标：建立 source inventory，回答“哪些文档真的能问，哪些只是登记线索”。

### Agent B：检索与证据链治理

负责 Task 3、Task 4。

目标：检索时正文优先，registry-only 降级，不再把登记卡当正式证据。

### Agent C：前端 NotebookLM 式体验

负责 Task 5、Task 6。

目标：前端展示知识源状态、证据等级、选源问答入口和透明失败提示。

---

## File Structure

### Create

- `apps/backend/src/marathon_qa_assistant/services/kb/source_inventory.py`  
  从 chunks 聚合 source 状态，输出 `ready / registry_only / missing_text / needs_rebuild`。

- `tests/test_source_inventory.py`  
  覆盖 source 状态分类、统计汇总和 registry-only 降级语义。

- `tests/test_source_aware_retrieval.py`  
  覆盖 source-aware ranking：正文证据优先，registry-only 只作为线索。

- `docs/rag_governance_todo.md`  
  面向人看的治理 todo，总结 source 审计、重建、检索、前端验收项。

### Modify

- `apps/backend/src/marathon_qa_assistant/apps/routers/reference.py`  
  增加 `GET /knowledge/sources` 和 `GET /knowledge/sources/summary`。

- `apps/backend/src/marathon_qa_assistant/services/vector_store.py`  
  检索 hit 增加 source 状态字段，必要时提供 source filter 参数。

- `apps/backend/src/marathon_qa_assistant/nodes/profile_and_retrieval.py`  
  `build_ranked_evidence()` 使用 source 状态调整证据等级和排序。

- `apps/backend/src/marathon_qa_assistant/services/kb/evidence_chain.py`  
  canonical evidence item 增加 `source_status`、`has_full_text`、`evidence_kind`。

- `apps/backend/src/marathon_qa_assistant/apps/schemas.py`  
  增加知识源 summary response schema，保证 API contract 清晰。

- `apps/web/src/scripts/apiClient.js`  
  增加 `loadKnowledgeSourceSummary()` 和 `loadKnowledgeSources()`。

- `apps/web/src/scripts/intelligentDocs.js`  
  加载知识源 summary，展示 NotebookLM 式 source health 和证据等级。

- `apps/web/src/pages/intelligent-docs.astro`  
  增加知识源概览区域、筛选入口和说明文案。

- `tests/test_astro_frontend_contract.py`  
  增加前端契约测试：页面包含知识源健康区、JS 调用 knowledge sources API、证据区区分 source status。

---

# Agent A — 知识源审计与 API

## Task 1: Source Inventory Service

**Files:**
- Create: `apps/backend/src/marathon_qa_assistant/services/kb/source_inventory.py`
- Test: `tests/test_source_inventory.py`

- [ ] **Step 1: Write failing tests for source status classification**

Create `tests/test_source_inventory.py`:

```python
from marathon_qa_assistant.services.kb.source_inventory import (
    classify_source_status,
    summarize_sources_from_chunks,
)


def test_classify_source_ready_when_document_sections_exist():
    chunks = [
        {
            "source_registry_id": "src_strength",
            "source_file": "strength.md",
            "section": "document_paragraph",
            "text": "Strength training improves running economy in distance runners.",
        },
        {
            "source_registry_id": "src_strength",
            "source_file": "strength.md",
            "section": "expert_source_registry",
            "text": "source registry card",
        },
    ]

    result = classify_source_status(chunks)

    assert result["source_status"] == "ready"
    assert result["has_full_text"] is True
    assert result["chunk_count"] == 2
    assert result["body_chunk_count"] == 1
    assert result["registry_chunk_count"] == 1


def test_classify_source_registry_only_when_no_body_sections_exist():
    chunks = [
        {
            "source_registry_id": "src_safety_training_errors_2012",
            "source_file": "safety_training_errors_2012.metadata",
            "section": "registry_preview",
            "text": "Training Errors and Running Related Injuries: A Systematic Review.",
        }
    ]

    result = classify_source_status(chunks)

    assert result["source_status"] == "registry_only"
    assert result["has_full_text"] is False
    assert result["evidence_policy"] == "line_only"


def test_summarize_sources_counts_ready_and_registry_only_sources():
    chunks = [
        {
            "source_registry_id": "src_ready",
            "source_file": "ready.md",
            "domain_pack": "training_load",
            "section": "document_paragraph",
            "text": "body",
        },
        {
            "source_registry_id": "src_registry",
            "source_file": "registry.metadata",
            "domain_pack": "load_injury_safety",
            "section": "registry_preview",
            "text": "registry card",
        },
    ]

    summary = summarize_sources_from_chunks(chunks)

    assert summary["total_sources"] == 2
    assert summary["ready_sources"] == 1
    assert summary["registry_only_sources"] == 1
    assert summary["total_chunks"] == 2
    assert summary["sources"][0]["source_registry_id"] == "src_ready"
    assert summary["sources"][1]["source_registry_id"] == "src_registry"
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
PYTHONPATH=apps/backend/src python -m pytest tests/test_source_inventory.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'marathon_qa_assistant.services.kb.source_inventory'
```

- [ ] **Step 3: Implement source inventory service**

Create `apps/backend/src/marathon_qa_assistant/services/kb/source_inventory.py`:

```python
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List
import json

BODY_SECTIONS = {"document_paragraph", "pdf_paragraph_candidate"}
REGISTRY_SECTIONS = {"registry_preview", "expert_source_registry", "source_registry"}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _source_id(chunk: Dict[str, Any]) -> str:
    return _clean(
        chunk.get("source_registry_id")
        or chunk.get("source_file")
        or chunk.get("source")
        or "unknown_source"
    )


def classify_source_status(chunks: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(chunks or [])
    sections = Counter(_clean(row.get("section")) for row in rows)
    body_chunk_count = sum(count for section, count in sections.items() if section in BODY_SECTIONS)
    registry_chunk_count = sum(count for section, count in sections.items() if section in REGISTRY_SECTIONS)
    has_full_text = body_chunk_count > 0
    if has_full_text:
        source_status = "ready"
        evidence_policy = "answerable"
    elif rows:
        source_status = "registry_only"
        evidence_policy = "line_only"
    else:
        source_status = "missing_text"
        evidence_policy = "not_answerable"

    first = rows[0] if rows else {}
    return {
        "source_registry_id": _source_id(first),
        "source_file": _clean(first.get("source_file")),
        "source_label": _clean(first.get("source_label")) or _clean(first.get("source_file")) or _source_id(first),
        "domain_pack": _clean(first.get("domain_pack")),
        "source_status": source_status,
        "has_full_text": has_full_text,
        "evidence_policy": evidence_policy,
        "chunk_count": len(rows),
        "body_chunk_count": body_chunk_count,
        "registry_chunk_count": registry_chunk_count,
        "sections": dict(sorted(sections.items())),
        "sample_text": _clean(first.get("text"))[:240],
    }


def summarize_sources_from_chunks(chunks: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    total_chunks = 0
    for chunk in chunks or []:
        total_chunks += 1
        grouped[_source_id(chunk)].append(chunk)

    sources = [classify_source_status(rows) for _, rows in sorted(grouped.items())]
    status_counts = Counter(item["source_status"] for item in sources)
    domain_counts = Counter(item.get("domain_pack") or "unknown" for item in sources)
    return {
        "total_sources": len(sources),
        "total_chunks": total_chunks,
        "ready_sources": int(status_counts.get("ready", 0)),
        "registry_only_sources": int(status_counts.get("registry_only", 0)),
        "missing_text_sources": int(status_counts.get("missing_text", 0)),
        "status_counts": dict(status_counts),
        "domain_pack_counts": dict(domain_counts),
        "sources": sources,
    }


def load_chunks_jsonl(chunks_path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with Path(chunks_path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
PYTHONPATH=apps/backend/src python -m pytest tests/test_source_inventory.py -q
```

Expected:

```text
3 passed
```

- [ ] **Step 5: Commit Agent A Task 1**

```bash
git add apps/backend/src/marathon_qa_assistant/services/kb/source_inventory.py tests/test_source_inventory.py
git commit -m "feat: add knowledge source inventory service"
```

---

## Task 2: Knowledge Source API Contract

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/apps/schemas.py`
- Modify: `apps/backend/src/marathon_qa_assistant/apps/routers/reference.py`
- Test: `tests/test_source_inventory.py`

- [ ] **Step 1: Add failing API contract tests**

Append to `tests/test_source_inventory.py`:

```python
from fastapi.testclient import TestClient
from marathon_qa_assistant.apps.api_app import app


def test_knowledge_sources_summary_endpoint_returns_source_statuses():
    client = TestClient(app)

    response = client.get("/knowledge/sources/summary")

    assert response.status_code == 200
    payload = response.json()
    assert "total_sources" in payload
    assert "ready_sources" in payload
    assert "registry_only_sources" in payload
    assert "total_chunks" in payload
    assert payload["total_sources"] >= payload["ready_sources"]


def test_knowledge_sources_endpoint_returns_sources_array():
    client = TestClient(app)

    response = client.get("/knowledge/sources")

    assert response.status_code == 200
    payload = response.json()
    assert "sources" in payload
    assert isinstance(payload["sources"], list)
    if payload["sources"]:
        first = payload["sources"][0]
        assert "source_registry_id" in first
        assert "source_status" in first
        assert "has_full_text" in first
```

- [ ] **Step 2: Run tests and verify they fail with 404**

Run:

```bash
PYTHONPATH=apps/backend/src python -m pytest tests/test_source_inventory.py::test_knowledge_sources_summary_endpoint_returns_source_statuses tests/test_source_inventory.py::test_knowledge_sources_endpoint_returns_sources_array -q
```

Expected:

```text
FAILED ... assert 404 == 200
```

- [ ] **Step 3: Add response schemas**

Modify `apps/backend/src/marathon_qa_assistant/apps/schemas.py`:

```python
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
```

- [ ] **Step 4: Add endpoints to reference router**

Modify `apps/backend/src/marathon_qa_assistant/apps/routers/reference.py` imports:

```python
from marathon_qa_assistant.apps.schemas import (
    KnowledgeSourcesResponse,
    ZoneReference,
)
from marathon_qa_assistant.core.app_state import V2_VECTOR_DIR
from marathon_qa_assistant.services.kb.source_inventory import (
    load_chunks_jsonl,
    summarize_sources_from_chunks,
)
```

Add endpoints:

```python
@router.get("/knowledge/sources", response_model=KnowledgeSourcesResponse)
def list_knowledge_sources():
    chunks_path = V2_VECTOR_DIR / "chunks.jsonl"
    if not chunks_path.exists():
        return KnowledgeSourcesResponse()
    return summarize_sources_from_chunks(load_chunks_jsonl(chunks_path))


@router.get("/knowledge/sources/summary", response_model=KnowledgeSourcesResponse)
def get_knowledge_sources_summary():
    chunks_path = V2_VECTOR_DIR / "chunks.jsonl"
    if not chunks_path.exists():
        return KnowledgeSourcesResponse()
    summary = summarize_sources_from_chunks(load_chunks_jsonl(chunks_path))
    summary["sources"] = []
    return summary
```

- [ ] **Step 5: Run API tests**

Run:

```bash
PYTHONPATH=apps/backend/src python -m pytest tests/test_source_inventory.py -q
```

Expected:

```text
5 passed
```

- [ ] **Step 6: Commit Agent A Task 2**

```bash
git add apps/backend/src/marathon_qa_assistant/apps/schemas.py apps/backend/src/marathon_qa_assistant/apps/routers/reference.py tests/test_source_inventory.py
git commit -m "feat: expose knowledge source inventory api"
```

---

# Agent B — 检索与证据链治理

## Task 3: Source-Aware Evidence Ranking

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/nodes/profile_and_retrieval.py`
- Test: `tests/test_source_aware_retrieval.py`

- [ ] **Step 1: Write failing source-aware ranking tests**

Create `tests/test_source_aware_retrieval.py`:

```python
from marathon_qa_assistant.nodes.profile_and_retrieval import build_ranked_evidence


def test_ready_body_evidence_ranks_above_registry_only_for_same_score():
    vector_hits = [
        {
            "chunk_id": "registry-1",
            "source_file": "registry.metadata",
            "source_registry_id": "src_registry",
            "section": "registry_preview",
            "text": "Training Errors and Running Related Injuries: A Systematic Review.",
            "score": 0.8,
            "source_status": "registry_only",
            "has_full_text": False,
        },
        {
            "chunk_id": "body-1",
            "source_file": "body.md",
            "source_registry_id": "src_body",
            "section": "document_paragraph",
            "text": "Running injuries are associated with abrupt training load changes.",
            "score": 0.8,
            "source_status": "ready",
            "has_full_text": True,
        },
    ]

    ranked = build_ranked_evidence(
        query="running injury training load",
        vector_hits=vector_hits,
        graph_edges=[],
        entities=["running", "injury"],
        top_k=None,
    )

    assert ranked[0]["chunk_id"] == "body-1"
    assert ranked[0]["source_status"] == "ready"
    assert ranked[1]["display_mode"] == "legacy_explanation"
    assert ranked[1]["evidence_kind"] == "source_registry_line"


def test_registry_only_evidence_is_marked_not_core_writable():
    ranked = build_ranked_evidence(
        query="injury prevention",
        vector_hits=[
            {
                "chunk_id": "registry-1",
                "source_file": "registry.metadata",
                "source_registry_id": "src_registry",
                "section": "registry_preview",
                "text": "A paper exists about injury prevention.",
                "score": 0.9,
                "source_status": "registry_only",
                "has_full_text": False,
            }
        ],
        graph_edges=[],
        entities=["injury"],
        top_k=None,
    )

    assert ranked[0]["can_write_core"] is False
    assert ranked[0]["explanation_only"] is True
    assert ranked[0]["evidence_kind"] == "source_registry_line"
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
PYTHONPATH=apps/backend/src python -m pytest tests/test_source_aware_retrieval.py -q
```

Expected: fails because `source_status` / `evidence_kind` are not propagated or ranking does not prioritize body chunks.

- [ ] **Step 3: Implement source-aware fields and ranking bonus**

Modify vector evidence construction inside `build_ranked_evidence()` in `apps/backend/src/marathon_qa_assistant/nodes/profile_and_retrieval.py`.

In the `ev` dict, add:

```python
            "source_status": hit.get("source_status") or ("ready" if hit.get("section") in {"document_paragraph", "pdf_paragraph_candidate"} else "registry_only"),
            "has_full_text": bool(hit.get("has_full_text") if "has_full_text" in hit else hit.get("section") in {"document_paragraph", "pdf_paragraph_candidate"}),
            "evidence_kind": "body_chunk" if hit.get("section") in {"document_paragraph", "pdf_paragraph_candidate"} else "source_registry_line",
```

After `relevance_score, score_breakdown = _compute_relevance_score(...)`, add:

```python
        if ev.get("has_full_text"):
            relevance_score = min(1.0, relevance_score + 0.05)
            score_breakdown["source_status_bonus"] = 0.05
        else:
            relevance_score = max(0.0, relevance_score - 0.20)
            score_breakdown["registry_only_penalty"] = 0.20
            ev["display_mode"] = "legacy_explanation"
            ev["can_write_core"] = False
            ev["explanation_only"] = True
            ev["evidence_kind"] = "source_registry_line"
```

- [ ] **Step 4: Run source-aware tests**

Run:

```bash
PYTHONPATH=apps/backend/src python -m pytest tests/test_source_aware_retrieval.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit Agent B Task 3**

```bash
git add apps/backend/src/marathon_qa_assistant/nodes/profile_and_retrieval.py tests/test_source_aware_retrieval.py
git commit -m "feat: rank full text evidence above registry lines"
```

---

## Task 4: Evidence Chain Source Status Contract

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/services/kb/evidence_chain.py`
- Modify: `apps/web/src/scripts/evidenceDrawer.js`
- Test: `tests/test_source_aware_retrieval.py`
- Test: `tests/test_astro_frontend_contract.py`

- [ ] **Step 1: Add backend evidence chain test**

Append to `tests/test_source_aware_retrieval.py`:

```python
from marathon_qa_assistant.services.kb.evidence_chain import build_evidence_chain


def test_evidence_chain_preserves_source_status_fields():
    chain = build_evidence_chain(
        query="injury prevention",
        ranked_evidence=[
            {
                "chunk_id": "body-1",
                "source_file": "body.md",
                "source_registry_id": "src_body",
                "source_status": "ready",
                "has_full_text": True,
                "evidence_kind": "body_chunk",
                "text_span": "Running injuries are associated with training load.",
                "display_mode": "verified_source",
            }
        ],
        answer_source_mode="verified_source",
    )

    item = chain["items"][0]
    assert item["source_status"] == "ready"
    assert item["has_full_text"] is True
    assert item["evidence_kind"] == "body_chunk"
```

- [ ] **Step 2: Add frontend contract test**

Append to `tests/test_astro_frontend_contract.py`:

```python

def test_evidence_ui_reads_source_status_fields():
    content = _read_stripped(EVIDENCE_DRAWER_SCRIPT) + "\n" + _read_stripped(INTELLIGENT_DOCS_SCRIPT)
    assert "source_status" in content
    assert "has_full_text" in content
    assert "evidence_kind" in content
    assert "正文证据" in content
    assert "仅登记线索" in content
```

- [ ] **Step 3: Run tests and verify they fail**

Run:

```bash
PYTHONPATH=apps/backend/src python -m pytest tests/test_source_aware_retrieval.py::test_evidence_chain_preserves_source_status_fields tests/test_astro_frontend_contract.py::test_evidence_ui_reads_source_status_fields -q
```

Expected: fails because chain/UI do not preserve or read these fields.

- [ ] **Step 4: Preserve fields in evidence chain**

Modify `apps/backend/src/marathon_qa_assistant/services/kb/evidence_chain.py` where evidence item dict is built. Add:

```python
        "source_status": str(item.get("source_status") or "unknown"),
        "has_full_text": bool(item.get("has_full_text")),
        "evidence_kind": str(item.get("evidence_kind") or "unknown"),
```

- [ ] **Step 5: Render labels in evidence drawer**

Modify `apps/web/src/scripts/evidenceDrawer.js` normalization to read:

```js
const sourceStatus = String(raw.source_status || "unknown");
const hasFullText = Boolean(raw.has_full_text);
const evidenceKind = String(raw.evidence_kind || "unknown");
const sourceStatusLabel = hasFullText || sourceStatus === "ready" ? "正文证据" : "仅登记线索";
```

Include `sourceStatusLabel` in the rendered card metadata line.

- [ ] **Step 6: Run backend/frontend contract tests**

Run:

```bash
PYTHONPATH=apps/backend/src python -m pytest tests/test_source_aware_retrieval.py tests/test_astro_frontend_contract.py -q
```

Expected: all selected tests pass.

- [ ] **Step 7: Commit Agent B Task 4**

```bash
git add apps/backend/src/marathon_qa_assistant/services/kb/evidence_chain.py apps/web/src/scripts/evidenceDrawer.js tests/test_source_aware_retrieval.py tests/test_astro_frontend_contract.py
git commit -m "feat: expose source status in evidence chain"
```

---

# Agent C — NotebookLM 式前端体验

## Task 5: Knowledge Source Summary UI

**Files:**
- Modify: `apps/web/src/pages/intelligent-docs.astro`
- Modify: `apps/web/src/scripts/apiClient.js`
- Modify: `apps/web/src/scripts/intelligentDocs.js`
- Test: `tests/test_astro_frontend_contract.py`

- [ ] **Step 1: Add failing frontend contract test**

Append to `tests/test_astro_frontend_contract.py`:

```python

def test_intelligent_docs_has_knowledge_source_summary_panel():
    page = _read_stripped(root / "apps" / "web" / "src" / "pages" / "intelligent-docs.astro")
    script = _read_stripped(INTELLIGENT_DOCS_SCRIPT)
    api_client = _read_stripped(root / "apps" / "web" / "src" / "scripts" / "apiClient.js")

    assert "data-source-summary" in page
    assert "data-ready-source-count" in page
    assert "data-registry-only-source-count" in page
    assert "loadKnowledgeSourceSummary" in api_client
    assert "/knowledge/sources/summary" in api_client
    assert "renderSourceSummary" in script
    assert "正文可问" in script
    assert "仅登记线索" in script
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
python -m pytest tests/test_astro_frontend_contract.py::test_intelligent_docs_has_knowledge_source_summary_panel -q
```

Expected: fails because panel/API client functions are missing.

- [ ] **Step 3: Add API client functions**

Modify `apps/web/src/scripts/apiClient.js` inside `window.__apiClient` IIFE.

Add function:

```js
  async function loadKnowledgeSourceSummary() {
    return apiFetch("/knowledge/sources/summary", { timeoutMs: 15000 });
  }

  async function loadKnowledgeSources() {
    return apiFetch("/knowledge/sources", { timeoutMs: 30000 });
  }
```

Expose them:

```js
    explainApiError, requestQueryPayloadFromBase,
    loadKnowledgeSourceSummary, loadKnowledgeSources,
```

- [ ] **Step 4: Add source summary markup**

Modify `apps/web/src/pages/intelligent-docs.astro` near the answer/evidence section:

```html
<section class="docs-source-summary" data-source-summary>
  <div>
    <p class="eyebrow">知识源状态</p>
    <h2>NotebookLM 式知识源透明度</h2>
    <p>只把有正文 chunk 的来源作为正式问答证据；仅登记来源会作为线索标注。</p>
  </div>
  <dl class="docs-source-stats">
    <div>
      <dt>全部知识源</dt>
      <dd data-total-source-count>-</dd>
    </div>
    <div>
      <dt>正文可问</dt>
      <dd data-ready-source-count>-</dd>
    </div>
    <div>
      <dt>仅登记线索</dt>
      <dd data-registry-only-source-count>-</dd>
    </div>
  </dl>
</section>
```

- [ ] **Step 5: Render summary in intelligentDocs.js**

Modify `apps/web/src/scripts/intelligentDocs.js`:

```js
  const sourceSummary = document.querySelector("[data-source-summary]");
  const totalSourceCount = document.querySelector("[data-total-source-count]");
  const readySourceCount = document.querySelector("[data-ready-source-count]");
  const registryOnlySourceCount = document.querySelector("[data-registry-only-source-count]");

  function renderSourceSummary(payload) {
    if (!sourceSummary || !payload) return;
    sourceSummary.hidden = false;
    if (totalSourceCount) totalSourceCount.textContent = String(payload.total_sources ?? "-");
    if (readySourceCount) readySourceCount.textContent = `${payload.ready_sources ?? "-"} 正文可问`;
    if (registryOnlySourceCount) registryOnlySourceCount.textContent = `${payload.registry_only_sources ?? "-"} 仅登记线索`;
  }

  async function loadSourceSummary() {
    if (!window.__apiClient?.loadKnowledgeSourceSummary) return;
    try {
      renderSourceSummary(await window.__apiClient.loadKnowledgeSourceSummary());
    } catch {
      renderSourceSummary({ total_sources: "-", ready_sources: "-", registry_only_sources: "-" });
    }
  }
```

Call it after `refreshHealth();`:

```js
  loadSourceSummary();
```

- [ ] **Step 6: Run frontend contract test**

Run:

```bash
python -m pytest tests/test_astro_frontend_contract.py::test_intelligent_docs_has_knowledge_source_summary_panel -q
```

Expected:

```text
1 passed
```

- [ ] **Step 7: Commit Agent C Task 5**

```bash
git add apps/web/src/pages/intelligent-docs.astro apps/web/src/scripts/apiClient.js apps/web/src/scripts/intelligentDocs.js tests/test_astro_frontend_contract.py
git commit -m "feat: show knowledge source summary on docs page"
```

---

## Task 6: Intelligent Docs Evidence Status Rendering

**Files:**
- Modify: `apps/web/src/scripts/intelligentDocs.js`
- Test: `tests/test_astro_frontend_contract.py`

- [ ] **Step 1: Add failing evidence rendering contract test**

Append to `tests/test_astro_frontend_contract.py`:

```python

def test_intelligent_docs_distinguishes_body_evidence_from_registry_lines():
    content = _read_stripped(INTELLIGENT_DOCS_SCRIPT)
    assert "sourceStatusLabel" in content
    assert "正文证据" in content
    assert "仅登记线索" in content
    assert "source_status" in content
    assert "has_full_text" in content
    assert "evidence_kind" in content
    assert "source-status" in content
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
python -m pytest tests/test_astro_frontend_contract.py::test_intelligent_docs_distinguishes_body_evidence_from_registry_lines -q
```

Expected: fails until the fields and labels are rendered.

- [ ] **Step 3: Update evidence normalization**

Modify `normalizeEvidenceItem()` in `apps/web/src/scripts/intelligentDocs.js`:

```js
    const sourceStatus = String(raw.source_status || "unknown");
    const hasFullText = Boolean(raw.has_full_text || sourceStatus === "ready");
    const evidenceKind = String(raw.evidence_kind || "unknown");
    const sourceStatusLabel = hasFullText || evidenceKind === "body_chunk" ? "正文证据" : "仅登记线索";
```

Return these fields:

```js
    return { title, file, page: locator, score: status, quote, relevancePercent, sourceStatusLabel, sourceStatus, hasFullText, evidenceKind };
```

- [ ] **Step 4: Update evidence HTML**

In the `.docs-locator` line, include source status:

```js
<div class="docs-locator">
  <span class="source-status">${escapeHtml(item.sourceStatusLabel)}</span> · ${escapeHtml(item.page)} · ${escapeHtml(item.score)}${lowRelevanceHint ? ` · ${escapeHtml(lowRelevanceHint)}` : ""}
</div>
```

- [ ] **Step 5: Run frontend contract test**

Run:

```bash
python -m pytest tests/test_astro_frontend_contract.py::test_intelligent_docs_distinguishes_body_evidence_from_registry_lines -q
```

Expected:

```text
1 passed
```

- [ ] **Step 6: Commit Agent C Task 6**

```bash
git add apps/web/src/scripts/intelligentDocs.js tests/test_astro_frontend_contract.py
git commit -m "feat: label docs evidence by source status"
```

---

# Cross-Agent Integration

## Task 7: End-to-End Contract and Smoke Verification

**Files:**
- Modify: `tests/test_astro_frontend_contract.py`
- Modify: `tests/test_source_inventory.py`
- Modify: `tests/test_source_aware_retrieval.py`
- Create: `docs/rag_governance_todo.md`

- [ ] **Step 1: Add governance todo document**

Create `docs/rag_governance_todo.md`:

```markdown
# RAG 知识源治理 Todo

## 已定位问题

- v2 索引可加载，FAISS 数量与 chunks.jsonl 一致。
- 当前知识源数量大于真正正文入库数量。
- registry-only source 不能当作正式证据。
- 前端需要展示 source 状态，避免用户误以为所有来源都已读全文。

## 验收目标

- `/knowledge/sources/summary` 返回 total/ready/registry_only/missing_text 统计。
- `/knowledge/sources` 返回每个 source 的 source_status、has_full_text、chunk_count、sections。
- 检索结果中 ready 正文证据优先于 registry-only 线索。
- evidence_chain 保留 source_status、has_full_text、evidence_kind。
- 智能文档页展示全部知识源、正文可问、仅登记线索数量。
- 证据卡区分“正文证据”和“仅登记线索”。

## 后续重建队列

1. 导出 registry_only source 清单。
2. 检查每个 registry_only source 是否有本地 PDF/MD/TXT。
3. 对存在本地正文但未入库的 source 标记 needs_rebuild。
4. 对只有 URL 的 source 标记 missing_text。
5. 对 needs_rebuild source 重跑抽取、切块、embedding 和 FAISS 构建。
6. 重建后运行 source inventory regression。
```

- [ ] **Step 2: Run all targeted tests**

Run:

```bash
PYTHONPATH=apps/backend/src python -m pytest tests/test_source_inventory.py tests/test_source_aware_retrieval.py tests/test_astro_frontend_contract.py -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 3: Run backend compile verification**

Run:

```bash
PYTHONPATH=apps/backend/src python -m py_compile \
  apps/backend/src/marathon_qa_assistant/services/kb/source_inventory.py \
  apps/backend/src/marathon_qa_assistant/apps/schemas.py \
  apps/backend/src/marathon_qa_assistant/apps/routers/reference.py \
  apps/backend/src/marathon_qa_assistant/nodes/profile_and_retrieval.py \
  apps/backend/src/marathon_qa_assistant/services/kb/evidence_chain.py
```

Expected: command exits 0 with no output.

- [ ] **Step 4: Smoke API manually against running backend**

Run:

```bash
python - <<'PY'
import urllib.request, json
for path in ["/health", "/knowledge/sources/summary"]:
    with urllib.request.urlopen(f"http://127.0.0.1:8000{path}", timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
        print(path, response.status, {k: payload.get(k) for k in ["status", "total_sources", "ready_sources", "registry_only_sources", "total_chunks"]})
PY
```

Expected example:

```text
/health 200 {'status': 'healthy', ...}
/knowledge/sources/summary 200 {'total_sources': 770, 'ready_sources': 39, 'registry_only_sources': 731, 'total_chunks': 14306}
```

- [ ] **Step 5: Commit integration docs and tests**

```bash
git add docs/rag_governance_todo.md tests/test_source_inventory.py tests/test_source_aware_retrieval.py tests/test_astro_frontend_contract.py
git commit -m "test: cover notebooklm style rag governance"
```

---

# Acceptance Criteria

- [ ] 后端提供 `/knowledge/sources/summary`，能显示总 source 数、正文可问 source 数、registry-only source 数、chunk 总数。
- [ ] 后端提供 `/knowledge/sources`，能列出每个 source 的 `source_status`、`has_full_text`、`chunk_count`、`sections`。
- [ ] 检索结果里 `ready` 正文 chunk 优先于 `registry_only` 登记线索。
- [ ] `registry_only` 不能写核心处方字段，只能作为解释性线索。
- [ ] `evidence_chain.items[]` 保留 `source_status`、`has_full_text`、`evidence_kind`。
- [ ] 智能文档页显示知识源概览：全部知识源、正文可问、仅登记线索。
- [ ] 智能文档页证据卡显示“正文证据”或“仅登记线索”。
- [ ] 所有新增 targeted tests 通过。
- [ ] 不重新启用 legacy/default/user fallback；运行时仍只加载 v2。

---

# Risks and Non-Goals

## Risks

- 当前 `intelligentDocs.js` 是新增脚本且前端契约测试已经较多，修改时必须避免破坏现有 evidence canonical field 断言。
- `build_ranked_evidence()` 已经承担较多排序逻辑，source-aware 调整必须小步加入，不要顺手重写整个排序器。
- `/knowledge/sources` 直接读取 14306 行 JSONL，当前规模可接受；如果后续 source 过大，再加缓存。

## Non-Goals

- 本计划不直接下载外部 PDF。
- 本计划不直接重建 FAISS 索引。
- 本计划不引入新依赖。
- 本计划不恢复旧库 fallback。
- 本计划不把 registry-only 伪装成正文证据。

---

# Self-Review

## Spec coverage

- 知识源审计：Task 1、Task 2 覆盖。
- source-aware 检索：Task 3 覆盖。
- evidence chain 字段：Task 4 覆盖。
- NotebookLM 式前端 source summary：Task 5 覆盖。
- 证据状态展示：Task 6 覆盖。
- 文档化 todo 和验收：Task 7 覆盖。

## Placeholder scan

本文没有 `TBD`、`TODO` 占位实现、未定义函数引用或“类似上一步”的省略步骤。所有新增函数名、字段名、路径和测试命令均明确给出。

## Type consistency

统一字段名：

- `source_status`
- `has_full_text`
- `evidence_kind`
- `source_registry_id`
- `chunk_count`
- `body_chunk_count`
- `registry_chunk_count`
- `evidence_policy`

前后端和测试均使用同一组字段。
