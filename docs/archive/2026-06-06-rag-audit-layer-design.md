# RAG 审核层设计细化

## 1. rag_auditor_node 的输入与输出

### 输入（从 state 读取）

```python
# 新增节点: rag_auditor_node
# 插入位置: executor → rag_auditor → critic_auditor

async def rag_auditor_node(state: IntegratedState, config: RunnableConfig) -> dict:
    plan = state.get("structured_training_plan", {})
    draft = state.get("draft_plan", "")
    profile = state.get("user_profile", {})
    
    # 提取本周课表
    week_plans = plan.get("week_plans", [])
    current_week = week_plans[0] if week_plans else {}
    days = current_week.get("days", [])
    
    # 提取周期性约束
    constraints = plan.get("weekly_structure_constraints", {})
    validation = plan.get("weekly_structure_validation", {})
    
    # 跑者画像关键字段
    weekly_mileage = profile.get("weekly_mileage", 40)
    experience = profile.get("experience_level", "")
    total_weeks = plan.get("total_weeks", 12)
    ...
```

### 输出（追加到 state）

```python
    return {
        "rag_audit_passed": bool,
        "rag_audit_feedback": str,        # 不通过时的具体理由 + 文献引用
        "rag_audit_score": int,            # 0-100, 综合质量评分
        "rag_audit_dimensions": {          # 每个审核维度的结果
            "session_params": {"passed": bool, "issues": [...]},
            "weekly_combination": {"passed": bool, "issues": [...]},
            "phase_appropriateness": {"passed": bool, "issues": [...]},
            "adjustment_quality": {"passed": bool, "issues": [...]},
        },
        "rag_audit_evidence": [...],       # 本次审核检索到的文献块
        "reasoning_log": [...],
    }
```

---

## 2. RAG 审核的四步流程（具体实现）

### Step 1: 构建审核查询

从生成的课表中提取结构化信息 → 转化为可检索的查询语句。

```python
def _build_audit_queries(week_days, profile, phase_name) -> List[AuditQuery]:
    queries = []
    
    for day in week_days:
        if day.get("is_rest"):
            continue
        
        training_type = day.get("training_type", "")
        workout_type = day.get("workout_type", "")
        duration = _extract_duration(day.get("main_set", ""))
        
        # 每节课生成一个审核查询
        if "节奏跑" in training_type or "tempo" in workout_type:
            queries.append(AuditQuery(
                dimension="session_params",
                query=f"业余跑者 节奏跑 持续时间 {duration}分钟 是否在文献推荐范围",
                context={"day": day, "expected_range": "20-30分钟 (Daniels T区)"},
            ))
        
        if "间歇" in training_type or "interval" in workout_type:
            queries.append(AuditQuery(
                dimension="session_params",
                query=f"间歇训练 组数 组间恢复比 业余跑者",
                context={"day": day, "expected_range": "总高强度时间 <=8分钟 (Daniels I区)"},
            ))
    
    # 周组合查询
    quality_types = [d.get("training_type") for d in week_days if _is_quality(d)]
    queries.append(AuditQuery(
        dimension="weekly_combination",
        query=f"{phase_name} 周课表结构 强度课组合 {' '.join(quality_types)}",
        context={"quality_count": len(quality_types), "phase": phase_name},
    ))
    
    # 调整质量查询（仅当有调整时）
    if _has_adjustments(week_days):
        queries.append(AuditQuery(
            dimension="adjustment_quality",
            query=f"跳课 补课 业余跑者 调整 训练负荷 ACWR",
            context={"adjustments": _list_adjustments(week_days)},
        ))
    
    return queries
```

### Step 2: KB 检索

