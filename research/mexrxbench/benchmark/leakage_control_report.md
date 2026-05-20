# Leakage Control Report

Purpose: document how the artifact separates system-visible input from evaluator-only labels and provenance metadata, and how the runner/evaluator fail closed when leakage appears in temporary test copies.

## Split Contract

| Split | File | Role | Rows | Manifest split role |
|---|---|---|---:|---|
| Default system-visible input | `benchmark/system_visible_cases.jsonl` | Solver input only | 500 | `system_visible` |
| Default evaluator labels | `benchmark/gold_labels.jsonl` | Evaluator-only labels | 500 | `evaluator_gold` |
| Default full audit view | `benchmark/m_exrxbench_v0.4_500_cases.jsonl` | Maintainer-facing labeled audit view | 500 | `labeled_full` |
| Default rule-basis map | `benchmark/case_to_rule_basis_map.jsonl` | Evaluator-side traceability map | 500 | `case_rule_basis_map` |
| Hard system-visible input | `benchmark/hard_system_visible_cases.jsonl` | Supplemental solver input only | 100 | `hard_system_visible` |
| Hard evaluator labels | `benchmark/hard_gold_labels.jsonl` | Supplemental evaluator-only labels | 100 | `hard_evaluator_gold` |
| Hard full audit view | `benchmark/m_exrxbench_v0.4_hard_100_cases.jsonl` | Supplemental labeled audit view | 100 | `hard_labeled_full` |
| Hard rule-basis map | `benchmark/hard_case_to_rule_basis_map.jsonl` | Supplemental evaluator-side map | 100 | `hard_case_rule_basis_map` |

All split files listed above have manifest schemas and stable sha256 entries where the manifest declares a digest.

## System-Visible Allowlist

The validator confirms that system-visible rows contain only:

| Field | Meaning |
|---|---|
| `case_id` | Stable synthetic case identifier. |
| `category` | Challenge category visible to the solver. |
| `user_query` | User request text. |
| `profile` | Synthetic runner profile. |
| `available_evidence_ids` | Evidence identifiers available to the solver. |
| `available_action_ids` | Action identifiers available to the solver. |
| `difficulty` | Default or hard subset marker. |

## Evaluator-Only Fields

The following fields must not appear in system-visible inputs or prediction files:

| Field group | Fields |
|---|---|
| Gold labels | `expected_behavior`, `gold_risk_level`, `required_rules`, `forbidden_outputs`, `rationale`, `notes` |
| Provenance and mapping | `case_family`, `variation_type`, `source_seed_id`, `annotation_notes`, `rule_basis_ids`, `rule_basis_links`, `mapping_status`, `mapping_confidence` |
| Generic leakage guard | Any nested key containing `gold` or `provenance` is treated as suspicious by the relevant validator path. |

## Executable Guards

| Guard | Implementation | Fail-closed behavior |
|---|---|---|
| Visible input guard | `demo/run_demo.py::load_cases` | Raises an error if any top-level evaluator-only field is present in a supplied case file. |
| Benchmark runner reuse | `demo/run_benchmark.py` imports `load_cases` from `run_demo.py` | Batch runs inherit the same input leakage guard. |
| Prediction guard | `demo/evaluate_results.py::load_predictions` and recursive field scan | Raises an error if predictions contain gold/provenance fields, including nested gold keys. |
| Dataset split guard | `benchmark/validate_traceable_dataset.py` | Checks visible field allowlist, nested forbidden keys, row counts, and aligned case IDs. |
| Artifact manifest guard | `demo/validate_artifacts.py::validate_manifest` | Requires declared split files to have schema references and checks declared hashes/row counts. |

## Negative Checks Run

Temporary files were created outside the artifact tree and removed after each check.

| Check | Injected field | Command shape | Observed result |
|---|---|---|---|
| Runner visible-input leak | `expected_behavior` in a copied visible row | `python demo\run_demo.py --cases <temp> --case-id mexrx-001` | Exit code 1; error reports evaluator-only fields. |
| Evaluator prediction leak | `gold_risk_level` in a copied prediction row | `python demo\evaluate_results.py --gold benchmark\gold_labels.jsonl --pred <temp> --output <temp>` | Exit code 1; error reports evaluator-only fields. |

These negative checks distinguish release files from temporary test copies: release inputs are unchanged, and the injected files are not part of the artifact manifest.

## Current Validation Status

| Command | Status | Evidence |
|---|---|---|
| `conda run -n torch2.5.1 python benchmark\validate_traceable_dataset.py` | Passed | Printed `traceable_dataset_validation_ok`. |
| `conda run -n torch2.5.1 python demo\validate_artifacts.py` | Blocked by hygiene scan | The validator reached text hygiene and rejected `TODO.md` because it contains a workspace-boundary marker currently outside the allowlist. |

The leakage controls themselves passed the dedicated validator and negative checks. The artifact-level validator needs a policy decision: either remove the marker from the release-facing TODO, move the TODO out of release files, or update the hygiene allowlist if that marker is intentionally allowed in TODO.

