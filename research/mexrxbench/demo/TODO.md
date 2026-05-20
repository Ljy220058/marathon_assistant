# Demo Redesign Team TODO

> **For agentic workers:** implement this plan phase by phase. Use at most three agents at any time. Do not push to Git unless the coordinator receives an explicit user request.

**Goal:** refactor `demo/static_trace_viewer.html` into a static reviewer-facing trace inspector for the M-EXRxBench Rule Challenge artifact.

**Architecture:** keep the demo as one dependency-free HTML file that can be opened directly from disk. The UI should make the permission boundary visible: the reference generator drafts inside a prescription contract, while rules decide risk, evidence eligibility, repair, refusal, and trace obligations.

**Tech Stack:** plain HTML, CSS, and JavaScript in `demo/static_trace_viewer.html`; no server, bundler, CDN, package manager, or external runtime.

---

## Global Scope

### Files In Scope

- Modify: `demo/static_trace_viewer.html`
- Modify if needed: `demo/README.md`
- Modify if needed: `README.md`
- Read-only evidence:
  - `artifacts/demo_runs/example_flow_trace.json`
  - `artifacts/demo_runs/full_rule_governed_v04.json`
  - `artifacts/demo_runs/single_red_flag.json`
  - `artifacts/demo_runs/hard100_full_rule_governed_eval.json`
  - `benchmark/concrete_example_flow.md`
  - `benchmark/leakage_control_report.md`
  - `benchmark/hard100_boundary_analysis.md`
  - `demo/validate_artifacts.py`

### Files Out Of Scope

- Do not modify unrelated manuscript directories.
- Do not modify benchmark labels, evaluator logic, runner behavior, or paper claims.
- Do not add generated screenshots, temporary browser files, local absolute paths, branch names, or internal process notes to the release package.

### Required Boundary Language

Use these phrases consistently:

- `Synthetic Rule Challenge artifact; not clinical validation.`
- `System-visible case data`
- `Evaluator-only labels (hidden)`
- `Prescription Contract`
- `Coach draft within contract`
- `Completeness means required-field presence, not semantic proof.`
- `Supplemental stress set, not main benchmark score.`

Avoid these positive claims:

- `clinically safe`
- `real-world safe`
- `medically validated`
- `deployable coach`
- `improves athlete outcomes`
- `expert-validated labels`

---

## Team Roles

### Agent 1: Reviewer UX Lead

**Skills:** `frontend-designer`, `academic-paper-reviewer`, `humanizer-zh`

**Owns:** reviewer information architecture, page wording, academic restraint, claim boundaries, visible explanation quality.

**May edit:** `demo/static_trace_viewer.html`, `demo/README.md`, `README.md`.

**Must not edit:** benchmark JSONL files, evaluator scripts, paper files.

### Agent 2: Trace And Data Integrity Lead

**Skills:** `project-flow-guardrails`, `security-scanner`, `verification-before-completion`

**Owns:** trace fields, split/leakage explanation, embedded example consistency, absence of gold-label leakage, validation commands.

**May edit:** `demo/static_trace_viewer.html`, `demo/README.md`.

**Must not edit:** gold labels, source registry, evaluator scoring logic.

### Agent 3: Static Implementation And QA Lead

**Skills:** `browser-use:browser`, `karpathy-guidelines`, `requesting-code-review`

**Owns:** static HTML implementation, keyboard accessibility, responsive layout, local-file loading, browser/manual inspection.

**May edit:** `demo/static_trace_viewer.html`.

**Must not edit:** benchmark data, paper source, release manifests unless a later phase explicitly adds them.

---

## Phase 0: Baseline Inspection And Safety Lock

**Objective:** establish the current behavior and prevent accidental changes to benchmark/evaluator semantics.

### Agent 1 Tasks

- [ ] Read `demo/static_trace_viewer.html` and list the current top-level UI sections.
- [ ] Read `demo/README.md` and `README.md` only for existing reviewer-path wording.
- [ ] Identify all current phrases that sound like marketing, product demo language, clinical deployment, or real-world safety.
- [ ] Write replacement wording directly into the implementation notes before editing HTML.

### Agent 2 Tasks

- [ ] Inspect `artifacts/demo_runs/example_flow_trace.json` and confirm the default case is `mexrx-011`.
- [ ] Inspect `artifacts/demo_runs/full_rule_governed_v04.json` and confirm it contains selectable result entries.
- [ ] Inspect `artifacts/demo_runs/hard100_full_rule_governed_eval.json` and record exact hard100 metrics used by the UI.
- [ ] Confirm that embedded examples do not include evaluator-only fields as solver-visible input.

### Agent 3 Tasks

