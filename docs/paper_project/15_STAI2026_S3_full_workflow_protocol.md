# STAI 2026 S3 Full Workflow 协议草图

## 1. 目标

S3 的目标不是简单“多加一个 prompt”，而是把安全敏感健身建议拆成可审计的 agentic RAG 工作流：

1. 检索证据。
2. 证据门控判断是否足以回答。
3. 生成带证据约束的答案。
4. 独立审计答案中的 claim、引用和风险建议。
5. 若审计失败，执行 repair 或拒答。

## 2. 与 S1 的差异

| 维度 | S1 Vanilla RAG | S3 Full Workflow |
|---|---|---|
| 检索 | Top-k context 直接进 prompt | Top-k context 先进入 evidence gate |
| 证据不足 | 由生成模型自行判断 | Evidence Gate 显式给出 `answerable/unanswerable/partial` |
| 风险题 | 只靠 prompt 安全提示 | Risk Gate 强制检查红旗症状、降级和转诊 |
| 引用 | 生成模型自由引用 | Citation Validator 检查引用是否对应 chunk_id |
| 审计 | 无独立审计 | Independent Auditor 拆 claim 并判 support/risk |
| 修复 | 无 | 若 unsupported/unsafe/invalid citation，进入 repair/refusal |

## 3. 输入 Schema

每个样本输入：

```json
{
  "qid": "STAI-P010",
  "category": "risk_safety",
  "question": "...",
  "evidence_id": "R11-E01",
  "safety_required": true,
  "retrieved_contexts": [
    {
      "rank": 1,
      "chunk_id": "...",
      "source_file": "...",
      "page": 1,
      "score": 0.61,
      "text": "..."
    }
  ]
}
```

## 4. Agent 节点

### 4.1 Evidence Gate

职责：

- 判断检索上下文是否足以回答原问题。
- 给出必须使用的 chunk 列表。
- 发现上下文无关、截断不足或证据冲突时阻断生成。

输出：

```json
{
  "gate_status": "answerable | partial | unanswerable",
  "required_chunks": ["chunk_id"],
  "missing_evidence": ["需要但缺失的信息"],
  "answer_constraints": ["只能回答定义", "不能泛化到所有跑者"],
  "notes": ""
}
```

### 4.2 Risk Gate

仅当 `safety_required=true` 时启用。

职责：

- 识别红旗症状：意识混乱、中暑迹象、胸痛、晕厥、明显心悸、已知心血管疾病等。
- 要求答案包含停止高风险行为、保守降级、专业/医疗评估。
- 禁止生成高强度训练处方。

输出：

```json
{
  "risk_level": "low | caution | high",
  "required_safety_actions": ["stop_activity", "cool_down", "medical_referral"],
  "forbidden_advice": ["continue_original_plan", "increase_intensity"],
  "notes": ""
}
```

### 4.3 Evidence-Constrained Answer Generator

职责：

- 只使用 Evidence Gate 允许的 chunk。
- 对缺证据部分明确拒答。
- 引用格式必须为 `[chunk_id, p.page]`。

输出：

```json
{
  "draft_answer": "...",
  "used_citations": [
    {"chunk_id": "...", "page": 1}
  ]
}
```

### 4.4 Independent Auditor

职责：

- 将答案拆成 claim。
- 检查 claim 是否被 used citations 支持。
- 检查风险建议是否满足 Risk Gate。
- 检查引用是否真实存在于 retrieved_contexts。

输出：

```json
{
  "audit_status": "pass | repair_required | refuse_required",
  "claims": [
    {
      "claim_id": "C1",
      "claim_text": "...",
      "support_status": "supported | partially_supported | unsupported | contradicted | not_applicable",
      "risk_status": "safe | caution | unsafe | not_applicable",
      "evidence": ["chunk_id"]
    }
  ],
  "invalid_citations": [],
  "repair_instructions": []
}
```

### 4.5 Repair / Refusal

触发条件：

- Evidence Gate 为 `unanswerable`。
- Auditor 发现 unsupported/contradicted claim。
- Auditor 发现 unsafe advice。
- Citation Validator 发现无效引用。

输出：

```json
{
  "final_answer": "...",
  "repair_action": "removed_unsupported_claims | added_safety_deescalation | refused_due_to_insufficient_evidence",
  "final_status": "answered | partial_answer | refused"
}
```

## 5. 运行产物

S3 每题必须保存完整 trace：

```json
{
  "qid": "...",
  "retrieved_contexts": [],
  "evidence_gate": {},
  "risk_gate": {},
  "draft_generation": {},
  "audit": {},
  "repair": {},
  "final_answer": "...",
  "final_status": "answered | partial_answer | refused"
}
```

## 6. 第一版实现建议

第一版不接入复杂多 agent 框架，先用单脚本顺序执行节点：

1. `run_stai_s3_full_workflow.py`
2. 读取同一份 benchmark JSONL。
3. 复用 `vector_store.retrieve`。
4. 每个节点调用 `qwen2.5:latest`，但节点 prompt 分离。
5. 每题逐条落盘，避免长运行失败后丢结果。

## 7. 评估假设

可检验假设：

- H1：S3 相比 S1/S1b，会降低 unsupported claim rate。
- H2：S3 相比 S1/S1b，会提高风险题 safe de-escalation rate。
- H3：S3 可能提高 refusal rate，但这些 refusal 更可解释，因为 trace 中有 Evidence Gate 或 Risk Gate 原因。

## 8. 消融连接

后续消融：

- A3 w/o Evidence Gate：直接生成，但保留 Auditor。
- A4 w/o Independent Auditor：保留 Evidence Gate，但无独立审计。
- A5 w/o Repair：发现问题后不修复，只记录审计失败。

这三组可以直接验证“agent workflow”是否是论文的实质创新点，而不是普通 RAG prompt engineering。
