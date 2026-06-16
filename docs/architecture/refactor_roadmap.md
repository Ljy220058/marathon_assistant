# 训练计划生成重构路线图

> 创建日期：2026-06-04
> 总目标：消除硬编码训练模板，建立 RAG-driven + LLM 教练决策的课表生成管线
> 验收准则：每项任务有独立验收标准，不达标必须重做

---

## 第一阶段：数据基础（先补数据，再动架构）

### Task 1 — 补齐动作库字段

**目标**：当前 21 条动作库记录中，`zone_range` 依赖硬编码 `CATEGORY_ZONE_MAP` 推断，缺独立 `warmup`/`cooldown` 字段。改造提取脚本，从 PDF 原文解析完整字段。

**改造文件**：`scripts/extract_action_library.py`

**验收标准**：
- [ ] 每条记录的 `zone_range` 优先来自 PDF 原文，`CATEGORY_ZONE_MAP` 仅作后备
- [ ] 每条记录新增 `warmup_suggestion` 字段（从 PDF 原文解析，空则 `null`）
- [ ] 每条记录新增 `cooldown_suggestion` 字段（从 PDF 原文解析，空则 `null`）
- [ ] 重新运行 `python scripts/extract_action_library.py`，输出 21 条记录均含以上字段
- [ ] `action_library_chunks.jsonl` 和 `chunks.jsonl` 同步更新
- [ ] 运行 `pytest tests/test_daily_schedule_generator.py -v` 全部通过
- [ ] 如 PDF 原文确实没有热身/冷身内容，字段为 `null`，不编造数据

**重做条件**：任一条验收标准不满足 → 重做本项。

---

### Task 2 — 添加热身/冷身/力量/恢复权威文献

**目标**：当前 KB 缺热身、冷身、力量训练、恢复/睡眠的同行评审文献。下载 → MD 清洗 → 追加到 v2 chunks 并重建 FAISS。

**需下载文献**：
1. Behm & Chaouachi (2011) — 动静拉伸急性效应综述
2. Garber et al. (2011) — ACSM 运动处方框架（如有动作库未覆盖部分）
3. Llanos-Lagos et al. (2024) — 力量训练对跑步表现 meta 分析
4. 一篇恢复/睡眠共识声明（如 Nédélec et al. 2015 恢复策略）

**验收标准**：
- [ ] 每篇文献下载完整 PDF（或至少能获取全文）
- [ ] PDF → MD 清洗（`scripts/convert_docs.py` 或等效管道）
- [ ] MD 追加到 `data/vector_kb/v2/chunks.jsonl`（chunk_id 格式与现有一致）
- [ ] FAISS 索引重建成功：`python apps/backend/src/marathon_qa_assistant/services/vector_store.py --mode build --vector-dir data/vector_kb/v2`
- [ ] 验证检索：用"马拉松热身拉伸"、"力量训练跑步"、"训练后恢复"分别检索，至少各命中 1 条新文献 chunk
- [ ] 每条新文献 chunk 的 `domain_pack` 字段不为空（如 `sports_science`）

**重做条件**：任一篇文献未能完整入库 → 该篇单独重做；FAISS 重建失败 → 整体重做。

---

### Task 3 — physiology.py 公式文献溯源

**目标**：给 `ZONE_LTHR_PCT`、`calculate_pace_zones`、心率→配速映射等计算函数标注出处。

**改造文件**：`apps/backend/src/marathon_qa_assistant/core/physiology.py`

**验收标准**：
- [ ] 每个函数/常量的 docstring 或行内注释标注文献出处
- [ ] 格式：`出处：作者 (年份), 章节/公式编号，DOI`
- [ ] 没有学术出处的，标注 `[coaching_practice]` 或 `[expert_consensus]`
- [ ] 标注不得编造——每个标注必须能在 KB 或 PubMed 中验证
- [ ] `python -m py_compile` 通过，不破坏现有 API

