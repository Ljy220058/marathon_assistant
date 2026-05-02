# RAG 检索对齐排查报告

## 结论

本次问题的根因不是 `reference_chunk_id` 失效，也不是当前 `retrieve()` 返回了错误格式的 `chunk_id`。

根因分为两层：

1. 评测集中的 `reference_chunk_id` 来自 [generate_eval_dataset.py](file:///c:/Users/26318/Documents/trae_projects/ollama_pro/%E9%A9%AC%E6%8B%89%E6%9D%BE%E5%8A%A9%E6%89%8B/scripts/generate_eval_dataset.py) 对当前 `vector_kb/chunks.jsonl` 的抽样结果，`10/10` 个参考 ID 都能在当前 `chunks.jsonl` 中找到。
2. 传统检索指标之所以全为 `0`，主要是因为当前评测按“精确 `chunk_id` 命中”计分，但实际检索经常出现两类情况：
   - 中文问题在英文知识库上召回偏弱，参考块在 Top-50 内都不可见。
   - 检索能命中同一文档甚至同一页的相邻块，但没有命中“生成评测题时抽中的那一个精确 chunk”。

## 证据

- 参考 ID 存在性：`10/10`
- Raw Top-5 精确命中：`0/10`
- Enhanced Top-5 精确命中：`0/10`
- Raw Top-50 精确命中：`3/10`
- Enhanced Top-50 精确命中：`3/10`
- Raw Top-5 同源文件命中：`5/10`
- Enhanced Top-5 同源文件命中：`7/10`
- Raw Top-5 同页命中：`2/10`
- Enhanced Top-5 同页命中：`3/10`

这说明“全为 0”并不等于 ID 体系错位，而是“精确 chunk 命中”这个指标口径过严，同时当前跨语言召回能力也不足。

## 关键样例

- “《运动科学》第三版的出版年份是什么？”
  - 参考块：`Periodization for Massive Strength Gains_p0017_c0005`
  - Top-5 已召回同页相邻块 `p0017_c0004`、`p0017_c0003`
  - 说明：检索已到正确页面，但精确块未中，导致 exact-chunk 记 `0`

- “什么是 periodization methodology？”
  - 参考块在 Top-50 排名 `42`
  - Top-5 已命中同一 PDF 且同一页其他块
  - 说明：问题方向对了，但 exact-chunk 指标过严

- “为什么需要记录日志？”
  - 参考块在 Top-50 排名 `17`
  - Top-5 已命中同一 PDF，不在同页
  - 说明：语义召回有一定相关性，但排序不足以进入 Top-5

- “HIIT组6分钟步行测试的结果是什么？”
  - 参考块在 Top-50 不可见
  - Top-5 也没有同源文件命中
  - 说明：这是跨语言语义召回不足的典型失败样本

## 代码定位

- [generate_eval_dataset.py](file:///c:/Users/26318/Documents/trae_projects/ollama_pro/%E9%A9%AC%E6%8B%89%E6%9D%BE%E5%8A%A9%E6%89%8B/scripts/generate_eval_dataset.py#L64-L69)
  - `reference_chunk_id` 直接取自被抽样 chunk 的 `chunk_id`

- [vector_store.py](file:///c:/Users/26318/Documents/trae_projects/ollama_pro/%E9%A9%AC%E6%8B%89%E6%9D%BE%E5%8A%A9%E6%89%8B/marathon_qa_assistant/services/vector_store.py#L442-L483)
  - `retrieve()` 当前本质上是基于 FAISS 的语义检索，再附加少量关键词扩展

## 当前判断

本问题本质上是“评测口径 + 检索能力”叠加造成的：

- 评测口径问题：`exact chunk id` 对生成式问答评测过严，容易把“命中同页相邻块”也算成失败。
- 检索能力问题：评测问题大多为中文，知识库 chunk 多为英文，当前向量检索对跨语言问答的召回不足；现有 `QUERY_HINTS` 只能带来有限改善。

## 产物

- `rank_report.json`
  - 每个问题的 Raw/Enhanced Top-5、Top-50 排名明细
- `rank_summary.json`
  - 汇总统计与逐题同源/同页命中情况

## 建议的下一单步

如果下一步继续只处理一个问题，优先建议二选一：

1. 调整评测口径：在 `evaluate_rag_ragas.py` 里同时输出 `exact chunk`、`same page`、`same source` 三档传统检索指标。
2. 提升跨语言召回：为中文问题增加英文检索改写或双查询融合，再观察 Top-5 exact hit 是否提升。
