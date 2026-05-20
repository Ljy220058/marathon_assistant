# STAI Claim-Evidence Audit v0.1

Last updated: 2026-05-11

## 1. Purpose

This audit checks whether the current paper draft makes claims that are supported by local artifacts, verified references, or explicit limitations. It is intentionally conservative: a claim is marked "revise" if it is directionally true but too strong for the current evidence.

Audited draft:

- `docs/paper_project/51_STAI_paper_draft_v0.1.md`
- `docs/paper_project/paper_stai2026/main.tex`
- `docs/paper_project/paper_stai2026/sections/*.tex`

Primary evidence artifacts:

- main benchmark: `docs/paper_project/stai_benchmark_v0.3_100_question_draft.jsonl`
- safety stress benchmark: `docs/paper_project/stai_safety_stress_benchmark_v0.2_30_question.jsonl`
- main run: `docs/paper_project/runs/stai_s3_rpg_100q_v03_qwen_run01`
- qwen stress run: `docs/paper_project/runs/stai_safety_stress_30q_hardened_v04_run03`
- llama3 stress run: `docs/paper_project/runs/stai_safety_stress_30q_hardened_v04_llama3_run03`
- llama3 subset run: `docs/paper_project/runs/stai_s3_rpg_40q_v03_llama3_run01`
- v0.3 ablation runs:
  - `docs/paper_project/runs/stai_ablation_no_gate_40q_v03_qwen_run02`
  - `docs/paper_project/runs/stai_ablation_no_audit_40q_v03_qwen_run01`
  - `docs/paper_project/runs/stai_ablation_no_repair_40q_v03_qwen_run01`
- current LaTeX bibliography: `docs/paper_project/paper_stai2026/references.bib`
- citation check: `docs/paper_project/53_STAI_related_work_citation_check_v0.1.md`
- BibTeX candidates: `docs/paper_project/54_STAI_references_bibtex_v0.1.bib`

## 2. Audit Rubric

| Status | Meaning |
|---|---|
| supported | Claim is backed by run artifacts, benchmark files, citation records, or conservative reasoning from them. |
| supported with boundary | Claim is usable only with explicit scope qualifiers. |
| revise | Claim is too strong or ambiguous and should be softened. |
| not supported | Claim should be removed unless new evidence is added. |

## 3. Contribution Claims

| Claim | Evidence | Status | Action |
|---|---|---|---|
| The paper proposes an evidence-gated audit-and-repair workflow. | Method section; S3 traces include evidence gate, risk gate, audit, repair, final status. | supported | Keep. |
| The contribution is workflow-level, not a new model or universal defense. | Positioning doc and limitations explicitly state this boundary. | supported | Keep. |
| The benchmark contains 100 questions, 90 evidence-backed and 10 designed-unanswerable controls. | `validate_stai_benchmark_questions.py` output: rows 100; evidence_status verified_span 90 / designed_unanswerable 10. | supported | Keep. |
| The safety-stress suite contains 30 prompts across five categories. | Stress benchmark and run summaries: prompt_injection 6, unsafe_request 8, citation_hallucination 6, overclaim_request 6, evidence_conflict 4. | supported | Keep. |
| Diagnostic runs, ablations, and case studies illustrate how refusal, repair, and hardening behave. | Runs, `46`-`50` docs, case table in draft. | supported with boundary | Use "diagnostic" and "pilot"; avoid "prove". |

## 4. Method Claims

| Claim | Evidence | Status | Action |
|---|---|---|---|
| S3 uses explicit control points instead of trusting a single generator. | Output traces include `evidence_gate`, `risk_gate`, `draft_generation`, `audit`, `repair`. | supported | Keep. |
| The pre-gate is deterministic request-level hardening. | Metadata has `pre_gate_mode=hardening_v0_4` for stress runs; outputs include triggered rule IDs. | supported | Keep. |
| The pre-gate is not a general prompt-injection defense. | This is a limitation and boundary, not a performance claim. | supported | Keep. |
| Evidence modes separate retrieval quality from downstream behavior. | Runs use `gold_only`, `retrieval_only`, and `retrieval_plus_gold`; main v0.3 run uses `retrieval_plus_gold`. | supported with boundary | Keep, but treat older v0.2 mode comparison as supporting diagnostic only. |
| Repair can convert to refusal when repair would require fabricated support. | Repair actions include `refused_due_to_insufficient_evidence` and `refused_due_to_insufficient_evidence_with_safety_deescalation`. | supported | Keep. |

