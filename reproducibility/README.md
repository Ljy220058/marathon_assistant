# Reproducibility

Run from the artifact root.

```powershell
powershell -ExecutionPolicy Bypass -File reproducibility\run_all.ps1
```

The script runs:

1. one red-flag demo case
2. the proposed full rule-governed system
3. baseline/proposed-system batch outputs
4. independent evaluation
5. Markdown summary rendering
6. artifact validation

No external model is required for this deterministic Rule Challenge reference artifact.
