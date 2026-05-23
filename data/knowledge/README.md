# Marathon Assistant Knowledge Base

This directory is the working area for the Marathon Assistant layered knowledge base. It is not a loose PDF dump. Every production-bound source must pass source registry, usage permission, metadata completeness, and evidence-boundary checks before it can affect training-plan generation.

## Current Scope

- `raw_sources/academic_literature/`: raw open-access PDFs grouped by evidence topic.
- `curated/academic_literature/paper_cards.jsonl`: paper-level metadata, one JSON object per line.
- `curated/academic_literature/source_registry.md`: human-readable registry for the first academic literature layer.
- `curated/academic_literature/references.bib`: preliminary BibTeX skeleton for paper/report writing.
- `packs/literature_pack/*/manifest.json`: grouped literature manifests.
- `runtime/literature_retrieval_policy.json`: retrieval policy for the literature layer.
- `governance/source_registry_v2.jsonl`: generated registry-v2 audit artifact for P0.
- `governance/chunk_schema_v2_preview.jsonl`: metadata-complete chunk-v2 preview for P1. This preview does not replace the runtime FAISS index yet.
- `governance/coverage_matrix.json`: first commercial-readiness coverage matrix for P2.
- `governance/domain_pack_seed_catalog.json`: structured seed catalog for P4-P10.
- `governance/golden_questions_summary.json`: golden-question coverage summary for P3.
- `governance/kb_release_report.json`: release gate report for P12.

## Retrieval Boundary

Academic literature defaults to explanation support, related work, safety rationale, nutrition background, and evaluation design. It must not directly override HMP protocol rules or action-library templates.

Core prescription fields can only be written by `protocol` or `action_library` sources with `prescription_permission=can_write_core`. When no local evidence exists, the system may answer with `llm_general_knowledge` for ordinary explanations, but it must not fake source paths, pages, citation ids, or write core prescription fields.