- [ ] Open `demo/static_trace_viewer.html` locally before changes.
- [ ] Record whether file upload, case selection, and JSON rendering already work.
- [ ] Record desktop layout issues at approximately `1366x768`.
- [ ] Record mobile/narrow layout issues at approximately `390x844`.

### Acceptance Criteria

- [ ] Baseline behavior is understood before edits.
- [ ] No benchmark, evaluator, or runner file is modified in this phase.
- [ ] The team agrees that the demo remains a static local HTML artifact.

---

## Phase 1: Reviewer Information Architecture

**Objective:** make the first screen understandable to a Rule Challenge reviewer in 30-60 seconds.

### Agent 1 Tasks

- [ ] Rename the page framing to `M-EXRxBench Reviewer Trace Inspector`.
- [ ] Add the boundary line: `Synthetic Rule Challenge artifact; not clinical validation.`
- [ ] Add a compact reviewer path strip with four steps:
  - `Validate artifact`
  - `Run one case`
  - `Inspect trace`
  - `Compare stress-set boundary`
- [ ] Add a case selector that clearly distinguishes embedded examples from uploaded result files.
- [ ] Add top-level tabs or segmented controls:
  - `Decision Flow`
  - `Trace JSON`
  - `Benchmark Notes`
  - `Hard100 Boundary`

### Agent 2 Tasks

- [ ] Ensure the visible first-screen summary includes only runtime output and system-visible input.
- [ ] Add a muted warning strip labeled `Evaluator-only labels (hidden)` without exposing gold labels as solver input.
- [ ] Verify that any split explanation uses the same field names as `benchmark/leakage_control_report.md`.

### Agent 3 Tasks

- [ ] Implement the layout with semantic regions: `header`, `main`, `section`, and labelled controls.
- [ ] Keep the first screen in a three-column layout on desktop:
  - left: system-visible input
  - center: decision flow
  - right: status, risk, audit, trace checklist
- [ ] Stack the same regions in reading order on narrow screens.

### Acceptance Criteria

- [ ] A reviewer can see case id, status, risk level, audit result, and repair state without scrolling on desktop.
- [ ] The page opens directly from `demo/static_trace_viewer.html`.
- [ ] The first screen does not look like a marketing landing page.

---

## Phase 2: Embedded Example Set

**Objective:** provide three representative examples that show explain-only, bounded repair, and fail-closed refusal.

### Agent 1 Tasks

- [ ] Define display labels for embedded examples:
  - `mexrx-011: R2 bounded repair`
  - `mexrx-024: R3 fail-closed refusal`
  - `mexrx-002: R0 explain-only`
- [ ] Write one concise reviewer-facing sentence for each example.
- [ ] Ensure all example explanations avoid medical truth claims.

### Agent 2 Tasks

- [ ] Extract or map runtime-safe example data from existing artifacts.
- [ ] Ensure each embedded example has:
  - `case_id`
  - `category`
  - `user_query`
  - `profile`
  - `available_evidence_ids`
  - `available_action_ids`
  - `risk_level`
  - `final_status`
  - `audit_result`
  - `repair_log`
  - `rules_fired`
  - `evidence_ids`
  - `action_ids`
- [ ] Do not embed `expected_behavior`, `gold_risk_level`, `required_rules`, `forbidden_outputs`, `rationale`, `notes`, `rule_basis_ids`, or `mapping_status` in the system-visible runtime view.

### Agent 3 Tasks

- [ ] Implement embedded example switching without page reload.
- [ ] Preserve manual JSON file loading.
- [ ] Preserve selection of individual cases when an uploaded JSON object contains a `results` array.
- [ ] Show parse errors with a short user-facing message and the raw technical error in a collapsible block.

### Acceptance Criteria

- [ ] `mexrx-011` renders as `risk_level=R2`, `final_status=partial_answer`, and bounded repair active.
- [ ] `mexrx-024` renders as an R3 fail-closed refusal with prescription actions disabled.
- [ ] `mexrx-002` renders as R0 explain-only without implying prescription authorization.
- [ ] Uploaded result files still render after the embedded examples are added.

---

## Phase 3: Rule-Governed Decision Flow

**Objective:** visually show that rules, not generation, decide permission boundaries.

### Agent 1 Tasks

- [ ] Use these module names exactly:
  - `System-visible case data`
  - `Input filter`
  - `RiskGate`
  - `EvidenceGate`
  - `Prescription Contract`
  - `Coach draft within contract`
  - `Rule Auditor`
  - `Bounded Repair`
  - `Fail-closed refusal`
  - `Final Answer`
- [ ] Add a compact legend:
  - `Solid box = rule decision module`
  - `Dashed box = draft/generation module`
  - `Red path = fail-closed safety boundary`
