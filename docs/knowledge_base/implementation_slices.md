# Knowledge Base Implementation Slices

## P0 文献层分组与登记

状态：已完成第一版。

验收：
- 有 5 个论文 RAG 分组。
- 有 `paper_cards.jsonl`、`source_registry.md`、`references.bib`。
- 每个分组有 manifest。
- 下载文件通过 PDF 头验证。

## P1 Canonical Evidence Schema

目标：把 paper card 升级为 evidence item。

验收：
- 新增 `evidence_items.jsonl`。
- 每条 evidence 有 `evidence_id`、`paper_id`、`group`、`claim_type`、`quote_or_summary`、`page_hint`、`allowed_runtime_use`。
- 未验证页码的 evidence 不进入训练生成。

## P2 文献 Chunking 与索引

目标：为论文 RAG 建立独立索引。

验收：
- 输出 `indexes/literature/chunks.jsonl`。
- chunk metadata 保留 `paper_id`、`group`、`source_url`、`local_pdf`。
- 产品默认检索不加载该索引。

## P3 规则抽取

目标：把可执行训练约束从文献层抽入协议层。

验收：
- 负荷、安全、营养规则进入独立 rule registry。
- 每条 rule 回链到 evidence item。
- 规则标注 `core_prescription` 或 `explanation_only`。

## P4 论文评测包

目标：支撑 workshop/demo/system paper。

验收：
- 建立 evidence coverage case set。
- 记录 protocol-only、RAG-only、layered evidence-gated 三种设置。
- 输出可复现实验 manifest。

