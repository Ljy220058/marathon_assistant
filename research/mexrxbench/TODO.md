# Rule Challenge Final Hardening TODO

Goal: convert the current M-EXRxBench package into a reviewer-readable Rule Challenge submission with explicit challenge definition, correctness/completeness criteria, rule contract, traceable evaluator-only labels, leakage control, reproducible validators, reference-system behavior evidence, hard-case boundary analysis, and a complete example flow.

Scope: all work stays inside this artifact directory. Do not modify unrelated manuscript workspaces. Do not claim external expert annotation, clinical validation, real-world safety, deployment readiness, or improved athlete outcomes.

Core claim to preserve:

> M-EXRxBench labels are evaluator-only challenge specifications for testing rule compliance, evidence boundaries, refusal behavior, bounded repair, and trace completeness. They are not clinical ground truth.

Current baseline already completed before this TODO:

- 500-case default synthetic benchmark.
- hard100 supplemental stress set.
- v0.5 traceable label layer with `rule_basis_ids`.
- rule-basis source registry.
- split integrity checks.
- manifest hashes.
- runnable validators and reproduction scripts.
- submitted title: `A Trace-Governed Rule Challenge for Evidence-Bounded Exercise Prescription`.

Execution status after this hardening pass:

- Final command gates passed locally.
- PDF metadata title is correct and the compiled PDF is 14 pages.
- Independent public artifact repository `https://github.com/Ljy220058/m-exrxbench` was updated on `main` at commit `19152fa`.
- Detailed command evidence is recorded in `reviews/final_hardening_verification_log.md`.

## Team Model

Use at most three agents in every phase. Each phase must assign work to all three agents, but the agents must keep file ownership separated where possible.

| Agent | Skills | Responsibility |
|---|---|---|
| Agent 1: Challenge/Formalism Lead | `academic-paper-reviewer`, `latex-paper-en`, `project-flow-guardrails` | Challenge definition, evaluation criteria, correctness/completeness argument, formal/semi-formal rule contract, paper wording. |
| Agent 2: Artifact/Repro Lead | `verification-before-completion`, `project-flow-guardrails`, `security-scanner` | Dataset split checks, validators, manifest, reproduction scripts, clean-clone/archive validation, release hygiene. |
| Agent 3: Trace/Example Lead | `academic-paper`, `paper-research-assistant`, `humanizer-zh` | Rule-basis traceability, example flow, reviewer-facing tables, limitation language, rebuttal-ready text. |

## Phase 0: Baseline And Scope Lock

Purpose: establish that this is final Rule Challenge hardening, not a new clinical validation project.

| Agent | Tasks | Output |
|---|---|---|
| Agent 1 | Check title, abstract, challenge statement, contribution list, and section order for Rule Challenge framing. | `reviews/final_hardening_scope_review.md` section: paper baseline. |
| Agent 2 | Record current commit, artifact URL, validator status, PDF metadata, PDF page count, and release-file list. | `reviews/final_hardening_scope_review.md` section: artifact baseline. |
| Agent 3 | Check whether trace, hard100, rule-basis labels, and concrete example flow are already explained clearly. | `reviews/final_hardening_scope_review.md` section: evidence-chain gaps. |

Checklist:

- [ ] Confirm title is exactly `A Trace-Governed Rule Challenge for Evidence-Bounded Exercise Prescription`.
- [ ] Confirm artifact URL is `https://github.com/Ljy220058/m-exrxbench`.
- [ ] Confirm no work is planned outside this artifact directory.
- [ ] Confirm no external annotation claim is added.
- [ ] Confirm labels are framed as evaluator-only challenge specifications, not clinical ground truth.
- [ ] Confirm PDF remains within 8-15 pages after later edits.

Acceptance:

- [ ] `reviews/final_hardening_scope_review.md` states what will be hardened and what will not be claimed.
- [ ] Any planned paper edit has a concrete target section and verification step.

## Phase 1: Challenge Definition Hardening

Purpose: make the challenge itself explicit so reviewers do not see the paper as only a system demo.

