# 新知识库 v2 可见证据报告 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把“问知识库 / 查训练依据”链路改成只使用 `data/vector_kb/v2`、归档旧库、完整传递可见证据，并强制 AI 报告正文包含“知识库可见证据”。

**Architecture:** 后端 runtime/provider 只加载 v2，并在 health 中显式暴露 schema 与 degraded 原因；retrieval → evidence bundle → evidence_chain → LLM prompt 全链路传递 canonical evidence 字段，不再把 legacy、graph hint、模型常识伪装成核心依据。前端只负责展示后端返回的证据状态和报告，不再用固定“基于 N 组依据生成”或伤病专属文案包装所有问题。

**Tech Stack:** Python 3、FastAPI、FAISS/LangChain、LangGraph fallback workflow、pytest、Astro、vanilla JavaScript。

---

## File Structure

- Modify: `apps/backend/src/marathon_qa_assistant/core/app_state.py`
  - 负责项目路径常量和默认 vector dir 选择；本计划把默认运行目录固定为 `V2_VECTOR_DIR`。
- Modify: `apps/backend/src/marathon_qa_assistant/core/kb_bootstrap.py`
  - 负责启动时加载 KB；本计划移除默认 legacy/user/default fallback，只接受 v2。
- Modify: `apps/backend/src/marathon_qa_assistant/services/vector_store.py`
  - 负责 FAISS 检索结果；本计划把 v2 metadata、定位信息、score breakdown 传播到 hit。
- Modify: `apps/backend/src/marathon_qa_assistant/nodes/profile_and_retrieval.py`
  - 负责 hybrid ranking；本计划把 visible evidence 与 graph-only hint 分层，并支持不截断传给 LLM 的可见证据。
- Modify: `apps/backend/src/marathon_qa_assistant/core/evidence_bundle.py`
  - 负责 state evidence lines / evidence base；本计划让 LLM 使用全部可见 evidence，并保留 why/score metadata。
- Modify: `apps/backend/src/marathon_qa_assistant/services/kb/evidence_chain.py`
  - 负责 evidence_chain payload；本计划强化 display mode / citation boundary，并保留可见证据统计。
- Modify: `apps/backend/src/marathon_qa_assistant/nodes/expert_nodes.py`
  - 负责 QA prompt；本计划强制知识库问答报告章节。
- Modify: `apps/backend/src/marathon_qa_assistant/apps/response_builders.py`
  - 负责 API response；本计划兜底校验报告是否包含“知识库可见证据”。
- Modify: `apps/web/src/pages/intelligent-docs.astro`
  - 负责智能文档页初始文案；本计划删除伤病硬编码初始提示。
- Modify: `apps/web/src/scripts/intelligentDocs.js`
  - 负责智能文档页动态标题和证据展示；本计划显示“新知识库可见证据 N 条 / 证据不足”。
- Create: `tests/test_kb_v2_runtime_contract.py`
  - 覆盖 v2-only runtime、无 legacy fallback、v2 缺失 degraded。
- Modify: `tests/test_evidence_chain_contract.py`
  - 覆盖 canonical evidence metadata、visible evidence 不被 top-5 截断、legacy/graph 不当核心证据。
- Create: `tests/test_kb_report_contract.py`
  - 覆盖报告必须包含固定章节，尤其是“知识库可见证据”。
- Modify: `tests/test_astro_frontend_contract.py`
  - 覆盖智能文档页标题和初始提示文案。
- Runtime operation: move legacy dirs into `archive/legacy_vector_kb_20260530/`
  - 归档而不是不可恢复删除；运行时不得扫描 `archive/`。

---

### Task 1: Enforce v2-only KB runtime defaults

**Files:**
- Create: `tests/test_kb_v2_runtime_contract.py`
- Modify: `apps/backend/src/marathon_qa_assistant/core/app_state.py:77-92`
- Modify: `apps/backend/src/marathon_qa_assistant/core/kb_bootstrap.py:23-35`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_kb_v2_runtime_contract.py` with:

```python
from pathlib import Path

from marathon_qa_assistant.core import app_state
from marathon_qa_assistant.core.kb_bootstrap import default_kb_candidate_dirs, bootstrap_knowledge_base


def test_preferred_vector_dir_is_always_v2_even_when_legacy_has_artifacts(monkeypatch):
    calls = []

    def fake_has_artifacts(path: Path) -> bool:
        calls.append(path)
        return path in {
            app_state.USER_VECTOR_DIR,
            app_state.RUNTIME_USER_VECTOR_DIR,
            app_state.LEGACY_USER_VECTOR_DIR,
            app_state.DEFAULT_VECTOR_DIR,
            app_state.LEGACY_DEFAULT_VECTOR_DIR,
        }

    monkeypatch.setattr(app_state, "has_vector_kb_artifacts", fake_has_artifacts)

    assert app_state.get_preferred_vector_dir() == app_state.V2_VECTOR_DIR
    assert calls == []