```python
def _retrieve_audit_evidence(queries: List[AuditQuery]) -> List[AuditEvidence]:
    evidence = []
    for q in queries:
        # 优先 FAISS 向量检索
        try:
            from marathon_qa_assistant.services.vector_store import retrieve
            hits = retrieve(q.query, top_k=3)
        except Exception:
            # JSONL 后备
            hits = _jsonl_keyword_search(q.query, top_k=3)
        
        for h in hits:
            evidence.append(AuditEvidence(
                query=q,
                chunk_id=h.get("chunk_id", ""),
                text=h.get("text", "")[:600],
                source_file=h.get("source_file", ""),
                score=h.get("score", 0.0),
            ))
    
    # 去重（同一 chunk 只保留最高分的命中）
    seen = set()
    unique = []
    for e in sorted(evidence, key=lambda x: x.score, reverse=True):
        if e.chunk_id not in seen:
            seen.add(e.chunk_id)
            unique.append(e)
    
    return unique[:8]  # 最多 8 条证据
```

### Step 3: LLM 对照判断

```python
AUDIT_PROMPT_TEMPLATE = """
你是一位运动训练学审核专家。你需要对照权威文献，判断以下训练课表是否存在偏离文献共识的问题。

## 本周课表
{week_schedule}

## 跑者画像
- 周跑量: {weekly_mileage}km
- 经验水平: {experience}
- 当前训练阶段: {phase_name}
- 训练总周数: {total_weeks}周

## 参考证据（从训练学文献和教材检索获得）
{evidence_text}

## 审核任务
请逐项判断以下四个维度，每个维度给出: 通过 / 有问题（附具体理由和文献引用）

### 1. 单节课参数审核
- 每节训练课的时长、强度、组数、间歇比是否在文献推荐的范围内？
- 参考: Daniels 训练参数表、Billat 间歇训练参数、Buchheit HIT 编程变量

### 2. 周课表组合审核
- 本周的强度课类型组合是否适合当前训练阶段？
- 参考: Pfitzinger 各阶段周课表模板

### 3. 阶段适宜性审核
- 每节课的训练类型是否适合跑者当前所处的训练阶段？
- 参考: 周期化理论（基础期不应有比赛模拟、减量期不应有新刺激）

### 4. 调整质量审核（仅当有调整时）
- 如果本周有因跳课导致的调整，调整后的课表是否合理？
- 参考: 部分停训研究 (Mujika 2000, Spiering 2021)、ACWR 安全区间 (Gabbett 2016)

## 输出格式（严格 JSON）
{
  "overall_pass": true,
  "overall_score": 85,
  "dimensions": {
    "session_params": {
      "pass": true,
      "issues": [],
      "evidence_refs": []
    },
    "weekly_combination": {
      "pass": false,
      "issues": [
        {
          "severity": "warning",
          "description": "基础期安排了比赛模拟跑，不符合阶段定位",
          "recommendation": "将比赛模拟跑替换为有氧阈值训练或节奏跑",
          "evidence": "Pfitzinger 基础期模板：强度课仅 1 节 LT 跑 (A 级来源)"
        }
      ],
      "evidence_refs": ["kb_pfitzinger_weekly_structure_summary"]
    },
    "phase_appropriateness": { ... },
    "adjustment_quality": { ... }
  }
}
"""
```

### Step 4: 决定是否打回

```python
def _should_reject(audit_result: dict) -> tuple[bool, str]:
    """判断审核结果是否需要打回重生成。"""
    dimensions = audit_result.get("dimensions", {})
    
    rejection_reasons = []
    
    for dim_name, dim_result in dimensions.items():
        for issue in dim_result.get("issues", []):
            # 硬违规（severity=critical）→ 必须打回
            if issue.get("severity") == "critical":
                rejection_reasons.append(
                    f"[{dim_name}] {issue['description']} "
                    f"→ 建议: {issue['recommendation']} "
                    f"({issue.get('evidence', '')})"
                )
            # 警告（severity=warning）→ 累积 ≥3 条时打回
            elif issue.get("severity") == "warning":
                rejection_reasons.append(
                    f"[{dim_name}] {issue['description']} "
                    f"({issue.get('evidence', '')})"
                )
    
    # 有硬违规 → 立即打回
    criticals = [r for r in rejection_reasons if "critical" in str(dimensions)]
    if criticals:
        return True, "\n".join(rejection_reasons)
    
    # 警告 ≥3 条 → 打回
    if len(rejection_reasons) >= 3:
        return True, "\n".join(rejection_reasons)
    
    return False, ""
```