| Agent | Tasks | Output |
|---|---|---|
| Agent 1 | Add or verify the one-sentence challenge definition, task boundary, and contribution framing in the paper. | Updated `paper/main.tex` and `submission_package/paper/main.tex` if needed. |
| Agent 2 | Verify listed system-visible fields match actual `benchmark/system_visible_cases.jsonl`. | `benchmark/challenge_definition_check.md` section: input-field verification. |
| Agent 3 | Prepare a compact reviewer-facing challenge definition table. | `benchmark/challenge_definition_check.md` section: challenge summary table. |

Required one-sentence definition:

```text
The challenge is to evaluate evidence-bounded exercise prescription agents under rule-governed risk, evidence, repair, and trace constraints.
```

Checklist:

- [ ] Define inputs: `user_query`.
- [ ] Define inputs: `profile`.
- [ ] Define inputs: `available_evidence_ids`.
- [ ] Define inputs: `available_action_ids`.
- [ ] Define inputs: constraints and system-visible case data.
- [ ] Define outputs: `answered`.
- [ ] Define outputs: `partial_answer`.
- [ ] Define outputs: `ask_clarification`.
- [ ] Define outputs: `refused`.
- [ ] State that this is not ordinary text-generation quality evaluation.
- [ ] State the tested behavior is a risk permission test.
- [ ] State the tested behavior is an evidence eligibility test.
- [ ] State the tested behavior is a forbidden-output test.
- [ ] State the tested behavior is a trace completeness test.
- [ ] State the tested behavior is a bounded repair test.
- [ ] Define evaluator-only fields: `expected_behavior`.
- [ ] Define evaluator-only fields: `gold_risk_level`.
- [ ] Define evaluator-only fields: `required_rules`.
- [ ] Define evaluator-only fields: `forbidden_outputs`.
- [ ] Define evaluator-only fields: `rationale`.
- [ ] Define evaluator-only fields: `rule_basis_ids`.
- [ ] State that system-visible split excludes gold/provenance fields.

Acceptance:

- [ ] Paper contains a clear challenge paragraph before benchmark details.
- [ ] `benchmark/challenge_definition_check.md` maps paper claims to actual file fields.
- [ ] The challenge definition can be read independently from the reference system description.

## Phase 2: Correctness And Completeness Argument

Purpose: define correctness and completeness inside the challenge, following the style of Rule Challenge papers that specify criteria rather than claiming clinical truth.

| Agent | Tasks | Output |
|---|---|---|
| Agent 1 | Write benchmark-internal correctness and completeness definitions. | `benchmark/benchmark_correctness_and_completeness_argument.md` section: definitions. |
| Agent 2 | Map each criterion to an executable validator, artifact file, or result table. | `benchmark/benchmark_correctness_and_completeness_argument.md` section: evidence mapping. |
| Agent 3 | Polish limitation wording so correctness is not confused with medical correctness. | Final wording in the argument file and optional paper text. |

Correctness checklist:

- [ ] Correctness is defined as benchmark-internal rule consistency, not medical correctness.
- [ ] `status` matches `expected_behavior`.
- [ ] trace `risk_level` matches `gold_risk_level`.
- [ ] R3 cases do not produce workout prescriptions.
- [ ] unsupported prescriptions are rejected, downgraded, or clarified.
- [ ] forbidden outputs are absent.
- [ ] required trace fields are present.

Completeness checklist:

- [ ] 10 categories are covered.
- [ ] 500 default cases are covered.
- [ ] each category has 50 cases.
- [ ] hard100 exists as a supplemental stress subset.
- [ ] R0/R1/R2/R3 risk levels are covered.
- [ ] `answered`, `partial_answer`, `ask_clarification`, and `refused` statuses are covered.
- [ ] hard100 is not merged into main benchmark metrics.
- [ ] hard100 is described as exposing boundary failures, not proving safety.
- [ ] hard100 is explicitly not clinical validation.

Required table:

| Criterion | Operational check | Artifact evidence | Limitation |
|---|---|---|---|
| Status correctness | Prediction status equals evaluator-only expected status. | `demo/evaluate_results.py`; evaluation JSON. | Challenge-internal only. |
| Risk correctness | Trace risk level equals evaluator-only gold risk. | trace outputs; evaluator summary. | Not medical diagnosis. |
| Forbidden-output safety | Forbidden outputs absent from final answer. | evaluator forbidden-output checks. | Pattern/rule based. |
| Trace completeness | Required trace fields present. | trace schema validator. | Presence is not semantic proof. |
| Coverage completeness | Categories, risks, statuses, and hard cases represented. | benchmark row counts and taxonomy. | Synthetic coverage, not population representativeness. |

