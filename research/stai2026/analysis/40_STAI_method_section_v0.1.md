# STAI Method Section v0.1

This is a paper-facing Method draft. It should be read as the basis for the final STAI manuscript, not as a complete implementation manual.

## 1. Method Overview

We propose an evidence-gated audit-and-repair workflow for safety-sensitive endurance-training advice. The workflow is designed around a simple principle: the language model should not be the only component deciding whether a user request is answerable, safe, or sufficiently supported by evidence. Instead, the system decomposes the advisory process into explicit control points: request-level filtering, evidence retrieval, evidence sufficiency checking, risk checking, evidence-constrained generation, independent auditing, and repair or refusal.

The workflow is evaluated as S3, the full system. Compared with vanilla RAG, S3 does not directly pass retrieved text to a generator and trust the generated answer. Retrieved or curated evidence is first passed through an Evidence Gate. Safety-sensitive cases are additionally checked by a Risk Gate. Draft answers are then reviewed by an independent Auditor, which can approve the answer, request citation or grounding repair, or force refusal.

The method is intentionally modular. Later experiments can replace individual modules, such as the deterministic pre-gate or retriever, while preserving the same trace schema and evaluation metrics.

## 2. Task and Output States

Given a user query \(q\), the system must return one of three output states:

- `answered`: the system provides an answer supported by available evidence and passes audit.
- `partial_answer`: the system provides a bounded answer after repair, usually because citation or support constraints required a conservative rewrite.
- `refused`: the system declines to answer because evidence is insufficient, the request is unsafe, or the request asks for unsupported claims, fabricated evidence, or unsafe continuation.

This output design treats refusal as a first-class result rather than a generic failure. In safety-sensitive advisory RAG, a correct refusal can be the desired behavior when the user asks for unsupported predictions, fabricated citations, medical reassurance, or dangerous training continuation.

## 3. Workflow Components

### 3.1 Pre-Gate Request Filter

The pre-gate is a deterministic request-level filter applied before retrieval and generation. It detects request patterns that should not be passed to the generator even if later retrieval returns superficially relevant text. The current v0.4 policy registry covers:

- instruction injection or evidence fabrication pressure;
- unsupported performance guarantees or precise individual predictions;
- red-flag symptoms paired with requests to continue or prescribe training;
- worsening or persistent pain paired with training-continuation pressure;
- requests to suppress safety advice or cherry-pick risk evidence.

If the pre-gate fires, the workflow returns a refusal with a policy-level reason. This module should be interpreted as a targeted request-level hardening layer, not as a general prompt-injection defense.

Expansion path: the deterministic pre-gate can later be replaced or augmented by a learned classifier or LLM-as-judge module, while retaining the same `pre_gate` trace fields and rule-level reporting.

### 3.2 Evidence Retrieval and Evidence Modes

The workflow supports three evidence modes:

- `retrieval_only`: uses ordinary vector-retrieved contexts from the current knowledge base.
- `gold_only`: uses curated benchmark evidence spans.
- `retrieval_plus_gold`: combines retrieved contexts with curated evidence.

These modes separate retrieval quality from downstream workflow behavior. `gold_only` serves as a curated-evidence upper bound, while `retrieval_only` exposes failures caused by retrieval noise or evidence misses. The main 100-question run uses `retrieval_plus_gold`, which is the most informative setting for testing the full workflow while retaining curated benchmark traceability.

### 3.3 Evidence Gate

The Evidence Gate decides whether the visible evidence is sufficient to answer the query. It outputs:

- `answerable`: evidence is sufficient for the requested answer.
- `partial`: evidence supports only a bounded answer.
- `unanswerable`: evidence is insufficient, irrelevant, missing, or unsafe to use for the requested claim.

The gate also records required evidence chunks and missing evidence. This makes evidence insufficiency auditable. A user request for a precise VO2max improvement, a guaranteed race result, or a nonexistent page citation should be rejected when the evidence does not support it.

### 3.4 Risk Gate

The Risk Gate identifies safety-sensitive cases and forbidden advice. It is activated for risk-related benchmark items and stress prompts. Risk examples include:

- chest pain, syncope, palpitations, fever, or suspected infection;
- known cardiovascular disease or long inactivity before vigorous exercise;
- exertional heat illness symptoms;
- persistent or worsening musculoskeletal pain;
- high fatigue or overreaching signals.

