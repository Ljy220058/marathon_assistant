# Evidence-Gated Agentic RAG 研究平台路线图

## 0. 升级后的目标

当前项目不再只服务于一次 workshop 投稿，而是升级为一个可长期扩展的研究平台雏形：

> A reproducible research platform for evidence-gated, audit-and-repair agentic RAG in safety-sensitive advisory tasks.

耐力训练/马拉松建议仍然是第一个 pilot domain，但系统设计要支持未来扩展到 sleep advice、injury recovery、nutrition safety、academic citation QA 等领域。

## 1. 三个核心模块

| 模块 | 目的 | 为什么重要 |
|---|---|---|
| Benchmark KB | 建立干净、可追踪、可复现的证据库 | 解决当前 S1/S3 大量证据不足和检索失败问题 |
| Experiment Harness | 统一运行 S0/S1/S1b/S3/A3/A4/A5 | 让实验不是零散脚本，而是可比较、可复跑 |
| Trace Viewer | 可视化问题、证据、gate、audit、repair、final answer | 让结果能被人工审阅、展示和调试 |

## 2. Phase A：Benchmark KB

目标：建立一个 benchmark 专用证据库，而不是继续依赖当前混杂的 `vector_kb`。

### A1. Evidence Schema

设计证据条目格式：

```json
{
  "evidence_id": "T12-E01",
  "domain": "endurance_training",
  "topic": "running_economy",
  "source_type": "academic_paper | official_guideline | textbook | race_policy",
  "source_title": "",
  "source_url_or_path": "",
  "page": "",
  "quote": "",
  "paraphrase": "",
  "supports_qids": ["STAI-P007"],
  "risk_category": "",
  "verification_status": "verified | pending | rejected",
  "notes": ""
}
```

输出：

- `docs/paper_project/benchmark_kb/evidence_schema.json`
- `docs/paper_project/benchmark_kb/evidence_items_v0.1.jsonl`

### A2. Evidence Gap Map

把 15 题 benchmark 映射到证据缺口：

| qid | topic | required evidence | current status | priority |
|---|---|---|---|---|

输出：

- `docs/paper_project/19_evidence_gap_to_fill.md`

### A3. Curated Source Collection

优先补三类来源：

1. Training intensity distribution / polarized training / pyramidal training
2. Heat illness / hot weather running safety
3. Cardiovascular red flags / exercise participation safety

要求：

- 不编造文献。
- 必须能定位原文、页码、段落或官方网页。
- 风险题优先官方/权威来源。

输出：

- `docs/paper_project/benchmark_kb/source_registry_v0.1.md`
- `docs/paper_project/benchmark_kb/evidence_items_v0.1.jsonl`

### A4. Evidence Bundle Retrieval

除了向量检索，增加 gold evidence bundle：

- 每个 qid 绑定 gold evidence_ids。
- S3 Evidence Gate 可先看到 gold bundle 或 retrieval+bundle 混合输入。
- 支持检索失败分析：gold evidence exists but retrieval missed。
- 运行模式至少包含 `retrieval_only`、`gold_only`、`retrieval_plus_gold` 三种。

输出：

- `docs/paper_project/benchmark_kb/qid_to_gold_evidence_v0.1.json`
- `scripts/stai_benchmark_kb.py`

当前状态：

- 已完成 P0 Gold Evidence Bundle 接入。
- S3 runner 已支持 `retrieval_only`、`gold_only`、`retrieval_plus_gold`。
- 已完成 `stai_s3_gold_only_50q_run02`，覆盖 50 题。
- 阶段总结见 `docs/paper_project/27_STAI_S3_gold_only_50q_summary.md`。

## 3. Phase B：Experiment Harness

目标：把 S0/S1/S1b/S3/A3/A4/A5 统一成一套实验入口。

### B1. Unified Run Config

设计 config：

```json
{
  "run_id": "",
  "system_id": "S3",
  "dataset": "",
  "kb": "",
  "model": "qwen2.5:latest",
  "retrieval_top_k": 5,
  "context_max_chars": 500,
  "components": {
    "evidence_gate": true,
    "risk_gate": true,
    "auditor": true,
    "repair": true
  }
}
```

输出：

- `configs/stai_experiments/s3_full.json`
- `configs/stai_experiments/a3_without_evidence_gate.json`
- `configs/stai_experiments/a4_without_auditor.json`
- `configs/stai_experiments/a5_without_repair.json`
- 统一 runner 需要读取 benchmark KB gold bundle，并保留 retrieved_contexts / gold_evidence_contexts / evidence_contexts 三层 trace。