## 5. Experiment Claims

| Claim | Evidence | Status | Action |
|---|---|---|---|
| Main qwen 100-question run produced 24 answered, 62 partial_answer, 14 refused. | Computed from `stai_s3_rpg_100q_v03_qwen_run01/outputs.jsonl`. | supported | Keep. |
| Main run refused 10 / 10 designed-unanswerable controls. | Computed from dataset + outputs. | supported | Keep. |
| Main run had 4 / 90 false refusals on answerable questions. | False-refusal qids: STAI-P036, STAI-P040, STAI-P081, STAI-P086. | supported | Keep. |
| Citation repair count is 62. | Audit `repair_required` 62; repair action `repaired_invalid_or_missing_citations` 62. | supported | Keep. |
| Safety stress refused 30 / 30 for both qwen and llama3. | Stress run outputs: qwen refused 30; llama3 refused 30. | supported | Keep. |
| Most safety-stress refusals occurred before generation. | Pre-gate triggered 28 / 30 for qwen; 29 / 30 for llama3. | supported | Keep. |
| Llama3 40-question subset produced 13 answered, 17 partial_answer, 10 refused. | Computed from `stai_s3_rpg_40q_v03_llama3_run01/outputs.jsonl`. | supported | Keep. |
| Llama3 subset had 0 / 30 false refusals and refused 10 / 10 designed-unanswerable controls. | Computed from dataset + outputs. | supported | Keep. |
| v0.3 ablation table values are correct. | Computed from ablation outputs. | supported | Keep. |
| `no_gate` removed refusal control for designed-unanswerable items in the ablation subset. | `no_gate` produced 0 / 10 designed-unanswerable refusals and 40 partial_answer outputs. | supported | Keep with subset-scoped diagnostic wording. |

## 6. Safety and Trustworthiness Claims

| Claim | Evidence | Status | Action |
|---|---|---|---|
| Refusal can be a correct output. | Designed-unanswerable controls and stress prompts are intentionally refusal-eligible. | supported | Keep. |
| The workflow makes failure modes observable. | Trace schema records intermediate gate/audit/repair states. | supported | Keep. |
| The workflow makes failure modes controllable. | Current evidence supports partial control through gates/repair; "controllable" alone may sound too broad. | revise | Soften to "more visible and partially controllable" or "more controllable within this pilot setting." |
| Safety-stress result establishes targeted request-level hardening. | 30-prompt constructed suite, two local models. | supported with boundary | Keep targeted wording. |
| Safety-stress result establishes general adversarial robustness. | No broad paraphrase/adaptive adversary/multi-turn testing. | not supported | Do not claim. |
| The system is clinically safe or deployment-ready. | No clinical validation or expert external annotation. | not supported | Do not claim. |

## 7. Related Work and Citation Claims

| Claim | Evidence | Status | Action |
|---|---|---|---|
| RAG and verifiability work motivate evidence traceability. | `53_STAI_related_work_citation_check_v0.1.md`; BibTeX entries in `54`. | supported | Keep. |
| Agentic RAG, verification, reflection, and repair motivate explicit critique/repair components. | Self-RAG, CRAG, CoVe, Reflexion, Self-Refine entries verified as candidates. | supported | Keep. |
| Tool and multi-agent systems motivate modular workflow design. | ReAct, MRKL, Toolformer, ReWOO, LLM Compiler, MemGPT, AutoGen, CAMEL, etc. | supported | Keep. |
| Our work is novel because it simply uses multiple agents. | Related work shows this is not new. | not supported | Do not claim. |
| Current BibTeX is final proceedings metadata. | Entries are arXiv/public-page candidates; proceedings versions not fully checked. | revise | Keep `54` as candidate BibTeX until final venue formatting. |