**重做条件**：标注无法验证 → 重做该标注；模块编译失败 → 重做。

---

### Task 4 — 证据 tier 标注 + 前端渲染

**目标**：证据分为三档 (`scientific_evidence` / `exercise_reference` / `protocol_rule`)，前端可视化区分。

**改造文件**：
- `apps/backend/src/marathon_qa_assistant/core/evidence_bundle.py` — 新增 `evidence_tier` 字段
- `apps/web/src/scripts/evidenceDrawer.js` — 前端渲染 tier 标签
- `apps/web/src/styles/evidence.css` — 新增 tier 样式

**验收标准**：
- [ ] `evidence_bundle.py` 中每个 evidence item 带 `evidence_tier` 字段
- [ ] tier 推导逻辑：`source_file` 含 DOI/PMID → `scientific_evidence`；含"动作库" → `exercise_reference`；来自 `protocol_rule`/`_ADAPTIVE_RULE_LIBRARY` → `protocol_rule`
- [ ] 前端 drawer 中每条证据左侧/顶部有颜色标签
- [ ] `scientific_evidence` 标签显示 DOI/PMID 外链（蓝色）
- [ ] `exercise_reference` 标签显示"训练动作参考"（绿色）
- [ ] `protocol_rule` 标签显示"系统规则层"（灰色）
- [ ] 无 tier 的旧数据在 `normalizeEvidencePages` 中自动推断
- [ ] `npm run build`（或等效前端构建）成功

**重做条件**：前后端 tier 字段不一致 → 重做；标签颜色/文案与预期不符 → 重做前端。

---

## 第二阶段：去除硬编码

### Task 5 — 删除 TRAINING_DISTANCE_FRACTIONS 和 FIXED_WARMUP_COOLDOWN 硬编码

**目标**：热身/冷身从动作库读取，距离比例从训练原则文献规则动态计算。

**改造文件**：`apps/backend/src/marathon_qa_assistant/core/training_plan_skeleton.py`

**验收标准**：
- [ ] `TRAINING_DISTANCE_FRACTIONS` 常量删除或标记为 `[deprecated]` fallback
- [ ] `FIXED_WARMUP_COOLDOWN` 常量删除或标记为 `[deprecated]` fallback
- [ ] `_main_km_for_type` 距离比例来源改为从文献规则动态计算（基于用户周跑量 × 训练类型系数）
- [ ] 热身/冷身距离调用 `workout_template_retriever.get_action_library_foundation_hits()` 读取
- [ ] 动作库无匹配时有降级策略（日志 warn + 使用保守默认值，不崩）
- [ ] 运行 `pytest tests/ -k "skeleton" -v` 全部通过（如无对应测试则运行全量）
- [ ] `python -m py_compile` 通过

**重做条件**：任一处仍直接引用已删除的硬编码常量 → 重做。降级策略缺失 → 重做。

---

### Task 6 — 骨架解耦：删除 session builder 中的硬编码训练参数

**目标**：保留训练类型选择逻辑，删除 `main_set` 硬编码字符串，改为输出约束描述。

**改造文件**：`apps/backend/src/marathon_qa_assistant/core/training_plan_skeleton.py`

**涉及函数**：
- `_build_quality_session` (~120 行)
- `_build_secondary_session` (~90 行)
- `_build_long_run_main_set` (~190 行)

**验收标准**：
- [ ] 三个函数不再返回硬编码的 `main_set` 文本（如 "12×400m @5K 配速"）
- [ ] 改为返回约束描述：`{workout_type, zone_range, target_duration_min, phase_context, intensity_hint}`
- [ ] 调用方（`daily_schedule_generator`）用约束从动作库检索具体课表候选项
- [ ] 训练类型选择逻辑（"base 期第 3 周 → 间歇跑"）保留不变
- [ ] 运行 `pytest tests/ -k "skeleton or plan" -v` 全部通过
- [ ] 生成一份示例计划，人工抽查：每个训练日的 `main_set` 能追溯到动作库 chunk