Acceptance:

- [ ] `benchmark/benchmark_correctness_and_completeness_argument.md` exists.
- [ ] Paper states that correctness is rule-consistency within the benchmark.
- [ ] Paper or supplement includes the correctness/completeness table.

## Phase 3: Rule Contract Hardening

Purpose: prove that rules, not free-form generation, determine permission boundaries.

| Agent | Tasks | Output |
|---|---|---|
| Agent 1 | Verify RiskGate, EvidenceGate, PrescriptionContract, Rule Auditor, and Bounded Repair definitions. | Updated paper/rule wording if needed. |
| Agent 2 | Check contract schema and validator coverage for required fields. | `rule_spec/rule_contract_coverage_check.md` section: executable coverage. |
| Agent 3 | Create a short reviewer-readable contract summary table. | `rule_spec/rule_contract_coverage_check.md` section: contract table. |

RiskGate checklist:

- [ ] R0 means explain-only.
- [ ] R1 allows contract-bound prescription.
- [ ] R2 means downgrade, clarify, or expert-boundary behavior.
- [ ] R3 means refusal or professional-evaluation boundary.

EvidenceGate checklist:

- [ ] Evidence can explain.
- [ ] Evidence can authorize prescription only when eligible.
- [ ] Evidence insufficiency triggers clarification/refusal.
- [ ] General knowledge cannot invent prescription actions.

PrescriptionContract checklist:

- [ ] Contract includes allowed actions.
- [ ] Contract includes prohibited actions.
- [ ] Contract includes risk level.
- [ ] Contract includes evidence IDs.
- [ ] Contract includes action IDs.
- [ ] Contract includes final status.
- [ ] Contract includes trace requirements.

Rule Auditor checklist:

- [ ] Auditor checks unsupported prescription.
- [ ] Auditor checks forbidden outputs.
- [ ] Auditor checks risk/status conflict.
- [ ] Auditor checks missing trace fields.

Bounded Repair checklist:

- [ ] R2 can be repaired by downgrade/restrict wording.
- [ ] R3 cannot be repaired into a training plan.
- [ ] Failed repair becomes refusal or clarification.

Acceptance:

- [ ] `rule_spec/rule_contract_coverage_check.md` maps each contract element to paper section, schema file, validator, or runner logic.
- [ ] The paper makes clear that the LLM/reference generator drafts within a rule contract; it does not set the permission boundary.

## Phase 4: Evaluator-Only Label Traceability

Purpose: answer the reviewer objection: "Were labels arbitrary?"

| Agent | Tasks | Output |
|---|---|---|
| Agent 1 | Ensure label language says "challenge specification", not clinical ground truth. | Updated paper/provenance wording if needed. |
| Agent 2 | Validate all `rule_basis_ids`, mapping statuses, mapping confidence values, and source registry links. | Validator output and `benchmark/rule_basis_traceability_matrix.md` evidence. |
| Agent 3 | Build a readable traceability matrix with example cases and source families. | `benchmark/rule_basis_traceability_matrix.md`. |

Checklist:

- [ ] Every default gold label has `rule_basis_ids`.
- [ ] Every hard100 gold label has `rule_basis_ids`.
- [ ] Every `rule_basis_id` resolves in `benchmark/rule_basis_sources.json`.
- [ ] R2/R3 cases bind safety, downgrade, restriction, or refusal basis IDs.
- [ ] Every required rule has a direct or supporting basis link where possible.
- [ ] `mapping_confidence` uses only allowed values such as `high`, `medium`, and `review`.
- [ ] `mapping_status` is documented and release mappings are reviewed.
- [ ] Conflict priority is documented: medical red flag.
- [ ] Conflict priority is documented: injury/fatigue/environment.
- [ ] Conflict priority is documented: evidence insufficiency.
- [ ] Conflict priority is documented: protocol constraint.
- [ ] Conflict priority is documented: capacity budget.
- [ ] Conflict priority is documented: user preference.
- [ ] Conflict priority is documented: performance goal.
- [ ] Paper states that traceable labels do not equal clinical ground truth.

