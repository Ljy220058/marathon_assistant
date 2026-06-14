# 第十二批证据链增强与动作库候选基础设施 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 固化“证据 tier + 生理公式溯源 + 动作库多候选项 + 文献补齐”的基础设施，避免后续 LLM coach 编造训练参数。

**Architecture:** 先用契约测试锁定已有后端/前端字段，再补缺失的文献与来源标注；动作库候选项只从已检索命中的结构化 card/hits 生成，LLM 只消费候选不直接发明主课。证据层级由后端 `evidence_bundle.py` 推断，前端 `evidenceDrawer.js` 仅渲染和兼容旧数据。

**Tech Stack:** Python 3.12, pytest, FastAPI backend package `marathon_qa_assistant`, Astro/vanilla JS frontend, FAISS vector KB, JSONL chunks.

---

## File Structure

- Modify: `apps/backend/src/marathon_qa_assistant/core/evidence_bundle.py` — 证据层级推断、bundle 输出字段。
- Modify: `apps/web/src/scripts/evidenceDrawer.js` — 证据 tier 前端 fallback 与渲染配置。
- Modify: `apps/backend/src/marathon_qa_assistant/core/physiology.py` — 心率/配速公式来源注释，不能编造 DOI。
- Modify: `apps/backend/src/marathon_qa_assistant/services/daily_schedule_generator.py` — `DailyScheduleItem.alternatives` 与动作库候选生成。
- Modify/Test: `tests/test_evidence_chain_contract.py` — 证据 tier 后端契约。
- Modify/Test: `tests/test_astro_frontend_contract.py` — 前端 evidence tier 文案/配置契约。
- Modify/Test: `tests/test_daily_schedule_generator.py` — alternatives 字段结构与不编造候选。
- Modify/Test: `tests/test_training_plan_context.py` or create `tests/test_physiology_provenance.py` — physiology 注释/编译契约。
- Optional data/docs: `data/vector_kb/v2_sharded/*/chunks.jsonl`, `docs/knowledge_base/periodization_literature_plan.md` — 仅在有全文来源时更新。

---

### Task 1: 锁定 backend evidence_tier 契约

**Files:**
- Modify: `tests/test_evidence_chain_contract.py`
- Modify if failing: `apps/backend/src/marathon_qa_assistant/core/evidence_bundle.py`

- [ ] **Step 1: Add failing tests for evidence tier inference**

Append these tests to `tests/test_evidence_chain_contract.py`:

```python
from marathon_qa_assistant.core.evidence_bundle import build_evidence_bundle


def test_evidence_bundle_infers_scientific_evidence_tier_from_domain_pack():
    bundle = build_evidence_bundle(
        query="半马热身",
        ranked_evidence=[{
            "chunk_id": "pmid-123",
            "source_file": "warmup_pmid_123.md",
            "text": "Warm-up reduces injury risk.",
            "domain_pack": "sports_science",
            "knowledge_layer": "literature",
        }],
    )
    item = bundle["evidence_items"][0]
    assert item["evidence_tier"] == "scientific_evidence"


def test_evidence_bundle_infers_protocol_rule_tier_from_structured_plan():
    bundle = build_evidence_bundle(
        query="半马计划",
        structured_training_plan={
            "half_marathon_protocol_validation": {"active": True, "passed": True},
            "half_marathon_protocol_cards": [{
                "title": "HMP 规则",
                "source": "protocol_rule",
                "summary": "比赛专项阶段容量上限。",
            }],
        },
    )
    assert any(
        item.get("evidence_tier") == "protocol_rule"
        for item in bundle["evidence_items"]
    )
```

- [ ] **Step 2: Run test to verify current behavior**

Run:

```bash
cd C:/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手
python -m pytest tests/test_evidence_chain_contract.py -q --tb=short
```

Expected: PASS if current implementation already covers it; otherwise FAIL on missing `evidence_tier`.

