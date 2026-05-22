# Execution Status Panel And Adjustment History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the "execution status panel + adjustment history" loop so users can see weekly compliance, deviation, recovery risk, next workout recommendation, missed-feedback reminders, and historical adaptive changes.

**Architecture:** The backend owns deterministic aggregation and risk rules from `training_calendar_events` and `training_event_feedback`; the frontend renders `StatusPanel`, `AdjustmentHistory`, and progress components without parsing Markdown. LLM output may be used only for clearly labeled general-knowledge explanation when no repository evidence exists; it must not decide risk level, medical referral, or core workout prescription.

**Tech Stack:** FastAPI/Pydantic backend, SQLite persistence via `services/database.py`, Astro frontend in `apps/web/src/pages/index.astro`, contract tests with `pytest`, frontend build with `npm run build`.

---

## Scope

This plan covers only the product loop selected by the user:

- Weekly execution status: completion rate, plan deviation, fatigue/sleep/pain risk, next workout recommendation.
- Feedback aggregation: completed, partially completed, skipped, missed feedback.
- Adaptive adjustment history: date, reason, adjustment content, affected upcoming sessions.
- Long-term progress: cycle progress, phase timeline, completed weeks.
- Fail-closed medical risk behavior.

Out of scope:

- New device integrations.
- Rewriting the training plan generator.
- Treating LLM text as the source of risk rules or core workout prescriptions.
- Broad repository cleanup or unrelated generated knowledge-base churn.

## Evidence And Product References

Internal references:

- `docs/product/backlog.md`: `StatusPanel`, risk rules, long-term progress, `AdjustmentHistory`.
- `docs/architecture/TECH_REQUIREMENTS_V2.md`: `/feedback`, `training_event_feedback`, medical-risk fail-closed, planned load proxy.
- `apps/backend/src/marathon_qa_assistant/core/state_models.py`: feedback normalization and adaptive rules.
- `apps/backend/src/marathon_qa_assistant/services/database.py`: persisted training plans, events, and feedback.
- `apps/web/src/pages/index.astro`: current Astro calendar and feedback UI.

External product references to preserve the product direction:

- TrainingPeaks calendar centers planned/completed workout compliance.
- TrainingPeaks structured workout overlay compares planned and completed sessions.
- Garmin Daily Suggested Workouts adapt based on training status, load, recovery, and sleep.

## Agent Configuration

Each priority level uses exactly 3 execution/review agents. The coordinator is not counted as an execution agent.

| Agent | Role | Responsibility |
|---|---|---|
| Agent 1 | Backend / Contract | Aggregation contract, risk rules, API, persistence |
| Agent 2 | Frontend / UX | `StatusPanel`, `AdjustmentHistory`, reminders, empty/error states |
| Agent 3 | QA / Reviewer | Contract tests, regression matrix, risk review |

## P0: Stabilize Execution Status And Risk Rules

### Agent Skills

| Agent | Skills |
|---|---|
| Agent 1 | `api-designer`, `senior-backend` |
| Agent 2 | `frontend-designer` |
| Agent 3 | `superpowers:test-driven-development` |

### TODO

- [ ] Agent 1: Define an `ExecutionStatusSummary` response contract with `week_start`, `week_end`, `completion_rate`, `planned_count`, `completed_count`, `partial_count`, `skipped_count`, `missed_feedback_count`, `plan_deviation`, `risk_level`, `risk_reasons`, `recovery_status`, `next_training_recommendation`, and `generation_status`.
- [ ] Agent 1: Aggregate this summary from `training_calendar_events` and `training_event_feedback`; do not infer completion from rendered Markdown.
- [ ] Agent 1: Implement deterministic risk priority: `medical_referral > pain_risk > high_fatigue > poor_sleep > missed_workout > normal`.
- [ ] Agent 1: Preserve medical fail-closed behavior for chest pain, dizziness/syncope, heat illness, and similar red flags: return `generation_status=medical_referral` and no training-load progression advice.
- [ ] Agent 1: Allow no-evidence explanatory fallback only as `source_type=llm_general_knowledge`; it must not affect `risk_level`, `risk_reasons`, or core workout prescription.
- [ ] Agent 2: Prepare frontend consumption shape for `ExecutionStatusSummary`; missing fields must render explicit empty states rather than fabricated values.
- [ ] Agent 3: Write failing tests for completed, partial, skipped, missed feedback, pain risk, high fatigue, poor sleep, and medical referral before implementation changes.