Acceptance:

- [ ] `benchmark/rule_basis_traceability_matrix.md` exists.
- [ ] The matrix includes default and hard100 examples.
- [ ] `benchmark/validate_traceable_dataset.py` passes.

## Phase 5: Leakage Control And Split Integrity

Purpose: prove benchmark evaluation is not contaminated by evaluator-only labels or provenance fields.

| Agent | Tasks | Output |
|---|---|---|
| Agent 1 | Verify paper explains system-visible vs evaluator-only split before evaluation results. | Updated paper text if needed. |
| Agent 2 | Strengthen or verify runner/evaluator fail-closed leakage checks. | `benchmark/leakage_control_report.md` section: executable checks. |
| Agent 3 | Add a concise split table for reviewer readability. | `benchmark/leakage_control_report.md` section: split table. |

System-visible allowlist:

- [ ] `case_id`
- [ ] `category`
- [ ] `user_query`
- [ ] `profile`
- [ ] `available_evidence_ids`
- [ ] `available_action_ids`
- [ ] `difficulty`

Forbidden visible fields:

- [ ] `expected_behavior`
- [ ] `gold_risk_level`
- [ ] `required_rules`
- [ ] `forbidden_outputs`
- [ ] `rationale`
- [ ] `notes`
- [ ] `rule_basis_ids`
- [ ] `mapping_status`
- [ ] `mapping_confidence`

Executable checks:

- [ ] `demo/run_demo.py` fails if input contains evaluator-only fields.
- [ ] `demo/run_benchmark.py` uses the same protected loader.
- [ ] `demo/evaluate_results.py` fails if prediction files contain gold/provenance fields.
- [ ] `artifacts/artifact_manifest.json` records split roles.
- [ ] `artifacts/artifact_manifest.json` records stable hashes.

Acceptance:

- [ ] `benchmark/leakage_control_report.md` exists.
- [ ] Deliberately injecting `expected_behavior` into a copied visible file causes runner failure.
- [ ] Deliberately injecting `gold_risk_level` into a copied prediction file causes evaluator failure.
- [ ] The report distinguishes actual release files from temporary negative-test copies.

## Phase 6: Validator And Reproducibility

Purpose: make the artifact runnable, inspectable, and verifiable from a reviewer perspective.

| Agent | Tasks | Output |
|---|---|---|
| Agent 1 | Confirm validator outputs support claims made in the paper. | Claim-to-command mapping in `artifact_checklist.md`. |
| Agent 2 | Run all validators, reproduction scripts, clean archive validation, and PDF metadata checks. | `reviews/final_hardening_verification_log.md`. |
| Agent 3 | Ensure README 5-minute reviewer path points to the same commands and does not mention unrelated projects. | Updated `README.md` if needed. |

Required commands from artifact root:

```powershell
conda run -n torch2.5.1 python benchmark\validate_traceable_dataset.py
conda run -n torch2.5.1 python demo\validate_artifacts.py
powershell -ExecutionPolicy Bypass -File reproducibility\run_all.ps1
powershell -ExecutionPolicy Bypass -File reproducibility\run_hard100.ps1
```

Required success sentinels:

- [ ] `traceable_dataset_validation_ok`
- [ ] `artifact_validation_ok`
- [ ] `m_exrx_reproducibility_ok`
- [ ] `m_exrx_hard100_reproducibility_ok`

Additional checks:

- [ ] Clean git archive or clean clone can run validators.
- [ ] README has a 5-minute reviewer path.
- [ ] Manifest hashes are stable across Windows worktree and git archive.
- [ ] PDF title metadata is correct.
- [ ] PDF remains 8-15 pages.

Acceptance:

- [ ] `reviews/final_hardening_verification_log.md` records exact commands, exit codes, and success sentinels.
- [ ] Any failure has a fix owner and rerun command.

## Phase 7: Reference System Behavior

Purpose: prove the reference system is a rule-contract executable example, not an answer-key reader.

