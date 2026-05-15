# Source Manifest

This folder is self-contained for the RuleML+RR 2026 M-EXRx paper. Copied files are general marathon assistant/HMP materials, not unrelated manuscript sources.

## Copied Docs

| File | Source | Purpose |
|---|---|---|
| `copied_docs/half_marathon_hmp_protocol.md` | project HMP protocol note | HMP protocol rules and training structure |
| `copied_docs/half_marathon_source_audit.md` | project HMP source audit | source audit for HMP materials |

## Copied Figures

| File | Source | Purpose |
|---|---|---|
| `figures/m_exrx_ieee_architecture.svg` | generated in this workspace | IEEE/CEUR-style architecture figure |
| `figures/m_exrx_ieee_architecture.pdf` | generated in this workspace | vector submission figure used by `paper/main.tex` |
| `figures/m_exrx_ieee_architecture.png` | generated in this workspace | preview image |
| `figures/m_exrx_ieee_architecture.py` | generated in this workspace | reproducible figure script |

## Read-Only Code Sources

These files are reference sources only. Do not move or rewrite them unless implementing a new M-EXRx module.

| File | Use |
|---|---|
| `marathon_qa_assistant/core/half_marathon_protocol.py` | protocol and action logic |
| `marathon_qa_assistant/core/half_marathon_capacity_budget.py` | capacity budget |
| `marathon_qa_assistant/core/half_marathon_validator.py` | protocol audit |
| `marathon_qa_assistant/core/half_marathon_repair_executor.py` | bounded repair reference |
| `marathon_qa_assistant/core/evidence_bundle.py` | evidence bundle and trace reference |
| `marathon_qa_assistant/nodes/expert_nodes.py` | earlier expert role prototype |

## Excluded Materials

Do not copy unrelated manuscript sources, private experiment runs, unrelated
benchmark JSONL files, private Overleaf packages, or local environment
configuration into this artifact.
