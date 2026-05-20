# STAI Related Work Citation Check v0.1

## 1. Purpose

This document records the citation-cleaning pass for the current STAI paper draft. It replaces the earlier "representative works to verify" list with a more submission-oriented related-work set.

Rules used in this pass:

- Do not invent venues, page ranges, DOIs, or publication status.
- Prefer arXiv metadata when official proceedings metadata has not yet been checked.
- Use references to support specific positioning claims, not as decoration.
- Do not frame multi-agent orchestration, RAG, or self-critique as our standalone novelty.

## 2. Related Work Structure Now Used

The draft now uses four related-work groups:

1. RAG, verifiability, and citation grounding.
2. Agentic retrieval, critique, and repair.
3. Tool-using and modular agent workflows.
4. Multi-agent coordination and high-stakes advisory settings.

This structure better matches the paper claim:

> We study an evidence-gated audit-and-repair workflow for safety-sensitive advisory RAG, evaluated through traceable refusal, repair, and grounding behavior.

## 3. Verified Candidate References

The entries below were checked against public arXiv metadata or public paper pages during this pass. "Use in draft" means the reference has been inserted into `51_STAI_paper_draft_v0.1.md`.

| Key | Verified title | Year used | Source | Use in draft | Role |
|---|---|---:|---|---|---|
| `lewis2020rag` | Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks | 2020 | arXiv:2005.11401 | yes | Foundational RAG |
| `liu2023verifiability` | Evaluating Verifiability in Generative Search Engines | 2023 | arXiv:2304.09848 | yes | Verifiability/citation grounding |
| `gao2023alce` | Enabling Large Language Models to Generate Text with Citations | 2023 | arXiv:2305.14627 | yes | Citation generation/evaluation |
| `niu2023ragtruth` | RAGTruth: A Hallucination Corpus for Developing Trustworthy Retrieval-Augmented Language Models | 2023 | arXiv:2401.00396 metadata published 2023-12-31 | yes | RAG hallucination corpus |
| `asai2023selfrag` | Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection | 2023 | arXiv:2310.11511 | yes | Retrieve/generate/critique |
| `yan2024crag` | Corrective Retrieval Augmented Generation | 2024 | arXiv:2401.15884 | yes | Retrieval correction |
| `dhuliawala2023cove` | Chain-of-Verification Reduces Hallucination in Large Language Models | 2023 | arXiv:2309.11495 | yes | Verification loop |
| `shinn2023reflexion` | Reflexion: Language Agents with Verbal Reinforcement Learning | 2023 | arXiv:2303.11366 | yes | Agent reflection |
| `madaan2023selfrefine` | Self-Refine: Iterative Refinement with Self-Feedback | 2023 | arXiv:2303.17651 | yes | Iterative repair |
| `yao2022react` | ReAct: Synergizing Reasoning and Acting in Language Models | 2022 | arXiv:2210.03629 | yes | Reasoning/action workflow |
| `karpas2022mrkl` | MRKL Systems: A modular, neuro-symbolic architecture that combines large language models, external knowledge sources and discrete reasoning | 2022 | arXiv:2205.00445 | yes | Modular LLM systems |
| `schick2023toolformer` | Toolformer: Language Models Can Teach Themselves to Use Tools | 2023 | arXiv:2302.04761 | yes | Tool use |
| `xu2023rewoo` | ReWOO: Decoupling Reasoning from Observations for Efficient Augmented Language Models | 2023 | arXiv:2305.18323 | yes | Decoupled workflow |
| `kim2023llmcompiler` | An LLM Compiler for Parallel Function Calling | 2023 | arXiv:2312.04511 | yes | Parallel function calling |
| `packer2023memgpt` | MemGPT: Towards LLMs as Operating Systems | 2023 | arXiv:2310.08560 | yes | Memory/state management |
| `wu2023autogen` | AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation | 2023 | arXiv:2308.08155 | yes | Multi-agent conversation |
| `li2023camel` | CAMEL: Communicative Agents for "Mind" Exploration of Large Language Model Society | 2023 | arXiv:2303.17760 | yes | Role-based agent communication |
| `qian2023chatdev` | ChatDev: Communicative Agents for Software Development | 2023 | arXiv:2307.07924 | yes | SOP-like multi-agent workflow |
| `hong2023metagpt` | MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework | 2023 | arXiv:2308.00352 | yes | Structured multi-agent collaboration |
| `chen2023agentverse` | AgentVerse: Facilitating Multi-Agent Collaboration and Exploring Emergent Behaviors | 2023 | arXiv:2308.10848 | yes | Multi-agent collaboration |
| `chen2023autoagents` | AutoAgents: A Framework for Automatic Agent Generation | 2023 | arXiv:2309.17288 | yes | Dynamic agent generation |
| `du2023debate` | Improving Factuality and Reasoning in Language Models through Multiagent Debate | 2023 | arXiv:2305.14325 | yes | Debate/disagreement |
| `kim2024mdagents` | MDAgents: An Adaptive Collaboration of LLMs for Medical Decision-Making | 2024 | arXiv:2404.15155 | yes | Risk-aware/high-stakes collaboration |

## 4. References Intentionally Not Promoted Yet

No reference was permanently rejected in this pass. However, any source without checked metadata should stay out of the formal draft until verified. The previous draft's title-only list has been removed from the main paper to avoid looking like an unchecked bibliography.

## 5. Current Related-Work Claim Boundaries

Safe claims:

- RAG and citation-verifiability work motivate evidence traceability.
- Agentic RAG and verification work motivate explicit retrieve/generate/critique/repair components.
- Tool and multi-agent frameworks motivate modular workflow design.
- High-stakes medical-agent work motivates risk-aware collaboration as inspiration.

Claims to avoid:

- "Our multi-agent workflow is novel" without qualification.
- "Our hardening layer is a general prompt-injection defense."
- "Our system is clinically safe."
- "Our benchmark is large-scale or expert-validated."
- "Our citation repair proves factual correctness."

## 6. Next Citation Tasks

Before submission:

1. Check whether each arXiv entry has a peer-reviewed proceedings version.
2. Replace arXiv-only metadata only when the proceedings version is verified.
3. Convert the BibTeX to the final venue style.
4. Run a citation-orphan check after LaTeX conversion.