| Agent | Tasks | Output |
|---|---|---|
| Agent 1 | Confirm paper calls the system a reference solution, not a clinical or deployment system. | Updated paper wording if needed. |
| Agent 2 | Verify runner reads only system-visible input and produces required trace fields. | `demo/reference_system_behavior_report.md` section: runner behavior. |
| Agent 3 | Prepare a compact behavior table mapping risk levels to final statuses and trace elements. | `demo/reference_system_behavior_report.md` section: behavior table. |

Checklist:

- [ ] Reference system input is system-visible only.
- [ ] Reference system does not read evaluator-only labels.
- [ ] Reference system follows RiskGate, EvidenceGate, Contract, Coach, Auditor, Repair sequence.
- [ ] Every case output includes trace.
- [ ] Every trace includes evidence IDs and action IDs as applicable.
- [ ] R3 cases fail closed.
- [ ] R2 cases downgrade, clarify, or refuse.
- [ ] Ablation baseline exists: no risk gate.
- [ ] Ablation baseline exists: no evidence gate.
- [ ] Ablation baseline exists: no contract.
- [ ] Ablation baseline exists: no repair.
- [ ] Ablation baseline exists: no auditor.

Acceptance:

- [ ] `demo/reference_system_behavior_report.md` exists.
- [ ] A sample run over one R0, one R1, one R2, and one R3 case is documented.

## Phase 8: Hard100 Boundary Analysis

Purpose: show that the benchmark is not only easy happy-path cases.

| Agent | Tasks | Output |
|---|---|---|
| Agent 1 | Ensure hard100 is framed as a supplemental boundary stress test. | Paper/README wording if needed. |
| Agent 2 | Verify hard100 runner and metrics are reproducible. | Updated hard100 summary evidence. |
| Agent 3 | Write a short hard100 interpretation note. | `benchmark/hard100_boundary_analysis.md`. |

Hard100 coverage checklist:

- [ ] conflicting signals
- [ ] prompt injection
- [ ] retrieval pollution
- [ ] medical red flag
- [ ] fatigue plus user pressure
- [ ] wearable uncertainty
- [ ] evidence gap
- [ ] injury ambiguity

Hard100 metrics checklist:

- [ ] status accuracy
- [ ] risk accuracy
- [ ] unsafe advice rate
- [ ] unsupported prescription rate
- [ ] rule violation rate
- [ ] trace completeness
- [ ] repair success rate

Acceptance:

- [ ] `benchmark/hard100_boundary_analysis.md` states that hard100 failures expose reference-solver boundaries and are not main benchmark scores.
- [ ] The hard100 table is not described as clinical safety evidence.

## Phase 9: Concrete Example Flow

Purpose: make the workflow legible through one complete case-level walkthrough.

| Agent | Tasks | Output |
|---|---|---|
| Agent 1 | Select one representative R2 case and ensure each rule step is defensible. | Example case selection note in `benchmark/concrete_example_flow.md`. |
| Agent 2 | Generate the example output and trace from the released runner. | `artifacts/demo_runs/example_flow_trace.json`. |
| Agent 3 | Write the readable walkthrough. | `benchmark/concrete_example_flow.md`; optional paper/supplement paragraph. |

Required example sections:

- [ ] User query: user asks for a training arrangement.
- [ ] System-visible input: profile, evidence IDs, action IDs.
- [ ] RiskGate result, e.g. R2 fatigue overload.
- [ ] EvidenceGate result: what evidence can explain and what cannot authorize high-intensity training.
- [ ] Candidate draft: contract-bound draft.
- [ ] Audit result: auditor finds a candidate violation or repair requirement.
- [ ] Bounded repair: hard session downgraded to rest/easy alternative.
- [ ] Final output: `partial_answer` with conservative boundary statement.
- [ ] Trace field: `case_id`.
- [ ] Trace field: `risk_level`.
- [ ] Trace field: `rules_fired`.
- [ ] Trace field: `evidence_ids`.
- [ ] Trace field: `action_ids`.
- [ ] Trace field: `audit_result`.
- [ ] Trace field: `repair_log`.
- [ ] Trace field: `final_status`.

Acceptance:

- [ ] `benchmark/concrete_example_flow.md` exists.
- [ ] The example trace is produced by the runner, not hand-written.
- [ ] The example is cited in README or supplement.

## Phase 10: Paper-Level Final Check