### Acceptance Criteria

- [ ] Backend tests prove the response contract is stable for plans with and without persisted feedback.
- [ ] Medical risk returns `medical_referral` and does not include high-intensity or "continue as normal" recommendations.
- [ ] `llm_general_knowledge` may appear only in explanation/source metadata, never as a risk-rule source.
- [ ] Existing `/feedback` clients remain compatible.

### Verification

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest tests/test_state_models.py tests/test_api_app.py -q
```

## P1: Ship StatusPanel User Overview

### Agent Skills

| Agent | Skills |
|---|---|
| Agent 1 | `database-architect` |
| Agent 2 | `frontend-designer` |
| Agent 3 | `superpowers:verification-before-completion` |

### TODO

- [ ] Agent 1: Add a backend query/helper that returns the current week's `ExecutionStatusSummary` for a plan without requiring the frontend to scan all events.
- [ ] Agent 1: Ensure the helper handles plans with no feedback, partial feedback, and stale feedback without throwing.
- [ ] Agent 2: Add `StatusPanel` above the calendar view with weekly completion, plan deviation, risk level, recovery status, and next workout recommendation.
- [ ] Agent 2: Display counts for completed, partial, skipped, and missed feedback.
- [ ] Agent 2: Add missed-feedback reminder entry for past training days that have no feedback.
- [ ] Agent 2: Distinguish visual states for `normal`, `attention`, `deescalate`, and `medical_referral`.
- [ ] Agent 3: Add frontend contract tests that assert `StatusPanel`, risk state, next recommendation, and missed-feedback reminder are present and distinguishable.

### Acceptance Criteria

- [ ] The user can understand this week's execution status without opening each day card.
- [ ] `medical_referral` state suppresses normal regenerate/adaptive-plan CTA copy.
- [ ] Empty state says there is no feedback yet; it does not imply the user is risk-free.
- [ ] Mobile layout remains readable and does not push the calendar into an unusable state.

### Verification

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest tests/test_astro_frontend_contract.py tests/test_api_app.py -q
cd apps/web
npm run build
```

## P2: Add AdjustmentHistory

### Agent Skills

| Agent | Skills |
|---|---|
| Agent 1 | `senior-backend` |
| Agent 2 | `frontend-designer` |
| Agent 3 | `superpowers:systematic-debugging` |

### TODO

- [ ] Agent 1: Return `AdjustmentHistory[]` from persisted feedback data with `feedback_id`, `created_at`, `plan_id`, `event_id`, `day_key`, `reason_codes`, `risk_gate`, `protocol_recheck`, `adaptive_adjustment`, `plan_diff`, and `affected_events`.
- [ ] Agent 1: Keep no-event feedback behavior non-blocking: compute advice but do not pretend it was persisted.
- [ ] Agent 1: Preserve stored `risk_gate` and `protocol_recheck` audit data when hydrating historical plans.
- [ ] Agent 2: Add `AdjustmentHistory` list in the calendar/status area, sorted newest first.
- [ ] Agent 2: Show adjustment reason, what changed, why it changed, and affected upcoming sessions.
- [ ] Agent 2: Add an explicit no-history empty state.
- [ ] Agent 3: Build a regression matrix for fatigue downgrade, pain risk, missed workout, no-risk completion, and medical referral.

### Acceptance Criteria

- [ ] Feedback with valid `plan_id + event_id` appears in adjustment history after save.
- [ ] Feedback without a valid event still returns advice but does not create a fake history row.
- [ ] History rows can distinguish fatigue downgrade, pain risk, missed workout, no-risk completion, and medical referral.
- [ ] Saved-plan reload preserves adjustment history and audit metadata.

