# Expert KB Coverage Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the marathon assistant able to prove which expert nodes have enough domain knowledge, load the intended v2 KB at runtime, and block/flag weak expert domains before production use.

**Architecture:** Keep the change small and evidence-first: fix the existing runtime KB health API, add a deterministic expert coverage report built from `coverage_matrix.json` plus `data/vector_kb/v2/chunks.jsonl`, then expose the report through tests and a CLI script. Do not change expert prompting or ingest new documents in this plan; this plan creates measurement and gates so the next ingestion batch is targeted.

**Tech Stack:** Python 3.12, conda torch2.5.1 environment, pytest, existing `marathon_qa_assistant` package, JSON/JSONL KB artifacts, FAISS vector KB.

---

## Current Facts

- Active repo: `C:/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手`
- Runtime bootstrap currently imports `probe_vector_kb_health` from `marathon_qa_assistant.services.vector_store`, but `vector_store.py` does not define it.
- Existing tests already expect `kb_bootstrap.default_kb_candidate_dirs()` to prefer `data/vector_kb/v2` before legacy/default KB.
- `data/knowledge/governance/coverage_matrix.json` shows every domain pack is either `partial` or `gap`.
- `data/vector_kb/v2/chunks.jsonl` has rich metadata: `domain_pack`, `prescription_permission`, `quality_tier`, `knowledge_layer`.
- `data/knowledge/governance/runtime_index_v2_manifest.json` says v2 is preview-ready but not commercial-approved because `approved_records=0` and `ready_records=0`.

## Non-Goals

- Do not ingest new PDFs or web sources in this implementation pass.
- Do not change LLM prompts or expert node behavior until coverage measurement is stable.
- Do not mark internal seed knowledge as approved.
- Do not enable commercial core prescription based only on preview/internal seed records.

## File Structure

- Modify: `apps/backend/src/marathon_qa_assistant/services/vector_store.py`
  - Add `probe_vector_kb_health(vector_dir: Path) -> dict` used by `core/kb_bootstrap.py`.
- Create: `apps/backend/src/marathon_qa_assistant/services/kb/expert_coverage.py`
  - Build expert-node coverage summaries from governance matrix and v2 chunks.
- Create: `tools/kb/expert_coverage_report.py`
  - CLI entrypoint that writes `data/knowledge/governance/expert_coverage_report.json`.
- Create: `scripts/expert_coverage_report.py`
  - Thin compatibility wrapper matching the existing `scripts/kb_gap_check.py` pattern.
- Create: `tests/test_vector_kb_health_probe.py`
  - Unit tests for `probe_vector_kb_health` on healthy, missing, legacy, and mixed directories.
- Create: `tests/test_kb_expert_coverage.py`
  - Unit tests for expert-to-domain coverage scoring and blocker detection.
- Modify: `data/knowledge/governance/expert_coverage_report.json`
  - Generated report artifact after the CLI runs.

---

### Task 1: Add vector KB health probe

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/services/vector_store.py`
- Test: `tests/test_vector_kb_health_probe.py`

- [ ] **Step 1: Write failing tests for the missing health probe**

Create `tests/test_vector_kb_health_probe.py`:

```python
import json
from pathlib import Path

from marathon_qa_assistant.services.vector_store import probe_vector_kb_health


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def _write_faiss_markers(vector_dir: Path) -> None:
    faiss_dir = vector_dir / "faiss_db"
    faiss_dir.mkdir(parents=True, exist_ok=True)
    (faiss_dir / "index.faiss").write_bytes(b"fake")
    (faiss_dir / "index.pkl").write_bytes(b"fake")


def test_probe_vector_kb_health_reports_missing_chunks(tmp_path):
    result = probe_vector_kb_health(tmp_path / "missing")

    assert result["ok"] is False
    assert result["source"] == "missing"
    assert result["chunks_count"] == 0
    assert result["faiss_ready"] is False
    assert "chunks.jsonl" in result["reason"]


def test_probe_vector_kb_health_reports_legacy_schema(tmp_path):
    vector_dir = tmp_path / "default"
    _write_jsonl(vector_dir / "chunks.jsonl", [{"chunk_id": "c1", "source_file": "a.pdf", "page": 1, "text": "hello"}])
    _write_faiss_markers(vector_dir)

    result = probe_vector_kb_health(vector_dir)

    assert result["ok"] is True
    assert result["source"] == "default"
    assert result["chunks_count"] == 1
    assert result["faiss_ready"] is True
    assert result["index_schema_version"] == "legacy"
    assert result["metadata_completeness"] == 0.0
    assert result["runtime_core_prescription_enabled"] is False