Purpose: final reviewer-oriented pass before resubmission, revision, or camera-ready update.

| Agent | Tasks | Output |
|---|---|---|
| Agent 1 | Read paper from Rule Challenge reviewer perspective and flag argument gaps. | `reviews/final_paper_rule_challenge_review.md` section: paper review. |
| Agent 2 | Check repo contents, commands, release hygiene, and reproducibility one final time. | `reviews/final_paper_rule_challenge_review.md` section: artifact review. |
| Agent 3 | Check whether trace/example/tables/figures are explained before or near first use. | `reviews/final_paper_rule_challenge_review.md` section: evidence presentation. |

Final checklist:

- [ ] Paper is visibly a Rule Challenge, not a generic LLM app.
- [ ] Labels are described as challenge specifications, not medical ground truth.
- [ ] Correctness/completeness argument exists.
- [ ] Formal or semi-formal rule contract exists.
- [ ] Trace example exists.
- [ ] Benchmark split figure exists and is explained.
- [ ] Results table exists and is explained.
- [ ] hard100 boundary analysis exists and is not merged into main scores.
- [ ] GitHub artifact URL is correct.
- [ ] Reproduction commands are present.
- [ ] No clinical validation claim.
- [ ] Future work includes external expert review.
- [ ] No unrelated manuscript files enter the release repo.
- [ ] No old-title PDFs enter the release repo.
- [ ] No zip archives enter the release repo.
- [ ] No `paper/main.pdf` enters the release repo.
- [ ] No internal review files enter the release repo.

Acceptance:

- [ ] `reviews/final_paper_rule_challenge_review.md` gives `Go`, `Conditional Go`, or `No-Go`.
- [ ] Any `Conditional Go` item has an owner, file path, and command-based verification step.

## Phase 11: Release Delivery

Purpose: update the independent public artifact repository only after clean validation.

| Agent | Tasks | Output |
|---|---|---|
| Agent 1 | Confirm public-facing text and paper references use the final title and artifact URL. | Release wording checklist. |
| Agent 2 | Build clean archive/tree, rerun validators, inspect `git status`, commit, and push to independent repo main. | Release commit hash and push evidence. |
| Agent 3 | Verify reviewer-facing README, artifact checklist, example flow, and limitations are readable after archive extraction. | Final release note in `reviews/final_hardening_verification_log.md`. |

Release hygiene checklist:

- [ ] Independent repository target is `https://github.com/Ljy220058/m-exrxbench`.
- [ ] Push target is `main`, not an internal working branch.
- [ ] No branch name or internal agent trace is exposed in the release docs.
- [ ] Submission package includes the final named PDF only.
- [ ] Artifact repo excludes unrelated manuscript directories.
- [ ] Artifact repo excludes internal notes unless intentionally included as reviewer documentation.

Acceptance:

- [ ] Clean validation passes before push.
- [ ] Remote `main` contains the intended artifact files.
- [ ] Final commit hash is recorded.

## Final Command Gate

Run from artifact root:

```powershell
conda run -n torch2.5.1 python benchmark\validate_traceable_dataset.py
conda run -n torch2.5.1 python demo\validate_artifacts.py
powershell -ExecutionPolicy Bypass -File reproducibility\run_all.ps1
powershell -ExecutionPolicy Bypass -File reproducibility\run_hard100.ps1
```

Run from `submission_package\paper`:

```powershell
conda run -n torch2.5.1 latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
```

PDF metadata check:

```powershell
conda run -n torch2.5.1 python -c "from pypdf import PdfReader; p=r'..\A_Trace-Governed_Rule_Challenge_for_Evidence-Bounded_Exercise_Prescription.pdf'; r=PdfReader(p); print(len(r.pages)); print(r.metadata.title)"
```

Release hygiene scan:

```powershell
conda run -n torch2.5.1 python demo\validate_artifacts.py
```

Required final evidence:

- [ ] `traceable_dataset_validation_ok`
- [ ] `artifact_validation_ok`
- [ ] `m_exrx_reproducibility_ok`
- [ ] `m_exrx_hard100_reproducibility_ok`
- [ ] PDF title metadata is correct.
- [ ] PDF is 8-15 pages.
- [ ] Independent GitHub repository is updated only after clean-tree validation.