### Verification

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest tests/test_api_app.py tests/test_astro_frontend_contract.py -q
```

## P3: Add Long-Term Progress And Missed-Feedback Loop

### Agent Skills

| Agent | Skills |
|---|---|
| Agent 1 | `observability-advisor` |
| Agent 2 | `frontend-designer` |
| Agent 3 | `superpowers:requesting-code-review` |

### TODO

- [ ] Agent 1: Add cycle progress fields: `current_week`, `total_weeks`, `cycle_completion_rate`, and `completed_weeks`.
- [ ] Agent 1: Add phase progress fields: phase name, week range, current/complete/upcoming state.
- [ ] Agent 1: Add analytics events for status panel opened, missed feedback clicked, adjustment history opened, and medical referral triggered; write only to runtime paths.
- [ ] Agent 2: Add `CycleProgressBar` with current week, total weeks, and cycle completion percentage.
- [ ] Agent 2: Add `PhaseTimeline` for base/specific/taper or available plan phases.
- [ ] Agent 2: Add `CompletedWeeksList` with each week completion rate and key workout summary.
- [ ] Agent 2: Make missed-feedback补录 refresh `StatusPanel` and `AdjustmentHistory`.
- [ ] Agent 3: Request review focused on stale state, medical-risk regressions, overclaiming completion, and analytics path hygiene.

### Acceptance Criteria

- [ ] Users can inspect current week, current phase, and completed weeks without reading a long plan.
- [ ] Missed feedback补录 updates completion rate, risk state, and adjustment history.
- [ ] Runtime analytics do not write into source-controlled app paths.
- [ ] Long-term progress works for 4, 12, 16, and 24 week plans without hard-coded week counts.

### Verification

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest tests/test_plan_workflow_expectations.py tests/test_astro_frontend_contract.py -q
cd apps/web
npm run build
```

## PM: Delivery Governance And Release Readiness

### Agent Skills

| Agent | Skills |
|---|---|
| Agent 1 | `codex-work-team:codex-work-team` |
| Agent 2 | `codex-todo-automation` |
| Agent 3 | `superpowers:verification-before-completion` |

### TODO

- [ ] Agent 1: Update `docs/product/backlog.md` so `StatusPanel`, risk rules, missed-feedback reminders, `AdjustmentHistory`, and long-term progress each have a clear completion definition.
- [ ] Agent 1: Update `docs/architecture/TECH_REQUIREMENTS_V2.md` with the status aggregation contract, deterministic risk rules, and the `llm_general_knowledge` explanation boundary.
- [ ] Agent 2: Convert the plan into trackable TODOs if the project TODO automation is used; keep product-code tasks separate from docs/governance tasks.
- [ ] Agent 3: Run final verification commands and record pass/fail status.
- [ ] Agent 3: Produce a final risk list covering missing device-derived physiological load, manual-feedback dependency, stale history risk, and LLM explanation-only fallback.

### Acceptance Criteria

- [ ] Product backlog has explicit acceptance criteria for every shipped panel/history/progress item.
- [ ] Architecture docs state that LLM general knowledge is allowed for explanation when evidence is absent, but not as the source of risk or prescription.
- [ ] No broad `git add .` is required; implementation, docs, tests, and generated data can be staged separately.
- [ ] Final report includes exact commands run and unresolved risks.

### Full Test Plan

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest tests/test_state_models.py -q
$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest tests/test_api_app.py -q
$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest tests/test_astro_frontend_contract.py -q
$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest tests/test_plan_workflow_expectations.py -q
cd apps/web
npm run build
```

## Execution Notes

- Use TDD for P0/P1/P2: write failing contract tests before implementation.
- Keep medical referral fail-closed across backend and frontend.
- Do not stage or commit unrelated dirty files from other agents.
- Do not include `data/vector_kb/default/knowledge_graph.json` in this work unless a separate evidence-index task explicitly owns it.
- When implementing with subagents, assign disjoint write scopes:
  - Agent 1: backend models/API/database/tests.
  - Agent 2: Astro/CSS/frontend contract tests.
  - Agent 3: tests, review notes, and risk checklist only.