- [ ] Add RiskGate helper text:
  - `R3 refuse; R2 downgrade; R1 allow; R0 explain`

### Agent 2 Tasks

- [ ] Ensure active modules are derived from the loaded result, not hard-coded for every case.
- [ ] Ensure R3 cases activate the fail-closed refusal path.
- [ ] Ensure R2 cases activate bounded repair only when repair evidence exists in `repair_log` or audit output.
- [ ] Ensure the flow does not display evaluator-only labels as decision inputs.

### Agent 3 Tasks

- [ ] Implement the flow using HTML/CSS boxes rather than canvas or external SVG libraries.
- [ ] Style `Coach draft within contract` with a dashed border and light neutral background.
- [ ] Style `Fail-closed refusal` with muted red border/background.
- [ ] Avoid arrow or label overlap at desktop and mobile widths.
- [ ] Do not use decorative gradients, large hero sections, stock-style imagery, or AI-looking illustrations.

### Acceptance Criteria

- [ ] The flow makes the LLM/reference generator subordinate to the rule contract.
- [ ] The refusal path is visually distinct but not visually loud.
- [ ] The UI remains readable in grayscale or black-and-white print.

---

## Phase 4: Trace Completeness And Split Integrity Panels

**Objective:** show inspectability without claiming semantic proof or clinical validation.

### Agent 1 Tasks

- [ ] Add a panel titled `Trace Completeness`.
- [ ] Add the note: `Completeness means required-field presence, not semantic proof.`
- [ ] Add a panel titled `Split Integrity`.
- [ ] Write one concise sentence explaining that the demo shows runtime traces, while evaluator-only labels remain hidden from solver inputs.

### Agent 2 Tasks

- [ ] Render required trace fields as checklist rows:
  - `case_id`
  - `profile_version`
  - `risk_level`
  - `rules_fired`
  - `evidence_ids`
  - `action_ids`
  - `expert_calls`
  - `audit_result`
  - `repair_log`
  - `final_status`
- [ ] Mark present fields as `present`.
- [ ] Mark missing fields as `missing` with a visible warning style.
- [ ] Render system-visible fields separately from evaluator-only hidden fields.
- [ ] Include monospace chips for `evidence_ids` and `action_ids`.

### Agent 3 Tasks

- [ ] Ensure checklist rows are keyboard-readable and screen-reader understandable.
- [ ] Use text labels in addition to color.
- [ ] Prevent long IDs or JSON strings from expanding panel widths.

### Acceptance Criteria

- [ ] Missing trace fields cannot be overlooked.
- [ ] The split panel explains leakage control without exposing hidden labels as runtime inputs.
- [ ] `mexrx-011` shows all required trace fields present if the artifact contains them.

---

## Phase 5: Hard100 Boundary Panel

**Objective:** disclose hard100 as a supplemental stress set and make boundary failures visible.

### Agent 1 Tasks

- [ ] Add a tab or section titled `Hard100 Boundary`.
- [ ] Add the label: `Supplemental stress set, not main benchmark score.`
- [ ] Add the sentence: `The hard set exposes reference-solver boundary failures; it is not clinical validation.`
- [ ] Link textually to `benchmark/hard100_boundary_analysis.md`.

### Agent 2 Tasks

- [ ] Display these exact metrics from the current hard100 artifact if they match the file:
  - `case_count=100`
  - `status_accuracy=0.670`
  - `risk_accuracy=0.720`
  - `unsafe_advice_rate=0.090`
  - `unsupported_prescription_rate=0.000`
  - `rule_violation_rate=0.000`
  - `trace_completeness=1.000`
  - `repair_success_rate=1.000`
- [ ] If the artifact values differ, use the artifact values and record the difference in the phase notes.
- [ ] Do not merge hard100 metrics into the default 500-case benchmark display.

### Agent 3 Tasks

- [ ] Render metrics as a compact table or key-value grid.
- [ ] Do not hide `unsafe_advice_rate`.
- [ ] Ensure the panel is readable on mobile without horizontal scrolling.

### Acceptance Criteria

- [ ] A reviewer can tell hard100 is separate from the main benchmark.
- [ ] Boundary failures are visible and not overexplained away.
- [ ] No clinical safety claim is attached to hard100 results.

---

## Phase 6: Static Implementation Quality

**Objective:** keep the viewer robust as a static local file.

### Agent 1 Tasks

- [ ] Review all visible copy for repetition, AI-like phrasing, and claim overreach.
- [ ] Replace decorative wording with direct inspection language.
- [ ] Confirm terminology matches the paper and artifact docs.

### Agent 2 Tasks

- [ ] Search the HTML for release-risk strings:
  - local absolute path markers
  - internal branch or tool markers
  - unrelated manuscript directory names
  - `clinical validation`
  - `real-world safe`
  - `medically validated`
