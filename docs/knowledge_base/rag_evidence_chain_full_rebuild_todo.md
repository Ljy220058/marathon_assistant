# RAG Evidence Chain Full Rebuild TODO

> 工作目录：`C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手`
>
> 目标：彻底修复“后端有来源但前端显示为知识库片段/页码未标注/无摘录”的问题，并把检索、证据链、健康态、前端 EvidenceDrawer、自动化测试和回归脚本收敛成可验收闭环。
>
> 执行原则：TDD 优先；保护当前未提交改动；禁止 `git add .`；不得提交 `data/vector_kb/**`、本地 profile、缓存、截图或临时产物；普通用户层不得暴露 `source_path/local_path/internal ids/retrieval_score`。

## 0. 当前根因

- 后端 `evidence_chain.items` 已返回 `source_label/text_span/chunk_id/expert_metadata.source_path/display_mode/user_facing_summary`，但前端 `evidenceDrawer.js` 只读取旧字段 `source_file/file/source_path/source/document/quote/excerpt/text/content/summary`，导致 UI 兜底显示“知识库片段 / 页码未标注 / 后端暂未返回摘录”。
- 后端 `evidence_chain.py` 在 runtime 不允许 verified vector source 时，会把 `verified_source` 降级为 `legacy_explanation` 并清空 `page/section/source_url`，导致即使 `chunk_id` 中含 `_p0003_` 也无法展示定位页码。
- `core/evidence_bundle.py::_normalize_health()` 当前只投影 `kb_ready/source/chunks_count/faiss_ready`，没有保留 `index_schema_version/metadata_completeness/runtime_core_prescription_enabled`，使 evidence display boundary 依赖的 health 信息容易丢失。
- 图谱/registry 命中与正文 chunk 命中混在一起；graph-only evidence 应该是 `graph_hint`，不能显示为 verified citation，但正文 chunk 应尽可能保留可解释来源、页码推断和文本摘录。

## 1. 总体验收标准

- [ ] `/query` 返回的 `evidence_chain.items` 中，正文 chunk 至少能稳定给出 `source_label`、`text_span`、`chunk_id`、`display_mode`、`user_facing_summary`，并在可推断时给出 `page` 或 `page_hint`。
- [ ] legacy/runtime preview 下，KB hit 不得被称为“已验证商用处方来源”，但可以显示为“旧知识库解释性来源/预览知识库解释性来源”，且保留用户可理解的来源名称、摘录、页码提示。
- [ ] verified source 仍必须满足 `source_url` 且有 `page` 或 `section`；只有 verified source 可以作为可点击 citation badge。
- [ ] `model_general_knowledge`、`needs_evidence`、`graph_hint`、`legacy_explanation` 均有明确中文展示文案，不再落入“知识库片段”兜底。
- [ ] 前端 EvidenceDrawer 优先读取 canonical `evidence_chain.items`，兼容旧字段，但不展示 `source_path/local_path/expert_metadata`。
- [ ] health payload 在 `/query`、`evidence_chain` 和 `rag_health` 中一致包含 `index_schema_version/metadata_completeness/runtime_core_prescription_enabled/commercial_core_prescription_enabled`。
- [ ] 自动化测试覆盖：字段映射、页码推断、legacy 降级保留展示定位、graph-only 不生成 citation、source_path 不泄漏、health gate、前端 build。
- [ ] 提供一条本地回归命令，可快速验证这个 bug 不会复发。

## 2. Agent 分工

### Agent A：Backend Contract & Health Gate

**目标：** 修复后端 canonical evidence DTO 与 runtime health 传递，保证 legacy 降级不再丢失用户展示所需的非敏感定位信息。

**重点文件：**
- `apps/backend/src/marathon_qa_assistant/services/kb/evidence_chain.py`
- `apps/backend/src/marathon_qa_assistant/core/evidence_bundle.py`
- `apps/backend/src/marathon_qa_assistant/apps/response_builders.py`
- `apps/backend/src/marathon_qa_assistant/apps/schemas.py`
- `tests/test_evidence_chain_contract.py`
- `tests/test_rag_metadata_preservation.py`
- `tests/test_kb_health.py`

**TODO：**
- [ ] 先写失败测试：legacy runtime 降级后，item 仍保留 `source_label/text_span/chunk_id`，并新增普通层安全字段 `page_hint` 或 `locator_hint`。
- [ ] 先写失败测试：`chunk_id="2016+-+Nutrition+for+Marathon+Running_p0003_c0002"` 且 `page=None` 时，canonical item 能推断 `page_hint=3`，但 `page` 仍只在 verified source 时作为真实页码。
- [ ] 先写失败测试：`expert_metadata.source_path` 不进入 public projection，`source_path_leak_count=0`。
- [ ] 先写失败测试：`_normalize_health()` 保留 `index_schema_version/metadata_completeness/runtime_core_prescription_enabled`。
- [ ] 实现 `_infer_page_from_chunk_id()`，支持 `_p0003_`、`p0028`、`page_12` 等稳定模式；不要从任意数字误判。
- [ ] 在 `evidence_chain_item_from_bundle_item()` 中新增 `page_hint` 和 `locator_hint`，用于普通层展示“页码提示/章节提示/片段 ID 提示”。
- [ ] 修改 `_apply_runtime_display_boundaries()`：降级时清空可点击 verified 字段 `source_url/page/section`，但保留 `page_hint/locator_hint/source_label/text_span/chunk_id/user_facing_summary`。
- [ ] 修改 `_normalize_health()`：不丢 runtime schema 和 metadata completeness。
- [ ] 确保 `answer_source_mode` 推断不因 legacy explanation 误判为 verified_rag。