def test_probe_vector_kb_health_reports_v2_schema(tmp_path):
    vector_dir = tmp_path / "v2"
    _write_jsonl(
        vector_dir / "chunks.jsonl",
        [
            {
                "chunk_id": "v2-1",
                "source_registry_id": "src_1",
                "source_file": "source.md",
                "source_url": "https://example.com/source",
                "local_path": "data/knowledge/source.md",
                "page": 1,
                "section": "intro",
                "text": "safe text",
                "language": "en",
                "evidence_domain": "protocol",
                "knowledge_layer": "document_index",
                "domain_pack": "training_protocols",
                "allowed_use": "core_prescription",
                "prescription_permission": "can_write_core",
                "quality_tier": "approved",
            }
        ],
    )
    _write_faiss_markers(vector_dir)

    result = probe_vector_kb_health(vector_dir)

    assert result["ok"] is True
    assert result["source"] == "v2"
    assert result["chunks_count"] == 1
    assert result["index_schema_version"] == "chunk_schema_v2"
    assert result["metadata_completeness"] == 1.0
    assert result["runtime_core_prescription_enabled"] is True


def test_probe_vector_kb_health_blocks_missing_faiss(tmp_path):
    vector_dir = tmp_path / "v2"
    _write_jsonl(vector_dir / "chunks.jsonl", [{"chunk_id": "c1", "source_file": "a.pdf", "page": 1, "text": "hello"}])

    result = probe_vector_kb_health(vector_dir)

    assert result["ok"] is False
    assert result["chunks_count"] == 1
    assert result["faiss_ready"] is False
    assert "index.faiss" in result["reason"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd "C:/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手" && python -m pytest tests/test_vector_kb_health_probe.py -v
```

Expected: FAIL with `ImportError: cannot import name 'probe_vector_kb_health'`.

- [ ] **Step 3: Implement `probe_vector_kb_health`**

Append this function near `load_vector_kb` in `apps/backend/src/marathon_qa_assistant/services/vector_store.py`:

```python
def _infer_vector_source(vector_dir: Path) -> str:
    name = vector_dir.name.lower()
    if name == "v2":
        return "v2"
    if name == "user" or "user" in str(vector_dir).lower():
        return "user"
    if name == "default" or name == "vector_kb":
        return "default"
    return name or "unknown"


def probe_vector_kb_health(vector_dir: Path) -> dict:
    """Return a cheap health summary without loading FAISS or embeddings."""
    from marathon_qa_assistant.services.kb.health import summarize_runtime_index_schema

    vector_path = Path(vector_dir)
    chunks_file = vector_path / "chunks.jsonl"
    faiss_index = vector_path / "faiss_db" / "index.faiss"
    source = _infer_vector_source(vector_path)

    if not chunks_file.exists():
        return {
            "ok": False,
            "ready": False,
            "source": "missing" if not vector_path.exists() else source,
            "vector_dir": str(vector_path),
            "reason": f"missing chunks.jsonl: {chunks_file}",
            "chunks_count": 0,
            "faiss_ready": False,
            "index_schema_version": "missing",
            "metadata_completeness": 0.0,
            "runtime_core_prescription_enabled": False,
        }

    chunks = load_chunks(chunks_file)
    schema = summarize_runtime_index_schema(chunks)
    faiss_ready = faiss_index.exists()
    ok = bool(chunks) and faiss_ready
    reason = "" if ok else ""
    if not chunks:
        reason = "chunks.jsonl is empty"
    elif not faiss_ready:
        reason = f"missing FAISS index.faiss: {faiss_index}"

    return {
        "ok": ok,
        "ready": ok,
        "source": source,
        "vector_dir": str(vector_path),
        "reason": reason,
        "chunks_count": len(chunks),
        "faiss_ready": faiss_ready,
        "index_schema_version": schema["index_schema_version"],
        "metadata_completeness": schema["metadata_completeness"],
        "runtime_core_prescription_enabled": schema["runtime_core_prescription_enabled"],
        "core_permission_violation_count": schema["core_permission_violation_count"],
    }
```

- [ ] **Step 4: Run targeted tests**

Run:

```bash
cd "C:/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手" && python -m pytest tests/test_vector_kb_health_probe.py tests/test_kb_bootstrap.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/backend/src/marathon_qa_assistant/services/vector_store.py tests/test_vector_kb_health_probe.py
git commit -m "fix: add vector KB health probe"
```

---

### Task 2: Add expert coverage service

**Files:**
- Create: `apps/backend/src/marathon_qa_assistant/services/kb/expert_coverage.py`
- Test: `tests/test_kb_expert_coverage.py`

- [ ] **Step 1: Write failing tests for expert coverage scoring**

Create `tests/test_kb_expert_coverage.py`:

```python
from marathon_qa_assistant.services.kb.expert_coverage import build_expert_coverage_report


def test_expert_coverage_marks_action_library_as_blocker_when_source_coverage_is_low():
    coverage_rows = [
        {
            "domain_pack": "training_protocols",
            "target_source_count": 20,
            "current_source_count": 7,
            "target_rule_count": 50,
            "current_rule_count": 63,
            "target_question_count": 10,
            "current_question_count": 10,
            "can_write_core": True,
            "gap_status": "partial",
        },
        {
            "domain_pack": "action_library",
            "target_source_count": 20,
            "current_source_count": 1,
            "target_rule_count": 100,
            "current_rule_count": 120,
            "target_question_count": 10,
            "current_question_count": 10,
            "can_write_core": True,
            "gap_status": "partial",
        },
    ]
    chunks = [
        {"domain_pack": "training_protocols", "prescription_permission": "can_write_core", "quality_tier": "internal_seed_needs_domain_review"},
        {"domain_pack": "action_library", "prescription_permission": "can_write_core", "quality_tier": "internal_seed_needs_domain_review"},
    ]

    report = build_expert_coverage_report(coverage_rows, chunks)
    coach = report["experts"]["coach_node"]

    assert coach["status"] == "blocked"
    assert "action_library" in coach["blocking_domains"]
    assert coach["domain_packs"]["action_library"]["source_coverage_ratio"] == 0.05


def test_expert_coverage_allows_nutritionist_as_partial_not_blocked():
    coverage_rows = [
        {
            "domain_pack": "nutrition_race_fueling",
            "target_source_count": 12,
            "current_source_count": 7,
            "target_rule_count": 40,
            "current_rule_count": 48,
            "target_question_count": 10,
            "current_question_count": 10,
            "can_write_core": False,
            "gap_status": "partial",
        }
    ]
    chunks = [
        {"domain_pack": "nutrition_race_fueling", "prescription_permission": "explanation_only", "quality_tier": "internal_seed_needs_domain_review"}
        for _ in range(48)
    ]

    report = build_expert_coverage_report(coverage_rows, chunks)
    nutritionist = report["experts"]["nutritionist_node"]

    assert nutritionist["status"] == "partial"
    assert nutritionist["blocking_domains"] == []
    assert nutritionist["chunk_count"] == 48


def test_expert_coverage_flags_user_profile_cases_gap():
    coverage_rows = [
        {
            "domain_pack": "user_profile_cases",
            "target_source_count": 100,
            "current_source_count": 0,
            "target_rule_count": 100,
            "current_rule_count": 0,
            "target_question_count": 10,
            "current_question_count": 10,
            "can_write_core": False,
            "gap_status": "gap",
        }
    ]

    report = build_expert_coverage_report(coverage_rows, [])

    assert "user_profile_cases" in report["global_blockers"]
    assert report["domain_packs"]["user_profile_cases"]["status"] == "gap"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd "C:/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手" && python -m pytest tests/test_kb_expert_coverage.py -v
```

Expected: FAIL with `ModuleNotFoundError` for `expert_coverage`.

- [ ] **Step 3: Implement expert coverage service**

Create `apps/backend/src/marathon_qa_assistant/services/kb/expert_coverage.py`:

```python
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List


EXPERT_DOMAIN_MAP = {
    "coach_node": ["training_protocols", "action_library", "training_load"],
    "executor_node": ["training_protocols", "action_library"],
    "nutritionist_node": ["nutrition_race_fueling", "nutrition_hydration_race_fueling"],
    "adaptive_coach_node": ["training_load", "medical_risk", "mobility_recovery"],
    "therapist_node": ["medical_risk", "rehab_return_to_run"],
    "critic_auditor_node": ["training_protocols", "action_library", "medical_risk", "rehab_return_to_run", "nutrition_race_fueling"],
    "research_analyst_node": ["endurance_training_protocols", "load_injury_safety", "nutrition_hydration_race_fueling"],
}

CORE_EXPERTS = {"coach_node", "executor_node"}
MIN_SOURCE_RATIO_FOR_CORE = 0.4
MIN_SOURCE_RATIO_FOR_PARTIAL = 0.25


def _ratio(current: int, target: int) -> float:
    if target <= 0:
        return 1.0 if current > 0 else 0.0
    return round(current / target, 4)


def _index_chunks(chunks: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "chunk_count": 0,
        "permission_counts": Counter(),
        "quality_tier_counts": Counter(),
        "knowledge_layer_counts": Counter(),
    })
    for chunk in chunks:
        domain = str(chunk.get("domain_pack") or "missing")
        grouped[domain]["chunk_count"] += 1
        grouped[domain]["permission_counts"][str(chunk.get("prescription_permission") or "missing")] += 1
        grouped[domain]["quality_tier_counts"][str(chunk.get("quality_tier") or "missing")] += 1
        grouped[domain]["knowledge_layer_counts"][str(chunk.get("knowledge_layer") or "missing")] += 1
    return {
        domain: {
            **stats,
            "permission_counts": dict(stats["permission_counts"]),
            "quality_tier_counts": dict(stats["quality_tier_counts"]),
            "knowledge_layer_counts": dict(stats["knowledge_layer_counts"]),
        }
        for domain, stats in grouped.items()
    }


