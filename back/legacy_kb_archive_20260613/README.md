# Legacy KB Archive 2026-06-13

This folder is a cold archive for deprecated knowledge-base artifacts and old workflow code.

Archived paths keep their original repository-relative layout so they can be inspected later without being loaded by runtime code.

Runtime KB paths after this archive:

- `data/vector_kb/v2`
- `data/vector_kb/v2_sharded`

Archived legacy paths:

- `data/vector_kb/default`
- `data/vector_kb/v2_old`
- `data/vector_kb/v2_baseline`
- `data/vector_kb/v2_sw`
- `data/vector_kb/v2_sharded_clean`
- `apps/backend/src/marathon_qa_assistant/nodes/profile_update.py`
- `docs/architecture/TECH_REQUIREMENTS_V2.md`
- `docs/architecture/backend_technical_overview.md`
- `docs/audits/repo_hygiene_inventory.md`
- `docs/knowledge_base/*_todo.md` files that still described `data/vector_kb/default` as runtime or rollback state
- `docs/quality/*` historical contracts, rounds, and reports that still referenced legacy vector KB paths
- `docs/superpowers/plans/*` and `docs/superpowers/specs/*` historical plans that still referenced legacy vector KB paths
- `scripts/rebuild_clean_sharded.py`

Do not point runtime loaders, tests, or rebuild scripts at this folder. It exists only for audit and manual rollback reference.
