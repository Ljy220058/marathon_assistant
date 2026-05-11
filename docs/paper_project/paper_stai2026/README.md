# STAI Manuscript Package

This directory is the first-pass LaTeX manuscript package for the STAI workshop paper.

## Contents

- `main.tex`: entry point
- `references.bib`: bibliography copied from the verified Markdown draft
- `sections/`: main paper sections
- `appendix/`: optional appendix tables
- `figures/`: local figure assets

## Build

Preferred build command:

```powershell
cd docs\paper_project\paper_stai2026
latexmk -pdf main.tex
```

Local Tectonic build used in this workspace:

```powershell
cd docs\paper_project\paper_stai2026
C:\Users\26318\tools\tectonic-0.16.9\tectonic.exe --outdir build main.tex
```

Fallback:

```powershell
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

## Current Scope

- The package is not yet checked against the official STAI/ECML PKDD workshop template.
- Author names and affiliations are still anonymous draft fields.
- The bibliography is a verified candidate bibliography, but proceedings versions may still need final confirmation.
- The package is intended to compile first, then be adapted to the final venue template.
