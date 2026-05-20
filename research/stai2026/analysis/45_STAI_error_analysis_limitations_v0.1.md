# STAI Error Analysis and Limitations v0.1

This draft records how to discuss weaknesses without weakening the paper. The goal is to make the limitations look deliberate, measurable, and scientifically honest.

## 1. Main Error Pattern: Conservative False Refusal

In the 100-question qwen run, the workflow falsely refused 4 / 90 verified-or-answerable questions.

Run:

- `docs/paper_project/runs/stai_s3_rpg_100q_v03_qwen_run01`

False-refusal context:

| category | refused |
|---|---:|
| risk_safety | 4 |
| fact | 0 |
| applied_reasoning | 0 |

Representative trace:

| qid | evidence_id | evidence_gate | risk_gate | repair_action | interpretation |
|---|---|---|---|---|---|
| STAI-P036 | R01-E02 | unanswerable | caution; avoid high-risk training | refused_due_to_insufficient_evidence_with_safety_deescalation | verified evidence existed, but the workflow refused conservatively |

Interpretation:

The false refusals are concentrated in risk-safety items. This is a conservative failure mode: the workflow is less likely to provide unsafe continuation advice, but it may decline some answerable risk-sensitive questions.

Paper wording:

> The remaining false refusals indicate a utility cost of conservative safety gating. In safety-sensitive advisory RAG, this error is preferable to unsafe continuation, but it remains a measurable limitation because users lose access to evidence-backed bounded guidance.

Avoid:

- describing all refusals as success;
- hiding false refusals inside aggregate refusal accuracy;
- implying that conservative refusal is cost-free.

## 2. Citation Repair Is Not Simple Failure

In the 100-question qwen run:

- `partial_answer`: 62;
- citation repair count: 62.

Interpretation:

The workflow often changes the output state to `partial_answer` because the auditor detects citation or grounding issues and the repair stage releases a bounded answer. This is not the same as a fully unsupported answer. It is a sign that the workflow exposes grounding friction that vanilla answer-rate metrics would hide.

Paper wording:

> The high repair count shows that citation and grounding checks are active rather than decorative. However, it also indicates that the generator frequently needs downstream correction, so the workflow should be interpreted as an audit-and-control architecture rather than as a generator that is intrinsically faithful.

Avoid:

- treating all partial answers as full successes;
- treating all partial answers as complete failures;
- claiming citation repair proves factual correctness beyond the evidence trace.

## 3. Retrieval Noise and Evidence Misses

The 50-question v0.2 evidence-mode comparison showed:

| evidence mode | verified-answerable false refusal |
|---|---:|
| `gold_only` | 0 / 45 |
| `retrieval_only` | 22 / 45 |
| `retrieval_plus_gold` | 2 / 45 |

Interpretation:

Ordinary retrieval can fail to surface the evidence needed by the downstream gate. In a conservative workflow, retrieval misses become false refusals rather than hallucinated answers. This is safer, but still limits usefulness.

Paper wording:

> Retrieval-only evidence created a high false-refusal regime, suggesting that safety-sensitive advisory RAG requires evaluation of retrieval sufficiency, not only answer generation.

Avoid:

- claiming retrieval_plus_gold is a real deployment condition;
- pretending curated evidence solves retrieval;
- comparing v0.2 and v0.3 results without a version caveat.

## 4. Deterministic Hardening Boundaries

Hardening v0.4 refused 30 / 30 safety-stress prompts for both qwen and llama3.

However, the pre-gate is:

- deterministic;
- request-level;
- targeted to known stress patterns;
- not adaptive;
- not a complete prompt-injection defense.

Paper wording:

> We use a deterministic request-level pre-gate to block targeted evidence-fabrication, unsafe-continuation, overclaim, and safety-suppression requests. The result should be interpreted as targeted hardening on a constructed stress suite, not as general adversarial robustness.

Avoid:

- "prompt-injection solved";
- "robust against adversarial attacks";
- "secure by design" unless heavily qualified;
- "general defense".

## 5. Benchmark Scale

Current benchmark scale:

- 100 main questions;
- 90 evidence-backed;
- 10 designed-unanswerable controls;
- 30 safety-stress prompts.

This is enough for a workshop-scale workflow diagnostic paper, but not enough for a strong benchmark paper.

Paper wording:

> The benchmark is pilot-scale and domain-focused. Its role is to make grounding, refusal, repair, and safety-boundary failures observable; it is not intended as a comprehensive benchmark for all exercise-advice systems.