The Risk Gate records required safety actions, such as stopping activity, lowering intensity, seeking professional evaluation, or refusing a high-intensity plan. It also records forbidden advice, such as continuing the original plan, increasing intensity, or providing diagnosis-like reassurance.

### 3.5 Evidence-Constrained Generator

If the request is not blocked and the evidence gate does not require immediate refusal, an answer generator drafts a response under explicit evidence and risk constraints. The generator is instructed to use only allowed evidence and to avoid unsupported claims. It must cite available evidence identifiers rather than inventing sources, pages, or DOI-like references.

The generator is not trusted as the final authority. Its output is a draft that must pass independent audit.

### 3.6 Independent Auditor

The Auditor checks the draft answer for claim support, citation validity, and risk compliance. It can return:

- `pass`: the answer can be released.
- `repair_required`: the answer may be salvageable through bounded repair.
- `refuse_required`: the answer should be refused because it is unsupported, unsafe, or citation-invalid in a way that cannot be safely repaired.

The Auditor makes `partial_answer` observable. In our experiments, many partial answers correspond to citation repair rather than complete answer failure. This is why the paper reports `partial_answer` and citation repair separately rather than collapsing everything into a binary success metric.

### 3.7 Repair or Refusal

The repair stage performs bounded correction. It can:

- remove unsupported claims;
- add safety de-escalation language;
- repair missing or invalid citations using available evidence;
- convert the output into refusal when repair would require fabricating support.

Repair is deliberately bounded. The system is not allowed to fill evidence gaps by model knowledge. If the evidence cannot support the requested claim, the workflow should refuse or provide a narrower answer.

## 4. Trace Schema

Each run stores a structured trace for every question:

```json
{
  "qid": "...",
  "question": "...",
  "evidence_mode": "retrieval_plus_gold",
  "pre_gate": {},
  "retrieved_contexts": [],
  "gold_evidence_contexts": [],
  "evidence_contexts": [],
  "evidence_gate": {},
  "risk_gate": {},
  "draft_generation": {},
  "audit": {},
  "repair": {},
  "final_answer": "...",
  "final_status": "answered | partial_answer | refused"
}
```

This trace design supports reproducibility and error analysis. It lets the paper distinguish:

- retrieval failure from evidence insufficiency;
- correct refusal from false refusal;
- citation repair from unsupported answer generation;
- safety-preserving refusal from unsafe continuation.

## 5. Workflow Variants and Ablations

The method supports direct ablations:

- `no_gate`: bypasses the Evidence Gate.
- `no_audit`: bypasses the independent Auditor.
- `no_repair`: disables repair after audit.
- `pre_gate_mode=off`: disables deterministic request hardening.
- `pre_gate_mode=hardening_v0_4`: enables the current request-level hardening rules.

These ablations are important for the paper claim. They show whether the workflow behavior is caused by explicit control points rather than by a single prompt.

## 6. Why This Is Agentic Rather Than Vanilla RAG

The workflow is agentic in the operational sense that distinct modules perform specialized roles with explicit intermediate states and control authority:

- the pre-gate can block before retrieval;
- the Evidence Gate can mark evidence as answerable, partial, or unanswerable;
- the Risk Gate can impose safety constraints;
- the generator drafts but cannot approve;
- the Auditor can reject or require repair;
- the repair/refusal stage determines the final status.

This differs from vanilla RAG, where retrieval and generation are usually collapsed into a single prompt-conditioned generation step. The innovation is not the use of persona prompts or role labels, but the auditable control loop over evidence, risk, generation, audit, and repair.

## 7. Method Claim Boundary

The method should be described as:

> a modular evidence-gated audit-and-repair workflow for safety-sensitive advisory RAG.

It should not be described as:

- a clinically validated training prescription system;
- a general adversarial prompt-injection defense;
- a large-scale benchmark solution;
- a proof that generated training advice improves athletic outcomes.

The current evidence supports workflow-level diagnostics, refusal behavior, citation traceability, and targeted safety-stress handling. It does not support real-world medical or coaching deployment claims.

## 8. Figure Caption Draft

**Figure 1. Evidence-gated audit-and-repair workflow for safety-sensitive endurance-training RAG.** A user query is first checked by a request-level pre-gate. Non-blocked requests enter retrieval and evidence gating. Safety-sensitive cases are constrained by a risk gate before generation. Draft answers are checked by an independent auditor and either released, repaired, or refused. The workflow records all intermediate states for diagnostic evaluation.
