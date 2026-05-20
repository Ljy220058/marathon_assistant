# Final Hardening Scope Review

Owner section: Agent 1, Challenge/Formalism Lead.

Date: 2026-05-16.

## Paper Baseline

| Item | Current status | Evidence | Scope decision |
|---|---|---|---|
| Title | Pass | Both `paper/main.tex` and `submission_package/paper/main.tex` use `A Trace-Governed Rule Challenge for Evidence-Bounded Exercise Prescription`. | Preserve exact title. |
| Artifact URL | Pass | Abstract/introduction area points to `https://github.com/Ljy220058/m-exrxbench`. | Preserve exact URL. |
| Rule Challenge framing | Pass after small patch | `Challenge Definition` now states: "The challenge is to evaluate evidence-bounded exercise prescription agents under rule-governed risk, evidence, repair, and trace constraints." | Keep the paper visibly about challenge definition plus reference solution. |
| Task boundary | Pass | The paper says the task is not open-ended coaching and evaluates whether a solver may answer, downgrade, clarify, or refuse. | Do not broaden into ordinary answer-quality evaluation. |
| Labels | Pass | The paper and benchmark protocol frame labels as evaluator-only fields; the abstract says results are artifact-level checks. | Preserve "challenge specification" framing, not clinical ground truth. |
| Rule contract | Pass with formalism support | `Rule Reasoning Interface`, `Risk and Evidence Gates`, `Prescription Contract`, and `Rule Auditor and Bounded Repair` are present. | Add supporting coverage notes outside the paper rather than expanding the manuscript heavily. |
| Correctness/completeness | Pass after small patch | `Metrics` now defines correctness as benchmark-internal rule consistency and completeness as declared challenge coverage. | Keep correctness separate from medical correctness and population representativeness. |
| Banned claims | Pass in visible paper text reviewed | The manuscript repeatedly rejects clinical safety, clinical validity, deployment readiness, and outcome claims. | Do not add external expert annotation, clinical validation, real-world safety, deployable coach, or outcome-improvement claims. |

## Hardened In This Pass

- Added an explicit one-sentence challenge definition to both manuscript copies.
- Added benchmark-internal correctness and completeness language to both manuscript copies.
- Created reviewer-facing support files for challenge definition, correctness/completeness, rule contract coverage, and final paper review.

## Not Hardened By Agent 1

- Artifact baseline: current commit, release-file list, validator status, PDF metadata, and page count remain Agent 2 ownership.
- Evidence-chain/example readability: trace example, hard100 exposition, and figure/table placement remain Agent 3 ownership.
- Release hygiene and public repository update remain outside this pass.

## Scope Lock

This pass stayed inside `docs/paper_project/marathon_exrx_ruleml2026/` and touched only the Agent 1 target files plus the two allowed manuscript files. No work was planned or performed in `paper_stai2026/`.

## Planned Paper Edit Verification

| Edit | Target section | Verification |
|---|---|---|
| Add challenge sentence | `Challenge Definition` | `rg -n "The challenge is to evaluate evidence-bounded" paper/main.tex submission_package/paper/main.tex` |
| Add correctness/completeness boundary | `Metrics` | `rg -n "benchmark-internal rule consistency|Completeness means" paper/main.tex submission_package/paper/main.tex` |