- [ ] **Step 3: Minimal backend fix if needed**

Ensure `_item_from_ranked_evidence()`, `_item_from_rag_source()`, and `_protocol_rule_items()` in `apps/backend/src/marathon_qa_assistant/core/evidence_bundle.py` include:

```python
"evidence_tier": _infer_evidence_tier(source),
```

For protocol items, use:

```python
"evidence_tier": EvidenceTier.PROTOCOL_RULE.value,
```

- [ ] **Step 4: Run test again**

Run:

```bash
python -m pytest tests/test_evidence_chain_contract.py -q --tb=short
```

Expected: PASS.

---

### Task 2: 锁定 frontend evidence_tier 渲染契约

**Files:**
- Modify: `tests/test_astro_frontend_contract.py`
- Modify if failing: `apps/web/src/scripts/evidenceDrawer.js`

- [ ] **Step 1: Add frontend static contract test**

Append to `tests/test_astro_frontend_contract.py`:

```python
from pathlib import Path


def test_evidence_drawer_renders_evidence_tier_labels():
    root = Path(__file__).resolve().parents[1]
    js = (root / "apps/web/src/scripts/evidenceDrawer.js").read_text(encoding="utf-8")
    assert "scientific_evidence" in js
    assert "训练动作参考" in js
    assert "系统规则层" in js
    assert "inferEvidenceTier" in js
    assert "tier_label" in js
    assert "tier_class" in js
```

- [ ] **Step 2: Run frontend contract test**

Run:

```bash
python -m pytest tests/test_astro_frontend_contract.py::test_evidence_drawer_renders_evidence_tier_labels -q
```

Expected: PASS if current implementation already includes these strings.

- [ ] **Step 3: Minimal frontend fix if needed**

In `apps/web/src/scripts/evidenceDrawer.js`, ensure the config exists:

```javascript
const EVIDENCE_TIER_CONFIG = {
  scientific_evidence: { label: "📚 科学文献", cssClass: "tier-scientific" },
  exercise_reference: { label: "🏃 训练动作参考", cssClass: "tier-exercise" },
  protocol_rule: { label: "⚙ 系统规则层", cssClass: "tier-protocol" },
};
```

And normalized items include:

```javascript
evidence_tier: evidenceTier,
tier_label: tierLabel(evidenceTier),
tier_class: tierClass(evidenceTier),
```

- [ ] **Step 4: Run test again**

Run:

```bash
python -m pytest tests/test_astro_frontend_contract.py::test_evidence_drawer_renders_evidence_tier_labels -q
```

Expected: PASS.

---

### Task 3: physiology.py 溯源守护测试

**Files:**
- Create: `tests/test_physiology_provenance.py`
- Modify if failing: `apps/backend/src/marathon_qa_assistant/core/physiology.py`

- [ ] **Step 1: Write provenance tests**

Create `tests/test_physiology_provenance.py`:

```python
from pathlib import Path


def test_physiology_documents_lthr_and_t_pace_sources():
    root = Path(__file__).resolve().parents[1]
    text = (root / "apps/backend/src/marathon_qa_assistant/core/physiology.py").read_text(encoding="utf-8")
    assert "Joe Friel" in text
    assert "ACSM" in text or "Garber" in text
    assert "Daniels" in text
    assert "[coaching_practice]" in text
    assert "[utility]" in text


def test_physiology_module_compiles():
    import py_compile
    root = Path(__file__).resolve().parents[1]
    py_compile.compile(str(root / "apps/backend/src/marathon_qa_assistant/core/physiology.py"), doraise=True)
```

- [ ] **Step 2: Run tests**

Run:

```bash
python -m pytest tests/test_physiology_provenance.py -q
```

Expected: PASS if current file already has honest source notes.

- [ ] **Step 3: Minimal docstring fix if needed**