**验收命令：**
```bash
cd /c/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手
PYTHONUTF8=1 PYTHONPATH=apps/backend/src python -m pytest tests/test_evidence_chain_contract.py tests/test_rag_metadata_preservation.py tests/test_kb_health.py -q
```

### Agent B：Frontend EvidenceDrawer Canonical Rendering

**目标：** 前端证据抽屉优先消费 `evidence_chain.items`，兼容后端 canonical 字段和旧字段，杜绝假来源与本地路径泄漏。

**重点文件：**
- `apps/web/src/scripts/evidenceDrawer.js`
- `apps/web/src/scripts/app.js`
- `apps/web/src/styles/evidence.css`
- `tests/test_astro_frontend_contract.py`

**TODO：**
- [ ] 先写失败测试或前端 contract 断言：`source_label/text_span/page_hint/display_mode/user_facing_summary` 能被渲染，不再显示“知识库片段/页码未标注”。
- [ ] `normalizeEvidencePages()` 优先读取 canonical 字段：`source_label`、`text_span`、`page_hint`、`locator_hint`、`display_mode`、`user_facing_summary`。
- [ ] 兼容 `expert_metadata.source_path` 仅用于内部判断，不展示。
- [ ] 增加 display mode 中文映射：
  - `verified_source`：可定位来源
  - `legacy_explanation`：旧知识库解释性来源
  - `graph_hint`：图谱关联线索
  - `model_general_knowledge`：模型常识说明
  - `needs_evidence`：待补证据
  - `rejected_source`：已阻断来源
- [ ] 当没有 `source_url + page/section` 时，不显示可点击 citation badge；只显示来源卡片和定位提示。
- [ ] `resolveEvidenceItemsForDrawer()` 支持从 `response.evidence_chain.items` 获取 canonical items，并按 `day.evidence_ids/evidence_refs/field_sources` 做关联；无法关联时可展示全局相关 evidence，但必须标注来源状态。
- [ ] 所有 UI 文案使用中文，避免暴露 backend raw enum 给普通用户。

**验收命令：**
```bash
cd /c/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手
PYTHONUTF8=1 PYTHONPATH=apps/backend/src python -m pytest tests/test_astro_frontend_contract.py -q
cd apps/web && npm run build
```

### Agent C：Graph/Retrieval Regression & Acceptance Gate

**目标：** 补齐 graph-only、retrieval metadata、health gate 和端到端回归脚本，形成最终验收报告。

**重点文件：**
- `apps/backend/src/marathon_qa_assistant/services/kb/graph_evidence.py`
- `apps/backend/src/marathon_qa_assistant/services/knowledge_graph.py`
- `apps/backend/src/marathon_qa_assistant/nodes/profile_and_retrieval.py`
- `tests/test_kb_graph_evidence.py`
- `tests/test_evidence_chain_contract.py`
- `tools/kb/verify_evidence_chain_regression.py`（如不存在则新建）

**TODO：**
- [ ] 先写失败测试：graph-only evidence 没有 `source_url/page/section/chunk_id` 时为 `graph_hint`，且没有可点击 citation。
- [ ] 先写失败测试：fusion hit 只有 vector side 有 locator anchor 时才可显示 verified/located source。
- [ ] 先写失败测试：retrieval metadata round-trip 不丢 `source_registry_id/source_url/section/evidence_domain/prescription_permission/quality_tier/review_status`。
- [ ] 新增最小回归脚本 `tools/kb/verify_evidence_chain_regression.py`，构造 3 类 payload：verified、legacy chunk、graph hint，并输出 JSON summary。
- [ ] 回归脚本检查：`source_path_leak_count=0`、legacy item 有 `source_label/text_span/page_hint`、graph item display mode 正确、fake citation gate 生效。
- [ ] 脚本返回码：全部通过为 0；任一 gate fail 为 1。

**验收命令：**
```bash
cd /c/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手
PYTHONUTF8=1 PYTHONPATH=apps/backend/src python -m pytest tests/test_kb_graph_evidence.py tests/test_evidence_chain_contract.py tests/test_rag_metadata_preservation.py -q
PYTHONUTF8=1 PYTHONPATH=apps/backend/src python tools/kb/verify_evidence_chain_regression.py
```

## 3. 最终总验收命令

```bash
cd /c/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手
PYTHONUTF8=1 PYTHONPATH=apps/backend/src python -m pytest tests/test_evidence_chain_contract.py tests/test_rag_metadata_preservation.py tests/test_kb_graph_evidence.py tests/test_kb_health.py tests/test_astro_frontend_contract.py -q
PYTHONUTF8=1 PYTHONPATH=apps/backend/src python tools/kb/verify_evidence_chain_regression.py
cd apps/web && npm run build
```

## 4. 完成记录

- [ ] Agent A 完成并通过验收。
- [ ] Agent B 完成并通过验收。
- [ ] Agent C 完成并通过验收。
- [ ] Controller 完成最终回归并给出验收结论。
