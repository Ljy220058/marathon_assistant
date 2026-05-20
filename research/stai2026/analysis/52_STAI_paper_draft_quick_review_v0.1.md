# STAI Paper Draft Quick Review v0.1

Reviewed file:

- `docs/paper_project/51_STAI_paper_draft_v0.1.md`

Review mode:

- quick pre-submission readiness review;
- methodology, novelty, evidence support, and claim-boundary focus;
- not a citation-compliance review.

## 1. Overall Assessment

The draft is now a coherent workshop-paper skeleton rather than a collection of project notes. It has a clear method, benchmark, experimental setup, results, ablation evidence, case studies, error analysis, and limitations.

Current readiness:

| dimension | assessment |
|---|---|
| paper identity | clear |
| method contribution | plausible for workshop |
| experiment support | medium but usable |
| claim boundary | mostly controlled |
| related work | present but citation-check incomplete |
| submission readiness | not ready yet; draft-ready |

Best current framing:

> a workflow-level diagnostic paper for trustworthy advisory RAG.

Avoid stronger framing:

- general secure RAG system;
- clinically validated training advisor;
- large-scale benchmark paper;
- broad multi-model evaluation.

## 2. Strengths

### 2.1 The method is concrete

The workflow is not just "RAG plus agents". It has named control points:

- pre-gate;
- Evidence Gate;
- Risk Gate;
- Evidence-Constrained Generator;
- Independent Auditor;
- Bounded Repair;
- Refusal.

This makes the innovation more defensible than a vague multi-agent claim.

### 2.2 Refusal is evaluated as a first-class state

The paper reports:

- designed-unanswerable refusal;
- false refusal;
- citation repair;
- safety-stress refusal.

This is a good fit for STAI because it emphasizes trustworthy behavior, not just answer rate.

### 2.3 Ablation result is useful

The v0.3 40-question ablation is one of the strongest pieces of evidence:

- full workflow: designed-unanswerable refused 10 / 10;
- `no_gate`: designed-unanswerable refused 0 / 10.

This directly supports the claim that the Evidence Gate is doing real work.

### 2.4 Case studies are balanced

The selected cases include:

- correct refusal;
- citation repair;
- conservative false refusal;
- stress blocking.

This makes the paper more credible because it does not hide failures.

## 3. Main Weaknesses

### 3.1 Related work is not citation-ready

The draft currently lists representative works by title. This avoids fabrication, but it is not yet a finished related-work section.

Required next step:

- verify authors, years, venues, arXiv IDs, and BibTeX;
- convert title lists into concise prose with real citations.

### 3.2 Benchmark labels are author-authored

The limitation is disclosed, but reviewers may still ask whether the benchmark labels are reliable.

Possible mitigation:

- add a small "annotation protocol" paragraph;
- include a short evidence-field schema table;
- optionally add a 10-20 item external or second-pass review if feasible.

### 3.3 Full 100-question ablation is not available

The v0.3 ablation is a balanced 40-question subset, not full 100. This is acceptable for a workshop paper if clearly labeled, but a reviewer may ask for full ablations.

Possible mitigation:

- keep the 40-question wording explicit;
- say it is a diagnostic subset;
- avoid writing "the ablation proves" in broad terms.

### 3.4 The current benchmark is still small

100 main questions plus 30 stress prompts is more credible than the earlier pilot, but it is still not a large benchmark.

Possible mitigation:

- emphasize versioning and expansion;
- frame the paper as a diagnostic workflow study;
- make future work concrete: 150-200 main questions, 50 stress prompts, more models, expert labels.

## 4. Reviewer Risk Forecast

Likely reviewer concerns:

1. "Is this just prompt engineering?"
   - Response: emphasize explicit trace states, Evidence Gate ablation, and case-study traces.

2. "Is the benchmark too small?"
   - Response: position as a focused pilot benchmark, not a large-scale benchmark paper.

3. "Are labels expert-validated?"
   - Response: no; state author-authored pilot labels and propose expert review as future work.

4. "Does safety-stress refusal prove robustness?"
   - Response: no; describe as targeted deterministic request-level hardening.

5. "Why is partial_answer so frequent?"
   - Response: explain citation repair and grounding observability.

## 5. Required Next Revisions

Priority order:

1. Convert Related Work from title lists into verified cited prose.
2. Add Figure 1 reference in the Method section.
3. Add a concise "Dataset and Evidence Schema" table.
4. Tighten Abstract to workshop length if needed.
5. Add a "Reproducibility Artifacts" paragraph listing datasets, run directories, and scripts.
6. Convert draft to LaTeX only after citations are verified.

## 6. Editorial Decision Simulation

Current simulated decision:

> Weak accept potential for a workshop after citation and related-work cleanup; currently not submission-ready because references are not verified and the related-work section is still scaffold-like.

The core paper is viable if kept honest:

- workflow-level diagnostic;
- pilot benchmark;
- targeted stress suite;
- no clinical deployment claim;
- no broad adversarial robustness claim.
