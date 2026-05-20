# Challenge Definition Check

Owner section: Agent 1, Challenge/Formalism Lead.

Date: 2026-05-16.

## One-Sentence Challenge Definition

Required definition now appears in both manuscript copies:

> The challenge is to evaluate evidence-bounded exercise prescription agents under rule-governed risk, evidence, repair, and trace constraints.

## Challenge Boundary

M-EXRxBench is not an ordinary text-generation quality task. The challenge asks whether a solver respects:

| Tested behavior | Operational meaning | Primary fields or traces |
|---|---|---|
| Risk permission test | Decide whether the request is R0/R1/R2/R3 and whether prescription is allowed. | `gold_risk_level`; output trace `risk_level`; `required_rules`. |
| Evidence eligibility test | Use only eligible evidence/action IDs for individualized prescription. | `available_evidence_ids`; `available_action_ids`; trace `evidence_ids`; trace `action_ids`. |
| Forbidden-output test | Avoid outputs blocked by risk, evidence, protocol, or scope rules. | `forbidden_outputs`; evaluator forbidden-output checks. |
| Trace completeness test | Emit the required trace surface for audit. | `trace_schema.json`; output `trace`. |
| Bounded repair test | Downgrade, restrict, clarify, or refuse when a candidate violates the contract. | `expected_behavior`; trace `audit_result`; trace `repair_log`; trace `final_status`. |

## System-Visible Field Verification

Verified from the first row of `benchmark/system_visible_cases.jsonl` and from `benchmark/traceable_dataset_schema.json`.

| Field | Present in visible file | Solver-visible role | Notes |
|---|---:|---|---|
| `case_id` | Yes | Case identity and join key. | Required by schema. |
| `category` | Yes | Case taxonomy signal. | One of 10 declared categories. |
| `user_query` | Yes | Natural-language request. | Required non-empty string. |
| `profile` | Yes | Runner/profile context. | Object. |
| `available_evidence_ids` | Yes | Evidence IDs the solver may cite. | Array of strings. |
| `available_action_ids` | Yes | Action IDs the solver may use. | Array of strings. |
| `difficulty` | Yes | Difficulty label. | `easy`, `medium`, or `hard`. |

The TODO mentions constraints and system-visible case data. In the released visible split, constraints appear through `profile`, `user_query`, category, available evidence IDs, and available action IDs rather than as a separate top-level `constraints` field.

## Output Field Mapping

Verified from `benchmark/result_schema.json`, `rule_spec/trace_schema.json`, and `demo/evaluate_results.py`.

| Required output concept | Concrete field | Verification source |
|---|---|---|
| `answered` | `status = "answered"` | `result_schema.json`; evaluator status accuracy. |
| `partial_answer` | `status = "partial_answer"` | `result_schema.json`; repair success logic. |
| `ask_clarification` | `status = "ask_clarification"` | `result_schema.json`. |
| `refused` | `status = "refused"` | `result_schema.json`; R3 unsafe-advice logic. |
| Trace risk | `trace.risk_level` | `trace_schema.json`; risk accuracy logic. |
| Trace evidence | `trace.evidence_ids` | `trace_schema.json`; unsupported-prescription logic. |
| Trace actions | `trace.action_ids` | `trace_schema.json`; unsupported-prescription logic. |
| Audit and repair | `trace.audit_result`, `trace.repair_log` | `trace_schema.json`; repair success logic. |
| Final status trace | `trace.final_status` | `trace_schema.json`; artifact validator checks status match. |

## Evaluator-Only Field Verification

Verified from the first row of `benchmark/gold_labels.jsonl`, `benchmark/annotation_protocol_v0.5.md`, and `benchmark/traceable_dataset_schema.json`.

| Evaluator-only field | Present in gold file | Purpose | Visibility |
|---|---:|---|---|
| `expected_behavior` | Yes | Gold status. | Evaluator only. |
| `gold_risk_level` | Yes | Gold risk level. | Evaluator only. |
| `required_rules` | Yes | Required rule firings. | Evaluator only. |
| `forbidden_outputs` | Yes | Blocked output boundary. | Evaluator only. |
| `rationale` | Yes | Label rationale. | Evaluator only. |
| `rule_basis_ids` | Not in `gold_labels.jsonl`; present in rule-basis map | Source-backed traceability for label decisions. | Evaluator/provenance only via `case_to_rule_basis_map.jsonl`. |

## Split Integrity Claim

`benchmark/traceable_dataset_schema.json` defines `system_visible` with `additionalProperties: false` and explicitly excludes evaluator-only fields such as `expected_behavior`, `gold_risk_level`, `required_rules`, `forbidden_outputs`, `rationale`, `rule_basis_ids`, and `mapping_status`. This supports the manuscript claim that solver-visible input excludes gold/provenance fields.

## Reviewer-Readable Challenge Summary

| Component | Definition |
|---|---|
| Input | A system-visible case with `user_query`, `profile`, `available_evidence_ids`, `available_action_ids`, category, difficulty, and case ID. |
| Output | A status plus answer text and required trace. |
| Success | Benchmark-internal rule consistency with evaluator-only status, risk, forbidden-output, evidence/action, repair, and trace expectations. |
| Failure | Unsafe prescription, unsupported prescription, wrong risk/status, forbidden output, missing trace, or illegal repair. |
| Boundary | Synthetic rule-compliance benchmark, not clinical ground truth or deployment evidence. |