**重做条件**：任一处仍输出硬编码 `main_set` → 重做。训练类型选择逻辑被破坏 → 重做。

---

### Task 7 — daily_schedule_generator 支持多候选项返回

**目标**：一个训练日返回主选 + N 个备选，LLM 教练节点从候选中做最终选择。

**改造文件**：`apps/backend/src/marathon_qa_assistant/services/daily_schedule_generator.py`

**验收标准**：
- [ ] `DailyScheduleItem` 新增 `alternatives: List[Dict]` 字段
- [ ] 每个候选项包含完整的 warmup/main_set/cooldown/zone_range
- [ ] 候选项来源为动作库中同一训练类型的不同 `content: a/b/c` 变体
- [ ] 无变体时 `alternatives` 为空列表（不崩，不编造）
- [ ] 运行 `pytest tests/test_daily_schedule_generator.py -v` 全部通过
- [ ] 新增测试：验证 `alternatives` 字段结构完整

**重做条件**：`alternatives` 包含重复项或来源不对 → 重做。

---

## 第三阶段：协议与查询可追溯性

### Task 8 — 半马协议层与动作库统一

**目标**：`half_marathon_protocol.py` 的 `main_set_candidates` 走同一套动作库查询体系，协议层只输出约束条件。

**改造文件**：
- `apps/backend/src/marathon_qa_assistant/core/half_marathon_protocol.py`
- `apps/backend/src/marathon_qa_assistant/services/workout_template_retriever.py`

**验收标准**：
- [ ] `HMP_WORKOUT_TYPES` 中删除硬编码 `main_set_candidates`
- [ ] 改为输出约束：`{workout_type, phase, zone_constraint, min_duration, max_duration}`
- [ ] 具体课表通过 `workout_template_retriever.get_action_library_foundation_hits()` 统一查询
- [ ] `compose_hmp_week_sessions()` 返回的每周课表可追溯到动作库
- [ ] 运行 `pytest tests/ -k "hmp or half_marathon" -v` 全部通过

**重做条件**：硬编码 `main_set_candidates` 仍有残留 → 重做。

---

### Task 9 — 检索快照落盘 + query 保留

**目标**：保留原始 query，每次检索落 JSON 快照，支持事后 `--replay` 复现。

**改造文件**：
- `apps/backend/src/marathon_qa_assistant/core/state_models.py` — 去掉 `del query`
- `apps/backend/src/marathon_qa_assistant/services/vector_store.py` — 新增 `snapshot_path` 参数
- `apps/backend/src/marathon_qa_assistant/core/profile_and_retrieval.py` — 调用时传 snapshot

**验收标准**：
- [ ] `build_workflow_trace()` 不再删除 `query` 字段
- [ ] `retrieve()` 函数新增可选参数 `snapshot_path: Optional[str] = None`
- [ ] 快照 JSON 包含：`query`、`variants`、`raw_faiss_hits`、`fused_evidence`、`top_k`、`timestamp`
- [ ] 新增 `--replay <snapshot_path>` CLI 参数，读取快照复现检索结果
- [ ] 复现结果与快照中的 `top_k` 一致（允许 FAISS 浮点误差的微小差异）
- [ ] 运行 `python apps/backend/src/marathon_qa_assistant/services/vector_store.py --mode test --vector-dir data/vector_kb/v2 --query "马拉松间歇训练"` 正常

**重做条件**：快照 JSON 缺字段 → 重做。`--replay` 复现结果不一致 → 重做。

---

### Task 10 — LLM 教练节点

**目标**：在 LangGraph 工作流中新增 `llm_coach` 节点，负责在骨架约束 + 动作库候选中做最终选择。

**改造文件**：
- `apps/backend/src/marathon_qa_assistant/nodes/` — 新增 `llm_coach.py`
- `apps/backend/src/marathon_qa_assistant/core/workflow.py` — 注册节点 + 路由
- `apps/backend/src/marathon_qa_assistant/core/state_models.py` — 新增状态字段

