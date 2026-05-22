# Domain Docs

This repository uses a single-context domain-doc layout by default.

## Read Order

Before architecture, triage, TDD planning, or issue generation, skills should read:

- `CONTEXT.md` at the repo root, if it exists.
- `docs/adr/`, if it exists and contains decisions relevant to the task.
- `docs/quality/shared_delivery_contract.md` for current cross-agent delivery constraints.
- `docs/architecture/TECH_REQUIREMENTS_V2.md` and `docs/product/backlog.md` when product requirements or training-plan behavior are in scope.

If `CONTEXT.md` or `docs/adr/` do not exist, proceed silently. Do not create them unless a planning or documentation task resolves new domain language or an architectural decision that needs to be preserved.

## Vocabulary Discipline

Use the repo's established product vocabulary:

- `受控训练计划生成器`
- `跑者画像`
- `结构化训练计划`
- `完整训练日历`
- `每日训练卡`
- `动作库`
- `HMP 基石协议`
- `needs_evidence`
- `llm_general_knowledge`
- `planned_load_proxy`
- `training_plan_review`

Do not replace these with loose synonyms in issue titles, TODOs, tests, or review findings.