---

## 3. 与现有 critic_auditor 的分工

| 检查项 | rag_auditor | critic_auditor（现有） |
|--------|:--:|:--:|
| 单节课参数是否在文献范围内 | ✅ (RAG+LLM) | ❌ |
| 周课表组合是否合理 | ✅ (RAG+LLM) | ❌ |
| 阶段适宜性 | ✅ (RAG+LLM) | ❌（HMP validator 部分覆盖） |
| 调整质量 | ✅ (RAG+LLM) | ❌ |
| 引用标签有效性 | ❌ | ✅ |
| 危险关键词扫描 | ❌ | ✅ |
| 证据来源完整性 | ❌ | ✅ |
| 强度课间隔 ≥48h | ❌ | ✅（HMP validator） |
| 跑量约束 | ❌ | ✅（HMP validator） |

**分工原则: rag_auditor 做需要文献对照的"质量判断"，critic_auditor 做不需要文献的"规则验证"。**

---

## 4. 审核循环（重试逻辑）

```
executor → rag_auditor → critic_auditor → after_critic_auditor_route
              │               │
              │ 不通过        │ 不通过
              │ ↓             │ ↓
              └─→ executor    └─→ executor
              (重试上限: 2)   (重试上限: 2)
                   │               │
                   └─── 共享迭代计数 ───┘
                        超过上限 → formatter (强制输出)
```

```python
# 在 after_critic_auditor_route 中新增 rag_auditor 路径

def after_critic_auditor_route(state: IntegratedState):
    # 新增: rag_auditor 未通过 → 打回重试
    if not state.get("rag_audit_passed", True):
        if state.get("iteration_count", 0) >= 2:
            return "formatter"  # 强制输出
        return "executor"       # 重试
    
    # 原有逻辑不变
    if state.get("is_approved"):
        return "formatter"
    ...
```

---

## 5. 审核反馈格式（给 executor 的重试提示）

当 rag_auditor 打回时，executor 收到的重试提示格式：

```
[RAG 审核未通过]

发现 2 个问题:

1. [session_params] 节奏跑 (周四) 时长仅 15 分钟，低于 Daniels T 区推荐的最短
   持续时间 (20 分钟)。建议延长至 20-25 分钟或改为巡航间歇形式。
   → 来源: Daniels Running Formula T 跑章节 (A 级)

2. [weekly_combination] 基础期同时安排了节奏跑和 VO2max 间歇——根据 Pfitzinger
   基础期模板，此阶段强度课应仅 1 节/周。建议保留节奏跑，将 VO2max 间歇移至
   建设期。
   → 来源: Pfitzinger Advanced Marathoning 基础期模板 (A 级)

请在上述建议基础上重新生成本周课表。
```

---

## 6. 实现依赖

| 前置条件 | 现状 | 行动 |
|---------|------|------|
| KB 有审核所需文献 | ✅ 7 条已入库 | 无需额外操作 |
| FAISS 索引可检索新 chunks | ❌ 未重建 | `python -m marathon_qa_assistant.services.vector_store --mode build` |
| LangGraph 支持新增节点 | ✅ workflow_graph.py 可扩展 | 添加 rag_auditor 节点 + 边 |
| executor 可接收审核反馈 | ❌ 当前不支持 | 需要让 executor 读取 review_feedback 字段 |

**立即阻塞项: FAISS 索引需要重建。** 不重建的话 RAG 审核只能用 JSONL 关键词匹配，效果打折（42% 命中率 vs 预期 60%+ 的向量检索）。