**验收标准**：
- [ ] `llm_coach` 节点接收：骨架约束、动作库候选项（主选 + 备选）、证据链、环境上下文
- [ ] 输出：选定的训练卡片 + 决策解释
- [ ] 决策解释逐条绑定到输入源（如 "选了候选 B 因为 today_temp=32°C 叠加上周训练负荷偏高 → 降量保速"）
- [ ] 不编造训练参数——所有输出参数来自输入候选
- [ ] 运行 `pytest tests/ -k "llm_coach" -v` 新增测试通过
- [ ] 如无匹配候选，LLM 节点返回降级方案并标记 `evidence_tier: "needs_evidence"`

**重做条件**：LLM 输出包含不在候选中的训练参数 → 重做。决策解释未绑定输入源 → 重做。

---

### Task 11 — 知识库清理（第一类 + 第二类）

**目标**：删除 AI/HCI 论文（~3,531 片段）和竞品分析文档（~142 片段），重建 FAISS。

**验收标准**：
- [ ] 从 `chunks.jsonl` 删除所有 `domain_pack` 为 `ai_hci` 或 `competitive_analysis` 的条目
- [ ] 删除对应的 `raw_sources/` 和 `domain_packs/` manifest 文件
- [ ] FAISS 索引重建成功
- [ ] 重建后 `chunks.jsonl` 行数从 14,327 减少到预期值（~9,654）
- [ ] 验证检索：马拉松相关查询仍返回有效结果
- [ ] 增量备份：删除的条目归档到 `archive/cleaned_chunks_20260604.jsonl`

**重做条件**：误删马拉松相关 chunk → 从备份恢复，修正过滤条件后重做。

---

## 第四阶段：质量验证

### Task 12 — 证据引用完整性测试

**目标**：自动化测试验证生成的训练计划中每条数据都有真实来源。

**改造文件**：新增 `tests/test_evidence_integrity.py`

**验收标准**：
- [ ] 测试生成一份完整的训练计划（mock 或真实调用）
- [ ] 遍历每个 `DailyScheduleItem` 的 `field_sources`
- [ ] 验证 `main_set` 来源不为空且来自动作库 chunk 或学术文献 chunk
- [ ] 验证 `warmup` 来源不为空
- [ ] 验证 `cooldown` 来源不为空
- [ ] 验证 `intensity` 来源不为空
- [ ] 验证不存在来源为 `null` 但内容是硬编码字符串的情况
- [ ] 测试在 CI 中可运行：`python -m pytest tests/test_evidence_integrity.py -v`
- [ ] 测试失败时明确输出：哪个字段、哪个训练日、缺什么来源

**重做条件**：测试本身有假阳性（通过但实际缺来源）→ 重做。

---

## 执行顺序

```
Phase 1 (可并行)
  ├── Task 1  补齐动作库字段
  ├── Task 2  添加权威文献
  ├── Task 3  physiology.py 文献溯源
  └── Task 4  证据 tier 标注 + 前端渲染

Phase 2 (依赖 Phase 1 完成)
  ├── Task 5  删除 TRAINING_DISTANCE_FRACTIONS / FIXED_WARMUP_COOLDOWN
  ├── Task 6  骨架解耦
  └── Task 7  多候选项返回

Phase 3 (依赖 Phase 2 完成)
  ├── Task 8  半马协议融合
  ├── Task 9  检索快照 + query 保留
  └── Task 10 LLM 教练节点

Phase 4 (依赖 Phase 2-3 完成)
  ├── Task 11 知识库清理
  └── Task 12 证据引用完整性测试
```

---

## 不达标流程

1. 验收标准中任一项不满足 → **该 Task 重做**，不继续下一 Task
2. 重做超过 2 次仍不达标 → 停下来，分析根因，更新本条验收标准或拆分 Task
3. 禁止"先跳过这个标准后面再补"——每个 Task 必须自我闭环