- [ ] Confirm any occurrence of `clinical validation` is only in a negated boundary statement.
- [ ] Confirm no embedded secret, token, private URL, or unrelated local path exists.

### Agent 3 Tasks

- [ ] Keep JavaScript small and self-contained.
- [ ] Use deterministic render functions for:
  - example selection
  - uploaded JSON parsing
  - result normalization
  - flow activation
  - trace checklist rendering
- [ ] Add visible focus states.
- [ ] Add `aria-live` for parse/render errors.
- [ ] Ensure long JSON blocks use wrapping or horizontal scrolling inside their own panel, not the page body.

### Acceptance Criteria

- [ ] The file remains dependency-free and opens by double-click.
- [ ] No local-only or internal-process strings appear in release-facing UI.
- [ ] Keyboard navigation works for file loading, example selection, tabs, and collapsible JSON sections.

---

## Phase 7: Documentation Sync

**Objective:** make README instructions match the redesigned static inspector.

### Agent 1 Tasks

- [ ] Update `demo/README.md` with a short description of `M-EXRxBench Reviewer Trace Inspector`.
- [ ] Keep instructions focused on reviewer use, not product demo language.
- [ ] Mention the three embedded examples and what they demonstrate.

### Agent 2 Tasks

- [ ] Ensure documentation does not say the viewer exposes gold labels as solver input.
- [ ] Ensure documentation does not say hard100 is part of the main benchmark score.
- [ ] Ensure documentation preserves the synthetic/not-clinical-validation boundary.

### Agent 3 Tasks

- [ ] If `README.md` has a reviewer path section, make sure it still tells reviewers they can open `demo/static_trace_viewer.html`.
- [ ] Do not add screenshots unless explicitly requested.
- [ ] Do not add new generated media files in this phase.

### Acceptance Criteria

- [ ] `demo/README.md` and `README.md` are consistent with the actual viewer.
- [ ] Reviewer instructions remain short enough for a 5-minute path.
- [ ] Documentation contains no local absolute paths or internal branch names.

---

## Phase 8: Verification And Review

**Objective:** verify the redesigned viewer and artifact before any release or push.

### Agent 1 Tasks

- [ ] Review the final viewer as a Rule Challenge reviewer.
- [ ] Confirm the first screen answers:
  - What is the challenge?
  - What is the input?
  - What is the output?
  - What did the rule layer decide?
  - What evidence/action IDs were used?
  - Why is this not clinical validation?
- [ ] Record any remaining wording issue in `demo/TODO.md` before marking this phase complete.

### Agent 2 Tasks

- [ ] Run artifact validation:

```powershell
cd docs\paper_project\marathon_exrx_ruleml2026
conda run -n torch2.5.1 python demo\validate_artifacts.py
```

Expected output includes:

```text
artifact_validation_ok
```

- [ ] Run release-risk scan:

```powershell
rg -n "real-world safe|medically validated|deployable coach|improves athlete outcomes|expert-validated labels" demo\static_trace_viewer.html demo\README.md README.md
```

Expected: no hits. Also run the artifact validator because it checks local path and unrelated workspace markers.

### Agent 3 Tasks

- [ ] Open `demo/static_trace_viewer.html` directly from the local filesystem.
- [ ] Load `artifacts/demo_runs/example_flow_trace.json`.
- [ ] Load `artifacts/demo_runs/full_rule_governed_v04.json`.
- [ ] Confirm `mexrx-011`, `mexrx-024`, and `mexrx-002` render correctly.
- [ ] Check desktop width around `1366px`.
- [ ] Check mobile width around `390px`.
- [ ] Confirm no overlapping arrows, cards, labels, tab buttons, or JSON panels.

### Acceptance Criteria

- [ ] `demo/validate_artifacts.py` passes.
- [ ] The static viewer opens locally without a server.
- [ ] Uploaded JSON files render.
- [ ] Embedded examples render.
- [ ] No release-risk strings remain.
- [ ] The UI improves reviewer inspectability without changing benchmark data, evaluator logic, or paper claims.

---

## Completion Checklist

- [ ] `demo/static_trace_viewer.html` is still one static file.
- [ ] No external dependency was introduced.
- [ ] `mexrx-011`, `mexrx-024`, and `mexrx-002` are available from the embedded selector.
- [ ] Trace completeness is shown as required-field presence only.
- [ ] System-visible and evaluator-only fields are separated.
- [ ] Hard100 is clearly supplemental.
- [ ] `demo/README.md` matches the redesigned viewer.
- [ ] `README.md` reviewer path still points to the viewer.
- [ ] Validation command passes.
- [ ] No Git push is performed without explicit user approval.