P0 citation-key pass on the LaTeX manuscript:

- `\cite{}` keys used in `main.tex`, `sections/*.tex`, and `appendix/*.tex`: 23 total, 23 unique.
- Missing keys in `docs/paper_project/paper_stai2026/references.bib`: none.
- Unused keys in `docs/paper_project/paper_stai2026/references.bib`: none.
- Related Work citation meanings remain aligned with `53_STAI_related_work_citation_check_v0.1.md`: RAG/verifiability citations support grounding and citation traceability; Self-RAG/CRAG/CoVe/Reflexion/Self-Refine support retrieve-generate-critique/repair positioning; ReAct/MRKL/Toolformer/ReWOO/LLM Compiler/MemGPT support modular workflow positioning; AutoGen/CAMEL/ChatDev/MetaGPT/AgentVerse/AutoAgents/Debate/MDAgents support multi-agent coordination or high-stakes advisory positioning.
- Unverified metadata boundary: final proceedings versions, page ranges, and venue metadata remain to be verified. Do not add page ranges, conference versions, or DOI changes unless programmatically verified from primary metadata.

## 8. Draft Revisions Required

The current LaTeX manuscript is broadly aligned with evidence. The earlier required softening has been applied or superseded:

1. Introduction now uses pilot-scoped workflow-diagnostic wording rather than "Our answer is yes."
2. Conclusion now states that the results make grounding, refusal, repair, and safety-boundary behavior "more observable in the reported setup" rather than broadly controllable.
3. Final P0 wording pass softened strong verbs:
   - `show how explicit control points affect` -> `illustrate how explicit control points affect`;
   - `frameworks ... demonstrate` -> `frameworks ... describe systems in which`;
   - `systems show that LLM applications can be decomposed` -> `systems illustrate ways to decompose LLM applications`;
   - `Reflexion and Self-Refine show` -> `Reflexion and Self-Refine study`;
   - `destroys refusal control` -> `removes refusal control ... in this subset`.

Optional later revision:

- Add a short note that safety-stress refusal is the expected target behavior for constructed stress prompts, not a false-refusal metric.

## 9. P0 Numeric Evidence Pass on LaTeX Manuscript

All manuscript result numbers listed below were recalculated from run artifacts on 2026-05-11. No manual result was added in this pass.

| Manuscript number / claim | Source artifact | Recomputed value | Status |
|---|---|---:|---|
| Main benchmark size | `stai_benchmark_v0.3_100_question_draft.jsonl` | 100 rows | supported |
| Main evidence-backed / designed-unanswerable split | `stai_benchmark_v0.3_100_question_draft.jsonl` | 90 verified_span / 10 designed_unanswerable | supported |
| Main category split | `stai_benchmark_v0.3_100_question_draft.jsonl` | fact 30, applied_reasoning 30, risk_safety 30, evidence_insufficient 10 | supported |
| Main qwen final statuses | `runs/stai_s3_rpg_100q_v03_qwen_run01/outputs.jsonl` and `summary_auto.json` | answered 24, partial_answer 62, refused 14 | supported |
| Main designed-unanswerable refusal | same main run | 10 / 10 | supported |
| Main answerable false refusal | same main run | 4 / 90; qids STAI-P036, STAI-P040, STAI-P081, STAI-P086 | supported |
| Main citation repair count | same main run | 62 | supported |
| Main risk-safety answered or partial_answer | same main run | 26 / 30 | supported |
| Safety-stress benchmark size and categories | `stai_safety_stress_benchmark_v0.2_30_question.jsonl` | 30 prompts; 6 prompt_injection, 8 unsafe_request, 6 citation_hallucination, 6 overclaim_request, 4 evidence_conflict | supported |
| Qwen safety-stress refusal | `runs/stai_safety_stress_30q_hardened_v04_run03/outputs.jsonl` | refused 30 / 30; pre-gate 28, ordinary gate 2 | supported |
| Llama3 safety-stress refusal | `runs/stai_safety_stress_30q_hardened_v04_llama3_run03/outputs.jsonl` | refused 30 / 30; pre-gate 29, ordinary gate 1 | supported |
| Llama3 40-question subset statuses | `runs/stai_s3_rpg_40q_v03_llama3_run01/outputs.jsonl` | answered 13, partial_answer 17, refused 10 | supported |
| Llama3 subset designed-unanswerable refusal / false refusal | same llama3 subset run | 10 / 10; 0 / 30 | supported |
| v0.3 no_gate ablation | `runs/stai_ablation_no_gate_40q_v03_qwen_run02/outputs.jsonl` | answered 0, partial_answer 40, refused 0; designed-refusal 0 / 10; false refusal 0 / 30; citation repair 40 | supported |
| v0.3 no_audit ablation | `runs/stai_ablation_no_audit_40q_v03_qwen_run01/outputs.jsonl` | answered 26, partial_answer 0, refused 14; designed-refusal 10 / 10; false refusal 4 / 30; citation repair 0 | supported |
| v0.3 no_repair ablation | `runs/stai_ablation_no_repair_40q_v03_qwen_run01/outputs.jsonl` | answered 27, partial_answer 0, refused 13; designed-refusal 10 / 10; false refusal 3 / 30; citation repair 0 | supported |

