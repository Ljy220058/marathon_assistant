# Marathon Assistant Knowledge Base

本目录是论文方向的分层知识库工作区，先承载“论文 RAG 可用”的学术文献素材，不直接覆盖现有产品运行时向量库。

## Current Scope

- `raw_sources/academic_literature/`: 按领域分组保存开放 PDF。
- `canonical/academic_literature/paper_cards.jsonl`: 论文级 metadata，每行一个 paper card。
- `canonical/academic_literature/source_registry.md`: 人可读的来源登记表。
- `canonical/academic_literature/references.bib`: 初版 BibTeX skeleton，后续写论文前仍需补全 venue 字段。
- `packs/literature_pack/*/manifest.json`: RAG 分组 manifest。
- `runtime/literature_retrieval_policy.json`: 文献层检索策略。

## Retrieval Boundary

论文文献层默认用于 related work、方法论定位、解释支持和评测设计。它不应直接覆盖 HMP 协议层或动作库层生成的核心训练处方。

