# STAI P1 Reviewer-Attack and Polish Report v0.1

Date: 2026-05-11

Scope: P1 pre-submission polish for `A Workflow-Level Diagnostic Study of Evidence-Gated Advisory RAG for Endurance Training Advice`.

## 1. Five-Reviewer Attack Map

| Reviewer lens | Likely attack | Current defense | Remaining caution |
| --- | --- | --- | --- |
| EIC / venue fit | The paper may be a narrow application paper rather than a secure/trustworthy AI paper. | The paper frames the contribution as workflow-level diagnostics for refusal, repair, evidence insufficiency, and safety-boundary behavior. | Keep title, abstract, and conclusion focused on trustworthy workflow observability, not training-plan generation. |
| Methodology reviewer | Benchmark is small and author-authored; ablation is only 40 questions. | The paper calls it a pilot benchmark, reports the 40-question ablation as a diagnostic subset, and avoids population-level claims. | Do not call the benchmark large-scale, representative, or externally validated. |
| Domain reviewer | Endurance-training evidence may be insufficient for coaching or medical claims. | The paper repeatedly states that it does not evaluate coaching efficacy, clinical safety, diagnosis, or deployment readiness. | Do not add practical training recommendations in the paper narrative. |
| Security reviewer | Deterministic hardening may be overstated as a defense. | The paper calls it targeted request-level hardening on constructed stress prompts, not general prompt-injection robustness. | Avoid phrases such as robust defense, secure against prompt injection, or adversarially robust. |
| Devil's advocate | The workflow may be an engineering combination of existing RAG, gates, and verifier/repair ideas. | Related Work now states that modularity is not new; the claimed contribution is making refusal, repair, false refusal, and safety-boundary behavior measurable workflow states. | Keep novelty claim diagnostic and empirical, not architectural-grand. |

## 2. Related Work Gap Audit

The Related Work section should support this narrow gap:

> Prior work provides retrieval, attribution, critique, repair, tool use, and agentic decomposition, but less often evaluates refusal, bounded repair, evidence insufficiency, and safety-boundary behavior as explicit measurable states in one traceable advisory workflow.

Checked actions:

- RAG grounding paragraph now motivates support/citation risk without claiming attribution is solved.
- Self-critique and repair paragraph now distinguishes final-answer improvement from diagnostic visibility.
- Agentic workflow paragraph now explicitly says modularity/tool use/multi-agent orchestration is not the novelty.
- Safety-sensitive advisory paragraph now avoids claiming medical or deployment safety.
- Bibliography metadata for several arXiv entries was corrected against the arXiv pages: `ragchecker2024`, `zhou2025ralmknow`, `maskey2025overrefusal`, and `yu2025safetydegradation`.

## 3. Case Study Polish

The Results case study paragraph now states that the cases are not additional performance wins and include a conservative failure mode. The four retained cases map to the intended paper roles:

| Role | QID | Function in paper |
| --- | --- | --- |
| Correct refusal | STAI-P046 | Shows refusal as intended success under insufficient evidence. |
| Citation repair | STAI-P003 | Shows audit/repair as observable grounding friction. |
| False refusal | STAI-P036 | Exposes utility cost from conservative safety behavior. |
| Safety stress blocking | STAI-S001 | Shows targeted request-level blocking before generation. |

## 4. Writing and Claim Boundary Check

Applied edits:

- Changed `partially controllable` to `diagnosable` in the Introduction.
- Changed `showing how` to `illustrate how` for ablation/case-study contribution language.
- Added text clarifying that citation repair is not evidence of coaching quality.
- Added a limitations paragraph stating that the study trades external validity for traceability.

Forbidden or high-risk claims to keep avoiding:

- robust defense
- secure against prompt injection
- clinically safe
- medically validated
- safe for deployment
- expert-validated benchmark
- broad model generalization

## 5. Artifact and Reproducibility Check

Paper-facing artifact base is recorded in `65_STAI_artifact_index_v0.1.md`. The final pre-submission check should still verify:

- `main.pdf` remains 16 pages after all P1 edits.
- No undefined citations or references.
- No overfull boxes.
- No local absolute paths, API keys, Chinese draft notes, or forbidden strong claims in the paper source.
- Paper-facing run directories contain `metadata.json` and `outputs.jsonl`.
- Public package excludes local build logs, local paths, Ollama caches, unrelated product files, and private notes.

## 6. P1 Judgment

P1 is now substantially addressed for the current workshop submission path. The remaining work is not more experiment expansion by default; it is final submission hygiene: compile, page count, source zip, anonymization, and artifact package checks.