Unverified-detail check:

- No manuscript page ranges for cited papers were found.
- No manuscript DOI claims beyond BibTeX metadata were found.
- Conference/proceedings versions remain to be verified; current `references.bib` uses arXiv-style metadata.
- Experimental setup should continue to avoid claims of external expert validation, clinical safety, real-world coaching efficacy, broad adversarial robustness, or broad model generalization.

## 10. Overall Assessment

Current status:

> Workshop-draft viable after minor wording softening.

The main evidence base is coherent for a STAI-style workshop paper if the paper remains framed as:

- workflow-level diagnostic evaluation;
- focused pilot benchmark;
- targeted safety-stress suite;
- local-model reproducible experiment;
- not clinical validation;
- not broad security robustness;
- not a large-scale benchmark.

The strongest current evidence is the combination of:

1. 100-question full workflow run;
2. 30-prompt safety-stress runs on two models;
3. 40-question second-model sanity check;
4. 40-question v0.3 ablation subset;
5. case studies exposing correct refusal, citation repair, false refusal, and stress blocking.

The weakest remaining points are:

1. no external expert label validation;
2. no full 100-question multi-model evaluation;
3. no broad adversarial paraphrase or multi-turn stress testing;
4. BibTeX still needs final proceedings/version cleanup;
5. benchmark is pilot-scale rather than comprehensive.

## 11. Final Submission Hygiene Update

Updated on 2026-05-13 after anonymous rebuild and final package generation.

| Check | Evidence | Status |
|---|---|---|
| Compact submission PDF exists | `docs/paper_project/stai2026_submission_main_8p_anonymous.pdf` | supported |
| Full manuscript PDF exists | `docs/paper_project/stai2026_submission_main_full_anonymous.pdf` | supported |
| Anonymous source package exists | `docs/paper_project/stai2026_anonymous_source_package_v0.2.zip` | supported |
| Compact PDF page count | PyMuPDF check: 7 pages | supported |
| Full PDF page count | PyMuPDF check: 16 pages | supported |
| PDF anonymity | First-page text contains `Anonymous Author(s)` and does not contain `Luo Jinyuan` or `罗锦源` | supported |
| Build log integrity | Fresh log scan found no undefined citation/reference warnings and no `Overfull \hbox` warnings | supported |
| Source package identity/secret scan | Strict scan found no local Windows path, author name, or `sk-...` style API key pattern | supported |
| 25-item author-side spotcheck | `docs/paper_project/68_STAI_25_item_author_spotcheck_v0.1.md` records 18 fully reasonable states, 7 boundary concerns, 22 no-overclaim labels, 2 mild overclaims, and 1 clear overgeneralization case | supported with boundary |

Boundary reminder: the package is suitable as an anonymous LaTeX source package for review, but the final submission system may still require real author metadata outside the PDF.
