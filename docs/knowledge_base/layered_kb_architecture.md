# 分层知识库架构

## 目标

把项目从“单一 RAG 文件夹”升级为 Evidence-Gated Layered Knowledge Base。论文叙事重点不是资料数量，而是不同证据角色如何约束训练计划生成。

## 层级

| 层 | 名称 | 作用 | 是否进入训练处方 |
|---|---|---|---|
| L0 | Raw Sources | 保存 PDF、OCR、论文、用户反馈和产品文档原件 | 否 |
| L1 | Canonical Evidence | 统一来源、主题、证据等级、引用位置 | 需审核 |
| L2 | Domain Knowledge Packs | HMP 协议、动作库、文献、用户反馈、产品文档分包 | 按包路由 |
| L3 | Retrieval Indexes | 为不同任务建立不同索引，避免混库 | 按 policy |
| L4 | Runtime Evidence Bundle | 日卡级输出字段来源、证据等级和回退路径 | 是 |
| L5 | Evaluation Artifacts | 保存论文评测集、trace、ablation 和 spotcheck | 否 |

## 当前已落地

第一版先落地 `academic_literature` 文献层：

- 5 个论文 RAG 分组
- 33 条 paper cards
- 27 个有效开放 PDF
- 5 个分组 manifest
- 1 个检索策略文件

## 关键边界

核心训练处方必须优先来自 HMP protocol pack 和 action library pack。学术文献层可以支持解释、相关工作、风险背景、营养建议和评测设计，但不能在未经结构化规则审核前直接改写主课。

