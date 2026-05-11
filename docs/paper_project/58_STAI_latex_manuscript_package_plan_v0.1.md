# STAI LaTeX Manuscript Package Plan v0.1

## 1. Purpose

This document defines how to convert the current Markdown-based STAI paper draft into a LaTeX manuscript package without losing traceability, citations, figures, tables, or claim boundaries.

Current source draft:

- `docs/paper_project/51_STAI_paper_draft_v0.1.md`

Supporting source files:

- `docs/paper_project/54_STAI_references_bibtex_v0.1.bib`
- `docs/paper_project/figures/figure1_method_workflow.png`
- `docs/paper_project/55_STAI_claim_evidence_audit_v0.1.md`
- `docs/paper_project/56_STAI_tables_and_figures_v0.1.md`
- `docs/paper_project/57_STAI_abstract_introduction_revision_v0.1.md`

## 2. Recommended Package Directory

Create a separate manuscript package under:

- `docs/paper_project/paper_stai2026/`

Recommended structure:

```text
docs/paper_project/paper_stai2026/
  main.tex
  references.bib
  figures/
    figure1_method_workflow.png
  sections/
    01_introduction.tex
    02_related_work.tex
    03_problem_setup.tex
    04_method.tex
    05_benchmark.tex
    06_experimental_setup.tex
    07_results.tex
    08_error_analysis.tex
    09_limitations.tex
    10_conclusion.tex
  appendix/
    appendix_tables.tex
  README.md
```

Rationale:

- `main.tex` stays small and mostly contains package imports, title metadata, abstract, and section includes.
- `sections/` prevents the paper from becoming one large hard-to-edit file.
- `appendix/` lets us move optional diagnostic tables out of the main text if page limits are tight.
- `README.md` records build commands, source artifact mapping, and what has not yet been venue-verified.

## 3. Template Choice

Until STAI releases or confirms a required template, use a conservative generic LaTeX article skeleton:

- document class: `article`
- bibliography: BibTeX-compatible `references.bib`
- table style: `booktabs`
- figure support: `graphicx`
- hyperlinks: `hyperref`
- citations: `natbib` or plain `\bibliographystyle{plainnat}`

Do not claim final venue compliance until the official STAI / ECML PKDD workshop template is checked.

When the official template is known:

1. Replace only the class and front-matter structure.
2. Keep section files stable.
3. Re-run compile and citation checks.
4. Re-check page length and appendix placement.

## 4. Content Mapping

| Markdown section | LaTeX target | Notes |
|---|---|---|
| Title | `main.tex` | Keep current title unless later title review changes it. |
| Abstract | `main.tex` | Current abstract is about 183 rough English words. |
| 1. Introduction | `sections/01_introduction.tex` | Preserve contribution-first framing. |
| 2. Related Work | `sections/02_related_work.tex` | Preserve all `\cite{}` keys. |
| 3. Problem Setup | `sections/03_problem_setup.tex` | Convert inline code states to `\texttt{}`. |
| 4. Method | `sections/04_method.tex` | Include Figure 1 here. |
| 5. Benchmark | `sections/05_benchmark.tex` | Keep pilot-scale language. |
| 6. Experimental Setup | `sections/06_experimental_setup.tex` | Keep reproducibility artifacts; consider moving long paths to appendix if needed. |
| 7. Results | `sections/07_results.tex` | Convert Table 1-4 with captions from `56`. |
| 8. Error Analysis | `sections/08_error_analysis.tex` | Preserve conservative false-refusal framing. |
| 9. Limitations | `sections/09_limitations.tex` | Keep strong boundaries. |
| 10. Conclusion | `sections/10_conclusion.tex` | Keep pilot evidence / partially controllable wording. |
| 11. References | `main.tex` bibliography block | Do not keep the Markdown note as a numbered section. |

## 5. Main-Text Table Plan

Main text should include:

1. Table 1: Main 100-question pilot benchmark result.
2. Table 2: Targeted safety-stress result.
3. Table 3: Representative case studies.
4. Table 4: v0.3 40-question ablation subset.

Appendix candidates:

- main category x status table;
- stress category result table;
- supplementary llama3 40-question subset table;
- v0.2 evidence-mode comparison.

Page-limit rule:

- If the paper exceeds the page limit, move Table 3 details and optional diagnostics to appendix first.
- Do not remove the limitations section to save space.

## 6. Figure Plan

Figure source:

- `docs/paper_project/figures/figure1_method_workflow.png`

LaTeX target:

- `docs/paper_project/paper_stai2026/figures/figure1_method_workflow.png`

Caption source:

- `docs/paper_project/56_STAI_tables_and_figures_v0.1.md`

Caption to use:

> Evidence-gated audit-and-repair workflow for safety-sensitive endurance-training advice. User requests first pass through request-level filtering and evidence retrieval. Evidence and risk gates determine whether generation is allowed, bounded, or refused. Draft answers must pass an independent grounding auditor; bounded citation/grounding repair can produce a partial answer or refusal when support remains insufficient. The figure highlights refusal as an explicit workflow state rather than a generic failure.

## 7. Bibliography Plan

Source BibTeX:

- `docs/paper_project/54_STAI_references_bibtex_v0.1.bib`

LaTeX target:

- `docs/paper_project/paper_stai2026/references.bib`

Current status:

- 23 citation keys appear in the Markdown draft.
- 23 BibTeX entries exist.
- No missing or unused citation keys were found in the latest check.

Boundary:

- The BibTeX file is a candidate bibliography based primarily on arXiv/public metadata.
- Proceedings versions should be verified before final submission.

## 8. Build and Verification Commands

After package creation, run:

```powershell
cd C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手\docs\paper_project\paper_stai2026
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

If `latexmk` is available, prefer:

```powershell
cd C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手\docs\paper_project\paper_stai2026
latexmk -pdf main.tex
```

Post-build checks:

- PDF is generated.
- No unresolved citations: search log for `Citation` and `undefined`.
- No unresolved references: search log for `Reference` and `undefined`.
- Figure 1 renders.
- Tables do not overflow page width.
- Abstract remains under the target venue limit.
- References are present and not empty.

## 9. Conversion Rules

Use these rules during conversion:

- Convert Markdown code states such as `partial_answer` to `\texttt{partial\_answer}`.
- Escape underscores in ordinary text.
- Keep citation keys unchanged.
- Use `table*` only if the target template supports two-column layout and the table is too wide.
- Prefer `booktabs` tables over vertical rules.
- Keep long artifact paths in monospace or move them to `README.md` / appendix.
- Do not invent acknowledgments, author affiliations, funding, or ethics text.

## 10. Required Manual Decisions Before Final Submission

These do not block initial package creation, but they must be resolved before submission:

1. Official STAI template or generic workshop template.
2. Author names, affiliations, and contact email.
3. Whether the paper is anonymous during review.
4. Page limit and appendix policy.
5. Final AI usage disclosure text.
6. Final data/code availability statement.
7. Whether to include v0.2 evidence-mode comparison in main text, appendix, or omit it.

## 11. Recommended Next Execution Step

Next step:

> Create `docs/paper_project/paper_stai2026/` and convert the current draft into a compilable LaTeX package using the structure above.

Minimum first-pass success criteria:

- `main.tex`, `references.bib`, section files, figure copy, appendix file, and README exist.
- `pdflatex`/`bibtex` or `latexmk` can build a PDF.
- Citation keys compile without missing entries.
- Figure 1 is included.
- Table 1-4 appear in the Results section.

Do not make claims about final submission readiness until the generated LaTeX package compiles and the official venue format is checked.
