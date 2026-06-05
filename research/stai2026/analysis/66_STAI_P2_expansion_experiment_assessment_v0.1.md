# STAI P2 Expansion Experiment Assessment v0.1

This document evaluates whether to run additional experiments before submission.

## Current Evidence Base

Already available:

- 100-question main benchmark with qwen2.5 full workflow.
- 30-prompt targeted safety-stress suite with qwen2.5 and llama3.
- 40-question llama3 main-benchmark sanity check.
- 40-question qwen diagnostic ablations: `no_gate`, `no_audit`, `no_repair`.
- 20-question evidence-boundary diagnostic pack plus 15-item manual adjudication.
- Older v0.2 evidence-mode comparison: `retrieval_only`, `gold_only`, `retrieval_plus_gold`.

## Option A: v0.3 100q Full Ablation

Decision: not recommended before the current STAI submission unless reviewers or page budget demand it.

Reason:

- It is the strongest experimental expansion, but also the most expensive.
- It would likely require new Results tables and new limitations.
- The existing 40-question balanced ablation already supports the paper's narrow diagnostic claim.

When to run:

- if the target venue asks for stronger ablation evidence;
- if the paper is expanded beyond workshop length;
- if we want a future journal version.

## Option B: Third Model or API Model

Decision: optional, lower priority than reproducibility packaging.

Reason:

- A third model would address the "single primary model" objection.
- But if only a small subset is run, it remains a sanity check, not a full model-generalization study.
- API models add cost, version instability, and reproducibility complications.

Recommended version if run:

- 30-40 question balanced subset only.
- Same `retrieval_plus_gold` mode.
- Report as supplementary model sensitivity, not robustness.

## Option C: Multi-Turn Safety Stress

Decision: valuable future work, not recommended for this submission unless the paper pivots more strongly toward security.

Reason:

- It fits STAI thematically.
- But it introduces a new interaction setting that current Method and Evaluation sections do not fully define.
- It would require new benchmark design, new state definitions, and likely new failure categories.

Recommended placement:

- Future work or appendix.
- Strong candidate for a follow-up paper on multi-turn advisory safety.

## Option D: Retrieval-Only vs Retrieval-Plus-Gold on v0.3

Decision: useful, but not urgent.

Reason:

- Older v0.2 evidence-mode comparison already supports the retrieval sufficiency argument.
- Re-running on v0.3 would make the claim cleaner, but would add experimental load and Results complexity.

Recommended compromise:

- Keep v0.2 evidence-mode comparison as supporting diagnostic evidence.
- If time allows after submission draft stabilization, run a 40-question v0.3 retrieval-mode subset rather than full 100q.

## Option E: External Runner / Coach Spotcheck

Decision: strongest credibility upgrade, but only if protocol is made formal.

Reason:

- It directly addresses the "author-authored labels" critique.
- But informal feedback cannot be called expert validation.
- A credible version needs a blinded sheet, rubric, reviewer background, conflict statement, and disagreement handling.

Recommended version:

- 20-30 item blind spotcheck.
- Ask 1-2 runners/coaches to label answerability, safety boundary, overclaim, and citation support.
- Write as "external sanity check" only, not expert validation, unless reviewers are qualified and the protocol is documented.

## Recommended Next Action

For the current paper:

1. Do not run v0.3 100q full ablation now.
2. Do not add multi-turn stress now.
3. Keep the older retrieval-mode comparison as supporting diagnostic evidence.
4. Focus on reproducibility packaging and final manuscript polish.
5. If one extra thing is worth doing, do a small external blind spotcheck, but only with a formal rubric and conservative wording.
