# Backend / RAG Commercial Hardening TODO

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Do not use `git add .`; stage explicit files only.

**Goal:** Turn the current backend, RAG evidence chain, privacy boundary, live evaluation workflow, and release gate from a local prototype into a commercially defensible app backend.

**Architecture:** Fix the proof chain first, then close safety/privacy leaks, then split large backend surfaces into smaller contract-owned modules. The system must keep model-general answers available when evidence is absent, but core training prescriptions must remain evidence-gated.

**Tech Stack:** FastAPI, Pydantic, LangGraph with fallback executor, SQLite local store, FAISS local vector runtime, GPT/DeepSeek-compatible chat APIs, pytest, Astro frontend contract tests.

---

## Working Rules

- [ ] Every P-level phase gets its own branch: `codex/commercial-hardening-p<N>-<slug>`.
- [ ] Before each phase, run `git status --short --branch` and write down unrelated dirty files.
- [ ] Never stage unrelated frontend agent work.
- [ ] Never stage `data/vector_kb/default/user_profile.json` unless the phase explicitly owns local profile fixture cleanup.
- [ ] Never commit API keys, raw provider headers, raw user health text, or local absolute paths.
- [ ] Every fix needs a targeted test first unless it is documentation-only.
- [ ] Every release claim needs fresh verification output from the same turn.
- [ ] Every report file generated for release must be checked for `sk-`, `Authorization`, `Bearer`, `C:\Users\`, `local_path`, and raw user notes.
- [ ] For production safety, normal users are `runner`; `expert` output requires explicit expert token.
- [ ] No "almost ready" language in gate reports. A blocker is either closed by evidence or still open.

---

## Current Blockers Mapped To Fix Phases

| Finding | Fix Phase | Target Outcome |
| --- | --- | --- |
| Live RAG-vs-Base proof is still dry-run | P1, P2 | 200 paired real answer artifacts and live GPT judge summary |
| Live eval artifact capture uses `live_eval_user` but API allows only `default_user` | P1 | Artifact capture can call `/query` without being blocked by user guard |
| Source registry has many `seed_only` records | P3 | More approved, locatable, reviewed sources per domain |
| Commercial gate says `commercial_ready=false` | P11 | Gate remains blocking until live proof and domain gaps are closed |
| Domain packs have clear coverage gaps | P3, P4 | Coverage thresholds met by real sources, not fake citations |
| `/query` accepts `ds_api_key` in request body | P5 | Provider keys come from server env or secure admin config only |
| Frontend still transmits API key in `/query` payload | P5, frontend notice | Frontend treats key entry as deprecated or disabled for production |
| No API token means default `expert` output | P6 | Default public projection is `runner` |
| Only `default_user` exists | P7 | Clear single-user MVP guard plus migration path to account model |
| Raw feedback health text is stored | P8 | Privacy policy, retention, redaction, export path, and tests |
| `/llm-options` reveals key configured state | P5 | Public view hides private provider state unless authenticated |
| Governance report leaks local absolute paths | P9 | Release artifacts contain portable relative paths only |
| `api_app.py` is a backend god file | P10 | Split routers/builders without behavior drift |
| Schemas rely heavily on `Dict[str, Any]` | P10, P12 | Typed DTOs for critical contracts |
| Status fields are stringly typed | P12 | Enums for source mode, generation status, response mode |
| `mode` and `stream` are unused or unclear | P12 | Remove, implement, or document compatibility behavior |
| `_save_plan_if_ready` swallows failures | P10 | Persistence failures become visible in response trace and metrics |
| `/query` mutates `structured_plan` with `workflow_trace` | P10 | Response-only trace does not pollute core plan payload |
| Runner projection uses blacklist | P6 | Runner response uses allowlist |
| `/query` owns too many product routes | P10 | Intent routing and response building split out |
| LangGraph and fallback route logic can drift | P13 | Single route table or parity test |
| Fallback uses shallow `state.update` | P13 | Safe merge or explicit state update contract |
| Fallback has no max step guard | P13 | Loop limit with error trace |
| Node names are English-only | P14 | Interview/operator glossary with Chinese meaning |
| FAISS filter is overfetch/post-filter only | P15 | Current limitation documented and migration spike isolated |
| DB schema has `SCHEMA_SQL`, migrations, and `_ensure_columns` | P16 | One documented evolution rule with compatibility exceptions |
| SQLite is local MVP, not commercial multi-user backend | P17 | Production persistence decision record |
| OAuth token columns do not enforce encryption | P8, P17 | Encryption boundary and testable guard |
| Metrics are in-process counters | P18 | Prometheus/OpenTelemetry-ready interface or explicit MVP caveat |
| Request id does not propagate everywhere | P18 | Request id appears in workflow trace, provider errors, persistence trace |
| Frontend stores health-adjacent data in `localStorage` | P8, frontend notice | Shared privacy contract for browser storage |
| EvidenceDrawer screenshots are untracked | P9 | Report references committed or explicitly generated artifacts |
| Dirty worktree mixes backend/frontend/data/docs | P0 | Branch and staging discipline restored |

---

## P0: Git Hygiene And Work Isolation

**Branch:** `codex/commercial-hardening-p0-git-hygiene`

**Owner:** Backend coordinator

**Problem In Plain Chinese:** 现在工作区太脏，后端、前端、知识库、报告、缓存都混在一起。继续修代码前，必须先知道哪些文件属于本轮，哪些文件是别人或工具留下的。

**Files:**
- Read: `TODO.md`
- Read: `docs/quality/shared_delivery_contract.md`
- Read: `docs/knowledge_base/*.md`
- Create if needed: `docs/quality/reports/commercial_hardening_git_inventory_YYYY-MM-DD.md`

**Tasks:**

- [x] Run: `git status --short --branch`.
- [x] Save a short inventory of dirty groups: backend code, frontend code, data runtime, governance reports, docs, tests, artifacts.
- [x] Identify untracked generated artifacts that should not be staged by default.
- [x] Mark `data/vector_kb/default/user_profile.json` as local-state risk unless a test explicitly needs it.
- [x] Confirm no nested `.git` directories exist under newly added folders.
- [x] Confirm no generated report contains raw API key or user health text.
- [x] Write a short staging policy: each P phase stages only its exact files.
- [x] Do not clean, delete, reset, or revert unrelated dirty files in this phase.

**Acceptance Criteria:**

- [x] A git inventory report exists.
- [x] The report names files that are unsafe to broad-stage.
- [x] No production code is changed in this phase.
- [x] Next phase can start with a known file ownership list.

**Verification:**

```powershell
git status --short --branch
rg -n "sk-|Authorization|Bearer|C:\\Users\\|raw_feedback_text" docs/quality data/knowledge/governance -S
```

---

## P1: Fix Live Eval Artifact Capture Entry

**Branch:** `codex/commercial-hardening-p1-live-eval-entry`

**Owner:** Backend / QA

**Problem In Plain Chinese:** 证明工具要问 `/query`，但它用 `live_eval_user`，后端只认 `default_user`。这会让真实评测还没开始就被自己拦住。

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/services/kb/live_eval_artifacts.py`
- Modify tests: `tests/test_kb_live_eval_artifacts.py`
- Possibly modify: `tools/kb/build_live_eval_answer_artifacts.py`

**Tasks:**

- [x] Add a failing test: artifact capture defaults to an API-accepted user.
- [x] Add a failing test: CLI can override eval user only when backend accepts it or when explicit `--user-id` is passed.
- [x] Decide implementation: use `default_user` for local proof, or add `--user-id default_user` default.
- [x] Ensure artifact payload does not include provider API key.
- [x] Ensure artifact payload includes `llm_provider`, `llm_model`, `response_mode`, and `timeout_sec`.
- [x] Ensure artifact summary records `question_count`, `artifact_count`, `paired_question_count`.
- [x] Ensure failed `/query` response raises a clear `LiveEvalArtifactConfigError` with HTTP status.
- [x] Add regression test for backend 400/401/500 response handling.

**Acceptance Criteria:**

- [x] `collect_live_eval_answer_artifacts(... max_questions=1 ...)` can target `/query` with accepted user id.
- [x] Missing provider key still fails closed before making network calls.
- [x] No key is written into artifact JSONL.
- [x] The tool does not silently treat HTTP error JSON as a valid answer.

**Verification:**

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/test_kb_live_eval_artifacts.py tests/test_kb_live_eval_contract.py -q
```

---

## P2: Run Real 200-Question GPT Live Proof

**Branch:** `codex/commercial-hardening-p2-live-proof`

**Owner:** QA / Reviewer

**Problem In Plain Chinese:** 现在只有 dry-run。dry-run 只能证明脚本结构没坏，不能证明我们的 RAG 答案真的比裸 GPT 答案更专业。

**Files:**
- Read: `tests/fixtures/kb_golden_questions_v2.json`
- Write generated artifact: `data/knowledge/governance/live_rag_vs_base_answer_artifacts.jsonl`
- Write generated report: `data/knowledge/governance/live_rag_vs_base_eval_summary.json`
- Modify if needed: `tools/kb/run_live_rag_vs_base_eval.py`

**Tasks:**

- [x] Confirm fixture has exactly 200 questions and required domain distribution.
- [ ] Confirm `GPT_API_KEY` or `OPENAI_API_KEY` is present only in environment. Blocked on 2026-05-25: current shell has no `GPT_API_KEY` / `OPENAI_API_KEY`; see `docs/quality/reports/live_eval_p2_blocker_2026-05-25.md`.
- [ ] Start backend on the correct local port for `/query`.
- [ ] Run live artifact capture for 3 questions first.
- [ ] Inspect the 3-question artifact: one `rag` and one `base_llm` row per question.
- [ ] Confirm artifact rows include `answer_hash`, `answer_source_mode`, `evidence_chain_summary`, `rag_health_summary`.
- [ ] Confirm artifact rows do not include raw prompt, local path, Authorization header, or API key.
- [ ] Run full 200-question artifact capture with `--resume`.
- [ ] Run GPT live pair judge on the 200-question artifact.
- [ ] Regenerate commercial gate report.
- [ ] If the judge fails thresholds, save failure examples and do not mark proof ready.

**Acceptance Criteria:**

- [ ] `dry_run=false`.
- [ ] `question_count=200`.
- [ ] `paired_question_count=200`.
- [ ] `answer_artifact_count=400`.
- [ ] `commercial_proof_ready=true` only if all thresholds are met.
- [ ] `proof_status=live_rag_advantage_proven` only if RAG win rate and safety dimensions pass.
- [ ] No report contains `sk-`, `Authorization`, `Bearer`, `C:\Users\`, `local_path`, or raw user health text.

**Verification:**

```powershell
$env:PYTHONUTF8='1'
python tools/kb/build_live_eval_answer_artifacts.py --provider gpt --max-questions 3 --resume
python tools/kb/run_live_rag_vs_base_eval.py --provider gpt --artifact-input data/knowledge/governance/live_rag_vs_base_answer_artifacts.jsonl --max-questions 3
python tools/kb/build_live_eval_answer_artifacts.py --provider gpt --max-questions 200 --resume
python tools/kb/run_live_rag_vs_base_eval.py --provider gpt --artifact-input data/knowledge/governance/live_rag_vs_base_answer_artifacts.jsonl --max-questions 200
rg -n "sk-|Authorization|Bearer|C:\\Users\\|local_path|raw_prompt|prompt" data/knowledge/governance/live_rag_vs_base_answer_artifacts.jsonl data/knowledge/governance/live_rag_vs_base_eval_summary.json -S
```

---

## P3: Close Source Approval Gap

**Branch:** `codex/commercial-hardening-p3-source-approval`

**Owner:** Knowledge Base / Backend

**Problem In Plain Chinese:** 知识库不是“文件越多越权威”。只有 approved、可定位、许可可用、文本质量合格的来源，才可以支撑商业证据。

**Files:**
- Modify data: `data/knowledge/governance/source_registry_v2.jsonl`
- Modify data: `data/knowledge/governance/source_review_queue.jsonl`
- Regenerate: `data/knowledge/governance/source_review_summary.json`
- Regenerate: `data/knowledge/governance/kb_ops_dashboard.json`
- Tools: `tools/kb/review_source_record.py`
- Tests: `tests/test_kb_source_review.py`, `tests/test_kb_source_registry.py`

**Tasks:**

- [x] Prioritize domain packs with blocker gaps: `medical_risk`, `rehab_return_to_run`, `training_load`, `strength_conditioning`, `mobility_recovery`, `nutrition_race_fueling`, `environment_race_context`, `user_profile_cases`.
- [x] For this pass, verify URL reachability or local pointer validity for `src_external_strava_training_log` and `src_external_strava_instant_workouts`.
- [ ] For each PDF, verify `%PDF` header when stored locally.
- [x] For each approved source in this pass, record license or allowed use.
- [x] For each approved source in this pass, mark whether it can write core prescription.
- [x] Keep this pass as explanation/product reference only; no reviewed source was promoted to `protocol` or `action_library`.
- [x] Do not approve source that cannot be located by URL/page/section.
- [x] Regenerate source review summary.
- [ ] Keep rejected or blocked sources as metadata-only, not runtime core evidence.
- [x] Write P3 report: `docs/quality/reports/source_approval_p3_2026-05-25.md`.

**Acceptance Criteria:**

- [x] `approved` count increases from current baseline: 19 -> 21.
- [ ] `seed_only` count decreases or remains explicitly justified.
- [x] No source approved in this pass lacks URL/page/section evidence.
- [ ] `core_permission_violation_count=0`.
- [ ] Commercial gate no longer reports avoidable source review blockers except true domain-thickness gaps.

**Verification:**

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/test_kb_source_review.py tests/test_kb_source_registry.py tests/test_kb_governance.py -q
python tools/kb/build_source_review_report.py
python tools/kb/build_kb_ops_dashboard.py
```

---

## P4: Close Domain Pack Coverage Gap

**Branch:** `codex/commercial-hardening-p4-domain-packs`

**Owner:** Knowledge Base / Product

**Problem In Plain Chinese:** 现在系统会说自己是多专家知识库，但很多专家领域只有 0 到 1 条可用来源，厚度不够。

**Files:**
- Modify: `data/knowledge/domain_packs/**`
- Modify: `data/knowledge/governance/source_registry_v2.jsonl`
- Modify: `tests/fixtures/kb_golden_questions_v2.json` only if adding validated questions
- Regenerate: `data/knowledge/governance/kb_ops_dashboard.json`

**Tasks:**

- [ ] Set minimum short-term threshold: each non-core domain pack has at least 3 approved sources.
- [ ] Set core threshold: `action_library` at least 10 approved sources or approved structured internal pack entries.
- [ ] Build `user_profile_cases` only from anonymized, reviewed data.
- [ ] Do not turn user raw feedback into case library without privacy review.
- [ ] Add coverage notes for competitor tasks based on real product docs or screenshots only.
- [ ] Add mobility/recovery and rehab sources separately; do not merge them into generic training advice.
- [ ] Add nutrition boundary sources without allowing nutritionist to write core training prescriptions.
- [ ] Regenerate gap report after each batch.

**Acceptance Criteria:**

- [ ] `kb_ops_dashboard.json` shows fewer domain gaps.
- [ ] `user_profile_cases` stays blocked until anonymized export passes privacy tests.
- [ ] Core prescription sources remain limited to protocol/action_library.
- [ ] No fake citation is introduced to close a gap.

**Verification:**

```powershell
$env:PYTHONUTF8='1'
python tools/kb/build_source_gap_report.py
python tools/kb/build_kb_ops_dashboard.py
python -m pytest tests/test_kb_source_gap_report.py tests/test_kb_ops_dashboard.py -q
```

---

## P5: Remove Request-Body Provider Key Flow

**Branch:** `codex/commercial-hardening-p5-provider-secrets`

**Owner:** Security / Backend / Frontend Contract

**Problem In Plain Chinese:** API key 不应该从用户浏览器穿过 `/query` 请求体。它应该在服务端环境变量或安全配置里。

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/apps/schemas.py`
- Modify: `apps/backend/src/marathon_qa_assistant/apps/api_app.py`
- Modify: `apps/backend/src/marathon_qa_assistant/nodes/common.py`
- Modify tests: `tests/test_api_app.py`, `tests/test_llm_provider_contract.py`, `tests/test_security_guards.py`
- Frontend notice: `docs/quality/shared_delivery_contract.md`

**Tasks:**

- [ ] Add failing test: `/query` ignores or rejects `ds_api_key` in request body in production mode.
- [ ] Add compatibility mode only for local dev if required, gated by explicit env var.
- [ ] Make OpenAI/GPT and DeepSeek keys server-side only by default.
- [ ] Ensure `/llm-options` does not reveal key configured state to unauthenticated public users.
- [ ] Add frontend contract notice: do not send provider keys in `/query`.
- [ ] Keep provider selection and model selection usable without exposing secrets.
- [ ] Scrub tests that normalize key-in-body as acceptable production behavior.

**Acceptance Criteria:**

- [ ] Production request model has no active `ds_api_key` path.
- [ ] Existing tests prove no key is stored in localStorage and no key is sent in normal query payload.
- [ ] Provider missing key returns safe provider error, not raw exception.
- [ ] Public `/llm-options` hides private key configured state unless authenticated.

**Verification:**

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/test_llm_provider_contract.py tests/test_security_guards.py tests/test_api_app.py -q
rg -n "ds_api_key|marathon_ds_api_key|api_key_configured" apps/backend/src apps/web/src tests docs/api -S
```

---

## P6: Make Runner Projection Allowlist-Based

**Branch:** `codex/commercial-hardening-p6-runner-projection`

**Owner:** Backend / Security

**Problem In Plain Chinese:** 现在普通用户响应靠黑名单删字段。新增敏感字段时，只要忘记加进黑名单，就可能漏给用户。

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/apps/api_app.py`
- Create if needed: `apps/backend/src/marathon_qa_assistant/apps/response_projection.py`
- Tests: `tests/test_evidence_chain_contract.py`, `tests/test_api_app.py`

**Tasks:**

- [ ] Add failing test with a fake sensitive field nested deeply in response.
- [ ] Confirm current blacklist behavior would leak the fake field.
- [ ] Create runner allowlist for top-level query response fields.
- [ ] Create allowlist for `evidence_chain.items[]`.
- [ ] Create allowlist for `daily_schedule_cards[]`.
- [ ] Create allowlist for `latest_feedback`.
- [ ] Keep expert response unchanged behind expert token.
- [ ] Preserve frontend-required public fields.
- [ ] Add regression test for candidate evidence downgrade.

**Acceptance Criteria:**

- [ ] Runner response cannot leak unknown nested sensitive fields.
- [ ] Expert response still includes debug fields only with valid expert token.
- [ ] Candidate evidence is visible only as `needs_evidence` or expert-only candidate.
- [ ] Frontend contract tests still pass.

**Verification:**

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/test_evidence_chain_contract.py tests/test_api_app.py tests/test_astro_frontend_contract.py -q
```

---

## P7: Clarify User Model And Auth Boundary

**Branch:** `codex/commercial-hardening-p7-user-auth-boundary`

**Owner:** Backend / Product

**Problem In Plain Chinese:** 现在是单用户 demo，不是完整账号系统。商业化前必须明确这是 MVP 限制，还是要开始接真实账号。

**Files:**
- Modify: `docs/architecture/repository_governance.md`
- Modify: `docs/api/openapi_contract.md`
- Possibly create: `docs/adr/YYYY-MM-DD-user-auth-boundary.md`
- Tests: `tests/test_api_app.py`

**Tasks:**

- [ ] Document current `default_user` single-user mode.
- [ ] Add explicit commercial blocker if multi-user deployment is attempted without auth.
- [ ] Ensure `live_eval` has a safe way to use `default_user` without pretending to be real user account support.
- [ ] Add tests that cross-user plan access is rejected.
- [ ] Add tests that feedback cannot be written to another user event.
- [ ] Decide future path: external auth provider, session auth, or API gateway auth.

**Acceptance Criteria:**

- [ ] Docs do not imply SaaS multi-user support exists today.
- [ ] Tests prove cross-user access is blocked in current single-user model.
- [ ] Release gate distinguishes local MVP from commercial multi-user readiness.

**Verification:**

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/test_api_app.py tests/test_release_engineering_contract.py -q
```

---

## P8: Health Data Privacy And Retention

**Branch:** `codex/commercial-hardening-p8-health-privacy`

**Owner:** Security / Database / Product

**Problem In Plain Chinese:** 疼痛、睡眠、疲劳、胸痛都属于敏感健康数据。现在能保存，但隐私边界还不够商业化。

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/services/database.py`
- Modify: `apps/backend/src/marathon_qa_assistant/services/kb/user_case_builder.py`
- Modify: `tools/kb/export_anonymized_user_cases.py`
- Create or modify: `docs/adr/YYYY-MM-DD-health-data-privacy.md`
- Tests: `tests/test_kb_user_case_privacy.py`, `tests/test_database_migrations.py`, `tests/test_security_guards.py`

**Tasks:**

- [ ] Classify fields: raw health text, normalized feedback, risk reasons, derived adjustment.
- [ ] Add redaction before case export.
- [ ] Add retention policy document for raw feedback text.
- [ ] Add deletion/export story for user feedback.
- [ ] Ensure anonymized case library never includes email, phone, token, local path, or raw notes.
- [ ] Define whether raw feedback stays in DB or only derived fields are retained.
- [ ] If OAuth token columns are used, document and test encryption boundary.
- [ ] Add frontend contract notice for browser localStorage health-adjacent data.

**Acceptance Criteria:**

- [ ] User case export fails if raw text contains personal data or secret-like strings.
- [ ] Privacy summary blocks unreviewed user cases from runtime.
- [ ] Release gate includes privacy status.
- [ ] No report exposes raw feedback text.

**Verification:**

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/test_kb_user_case_privacy.py tests/test_database_migrations.py tests/test_security_guards.py -q
python tools/kb/build_user_case_privacy_summary.py
```

---

## P9: Sanitize Release Artifacts And Evidence Screenshots

**Branch:** `codex/commercial-hardening-p9-artifact-sanitization`

**Owner:** Release Engineering / QA

**Problem In Plain Chinese:** 报告里不能出现本机路径、密钥、Authorization、未提交截图路径。否则报告本身不可信。

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/services/kb/audit_artifacts.py`
- Modify: `tools/kb/build_commercial_kb_gate_report.py`
- Modify reports under: `data/knowledge/governance/*.json`
- Tests: `tests/test_kb_audit_artifacts.py`, `tests/test_kb_commercial_gate.py`

**Tasks:**

- [ ] Add test for Windows absolute path redaction.
- [ ] Add test for `local_path` removal from public release reports.
- [ ] Add test for screenshot artifact path existence or generated-artifact marker.
- [ ] Redact current runtime manifest absolute path fields in public report.
- [ ] Keep internal build manifest separate from public release gate report.
- [ ] Add a release scan command to shared contract.

**Acceptance Criteria:**

- [ ] Public gate report has no `C:\Users\...`.
- [ ] Public gate report has no raw local source path.
- [ ] EvidenceDrawer screenshot references are either committed artifacts or clearly marked generated-local.
- [ ] Secret scan passes on governance report set.

**Verification:**

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/test_kb_audit_artifacts.py tests/test_kb_commercial_gate.py -q
rg -n "sk-|Authorization|Bearer|C:\\Users\\|local_path|source_path" data/knowledge/governance docs/quality -S
```

---

## P10: Split `api_app.py` Without Behavior Drift

**Branch:** `codex/commercial-hardening-p10-api-split`

**Owner:** Backend

**Problem In Plain Chinese:** `api_app.py` 已经什么都管。继续往里塞功能会越来越难测，也越来越难面试讲清楚。

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/apps/api_app.py`
- Create: `apps/backend/src/marathon_qa_assistant/apps/routers/query.py`
- Create: `apps/backend/src/marathon_qa_assistant/apps/routers/feedback.py`
- Create: `apps/backend/src/marathon_qa_assistant/apps/routers/plans.py`
- Create: `apps/backend/src/marathon_qa_assistant/apps/routers/profile.py`
- Create: `apps/backend/src/marathon_qa_assistant/apps/response_builders.py`
- Create: `apps/backend/src/marathon_qa_assistant/apps/response_projection.py`
- Tests: `tests/test_api_app.py`, `tests/test_openapi_contract.py`

**Tasks:**

- [ ] Characterize current `/health`, `/query`, `/feedback`, `/plans`, `/profile` behavior with tests before moving code.
- [ ] Move only pure response building first.
- [ ] Move projection logic after tests pass.
- [ ] Move `/feedback` router.
- [ ] Move `/plans` router.
- [ ] Move `/profile` router.
- [ ] Move `/query` router last.
- [ ] Keep FastAPI app construction in `api_app.py`.
- [ ] Do not change endpoint paths.
- [ ] Do not change response fields unless covered by explicit compatibility tests.
- [ ] Make `_save_plan_if_ready` return visible persistence status instead of silent `None`.
- [ ] Stop mutating `structured_plan` with `workflow_trace`; attach trace only to response and saved audit metadata.

**Acceptance Criteria:**

- [ ] OpenAPI paths remain stable.
- [ ] Existing API tests pass.
- [ ] Query response still includes `answer_source_mode`, `rag_health`, `workflow_trace`, `evidence_chain`.
- [ ] Persistence failure is visible in `generation_status`, `message`, or workflow trace.
- [ ] `api_app.py` becomes app bootstrap plus router registration, not business logic.

**Verification:**

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/test_api_app.py tests/test_openapi_contract.py tests/test_observability_contract.py -q
```

---

## P11: Rebuild Commercial Gate From Current Artifacts

**Branch:** `codex/commercial-hardening-p11-gate`

**Owner:** Release Engineering / QA

**Problem In Plain Chinese:** 商用 gate 应该只相信当前重新生成的证据，不能引用旧报告、旧截图、旧 dry-run。

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/services/kb/commercial_gate.py`
- Modify: `tools/kb/build_commercial_kb_gate_report.py`
- Regenerate: `data/knowledge/governance/commercial_kb_gate_report.json`
- Tests: `tests/test_kb_commercial_gate.py`, `tests/test_kb_ops_dashboard.py`

**Tasks:**

- [ ] Gate must require live eval summary file to be fresh or explicitly versioned.
- [ ] Gate must fail if live eval is dry-run.
- [ ] Gate must fail if paired question count is below 200.
- [ ] Gate must fail if `commercial_proof_ready=false`.
- [ ] Gate must include domain pack blockers.
- [ ] Gate must include privacy blockers.
- [ ] Gate must include artifact sanitization blockers.
- [ ] Gate must include frontend evidence contract status.
- [ ] Gate must include source approval status.
- [ ] Gate must produce a next TODO list when failed.

**Acceptance Criteria:**

- [ ] `commercial_ready=true` appears only when all required evidence is current and passing.
- [ ] Failed gate output is honest and actionable.
- [ ] No stale dry-run can clear the blocker.

**Verification:**

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/test_kb_commercial_gate.py tests/test_kb_ops_dashboard.py -q
python tools/kb/build_commercial_kb_gate_report.py
```

---

## P12: Make Critical API Fields Typed

**Branch:** `codex/commercial-hardening-p12-typed-contracts`

**Owner:** API Designer / Backend

**Problem In Plain Chinese:** 关键状态字段现在都是普通字符串。前后端靠记忆写字符串，迟早会拼错。

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/apps/schemas.py`
- Possibly create: `apps/backend/src/marathon_qa_assistant/apps/api_enums.py`
- Tests: `tests/test_openapi_contract.py`, `tests/test_api_app.py`

**Tasks:**

- [ ] Add `GenerationStatus` enum.
- [ ] Add `AnswerSourceMode` enum.
- [ ] Add `ResponseMode` enum.
- [ ] Add `EvidenceDisplayMode` enum if not already centralized.
- [ ] Decide `mode` behavior: remove from docs, keep as compatibility no-op, or implement.
- [ ] Decide `stream` behavior: remove from docs, keep as compatibility no-op, or define a separate streaming endpoint plan with owner and tests.
- [ ] Add OpenAPI tests for enum values.
- [ ] Keep backward-compatible parsing for old clients where safe.

**Acceptance Criteria:**

- [ ] OpenAPI shows finite status values.
- [ ] Tests reject unknown status where strict mode is needed.
- [ ] Frontend contract reads the same allowed values from backend.
- [ ] No hidden status string appears only in implementation.

**Verification:**

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/test_openapi_contract.py tests/test_api_app.py tests/test_astro_frontend_contract.py -q
```

---

## P13: Make Workflow Fallback Safe And Traceable

**Branch:** `codex/commercial-hardening-p13-workflow-fallback`

**Owner:** Backend / Workflow

**Problem In Plain Chinese:** LangGraph 和 fallback 是两套路由。fallback 现在还能跑，但没有最大步数保护，状态合并也比较粗。

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/core/workflow_graph.py`
- Tests: `tests/test_plan_workflow_expectations.py`, `tests/test_router_behavior.py`

**Tasks:**

- [ ] Add route parity test: fallback and LangGraph route table cover the same nodes.
- [ ] Add max step guard to fallback executor.
- [ ] Add test for infinite route prevention.
- [ ] Replace shallow `state.update(output)` where nested state can be corrupted.
- [ ] Add workflow trace event for fallback max-step failure.
- [ ] Add route visualization or route table export for docs.

**Acceptance Criteria:**

- [ ] Fallback cannot loop forever.
- [ ] Route drift becomes test failure.
- [ ] Nested state updates are intentional.
- [ ] Workflow failure is visible in trace, not silent.

**Verification:**

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/test_router_behavior.py tests/test_plan_workflow_expectations.py tests/test_working_state_audit_loop.py -q
```

---

## P14: Add Chinese Workflow Glossary For Interview And Ops

**Branch:** `codex/commercial-hardening-p14-workflow-glossary`

**Owner:** Documentation / Backend

**Problem In Plain Chinese:** `security_gate`, `router`, `coach`, `therapist`, `critic_auditor` 这些节点名对开发者有用，但对面试讲解和团队交接不够直观。

**Files:**
- Modify: `docs/architecture/backend_technical_overview.md`
- Modify or create: `docs/architecture/workflow_node_glossary.md`

**Tasks:**

- [ ] Explain `security_gate`: 安全门，先判断请求是否危险、是否需要拦截。
- [ ] Explain `router`: 分流器，判断用户是在问普通问题、改画像、要计划、要反馈调整。
- [ ] Explain `entity_extraction`: 信息抽取，把用户话里的目标、日期、跑量、疼痛等抓出来。
- [ ] Explain `wiki_search`: 知识检索入口，查本地知识库或相关上下文。
- [ ] Explain `profiler`: 画像整理器，把用户信息整理成跑者画像。
- [ ] Explain `planner`: 计划草案生成器。
- [ ] Explain `executor`: 计划执行细化器，把草案变成更完整结构。
- [ ] Explain `coach`: 跑步教练专家，主要看训练结构和课表。
- [ ] Explain `therapist`: 康复/风险专家，主要看疼痛、疲劳、恢复边界。
- [ ] Explain `nutritionist`: 营养专家，只给营养补给建议，不写核心训练处方。
- [ ] Explain `critic_auditor`: 审核专家，检查风险、证据、越权。
- [ ] Explain `formatter`: 输出整理器，把内部状态变成用户能读的结果。
- [ ] Explain `guided_questions_generator`: 追问生成器，用于下一步引导。
- [ ] Explain `adaptive_coach`: 反馈调整专家，处理完成/跳过/疼痛后的调整。
- [ ] Explain `missing_info_handler`: 缺信息处理器，普通问答不能硬拒答，核心处方缺证据才 fail-closed。

**Acceptance Criteria:**

- [ ] Glossary uses plain Chinese first.
- [ ] Technical terms include parentheses explanation.
- [ ] Docs match actual node registry in `workflow.py`.
- [ ] No node is documented as doing something it does not do.

**Verification:**

```powershell
rg -n "security_gate|critic_auditor|missing_info_handler|adaptive_coach" docs/architecture apps/backend/src/marathon_qa_assistant/core/workflow.py -S
```

---

## P15: Document FAISS Limitation And Retriever Migration Path

**Branch:** `codex/commercial-hardening-p15-retriever-path`

**Owner:** RAG / Architecture

**Problem In Plain Chinese:** 现在 FAISS 能用，但 metadata filter 是先多取再过滤。商业化后如果数据量变大，这会影响准确性和性能。

**Files:**
- Modify: `docs/adr/2026-05-24-kb-retriever-migration-spike.md`
- Modify: `apps/backend/src/marathon_qa_assistant/services/kb/retriever_port.py`
- Tests: `tests/test_kb_retriever_port_contract.py`, `tests/test_vector_kb_runtime_contract.py`

**Tasks:**

- [ ] Document current FAISS mode: local preview, overfetch then post-filter.
- [ ] Define when to move to Qdrant: native payload filter, production vector service, domain pack filtering.
- [ ] Define when to use pgvector: if evidence, user data, plans, and audit data need database-level governance.
- [ ] Keep `RetrieverPort` as upper-layer boundary.
- [ ] Add benchmark for metadata filter recall under current FAISS setup.
- [ ] Do not migrate vector DB in this phase.

**Acceptance Criteria:**

- [ ] No upper-layer code depends directly on FAISS-specific behavior.
- [ ] Migration decision is documented with trigger thresholds.
- [ ] Current limitation is visible in `/evidence-tier-reference` or ops docs.

**Verification:**

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/test_kb_retriever_port_contract.py tests/test_vector_kb_runtime_contract.py -q
python tools/kb/benchmark_retriever_filters.py
```

---

## P16: Normalize Database Evolution Rules

**Branch:** `codex/commercial-hardening-p16-db-evolution`

**Owner:** Database / Backend

**Problem In Plain Chinese:** 现在既有 `SCHEMA_SQL`，又有 migration，又有 `_ensure_columns`。短期兼容老库可以，但长期容易不知道哪个才是真实 schema。

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/services/database.py`
- Modify: `apps/backend/src/marathon_qa_assistant/services/migrations/*.sql`
- Modify: `docs/architecture/repository_governance.md`
- Tests: `tests/test_database_migrations.py`

**Tasks:**

- [ ] Document schema source of truth.
- [ ] Keep `_ensure_columns` only for legacy compatibility, not new features.
- [ ] New DB columns must go through migration file.
- [ ] Migration files must be immutable after applied.
- [ ] Add rollback note or forward-fix policy.
- [ ] Add test that modifying applied migration fails.
- [ ] Add test that new migration applies idempotently.

**Acceptance Criteria:**

- [ ] New schema changes have a versioned migration.
- [ ] Legacy compatibility is explicit and bounded.
- [ ] Tests prove checksum guard works.

**Verification:**

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/test_database_migrations.py -q
```

---

## P17: Production Persistence ADR

**Branch:** `codex/commercial-hardening-p17-production-persistence`

**Owner:** Architecture / Database

**Problem In Plain Chinese:** SQLite 适合本地 MVP，但商业 App 需要多用户、备份、审计、恢复、并发和数据删除能力。

**Files:**
- Create: `docs/adr/YYYY-MM-DD-production-persistence-target.md`
- Modify: `docs/architecture/maintenance_roadmap.md`

**Tasks:**

- [ ] Record current SQLite scope: local MVP and developer preview.
- [ ] Define production target options: PostgreSQL, managed Postgres, or hybrid Postgres plus vector DB.
- [ ] Define user data deletion requirements.
- [ ] Define backup/restore requirements.
- [ ] Define audit-log requirements for feedback and plan edits.
- [ ] Define encryption-at-rest responsibility.
- [ ] Define migration path from local SQLite to production store.

**Acceptance Criteria:**

- [ ] Docs do not imply SQLite is production-ready for multi-user commercial deployment.
- [ ] Future persistence choice has clear decision criteria.
- [ ] Health data and OAuth token storage are covered.

**Verification:**

```powershell
rg -n "SQLite|PostgreSQL|backup|restore|delete|encryption|OAuth" docs/adr docs/architecture -S
```

---

## P18: Production Observability Baseline

**Branch:** `codex/commercial-hardening-p18-observability`

**Owner:** Observability / Backend

**Problem In Plain Chinese:** 现在指标是进程内计数器，重启就没。商用需要能看错误率、延迟、RAG 命中、证据降级、医疗红旗、成本。

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/core/observability.py`
- Modify: `apps/backend/src/marathon_qa_assistant/apps/api_app.py`
- Modify: `docs/architecture/observability_baseline.md`
- Tests: `tests/test_observability_contract.py`

**Tasks:**

- [ ] Propagate request id into workflow trace.
- [ ] Propagate request id into provider error metadata without leaking prompt.
- [ ] Add metric for live eval artifact capture failures.
- [ ] Add metric for evidence gate downgrade counts.
- [ ] Add metric for model general knowledge fallback count.
- [ ] Add metric for plan persistence failure count.
- [ ] Add SLI/SLO doc for `/query`, `/feedback`, and evidence drawer readiness.
- [ ] Keep high-cardinality labels out of metrics.
- [ ] Prepare Prometheus/OpenTelemetry adapter boundary without adding heavy dependency unless approved.

**Acceptance Criteria:**

- [ ] Request id can connect HTTP response, workflow trace, and provider failure.
- [ ] Metrics do not include prompt text or user health notes.
- [ ] Ops docs explain what to check during failed generation.

**Verification:**

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/test_observability_contract.py tests/test_api_app.py -q
```

---

## P19: Shared Frontend Contract Notice

**Branch:** `codex/commercial-hardening-p19-frontend-contract`

**Owner:** Backend coordinator and frontend owner

**Problem In Plain Chinese:** 后端会改证据状态、密钥传递、隐私边界。前端必须同步知道哪些东西不能再展示或存储。

**Files:**
- Modify: `docs/quality/shared_delivery_contract.md`
- Possibly modify: `docs/product/frontend_component_acceptance_matrix.md`

**Tasks:**

- [ ] Tell frontend: provider API key must not be sent in `/query` in production mode.
- [ ] Tell frontend: normal user must be treated as `runner`, not `expert`.
- [ ] Tell frontend: `model_general_knowledge` means "模型常识说明", not evidence citation.
- [ ] Tell frontend: `needs_evidence` must not look like "已生成权威计划".
- [ ] Tell frontend: browser storage must not keep sensitive health notes long-term.
- [ ] Tell frontend: `evidence_chain.items[]` is optional and must tolerate missing verified sources.
- [ ] Tell frontend: candidate evidence is expert-only.
- [ ] Tell frontend: release screenshot artifacts must be committed or regenerated by documented command.

**Acceptance Criteria:**

- [ ] Shared contract contains backend-owned changes and frontend action items.
- [ ] No frontend code is changed in this backend-only phase unless explicitly coordinated.
- [ ] Frontend has a clear checklist for acceptance.

**Verification:**

```powershell
rg -n "model_general_knowledge|needs_evidence|candidate_evidence|ds_api_key|runner|expert" docs/quality/shared_delivery_contract.md -S
```

---

## Final Release Verification

Run this only after P0-P19 are complete and all generated reports are current.

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/test_api_app.py tests/test_openapi_contract.py tests/test_security_guards.py tests/test_database_migrations.py tests/test_observability_contract.py -q
python -m pytest tests/test_kb_live_eval_artifacts.py tests/test_kb_live_eval_contract.py tests/test_kb_commercial_gate.py tests/test_kb_ops_dashboard.py tests/test_kb_audit_artifacts.py -q
python -m pytest tests/test_evidence_chain_contract.py tests/test_expert_retrieval_profiles.py tests/test_vector_kb_runtime_contract.py tests/test_kb_retriever_port_contract.py -q
python tools/kb/build_commercial_kb_gate_report.py
python tools/kb/build_kb_ops_dashboard.py
rg -n "sk-|Authorization|Bearer|C:\\Users\\|local_path|source_path|raw_prompt" data/knowledge/governance docs/quality -S
git diff --check
git status --short --branch
```

**Commercial Acceptance:**

- [ ] `commercial_kb_gate_report.json` has `commercial_ready=true`.
- [ ] `live_rag_vs_base_eval_summary.json` has `dry_run=false`.
- [ ] `live_rag_vs_base_eval_summary.json` has `paired_question_count=200`.
- [ ] RAG has no P0 failure in fake citation, core permission, medical safety, or load truthfulness.
- [ ] Runner response projection is allowlist-based.
- [ ] Provider secrets are server-side only in production mode.
- [ ] Health data privacy story is documented and tested.
- [ ] Request id and metrics cover failure diagnosis.
- [ ] Frontend shared contract has no unresolved backend-owned blocker.
- [ ] No broad staging is needed to deliver the release.