In `apps/backend/src/marathon_qa_assistant/core/physiology.py`, ensure module docstring and `calculate_hr_zones()` / `calculate_pace_zones()` mention:

```python
"""
出处：
- Joe Friel ... LTHR / T-Pace 框架。
- Garber et al. 2011 / ACSM ... 通用运动处方强度分级。
- Jack Daniels ... VDOT / 配速区间体系。
- 本系统 9 区具体百分比为 [coaching_practice]，不是单一论文公式。
"""
```

Do not add DOI unless the source has been verified locally or in PubMed.

- [ ] **Step 4: Run tests again**

Run:

```bash
python -m pytest tests/test_physiology_provenance.py -q
```

Expected: PASS.

---

### Task 4: 动作库 alternatives 字段结构契约

**Files:**
- Modify: `tests/test_daily_schedule_generator.py`
- Modify if failing: `apps/backend/src/marathon_qa_assistant/services/daily_schedule_generator.py`

- [ ] **Step 1: Add alternatives structure test**

Append to `tests/test_daily_schedule_generator.py`:

```python
from marathon_qa_assistant.services.daily_schedule_generator import DailyScheduleItem


def test_daily_schedule_item_serializes_alternatives():
    item = DailyScheduleItem(
        date="2026-06-07",
        day_label="周日",
        week_index=1,
        day_index=7,
        phase="基础期",
        training_type="轻松跑",
        training_type_label="轻松跑",
        workout_type="easy_run",
        zone_range="Z1-Z2",
        zone_label="低强度",
        intensity_target="轻松",
        main_set="30分钟轻松跑",
        warmup="10分钟热身",
        cooldown="10分钟冷身",
        alternative="",
        training_objective="恢复",
        evidence_tier="exercise_reference",
        evidence_tier_label="训练动作参考",
        alternatives=[{
            "warmup": "8分钟热身",
            "main_set": "25分钟轻松跑",
            "cooldown": "8分钟冷身",
            "zone_range": "Z1-Z2",
            "source_chunk_id": "action-library-easy-1",
            "reason": "同类型低强度备选",
        }],
    )
    data = item.to_dict()
    assert data["alternatives"][0]["main_set"] == "25分钟轻松跑"
    assert data["alternatives"][0]["source_chunk_id"] == "action-library-easy-1"
```

- [ ] **Step 2: Run test**

Run:

```bash
python -m pytest tests/test_daily_schedule_generator.py::test_daily_schedule_item_serializes_alternatives -q
```

Expected: PASS if dataclass already has `alternatives` and `to_dict()` uses `asdict()`.

- [ ] **Step 3: Minimal implementation if needed**

In `DailyScheduleItem`, add:

```python
alternatives: List[Dict[str, Any]] = field(default_factory=list)
```

No generator should fabricate alternatives when there are no hits; use `alternatives=[]`.

- [ ] **Step 4: Run all daily schedule tests**

Run:

```bash
python -m pytest tests/test_daily_schedule_generator.py -q --tb=short
```

Expected: PASS.

---

### Task 5: 多候选项不编造规则测试

**Files:**
- Modify: `tests/test_daily_schedule_generator.py`
- Modify if failing: `apps/backend/src/marathon_qa_assistant/services/daily_schedule_generator.py`

- [ ] **Step 1: Add no-fabrication test for fallback cards**

Append:

```python
from marathon_qa_assistant.services.daily_schedule_generator import _build_alternatives_from_hits


def test_build_alternatives_from_empty_hits_returns_empty_list():
    assert _build_alternatives_from_hits([], "easy_run", "Z1-Z2") == []
```

- [ ] **Step 2: Run test**

Run:

```bash
python -m pytest tests/test_daily_schedule_generator.py::test_build_alternatives_from_empty_hits_returns_empty_list -q
```

Expected: PASS. If function signature differs, inspect current signature and update the test to match actual parameter names without changing production behavior.

- [ ] **Step 3: Minimal implementation if needed**