def test_default_kb_candidate_dirs_only_contains_v2_runtime_path():
    assert default_kb_candidate_dirs() == [app_state.V2_VECTOR_DIR]


def test_bootstrap_reports_degraded_when_v2_unavailable_without_legacy_fallback(monkeypatch, tmp_path):
    v2_dir = tmp_path / "data" / "vector_kb" / "v2"
    legacy_dir = tmp_path / "vector_kb"

    def fake_probe(path: Path):
        if path == v2_dir:
            return {
                "ok": False,
                "ready": False,
                "source": str(path),
                "reason": "missing chunks.jsonl or faiss index",
                "index_schema_version": "missing",
                "metadata_completeness": 0.0,
                "runtime_core_prescription_enabled": False,
            }
        return {
            "ok": True,
            "ready": True,
            "source": str(path),
            "reason": "legacy should not be checked",
            "index_schema_version": "legacy_chunk_schema",
            "metadata_completeness": 0.2,
            "runtime_core_prescription_enabled": True,
        }

    loaded_paths = []

    def fake_load(path: Path):
        loaded_paths.append(path)
        return ([{"chunk_id": "legacy"}], object(), object(), None)

    monkeypatch.setattr("marathon_qa_assistant.core.kb_bootstrap.probe_vector_kb_health", fake_probe)
    monkeypatch.setattr("marathon_qa_assistant.core.kb_bootstrap.load_vector_kb", fake_load)
    monkeypatch.setattr("marathon_qa_assistant.core.kb_bootstrap.set_kb_data", lambda *args, **kwargs: None)

    report = bootstrap_knowledge_base([v2_dir, legacy_dir])

    assert report["ok"] is False
    assert report["ready"] is False
    assert report["mode"] == "empty"
    assert "missing chunks.jsonl or faiss index" in report["reason"]
    assert loaded_paths == []
    assert all("legacy" not in item.get("index_schema_version", "") for item in report["health_reports"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd /c/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手
PYTHONUTF8=1 PYTHONPATH=apps/backend/src python -m pytest tests/test_kb_v2_runtime_contract.py -q
```

Expected: FAIL because `get_preferred_vector_dir()` still checks user/legacy dirs and `default_kb_candidate_dirs()` still returns multiple fallback paths.

- [ ] **Step 3: Implement v2-only defaults**

In `apps/backend/src/marathon_qa_assistant/core/app_state.py`, replace `get_preferred_vector_dir()` with:

```python
def get_preferred_vector_dir() -> Path:
    """
    返回运行时唯一允许加载的知识库目录。
    旧库/user/default 路径只保留为归档和迁移常量，不参与运行时 fallback。
    """
    return V2_VECTOR_DIR
```

In `apps/backend/src/marathon_qa_assistant/core/kb_bootstrap.py`, replace `default_kb_candidate_dirs()` with:

```python
def default_kb_candidate_dirs() -> List[Path]:
    """运行时只允许新知识库 v2；legacy/user/default 不再自动 fallback。"""
    return [V2_VECTOR_DIR]
```

Update `bootstrap_knowledge_base()` docstring from:

```python
"""统一加载知识库：优先用户库，失败后回退默认库，最终进入空库模式。"""
```

to:

```python
"""统一加载知识库：只加载 v2；失败时进入 degraded/empty，不静默回退 legacy。"""
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
PYTHONUTF8=1 PYTHONPATH=apps/backend/src python -m pytest tests/test_kb_v2_runtime_contract.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_kb_v2_runtime_contract.py apps/backend/src/marathon_qa_assistant/core/app_state.py apps/backend/src/marathon_qa_assistant/core/kb_bootstrap.py
git commit -m "fix: enforce v2 knowledge base runtime"
```

---

### Task 2: Archive legacy vector stores outside runtime path

**Files:**
- Runtime move: `vector_kb/` → `archive/legacy_vector_kb_20260530/vector_kb/` when present
- Runtime move: `vector_kb_user/` → `archive/legacy_vector_kb_20260530/vector_kb_user/` when present
- Runtime move: `data/vector_kb/default/` → `archive/legacy_vector_kb_20260530/data_vector_kb_default/` when present
- Runtime move: `data/vector_kb/user/` → `archive/legacy_vector_kb_20260530/data_vector_kb_user/` when present
- Create: `tests/test_legacy_kb_archive_contract.py`

- [ ] **Step 1: Write the failing archive contract test**

Create `tests/test_legacy_kb_archive_contract.py` with:

```python
from marathon_qa_assistant.core import app_state
from marathon_qa_assistant.core.kb_bootstrap import default_kb_candidate_dirs


def test_runtime_candidate_dirs_do_not_include_archive_or_legacy_paths():
    candidates = [str(path).replace("\\", "/") for path in default_kb_candidate_dirs()]

    assert candidates == [str(app_state.V2_VECTOR_DIR).replace("\\", "/")]
    assert all("/archive/" not in path for path in candidates)
    assert all(not path.endswith("/vector_kb") for path in candidates)
    assert all(not path.endswith("/vector_kb_user") for path in candidates)
    assert all("/data/vector_kb/default" not in path for path in candidates)
    assert all("/data/vector_kb/user" not in path for path in candidates)
```

- [ ] **Step 2: Run test to verify runtime contract**

Run:

```bash
PYTHONUTF8=1 PYTHONPATH=apps/backend/src python -m pytest tests/test_legacy_kb_archive_contract.py -q
```

Expected before Task 1 implementation: FAIL because legacy/default/user paths can still appear. Expected after Task 1: PASS. Keep this test as the archival guard.

- [ ] **Step 3: Inspect actual legacy dirs before moving**

Run:

```bash
python - <<'PY'
from pathlib import Path
root = Path('/c/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手')
for rel in ['vector_kb', 'vector_kb_user', 'data/vector_kb/default', 'data/vector_kb/user']:
    path = root / rel
    print(f'{rel}: exists={path.exists()} is_dir={path.is_dir()}')
PY
```

Expected: prints which legacy dirs exist. If none exist, record that no filesystem archive was needed.

- [ ] **Step 4: Move existing legacy dirs into archive**

Run:

```bash
python - <<'PY'
from pathlib import Path
import shutil

root = Path('/c/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手')
archive = root / 'archive' / 'legacy_vector_kb_20260530'
archive.mkdir(parents=True, exist_ok=True)

moves = {
    'vector_kb': 'vector_kb',
    'vector_kb_user': 'vector_kb_user',
    'data/vector_kb/default': 'data_vector_kb_default',
    'data/vector_kb/user': 'data_vector_kb_user',
}

for src_rel, dst_name in moves.items():
    src = root / src_rel
    dst = archive / dst_name
    if not src.exists():
        print(f'skip missing {src_rel}')
        continue
    if dst.exists():
        print(f'skip existing archive target {dst}')
        continue
    shutil.move(str(src), str(dst))
    print(f'moved {src_rel} -> {dst.relative_to(root)}')
PY
```

Expected: existing legacy dirs are moved under `archive/legacy_vector_kb_20260530/`; missing dirs are skipped. `data/vector_kb/v2/` must remain untouched.

- [ ] **Step 5: Verify v2 is still present and runtime contract passes**

Run:

```bash
python - <<'PY'
from pathlib import Path
root = Path('/c/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手')
v2 = root / 'data' / 'vector_kb' / 'v2'
print('v2 chunks:', (v2 / 'chunks.jsonl').exists())
print('v2 faiss:', (v2 / 'faiss_db' / 'index.faiss').exists())
PY
PYTHONUTF8=1 PYTHONPATH=apps/backend/src python -m pytest tests/test_legacy_kb_archive_contract.py tests/test_kb_v2_runtime_contract.py -q
```

Expected: v2 chunks and FAISS both print `True`; tests PASS.

- [ ] **Step 6: Commit archive movement and contract**

```bash
git add tests/test_legacy_kb_archive_contract.py archive/legacy_vector_kb_20260530
git add -u vector_kb vector_kb_user data/vector_kb/default data/vector_kb/user
git commit -m "chore: archive legacy vector knowledge bases"
```

If one or more legacy dirs are untracked and too large to commit, do not force-add large binary artifacts. Instead commit only the contract test and report the local archive move in the final verification notes.

---

### Task 3: Propagate canonical v2 retrieval metadata

**Files:**
- Modify: `tests/test_evidence_chain_contract.py`
- Modify: `apps/backend/src/marathon_qa_assistant/services/vector_store.py:723-737`

- [ ] **Step 1: Write the failing metadata propagation test**

Append to `tests/test_evidence_chain_contract.py`:

```python
def test_vector_retrieve_preserves_v2_canonical_metadata(monkeypatch):
    from marathon_qa_assistant.services import vector_store

    class FakeDoc:
        page_content = "短跑技术可以通过放松跑和短距离加速跑融入中长跑训练。"
        metadata = {
            "chunk_id": "v2-tech-001",
            "source_label": "跑步技术训练手册",
            "source_file": "running-technique.md",
            "source_url": "https://example.test/running-technique",
            "page": 12,
            "page_hint": "p.12",
            "locator_hint": "第 3 章 / 技术跑",
            "section": "短距离加速跑",
            "text_span": "短距离加速跑应放在轻松跑后，控制总量。",
            "source_registry_id": "src_running_technique",
            "language": "zh",
            "evidence_domain": "running_technique",
            "knowledge_layer": "training_method",
            "domain_pack": "marathon_v2",
            "allowed_use": "training_reference",
            "prescription_permission": "core",
            "quality_tier": "reviewed",
        }

    class FakeStore:
        def similarity_search_with_score(self, query, k):
            return [(FakeDoc(), 0.25)]

    hits = vector_store.retrieve("中长跑如何融入短跑技术", [], None, FakeStore(), top_k=1)

    assert hits == [
        {
            "score": 0.8,
            "chunk_id": "v2-tech-001",
            "source_file": "running-technique.md",
            "source_path": "",
            "page": 12,
            "text": "短跑技术可以通过放松跑和短距离加速跑融入中长跑训练。",
            "distance": 0.25,
            "source_label": "跑步技术训练手册",
            "source_url": "https://example.test/running-technique",
            "page_hint": "p.12",
            "locator_hint": "第 3 章 / 技术跑",
            "section": "短距离加速跑",
            "text_span": "短距离加速跑应放在轻松跑后，控制总量。",
            "source_registry_id": "src_running_technique",
            "language": "zh",
            "evidence_domain": "running_technique",
            "knowledge_layer": "training_method",
            "domain_pack": "marathon_v2",
            "allowed_use": "training_reference",
            "prescription_permission": "core",
            "quality_tier": "reviewed",
            "retrieval_mode": "vector",
            "why_retrieved": "FAISS similarity search matched the query after keyword expansion.",
            "score_breakdown": {"vector_score": 0.8, "distance": 0.25},
        }
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONUTF8=1 PYTHONPATH=apps/backend/src python -m pytest tests/test_evidence_chain_contract.py::test_vector_retrieve_preserves_v2_canonical_metadata -q
```

Expected: FAIL because `retrieve()` currently drops canonical metadata and does not include `why_retrieved` / `score_breakdown`.

- [ ] **Step 3: Implement metadata propagation**

In `apps/backend/src/marathon_qa_assistant/services/vector_store.py`, add near imports/constants:

```python
RETRIEVAL_METADATA_KEYS = (
    "source_label",
    "source_registry_id",
    "source_url",
    "local_path",
    "page_hint",
    "locator_hint",
    "section",
    "paragraph_index",
    "char_start",
    "char_end",
    "text_span",
    "language",
    "evidence_domain",
    "knowledge_layer",
    "domain_pack",
    "allowed_use",
    "prescription_permission",
    "quality_tier",
    "review_status",
    "exclude_from_training_generation",
    "needs_review",
)
```

Replace the `hits.append({...})` block inside `retrieve()` with:

```python
        metadata = dict(doc.metadata or {})
        source_file = metadata.get("source_file", "unknown")
        hit = {
            "score": score,
            "chunk_id": metadata.get("chunk_id", "unknown"),
            "source_file": source_file,
            "source_path": metadata.get("source_path", "") or infer_source_path(source_file),
            "page": metadata.get("page", 1),
            "text": doc.page_content,
            "distance": float(distance),
            "retrieval_mode": "vector",
            "why_retrieved": "FAISS similarity search matched the query after keyword expansion.",
            "score_breakdown": {"vector_score": score, "distance": float(distance)},
        }
        # v2 chunk metadata is part of the user-visible evidence contract.
        for key in RETRIEVAL_METADATA_KEYS:
            if key in metadata:
                hit[key] = metadata.get(key)
        hits.append(hit)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
PYTHONUTF8=1 PYTHONPATH=apps/backend/src python -m pytest tests/test_evidence_chain_contract.py::test_vector_retrieve_preserves_v2_canonical_metadata -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_evidence_chain_contract.py apps/backend/src/marathon_qa_assistant/services/vector_store.py
git commit -m "fix: preserve v2 retrieval metadata"
```

---

### Task 4: Keep all visible evidence for LLM while separating graph and legacy boundaries

**Files:**
- Modify: `tests/test_evidence_chain_contract.py`
- Modify: `apps/backend/src/marathon_qa_assistant/nodes/profile_and_retrieval.py`
- Modify: `apps/backend/src/marathon_qa_assistant/core/evidence_bundle.py`

- [ ] **Step 1: Write failing tests for visibility and evidence boundaries**

Append to `tests/test_evidence_chain_contract.py`:

```python
def test_ranked_evidence_can_return_all_visible_v2_chunks_without_top5_truncation():
    from marathon_qa_assistant.nodes.profile_and_retrieval import build_ranked_evidence

    vector_hits = [
        {
            "chunk_id": f"v2-{idx}",
            "source_label": f"技术文档 {idx}",
            "source_file": f"tech-{idx}.md",
            "page_hint": f"p.{idx}",
            "locator_hint": f"第 {idx} 节",
            "text_span": f"第 {idx} 条可见证据。",
            "text": f"第 {idx} 条可见证据。",
            "score": 1.0 - idx * 0.01,
            "retrieval_mode": "vector",
            "prescription_permission": "core",
            "quality_tier": "reviewed",
        }
        for idx in range(1, 9)
    ]

    ranked = build_ranked_evidence(
        "中长跑怎么融入短跑技术",
        vector_hits,
        graph_edges=[],
        entities=["中长跑", "短跑技术"],
        top_k=None,
    )

    assert len(ranked) == 8
    assert [item["citation_label"] for item in ranked] == [f"[{idx}]" for idx in range(1, 9)]
    assert all(item["display_mode"] == "verified_source" for item in ranked)
    assert all(item["can_write_core"] is True for item in ranked)


def test_graph_only_evidence_is_hint_not_core_prescription():
    from marathon_qa_assistant.nodes.profile_and_retrieval import build_ranked_evidence

    graph_edges = [
        {
            "source": "短跑技术",
            "target": "跑步经济性",
            "relation": "supports",
            "confidence": 0.9,
        }
    ]

    ranked = build_ranked_evidence(
        "中长跑怎么融入短跑技术",
        vector_hits=[],
        graph_edges=graph_edges,
        entities=["短跑技术"],
        top_k=None,
    )

    assert ranked
    assert ranked[0]["display_mode"] == "graph_hint"
    assert ranked[0]["can_write_core"] is False
    assert ranked[0]["explanation_only"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONUTF8=1 PYTHONPATH=apps/backend/src python -m pytest tests/test_evidence_chain_contract.py::test_ranked_evidence_can_return_all_visible_v2_chunks_without_top5_truncation tests/test_evidence_chain_contract.py::test_graph_only_evidence_is_hint_not_core_prescription -q
```

Expected: FAIL because `build_ranked_evidence()` currently slices `ranked_list[:top_k]` and does not guarantee these canonical boundary fields.

- [ ] **Step 3: Implement ranking boundary fields**

In `apps/backend/src/marathon_qa_assistant/nodes/profile_and_retrieval.py`, change the function signature to accept unlimited evidence:

```python
def build_ranked_evidence(
    query: str,
    vector_hits: List[Dict[str, Any]],
    graph_edges: List[Dict[str, Any]],
    entities: List[str],
    top_k: Optional[int] = None,
) -> List[Evidence]:
```

Ensure `Optional` is imported from `typing`.

When creating a vector evidence item, include these fields:

```python
        ev.update({
            "source_label": hit.get("source_label") or hit.get("source_file") or "来源待补充",
            "text_span": hit.get("text_span") or hit.get("text", ""),
            "page_hint": hit.get("page_hint") or (f"p.{hit.get('page')}" if hit.get("page") else ""),
            "locator_hint": hit.get("locator_hint") or hit.get("section") or "定位待补充",
            "display_mode": "verified_source",
            "prescription_permission": hit.get("prescription_permission") or "core",
            "can_write_core": True,
            "explanation_only": False,
            "retrieval_mode": hit.get("retrieval_mode") or "vector",
            "why_retrieved": hit.get("why_retrieved") or "Vector retrieval matched the query.",
            "score_breakdown": hit.get("score_breakdown") or {"vector_score": hit.get("score", 0.0)},
        })
```

When creating a graph-only item, include:

```python
        ev.update({
            "source_label": "知识图谱关联线索",
            "text_span": f"{edge.get('source', '')} {edge.get('relation', '')} {edge.get('target', '')}".strip(),
            "locator_hint": "图谱线索，无可定位文档片段",
            "display_mode": "graph_hint",
            "prescription_permission": "explanation_only",
            "can_write_core": False,
            "explanation_only": True,
            "retrieval_mode": "graph",
            "why_retrieved": "Knowledge graph relation matched extracted entities.",
            "score_breakdown": {"graph_confidence": float(edge.get("confidence") or 0.0)},
        })
```

Replace final slicing:

```python
final_list = ranked_list[:top_k]
```

with:

```python
final_list = ranked_list if top_k is None else ranked_list[:top_k]
```

- [ ] **Step 4: Update evidence bundle formatting to allow all visible evidence**

In `apps/backend/src/marathon_qa_assistant/core/evidence_bundle.py`, change defaults:

```python
def format_evidence_bundle_lines(bundle: Dict[str, Any], limit: Optional[int] = None) -> str:
```

and:

```python
def evidence_base_from_bundle(bundle: Dict[str, Any], limit: Optional[int] = None) -> List[Dict[str, Any]]:
```

Inside both functions, use:

```python
items = bundle.get("items") or bundle.get("evidence") or []
if limit is not None:
    items = items[:limit]
```

Preserve `why_retrieved` and `score_breakdown` in `_item_from_ranked_evidence()` by adding them to `EVIDENCE_METADATA_KEYS`:

```python
    "why_retrieved",
    "score_breakdown",
    "display_mode",
    "can_write_core",
    "explanation_only",
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```bash
PYTHONUTF8=1 PYTHONPATH=apps/backend/src python -m pytest tests/test_evidence_chain_contract.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/test_evidence_chain_contract.py apps/backend/src/marathon_qa_assistant/nodes/profile_and_retrieval.py apps/backend/src/marathon_qa_assistant/core/evidence_bundle.py
git commit -m "fix: keep visible evidence through ranking"
```

---

### Task 5: Force QA reports to include visible evidence section

**Files:**
- Create: `tests/test_kb_report_contract.py`
- Modify: `apps/backend/src/marathon_qa_assistant/nodes/expert_nodes.py`
- Modify: `apps/backend/src/marathon_qa_assistant/apps/response_builders.py`

- [ ] **Step 1: Write failing report contract tests**

Create `tests/test_kb_report_contract.py` with:

```python
from marathon_qa_assistant.apps.response_builders import ensure_kb_visible_evidence_report_sections


REQUIRED_SECTIONS = [
    "## 结论",
    "## 训练建议",
    "## 专项不受影响的边界",
    "## 知识库可见证据",
    "## 证据不足或待核验之处",
]


def test_ensure_kb_visible_evidence_report_sections_adds_required_sections():
    report = "短跑技术可以少量融入中长跑训练。"
    evidence_chain = {
        "items": [
            {
                "citation_label": "[1]",
                "source_label": "跑步技术训练手册",
                "locator_hint": "第 3 章",
                "text_span": "短距离加速跑应控制总量。",
                "display_mode": "verified_source",
            }
        ]
    }

    result = ensure_kb_visible_evidence_report_sections(report, evidence_chain)

    for section in REQUIRED_SECTIONS:
        assert section in result
    assert "[1] 跑步技术训练手册" in result
    assert "短距离加速跑应控制总量。" in result


def test_ensure_kb_visible_evidence_report_sections_preserves_existing_valid_report():
    report = """## 结论
可以融入。

## 训练建议
每周一次。

## 专项不受影响的边界
总量受控。

## 知识库可见证据
- [1] 跑步技术训练手册：短距离加速跑应控制总量。

## 证据不足或待核验之处
需要个体化验证。
"""

    assert ensure_kb_visible_evidence_report_sections(report, {"items": []}) == report
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONUTF8=1 PYTHONPATH=apps/backend/src python -m pytest tests/test_kb_report_contract.py -q
```

Expected: FAIL because `ensure_kb_visible_evidence_report_sections` does not exist.

- [ ] **Step 3: Add report section helper**

In `apps/backend/src/marathon_qa_assistant/apps/response_builders.py`, add near other helper functions:

```python
KB_REPORT_REQUIRED_SECTIONS = (
    "## 结论",
    "## 训练建议",
    "## 专项不受影响的边界",
    "## 知识库可见证据",
    "## 证据不足或待核验之处",
)


def _visible_evidence_lines_from_chain(evidence_chain: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    for idx, item in enumerate(evidence_chain.get("items") or [], start=1):
        if not isinstance(item, dict):
            continue
        label = str(item.get("citation_label") or f"[{idx}]").strip()
        source = str(item.get("source_label") or item.get("title") or "来源待补充").strip()
        locator = str(item.get("locator_hint") or item.get("page_hint") or "定位待补充").strip()
        span = str(item.get("text_span") or item.get("user_facing_summary") or "当前证据缺少可见摘录。").strip()
        mode = str(item.get("display_mode") or "needs_evidence").strip()
        lines.append(f"- {label} {source}（{locator}，{mode}）：{span}")
    return lines


def ensure_kb_visible_evidence_report_sections(report: str, evidence_chain: Dict[str, Any]) -> str:
    """保证知识库问答报告正文包含固定章节和可见证据列表。"""
    text = str(report or "").strip()
    if text and all(section in text for section in KB_REPORT_REQUIRED_SECTIONS):
        return text

    evidence_lines = _visible_evidence_lines_from_chain(evidence_chain)
    evidence_block = "\n".join(evidence_lines) if evidence_lines else "- 当前没有足够可定位的新知识库证据。"
    insufficiency = "- 若建议未在上方证据中出现，应视为待核验，不作为强训练处方依据。"

    return "\n\n".join(
        [
            "## 结论\n" + (text or "当前问题需要结合新知识库证据谨慎判断。"),
            "## 训练建议\n请优先采用上方结论中已被新知识库证据支持的建议；未被证据覆盖的内容只作为待核验方向。",
            "## 专项不受影响的边界\n任何短跑技术、力量或高强度内容都不应挤占中长跑专项有氧、阈值和恢复安排。",
            "## 知识库可见证据\n" + evidence_block,
            "## 证据不足或待核验之处\n" + insufficiency,
        ]
    )
```

In `_query_response_from_state()` after `evidence_chain` is available and before response dict is returned, normalize the report for knowledge-base QA responses:

```python
    final_report = ensure_kb_visible_evidence_report_sections(
        str(result.get("final_report") or result.get("report") or ""),
        evidence_chain,
    )
```

Use `final_report` for `report`, `message`, and `structured_report` summary fields where the current code uses raw `result.get("final_report") or result.get("report")`.

- [ ] **Step 4: Strengthen expert prompt**

In `apps/backend/src/marathon_qa_assistant/nodes/expert_nodes.py`, replace:

```python
本地知识库证据：
{format_state_evidence_lines(state, limit=5)}
```

with:

```python
本地知识库可见证据（必须全部处理，不能只给结论）：
{format_state_evidence_lines(state, limit=None)}
```

Add this instruction to the QA prompt body:

```text
报告格式必须包含且只能省略空行，不能省略章节标题：
## 结论
## 训练建议
## 专项不受影响的边界
## 知识库可见证据
## 证据不足或待核验之处

“知识库可见证据”章节必须逐条覆盖上方传入的可见证据；如果某条证据是 graph_hint、legacy_explanation、model_general_knowledge、needs_evidence 或 rejected_source，必须明确写出它不能作为核心训练处方依据。
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```bash
PYTHONUTF8=1 PYTHONPATH=apps/backend/src python -m pytest tests/test_kb_report_contract.py -q
```

Expected: PASS.

- [ ] **Step 6: Run response/evidence related tests**

Run:

```bash
PYTHONUTF8=1 PYTHONPATH=apps/backend/src python -m pytest tests/test_kb_report_contract.py tests/test_evidence_chain_contract.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add tests/test_kb_report_contract.py apps/backend/src/marathon_qa_assistant/nodes/expert_nodes.py apps/backend/src/marathon_qa_assistant/apps/response_builders.py
git commit -m "fix: require visible evidence in kb reports"
```

---

### Task 6: Update intelligent docs copy for v2 evidence semantics

**Files:**
- Modify: `tests/test_astro_frontend_contract.py`
- Modify: `apps/web/src/pages/intelligent-docs.astro`
- Modify: `apps/web/src/scripts/intelligentDocs.js`

- [ ] **Step 1: Write failing frontend contract tests**

Append to `tests/test_astro_frontend_contract.py`:

```python
def test_intelligent_docs_initial_copy_is_v2_kb_generic_not_injury_specific():
    content = _read_stripped(root / "apps" / "web" / "src" / "pages" / "intelligent-docs.astro")
    assert "AI 回答（等待新知识库检索）" in content
    assert "缺少疼痛等级、持续时间和是否影响步态" not in content
    assert "新知识库 v2" in content


def test_intelligent_docs_title_uses_visible_evidence_language():
    content = _read_stripped(INTELLIGENT_DOCS_SCRIPT)
    assert "新知识库可见证据" in content
    assert "基于 ${evidenceCount} 组依据生成" not in content
    assert "等待新知识库检索" in content
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONUTF8=1 PYTHONPATH=apps/backend/src python -m pytest tests/test_astro_frontend_contract.py::test_intelligent_docs_initial_copy_is_v2_kb_generic_not_injury_specific tests/test_astro_frontend_contract.py::test_intelligent_docs_title_uses_visible_evidence_language -q
```

Expected: FAIL because `intelligent-docs.astro` still has injury-specific initial copy and `intelligentDocs.js` still says `基于 N 组依据生成`.

- [ ] **Step 3: Update static Astro copy**

In `apps/web/src/pages/intelligent-docs.astro`, replace:

```astro
<h2 id="docs-answer-title" data-docs-answer-title>AI 回答（基于 4 组依据生成）</h2>
```

with:

```astro
<h2 id="docs-answer-title" data-docs-answer-title>AI 回答（等待新知识库检索）</h2>
```

Replace the initial alert body mentioning pain/gait with:

```astro
<div><strong>新知识库 v2：</strong>提交问题后会展示后端返回的可见证据；证据不足时会明确标注待核验之处。</div>
```

- [ ] **Step 4: Update dynamic title**

In `apps/web/src/scripts/intelligentDocs.js`, replace:

```js
const evidenceCount = collectEvidenceItems(payload).length || 4;
if (answerTitle) answerTitle.textContent = `AI 回答（基于 ${evidenceCount} 组依据生成）`;
```

with:

```js
const evidenceCount = collectEvidenceItems(payload).length;
if (answerTitle) {
  answerTitle.textContent = evidenceCount > 0
    ? `AI 回答（新知识库可见证据 ${evidenceCount} 条）`
    : "AI 回答（新知识库证据不足）";
}
```

Ensure the initial loading state uses generic v2 copy:

```js
setAlert("info", "<strong>正在检索新知识库 v2：</strong>先检索可见证据，再生成包含证据章节的报告。");
```

- [ ] **Step 5: Run frontend contract tests**

Run:

```bash
PYTHONUTF8=1 PYTHONPATH=apps/backend/src python -m pytest tests/test_astro_frontend_contract.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/test_astro_frontend_contract.py apps/web/src/pages/intelligent-docs.astro apps/web/src/scripts/intelligentDocs.js
git commit -m "fix: clarify v2 evidence copy in docs ui"
```

---

### Task 7: End-to-end smoke verification for the user query

**Files:**
- No production file changes expected.
- Runtime verification against local API.

- [ ] **Step 1: Run targeted backend tests**

Run:

```bash
cd /c/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手
PYTHONUTF8=1 PYTHONPATH=apps/backend/src python -m pytest \
  tests/test_kb_v2_runtime_contract.py \
  tests/test_legacy_kb_archive_contract.py \
  tests/test_evidence_chain_contract.py \
  tests/test_kb_report_contract.py \
  -q
```

Expected: PASS.

- [ ] **Step 2: Run targeted frontend contract tests**

Run:

```bash
PYTHONUTF8=1 PYTHONPATH=apps/backend/src python -m pytest tests/test_astro_frontend_contract.py -q
```

Expected: PASS.

- [ ] **Step 3: Compile touched backend modules**

Run:

```bash
PYTHONUTF8=1 PYTHONPATH=apps/backend/src python -m py_compile \
  apps/backend/src/marathon_qa_assistant/core/app_state.py \
  apps/backend/src/marathon_qa_assistant/core/kb_bootstrap.py \
  apps/backend/src/marathon_qa_assistant/services/vector_store.py \
  apps/backend/src/marathon_qa_assistant/nodes/profile_and_retrieval.py \
  apps/backend/src/marathon_qa_assistant/core/evidence_bundle.py \
  apps/backend/src/marathon_qa_assistant/services/kb/evidence_chain.py \
  apps/backend/src/marathon_qa_assistant/nodes/expert_nodes.py \
  apps/backend/src/marathon_qa_assistant/apps/response_builders.py
```

Expected: command exits 0.

- [ ] **Step 4: Start or reuse backend, then check health**

If backend is not running, run:

```bash
PYTHONUTF8=1 PYTHONPATH=apps/backend/src MARATHON_ALLOWED_ORIGINS='http://127.0.0.1:4321,http://localhost:4321,http://127.0.0.1:4322,http://localhost:4322' python apps/backend/src/marathon_qa_assistant/apps/api_app.py
```

In another command, run:

```bash
python - <<'PY'
import json
import urllib.request

payload = json.load(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=10))
print(json.dumps(payload, ensure_ascii=False, indent=2))
rag = payload.get('rag_health') or payload.get('kb_health') or payload
assert 'v2' in json.dumps(rag, ensure_ascii=False)
assert 'legacy' not in json.dumps(rag, ensure_ascii=False).lower()
PY
```

Expected: health shows v2 runtime information and no legacy fallback.

- [ ] **Step 5: Query the user’s problematic question**

Run:

```bash
python - <<'PY'
import json
import urllib.request

body = json.dumps({
    'query': '中长跑选手怎么把短跑技术融入进去，不影响专项？',
    'mode': 'team'
}, ensure_ascii=False).encode('utf-8')
req = urllib.request.Request(
    'http://127.0.0.1:8000/query',
    data=body,
    headers={'Content-Type': 'application/json'},
    method='POST',
)
with urllib.request.urlopen(req, timeout=120) as resp:
    payload = json.loads(resp.read().decode('utf-8'))
report = payload.get('report') or payload.get('message') or ''
chain = payload.get('evidence_chain') or {}
items = chain.get('items') or []
print('sections_ok=', all(section in report for section in ['## 结论', '## 训练建议', '## 专项不受影响的边界', '## 知识库可见证据', '## 证据不足或待核验之处']))
print('evidence_count=', len(items))
print('answer_source_mode=', chain.get('answer_source_mode'))
print(report[:1200])
assert '## 知识库可见证据' in report
assert '疼痛等级、持续时间和是否影响步态' not in report
for item in items:
    assert item.get('source_label')
    assert item.get('display_mode')
PY
```

Expected: response contains all required sections, evidence_count is the number of returned visible evidence items, no hardcoded injury prompt appears, each evidence item has canonical fields.

- [ ] **Step 6: Commit final verification note if needed**

If verification required small test-only adjustments, commit them:

```bash
git add tests apps/backend/src apps/web/src
 git commit -m "test: verify v2 evidence report flow"
```

If no files changed, do not create an empty commit. Record commands and results in the final response.

---

## Self-Review

### Spec coverage

- Runtime only uses `data/vector_kb/v2`: Task 1.
- Legacy exits runtime and is archived: Task 2.
- No silent fallback to legacy: Task 1 and Task 2 tests.
- Visible evidence carries `chunk_id`, `source_label`, `text_span`, `locator_hint`, `display_mode`, `retrieval_mode`, `score_breakdown`, `why_retrieved`: Task 3 and Task 4.
- Evidence gating labels graph/legacy/model/needs/rejected boundaries instead of hiding or upgrading them: Task 4 and existing evidence_chain tests.
- LLM report must contain fixed sections and cover visible evidence: Task 5.
- Frontend no longer displays confusing generic “基于 N 组依据生成” or injury-specific prompt for non-injury questions: Task 6.
- End-to-end user query verification: Task 7.

### Placeholder scan

No `TBD`, `TODO`, “similar to”, or undefined future implementation placeholders remain. Each code-changing task includes concrete test code, implementation snippets, commands, expected failure/pass state, and commit command.

### Type consistency

- `top_k` changes to `Optional[int]`; Task 4 explicitly imports `Optional` and treats `None` as unlimited.
- Canonical evidence fields use the same names across vector retrieval, ranked evidence, evidence bundle, evidence_chain, frontend, and tests.
- Required report sections are identical in prompt, response helper, and tests.

---

## Execution Handoff

Recommended implementation mode: **Subagent-Driven**. Split by role:

1. **Runtime subagent:** Task 1 + Task 2.
2. **Retrieval/evidence subagent:** Task 3 + Task 4.
3. **Report contract subagent:** Task 5.
4. **Frontend contract subagent:** Task 6.
5. **Verification lead:** Task 7 and final regression report.