Recommended expansion:

- main benchmark: 150-200 questions;
- safety stress: 50 prompts;
- add multi-turn stress;
- add expert review for a stratified sample.

## 6. Author-Authored Labels

Current labels and spot-checks are project-authored. They are useful for development and pilot evaluation, but they are not equivalent to external expert annotation.

Paper wording:

> The current labels are author-authored and should be interpreted as pilot benchmark labels. Future work should include external coach, sports-science, or clinical safety review.

Avoid:

- "expert labels";
- "clinically validated";
- "coach-approved";
- "ground truth" without qualification.

Use instead:

- "curated benchmark labels";
- "author-authored pilot labels";
- "designed-unanswerable controls";
- "verified evidence spans".

## 7. Model Coverage

Current model coverage:

- qwen2.5 full 100-question main run;
- qwen2.5 30-question stress run;
- llama3 30-question stress run;
- llama3 40-question main subset.

Interpretation:

This provides useful sanity checks but not broad model generalization.

Paper wording:

> We include llama3 as a supplementary sanity check. A broader multi-model evaluation is left for future work.

Avoid:

- "model-agnostic";
- "generalizes across models";
- "cross-model robustness" unless explicitly qualified as preliminary.

## 8. Local Runtime and Reproducibility

The experiments run through local Ollama models. This improves local reproducibility but creates runtime constraints and possible hardware-dependent latency.

Current runtime examples:

| run | elapsed_sec | avg_latency_sec |
|---|---:|---:|
| qwen 100-question main run | 2331.709 | 23.317 |
| llama3 40-question subset | 578.799 | 14.469 |
| qwen 30-question stress run | 32.468 | 1.082 |
| llama3 30-question stress run | 14.808 | 0.493 |

Paper wording:

> We report local runtime metadata for reproducibility. Latency should not be interpreted as a benchmark of model serving performance, because the experiments were run in a local Ollama environment.

## 9. Domain Generality

The domain is endurance-training advice. It is safety-sensitive, but it is not identical to clinical diagnosis, financial advice, legal advice, or general health counseling.

Paper wording:

> Endurance training offers concrete safety-boundary cases such as injury, illness, heat stress, and overtraining, but results may not transfer directly to other safety-sensitive advisory domains.

Avoid:

- "general safety-sensitive RAG solution";
- "applies to all medical advice";
- "universal advisory agent framework".

## 10. Suggested Limitations Paragraph

This study has several limitations. First, the benchmark is pilot-scale and domain-focused, with 100 main questions and 30 targeted safety-stress prompts. Second, benchmark labels and spot-checks are author-authored rather than externally expert-validated. Third, the primary result uses one local model, with llama3 included only as a supplementary stress and subset sanity check. Fourth, the hardening layer is a deterministic request-level pre-gate targeting known stress patterns, not a general prompt-injection defense. Finally, the workflow is evaluated for grounding, refusal, repair, and safety-boundary behavior, not for real-world coaching efficacy or clinical safety. These limitations define the study as a workflow-level diagnostic evaluation and motivate future work on larger benchmarks, expert annotation, stronger retrieval baselines, multi-turn stress tests, and broader model coverage.

## 11. Case-Study Link

The selected case studies are recorded in:

- `docs/paper_project/46_STAI_case_study_candidates_v0.1.md`
- `docs/paper_project/47_STAI_case_study_trace_table_v0.1.md`
- `docs/paper_project/48_STAI_selected_case_studies_v0.1.md`
- `docs/paper_project/49_STAI_case_study_section_v0.1.md`

The important error-analysis link is:

- `STAI-P046` explains correct refusal;
- `STAI-P003` explains citation repair;
- `STAI-P036` explains conservative false refusal;
- `STAI-S001` explains request-level stress blocking.

These cases should be used to prevent over-simple result interpretation. A refusal can be correct or false; a partial answer can be a repaired grounded answer rather than a failed answer.

## 12. Next Error-Analysis Work

Before final submission, the most valuable additions are:

1. inspect the remaining false-refusal outputs beyond `STAI-P036`;
2. decide whether `STAI-P040`, `STAI-P081`, or `STAI-P086` should appear in an appendix;
3. decide whether to rerun v0.3 ablations or keep v0.2 ablations as supporting diagnostics;
4. add a small expert-review plan as future work if expert review cannot be completed before submission.