In `_build_alternatives_from_hits()`, ensure first guard is:

```python
if not hits:
    return []
```

- [ ] **Step 4: Run related tests**

Run:

```bash
python -m pytest tests/test_daily_schedule_generator.py tests/test_workout_template_retriever.py -q --tb=short
```

Expected: PASS.

---

### Task 6: 文献补齐只做“可验证入库”，不伪造全文

**Files:**
- Modify only if full text is available: `data/vector_kb/v2_sharded/*/chunks.jsonl`
- Modify: `docs/knowledge_base/periodization_literature_plan.md`
- Optional: `docs/audits/accepted_limitations.md`

- [ ] **Step 1: Add literature acquisition checklist doc section**

Append to `docs/knowledge_base/periodization_literature_plan.md`:

```markdown
## 第十二批文献补齐准入规则

- Behm & Chaouachi (2011): 仅在拿到全文 PDF 或开放全文 HTML 后入库；否则只登记为待获取。
- Garber et al. (2011) / ACSM: 仅用于通用运动处方背景，不覆盖系统内 9 区百分比。
- Llanos-Lagos et al. (2024): 用于力量训练对跑步表现的证据包，不直接生成跑步主课参数。
- Nédélec et al. (2015) 或同等级恢复/睡眠共识：用于恢复建议，不直接替代医学建议。

入库前必须满足：source_url、source_title、year、authors、full_text_available=true、domain_pack=sports_science。
```

- [ ] **Step 2: Run docs grep sanity check**

Run:

```bash
rg -n "第十二批文献补齐准入规则|full_text_available=true" docs/knowledge_base/periodization_literature_plan.md
```

Expected: both strings appear.

- [ ] **Step 3: If no full text is locally available, do not modify KB data**

Record limitation in `docs/audits/accepted_limitations.md`:

```markdown
## 第十二批：文献补齐未入库项

未拿到全文的文献不生成详细 chunk，不进入核心处方证据链；只允许作为待获取清单。
```

- [ ] **Step 4: If full text is available, rebuild vector index**

Only after adding verified chunks, run:

```bash
bash tools/kb/rebuild_faiss.sh
python apps/backend/src/marathon_qa_assistant/services/vector_store.py --mode test --vector-dir data/vector_kb/v2_sharded/training_protocol --query "马拉松热身拉伸"
```

Expected: retrieval output includes at least one new `sports_science` chunk.

---

### Task 7: Regression verification matrix

**Files:**
- No code changes unless failures are traced to this batch.

- [ ] **Step 1: Run backend contract tests**

Run:

```bash
python -m pytest \
  tests/test_evidence_chain_contract.py \
  tests/test_daily_schedule_generator.py \
  tests/test_physiology_provenance.py \
  tests/test_astro_frontend_contract.py \
  -q --tb=short
```

Expected: PASS.

- [ ] **Step 2: Run training safety smoke tests**

Run:

```bash
python -m pytest \
  tests/test_volume_allocation.py \
  tests/test_half_marathon_validator.py \
  tests/test_half_marathon_capacity_budget.py \
  tests/test_state_models.py \
  -q --tb=short
```

Expected: PASS.

- [ ] **Step 3: Check diff scope**

Run:

```bash
git diff --stat HEAD
```

Expected: changed files limited to tests, `evidence_bundle.py`, `evidenceDrawer.js`, `physiology.py`, `daily_schedule_generator.py`, and docs/data only if Task 6 had verified full text.

---

## Self-Review

- Spec coverage: Task 1-2 cover evidence tier backend/frontend; Task 3 covers physiology provenance; Task 4-5 cover action-library alternatives; Task 6 covers literature expansion without fake full text; Task 7 covers verification.
- Placeholder scan: no TBD/TODO/“implement later” placeholders remain.
- Type consistency: `evidence_tier`, `tier_label`, `tier_class`, and `alternatives` match current code field names.