### B2. Unified Runner

目标：

- 用一个 runner 跑不同系统配置。
- 每题逐条落盘。
- 每个节点保存 trace。
- 支持 resume。

输出：

- `scripts/run_stai_experiment.py`

### B3. Unified Metrics

目标：

- 支持 S0/S1/S1b/S3/A3/A4/A5 的统一指标表。
- 区分 evidence grounding、safety behavior、citation validity、refusal behavior。

输出：

- `scripts/compute_stai_metrics_unified.py`
- `docs/paper_project/metrics_schema_v0.1.md`

## 4. Phase C：Trace Viewer

目标：让研究过程可看、可审阅、可展示。

### C1. Static HTML Viewer

第一版先做静态 HTML，不引入复杂前端依赖。

功能：

- 选择 qid。
- 并排查看 S1/S1b/S3。
- 展示 retrieved contexts。
- 展示 Evidence Gate / Risk Gate / Auditor / Repair。
- 高亮 final answer 和 citation。

输出：

- `scripts/render_trace_viewer.py`
- `docs/paper_project/trace_viewer/index.html`

### C2. Review UI

第二版可加人工标注界面：

- claim support 下拉选择。
- safety status 下拉选择。
- citation check。
- 导出 reviewed JSONL。

输出：

- 可选：Streamlit/Gradio/local HTML form。

## 5. Phase D：Benchmark Expansion

目标：先从 15 题扩到 50 题，再根据证据补全情况继续扩到 60-100 题。

当前 v0.2 目标配比：

| category | target N | 说明 |
|---|---:|---|
| factual_grounding | 15 | 定义、研究结论、概念 |
| applied_reasoning | 15 | 证据约束下的训练建议 |
| risk_safety | 15 | 高温、心血管、伤病、恢复 |
| evidence_insufficient | 5 | 应拒答或部分回答 |

后续 v0.3 扩展到 60-100 题时，再加入 citation_robustness 和 adversarial_unsafe 的更细分设计：

| category | target N | 说明 |
|---|---:|---|
| factual_grounding | 20 | 定义、研究结论、概念 |
| applied_reasoning | 20 | 证据约束下的训练建议 |
| risk_safety | 25 | 高温、心血管、伤病、恢复 |
| evidence_insufficient | 15 | 应拒答或部分回答 |
| citation_robustness | 10 | 测引用格式和无效引用 |
| adversarial_unsafe | 10 | 用户诱导危险建议 |

输出：

- `docs/paper_project/26_benchmark_v0.2_50题扩展设计.md`
- `docs/paper_project/stai_benchmark_v0.2_50_question_draft.jsonl`
- `docs/paper_project/benchmark_v0.2_questions.jsonl`
- `docs/paper_project/benchmark_v0.2_design.md`

## 6. Phase E：跨领域小验证

若时间充足，增加一个 10 题 mini-domain：

候选：

1. Sleep advice
2. Injury recovery advice
3. Academic citation QA
4. Nutrition safety advice

推荐：Academic citation QA 或 injury recovery advice。

原因：

- Academic citation QA 与“防编造引用”高度一致。
- Injury recovery advice 与当前运动安全域相近，迁移成本低。

输出：

- `docs/paper_project/cross_domain_pilot_design.md`

## 7. 推荐近期执行顺序

当前不急于投稿时，推荐顺序：

1. Phase B：Experiment Harness
2. Phase B/C 之间：Unified Metrics 最小版
3. Phase C：Trace Viewer
4. Phase D：Benchmark Expansion
5. Phase E：Cross-domain pilot

其中 Phase A 的 50 题 benchmark 与 gold evidence bundle 已经形成第一版可运行底座。接下来重点转向统一实验入口、指标和 trace review。

## 8. 最近 5 个具体任务

1. 创建 `benchmark_kb` 目录和 schema。
2. 生成 15 题 evidence gap map。
3. 从现有 `08_v0.1证据段落抽取表.md` 迁移 verified evidence 到 evidence_items JSONL。
4. 为 P001-P015 建立 qid_to_gold_evidence 初版。
5. 修改 S3 runner，使其支持 `retrieval_only`、`gold_evidence_bundle` 和 `retrieval+gold` 三种证据输入模式。
