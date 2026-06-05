# STAI 2026 Manuscript Package

This directory contains the LNCS-adapted review manuscript package for the STAI 2026 workshop submission.

## Official Requirements Checked

Sources checked on 2026-05-11:

- STAI 2026 official site: https://stai-workshop.org/
- ECML PKDD 2026 workshop track: https://ecmlpkdd.org/2026/submissions-workshop-track/
- ECML PKDD 2026 ethics page: https://ecmlpkdd.org/2026/ethics/
- Springer LNCS proceedings guidelines and template: https://www.springer.com/gp/computer-science/lncs/conference-proceedings-guidelines

Current interpretation for this manuscript:

- Track: STAI 2026 regular paper.
- Length: 12 to 16 pages, including references.
- Template: Springer LNCS LaTeX2e (`llncs.cls`) with `splncs04.bst`.
- Review anonymity: keep the review PDF anonymous unless STAI/ECML PKDD CMT instructions explicitly request a non-anonymous upload at submission time.
- References: LNCS numeric bibliography via BibTeX and `splncs04.bst`.
- Appendix: appendix tables are kept outside the main review PDF; do not use appendix material to exceed the main page budget.
- Responsible AI disclosure: included as an unnumbered section before references.
- Ethics: ECML PKDD requires authors to consider ethical issues; the current draft keeps safety, refusal, and claim-boundary limitations explicit.

## Files

- `main.tex`: LNCS-adapted full review manuscript entry point.
- `main_8p.tex`: compact 8-page submission entry point used for the current STAI target.
- `main.pre-lncs-backup.tex`: pre-migration compilable draft kept for reference.
- `llncs.cls`: Springer LNCS class copied from the official author kit.
- `splncs04.bst`: Springer LNCS bibliography style copied from the official author kit.
- `references.bib`: manuscript bibliography.
- `sections/`: main paper sections.
- `appendix/`: supplementary appendix tables, not included in the main review PDF.
- `figures/`: local figure assets, including `figure1_method_workflow_nature.pdf`.
- `template/llncs/`: unpacked official Springer author kit reference files.

## Local Build

Preferred command when a full TeX Live or MiKTeX environment is available:

```powershell
cd docs\paper_project\paper_stai2026
latexmk -pdf -interaction=nonstopmode -file-line-error -outdir=build main.tex
```

Workspace command used here:

```powershell
cd docs\paper_project\paper_stai2026
C:\Users\26318\.codex\.tmp\bundled-marketplaces\openai-bundled\plugins\latex-tectonic\bin\tectonic.exe -k --keep-logs -o build main.tex
```

Compact 8-page submission build:

```powershell
cd docs\paper_project\paper_stai2026
C:\Users\26318\.codex\.tmp\bundled-marketplaces\openai-bundled\plugins\latex-tectonic\bin\tectonic.exe -k --keep-logs -o build_8p main_8p.tex
```

Classic fallback:

```powershell
pdflatex -interaction=nonstopmode -file-line-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -file-line-error main.tex
pdflatex -interaction=nonstopmode -file-line-error main.tex
```

## Overleaf Upload

Upload the following paths as one project:

- `main.tex`
- `main_8p.tex`
- `references.bib`
- `llncs.cls`
- `splncs04.bst`
- `sections/`
- `figures/`

Do not upload local build outputs (`build/`, `build_verify/`) or private run/data directories. The `appendix/` directory can be uploaded only if supplementary material is allowed and submitted separately from the main PDF.

Recommended Overleaf settings:

- Main document: `main.tex`
- Compiler: pdfLaTeX or LaTeX; if Overleaf selects XeLaTeX automatically, keep the generated PDF but re-check line breaking and bibliography.
- Bibliography: BibTeX.

## Anonymous Submission Checklist

- Authors: `Anonymous Author(s)` in `main.tex`.
- Affiliation: `Paper under double-blind review`.
- Acknowledgements: omitted from the review PDF.
- Data and code paths: replaced with artifact identifiers in the paper body.
- Local Windows paths: not present in the review manuscript source; this README records local build commands for workspace use only and should be excluded from anonymous source upload if strict path hygiene is required.
- Public repository or author-identifying URL: not included in the review PDF.
- Appendix: excluded from the main review PDF; keep supplementary files anonymous if submitted.

## Template Adaptation Status

- `main.tex` migrated from generic `article` to Springer LNCS `llncs`.
- Bibliography migrated from `plainnat` / `natbib` to `splncs04.bst`.
- `\citep{...}` commands replaced by LNCS-compatible `\cite{...}`.
- Current title selected as the more restrained diagnostic-study version: "A Workflow-Level Diagnostic Study of Evidence-Gated Advisory RAG for Endurance Training Advice".
- Stronger candidate title kept only as historical context in `main.pre-lncs-backup.tex`.
- Main figure for the current submission remains `figures/figure1_method_workflow_nature.pdf`.
- Appendix tables remain in `appendix/appendix_tables.tex` as supplementary material.
- Final local verification produced `build_8p/main_8p.pdf` as a 7-page compact PDF and `build/main.pdf` as a 16-page full LNCS PDF.
- Final log scan found no undefined citation/reference and no `Overfull` warnings; remaining TeX messages are `Underfull` line-breaking warnings in narrow tables.
