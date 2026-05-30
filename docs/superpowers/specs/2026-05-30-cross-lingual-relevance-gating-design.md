# Cross-Lingual Relevance Gating Design

## Goal

让中文训练问题命中英文运动科学正文证据时，不再因为中文词面无法直接匹配英文 chunk 而被误罚为低相关；同时防止 registry-only 线索或领域冲突正文被保护分误放进核心报告。

## Problem

样例问题：

```text
中长跑选手 怎么把短跑技术融入进去，不影响专项
```

本地 FAISS 能命中高质量正文证据：

- `chunkv2_src_train_world_class_middle_distance_2021_0101`
- `source_file=train_world_class_middle_distance_2021.md`
- `section=document_paragraph`
- 正文包含 `Middle-distance runners perform short-sprint training ... supplement ... MSS ...`

但 `build_ranked_evidence()` 的二次相关度层把它降到约 `8%`。根因是 `_extract_relevance_terms()` 把中文问题抽成整段中文短语，例如 `中长跑选手`、`怎么把短跑技术融入进去`、`不影响专项`，而 `_term_overlap_score()` 用这些中文短语去英文正文里做字符串包含，结果 `term_overlap=0`，触发 `term_mismatch_penalty=0.35`。

## Scope

本设计只修改后端 relevance gating，不改 FAISS 建库、不改 embedding、不改前端 UI、不调用外部翻译 API、不引入 LLM 判别、不新增分词依赖。

关键文件：

- `apps/backend/src/marathon_qa_assistant/nodes/profile_and_retrieval.py`
- `tests/test_source_aware_retrieval.py` 或新增相邻后端测试文件

## Recommended Approach

采用“跨语言领域词扩展 + domain-compatible 正文证据保护分”。

### 1. 领域词提取

新增轻量领域词匹配，不依赖复杂中文分词。对于中文 query，从固定运动训练词表中提取短概念，例如：

- `中长跑`
- `短跑`
- `短跑技术`
- `专项`
- `速度`
- `力量训练`
- `跑步经济性`
- `乳酸阈值`
- `恢复`
- `伤病`
- `补给`

这些词与当前正则提取结果合并，但去掉过长整句短语，避免把 `怎么把短跑技术融入进去` 当作唯一相关词。

### 2. 中英领域词扩展

新增固定映射，例如：

```python
CROSS_LINGUAL_RELEVANCE_TERMS = {
    "中长跑": ["middle-distance", "middle distance", "distance runners", "800", "1500"],
    "短跑": ["sprint", "sprinting", "short-sprint", "short sprint", "maximal sprint speed", "mss"],
    "短跑技术": ["sprint training", "sprint mechanics", "mechanics", "maximal sprint speed", "mss"],
    "专项": ["specific", "specificity", "sport-specific", "specific training", "supplement", "main goal"],
    "力量训练": ["strength training", "resistance training", "plyometric", "neuromuscular"],
    "跑步经济性": ["running economy", "energy cost"],
    "乳酸阈值": ["lactate threshold", "lt2", "threshold"],
    "恢复": ["recovery", "fatigue", "adaptation"],
    "伤病": ["injury", "pain", "rehabilitation", "return to running"],
    "补给": ["nutrition", "fueling", "carbohydrate", "hydration"],
}
```

`_extract_relevance_terms(query, entities)` 应输出中文领域词和英文扩展词，供 `_term_overlap_score()` 使用。

### 3. 领域一致性判定

新增轻量 domain inference，不调用模型。根据 query terms、expanded terms、evidence text、source_file、domain_pack 判断训练/力量/营养/伤病等领域。

保护分只在 domain compatible 时触发：

- query domain 与 evidence domain 有交集；或
- evidence domain 不明确，但 evidence 是 ready body chunk，且 vector score 足够高。

领域冲突时不能触发正文保护分。例如训练技术问题命中纯营养补给 chunk，不应因为 raw vector score 高就获得 55% 保护分。

### 4. 正文证据保护分

在 `build_ranked_evidence()` 计算 relevance 后增加保护：

```python
if (
    has_full_text
    and evidence_kind == "body_chunk"
    and source_status == "ready"
    and raw_vector_score >= 0.65
    and domain_compatible
):
    relevance_score = max(relevance_score, 0.55)
```

registry-only / explanation-only / source_registry_line 不享受保护分，即使词表命中也只能作为线索。

保护分目的不是把证据变成最高相关，而是避免高质量正文证据被显示为“可能不相关，已折叠”。建议最低分为 `0.55`。

## Expected Behavior

### 样例 1：中长跑 + 短跑技术

Query：

```text
中长跑选手 怎么把短跑技术融入进去，不影响专项
```

命中正文：

```text
Middle-distance runners perform short-sprint training ... supplement ... MSS ...
```

期望：

- `source_status == "ready"`
- `has_full_text is True`
- `evidence_kind == "body_chunk"`
- `display_mode == "verified_source"`
- `relevance_percent >= 55`

### 样例 2：力量训练 + 跑步经济性

Query：

```text
力量训练能不能改善中长跑跑步经济性
```

英文正文包含：

```text
Strength training programs in middle- and long-distance runners improve running economy ...
```

期望：正文证据相关度不被误罚到低相关，`relevance_percent >= 55`。

### 样例 3：registry-only 不保护

如果命中 `section=expert_source_registry`，即使文本包含 `middle-distance`、`sprint`，也不能获得正文保护分。

期望：

- `source_status == "registry_only"`
- `evidence_kind == "source_registry_line"`
- `relevance_percent < 55`

### 样例 4：领域冲突不保护

训练技术 query 如果命中纯营养正文，例如 `carbohydrate / hydration / fueling`，不能因为 raw vector score 高就获得正文保护分。

期望：`relevance_percent < 55`。

## Testing Plan

新增或更新后端测试，使用 `build_ranked_evidence()` 的小型 synthetic hit，不依赖真实 FAISS 或外部服务：

1. `test_cross_lingual_middle_distance_sprint_evidence_not_penalized`
2. `test_cross_lingual_strength_running_economy_evidence_not_penalized`
3. `test_registry_only_cross_lingual_match_does_not_get_body_floor`
4. `test_high_vector_score_domain_conflict_does_not_get_body_floor`

每个测试直接构造 `vector_hits`，验证 `relevance_percent`、`source_status`、`evidence_kind`、`display_mode`。

建议验证命令：

```bash
PYTHONPATH=apps/backend/src python -m pytest tests/test_source_aware_retrieval.py -q
```

如果新增测试文件，则运行对应文件。

## Risks and Guardrails

- 词表过宽会误召回：通过 domain-compatible 约束降低风险。
- 保护分过高会伪造强相关：固定为 `0.55`，只保证不被低相关折叠，不代表最高可信。
- registry-only 不能保护：避免登记线索进入核心处方。
- 不引入外部翻译 API：避免延迟、隐私和可用性风险。
- 不重构整个 RAG pipeline：保持改动聚焦，降低回归风险。

## Out of Scope

- 不重建知识库。
- 不更换 embedding 模型。
- 不修改前端来源列表 UI。
- 不调用 DeepSeek 或其他 LLM 做相关性判断。
- 不新增 jieba、spacy 等依赖。