def _domain_summary(row: Dict[str, Any], chunk_stats: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    domain = str(row["domain_pack"])
    current_sources = int(row.get("current_source_count") or 0)
    target_sources = int(row.get("target_source_count") or 0)
    current_rules = int(row.get("current_rule_count") or 0)
    target_rules = int(row.get("target_rule_count") or 0)
    stats = chunk_stats.get(domain, {})
    source_ratio = _ratio(current_sources, target_sources)
    rule_ratio = _ratio(current_rules, target_rules)
    status = str(row.get("gap_status") or "gap")
    if status != "gap" and source_ratio < MIN_SOURCE_RATIO_FOR_PARTIAL:
        status = "weak_partial"
    return {
        "domain_pack": domain,
        "status": status,
        "can_write_core": bool(row.get("can_write_core")),
        "current_source_count": current_sources,
        "target_source_count": target_sources,
        "source_coverage_ratio": source_ratio,
        "current_rule_count": current_rules,
        "target_rule_count": target_rules,
        "rule_coverage_ratio": rule_ratio,
        "current_question_count": int(row.get("current_question_count") or 0),
        "target_question_count": int(row.get("target_question_count") or 0),
        "chunk_count": int(stats.get("chunk_count") or 0),
        "permission_counts": stats.get("permission_counts", {}),
        "quality_tier_counts": stats.get("quality_tier_counts", {}),
        "knowledge_layer_counts": stats.get("knowledge_layer_counts", {}),
    }


def _expert_status(expert: str, domains: Dict[str, Dict[str, Any]]) -> tuple[str, List[str]]:
    blocking = []
    for domain, summary in domains.items():
        if summary["status"] == "gap":
            blocking.append(domain)
            continue
        if expert in CORE_EXPERTS and summary["can_write_core"] and summary["source_coverage_ratio"] < MIN_SOURCE_RATIO_FOR_CORE:
            blocking.append(domain)
    if blocking:
        return "blocked", blocking
    if any(summary["status"] in {"partial", "weak_partial"} for summary in domains.values()):
        return "partial", []
    return "covered", []


def build_expert_coverage_report(coverage_rows: List[Dict[str, Any]], chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    chunk_stats = _index_chunks(chunks)
    row_by_domain = {str(row["domain_pack"]): row for row in coverage_rows}
    domain_summaries = {
        domain: _domain_summary(row, chunk_stats)
        for domain, row in row_by_domain.items()
    }

    for domain, stats in chunk_stats.items():
        if domain not in domain_summaries:
            domain_summaries[domain] = {
                "domain_pack": domain,
                "status": "runtime_only",
                "can_write_core": False,
                "current_source_count": 0,
                "target_source_count": 0,
                "source_coverage_ratio": 0.0,
                "current_rule_count": 0,
                "target_rule_count": 0,
                "rule_coverage_ratio": 0.0,
                "current_question_count": 0,
                "target_question_count": 0,
                "chunk_count": int(stats.get("chunk_count") or 0),
                "permission_counts": stats.get("permission_counts", {}),
                "quality_tier_counts": stats.get("quality_tier_counts", {}),
                "knowledge_layer_counts": stats.get("knowledge_layer_counts", {}),
            }

    experts = {}
    for expert, domain_names in EXPERT_DOMAIN_MAP.items():
        expert_domains = {
            domain: domain_summaries[domain]
            for domain in domain_names
            if domain in domain_summaries
        }
        status, blocking_domains = _expert_status(expert, expert_domains)
        experts[expert] = {
            "status": status,
            "blocking_domains": blocking_domains,
            "domain_names": list(expert_domains),
            "chunk_count": sum(summary["chunk_count"] for summary in expert_domains.values()),
            "domain_packs": expert_domains,
        }

    global_blockers = sorted(
        domain
        for domain, summary in domain_summaries.items()
        if summary["status"] == "gap" or (summary["can_write_core"] and summary["source_coverage_ratio"] < MIN_SOURCE_RATIO_FOR_CORE)
    )
    return {
        "status": "blocked" if global_blockers else "partial",
        "global_blockers": global_blockers,
        "domain_packs": domain_summaries,
        "experts": experts,
    }
```

- [ ] **Step 4: Run targeted tests**

Run:

```bash
cd "C:/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手" && python -m pytest tests/test_kb_expert_coverage.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/backend/src/marathon_qa_assistant/services/kb/expert_coverage.py tests/test_kb_expert_coverage.py
git commit -m "feat: add expert KB coverage report service"
```

---

### Task 3: Add CLI report generator

**Files:**
- Create: `tools/kb/expert_coverage_report.py`
- Create: `scripts/expert_coverage_report.py`
- Modify: `data/knowledge/governance/expert_coverage_report.json`

- [ ] **Step 1: Add CLI tool**

Create `tools/kb/expert_coverage_report.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from marathon_qa_assistant.services.kb.expert_coverage import build_expert_coverage_report


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in current.parents:
        if (candidate / ".git").exists() and (candidate / "apps").exists():
            return candidate
    return Path.cwd().resolve()


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def build_report_from_paths(coverage_path: Path, chunks_path: Path) -> Dict[str, Any]:
    coverage_rows = json.loads(coverage_path.read_text(encoding="utf-8"))
    chunks = _load_jsonl(chunks_path)
    return build_expert_coverage_report(coverage_rows, chunks)


def main() -> None:
    root = _find_project_root()
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage", default=str(root / "data/knowledge/governance/coverage_matrix.json"))
    parser.add_argument("--chunks", default=str(root / "data/vector_kb/v2/chunks.jsonl"))
    parser.add_argument("--output", default=str(root / "data/knowledge/governance/expert_coverage_report.json"))
    args = parser.parse_args()

    report = build_report_from_paths(Path(args.coverage), Path(args.chunks))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output_path), "status": report["status"], "global_blockers": report["global_blockers"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Add compatibility wrapper**

Create `scripts/expert_coverage_report.py`:

```python
from __future__ import annotations

import importlib.util
import runpy
from pathlib import Path

_TARGET = Path(__file__).resolve().parents[1] / "tools/kb/expert_coverage_report.py"
_SPEC = importlib.util.spec_from_file_location(f"_migrated_{Path(__file__).stem}", _TARGET)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Cannot load migrated script: {_TARGET}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

globals().update({name: value for name, value in vars(_MODULE).items() if not name.startswith("__")})

if __name__ == "__main__":
    runpy.run_path(str(_TARGET), run_name="__main__")
```

- [ ] **Step 3: Run CLI to generate report**

Run:

```bash
cd "C:/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手" && PYTHONPATH="apps/backend/src" python tools/kb/expert_coverage_report.py
```

Expected output includes:

```json
{
  "status": "blocked",
  "global_blockers": [
    "action_library",
    "training_protocols",
    "user_profile_cases"
  ]
}
```

The exact blocker list may include additional domains if their source coverage remains below threshold.

- [ ] **Step 4: Inspect generated report**

Run:

```bash
cd "C:/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手" && python -c "import json; p='data/knowledge/governance/expert_coverage_report.json'; r=json.load(open(p, encoding='utf-8')); print(r['status']); print(r['experts']['coach_node']['status']); print(r['experts']['nutritionist_node']['status'])"
```

Expected: first line `blocked`; `coach_node` should be `blocked`; `nutritionist_node` should be `partial` unless coverage data changes.

- [ ] **Step 5: Commit**

```bash
git add tools/kb/expert_coverage_report.py scripts/expert_coverage_report.py data/knowledge/governance/expert_coverage_report.json
git commit -m "feat: generate expert KB coverage report"
```

---

### Task 4: Add runtime bootstrap verification gate

**Files:**
- Modify: `tests/test_kb_bootstrap.py`

- [ ] **Step 1: Add regression test for current real artifacts**

Append to `tests/test_kb_bootstrap.py`:

```python
def test_real_project_v2_vector_kb_health_is_preview_ready():
    report = kb_bootstrap.probe_vector_kb_health(kb_bootstrap.V2_VECTOR_DIR)

    assert report["ok"] is True
    assert report["source"] == "v2"
    assert report["chunks_count"] == 750
    assert report["index_schema_version"] == "chunk_schema_v2"
    assert report["metadata_completeness"] == 1.0
```

- [ ] **Step 2: Run test**

Run:

```bash
cd "C:/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手" && PYTHONPATH="apps/backend/src" python -m pytest tests/test_kb_bootstrap.py::test_real_project_v2_vector_kb_health_is_preview_ready -v
```

Expected: PASS.

- [ ] **Step 3: Run bootstrap test file**

Run:

```bash
cd "C:/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手" && PYTHONPATH="apps/backend/src" python -m pytest tests/test_kb_bootstrap.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_kb_bootstrap.py
git commit -m "test: verify v2 KB runtime health gate"
```

---

### Task 5: Run final verification and decide next ingestion batch

**Files:**
- No code changes unless tests expose a defect.

- [ ] **Step 1: Run KB-related tests**

Run:

```bash
cd "C:/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手" && PYTHONPATH="apps/backend/src" python -m pytest tests/test_kb_bootstrap.py tests/test_kb_health.py tests/test_vector_kb_health_probe.py tests/test_kb_expert_coverage.py -v
```

Expected: PASS.

- [ ] **Step 2: Run expert coverage report**

Run:

```bash
cd "C:/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手" && PYTHONPATH="apps/backend/src" python tools/kb/expert_coverage_report.py
```

Expected: report generated at `data/knowledge/governance/expert_coverage_report.json`.

- [ ] **Step 3: Record next ingestion targets from report**

Run:

```bash
cd "C:/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手" && python -c "import json; r=json.load(open('data/knowledge/governance/expert_coverage_report.json', encoding='utf-8')); print('\n'.join(r['global_blockers']))"
```

Expected current priority:

```text
action_library
training_protocols
user_profile_cases
```

If additional blockers appear, prioritize them in this order:

1. `action_library` because it writes core workout prescriptions and is only 1/20 sources.
2. `training_protocols` because it writes core training structure and is 7/20 sources.
3. `medical_risk` and `rehab_return_to_run` because they define safety boundaries.
4. `mobility_recovery`, `strength_conditioning`, and `environment_race_context` because they are weak-source support domains.
5. `user_profile_cases` only after privacy/anonymization policy is finalized.

- [ ] **Step 4: Run git status**

Run:

```bash
cd "C:/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手" && git status --short
```

Expected: only intentional files from this plan are modified/untracked.

- [ ] **Step 5: Commit final report refresh if needed**

```bash
git add data/knowledge/governance/expert_coverage_report.json
git commit -m "chore: refresh expert KB coverage report"
```

Skip this commit if the report was already committed in Task 3 and has not changed.

---

## Acceptance Criteria

- `kb_bootstrap.py` can import and call `probe_vector_kb_health` successfully.
- Runtime candidate selection can health-check `data/vector_kb/v2` without loading embeddings.
- `data/knowledge/governance/expert_coverage_report.json` exists and lists per-expert status.
- `coach_node` and `executor_node` are blocked or partial based on actual `training_protocols/action_library` evidence, not guesswork.
- `nutritionist_node`, `adaptive_coach_node`, `therapist_node`, and `research_analyst_node` have explicit status and domain counts.
- Tests pass for vector KB health, bootstrap, KB health schema, and expert coverage report.

## Residual Risks After This Plan

- The report measures existing artifacts; it does not improve source quality by itself.
- v2 contains many `internal_seed_needs_domain_review` chunks, so commercial production still needs source review/approval.
- Real ingestion of new sources should be a separate plan with source registry review, licensing checks, and evaluation questions.
- User profile cases require privacy review before real data can be added.
