# Supplementary Artifact Note

The supplementary artifact for this Rule Challenge submission is prepared for
public release at:

https://github.com/Ljy220058/m-exrxbench

It contains the M-EXRxBench benchmark splits, rule specifications, schemas,
reference runner, evaluator, baseline outputs, stored traces, figures, static
trace viewer, and reproducibility scripts. The manuscript keeps the detailed
artifact pathway outside the paper body; the accompanying figure in this folder
summarizes the reviewer path from benchmark input to trace and evaluation
record.

The reviewer-facing reproduction path is explicit rather than only a code
release. From the artifact root, run:

```powershell
powershell -ExecutionPolicy Bypass -File reproducibility\run_all.ps1
powershell -ExecutionPolicy Bypass -File reproducibility\run_hard100.ps1
```

The default script regenerates the 500-case reference output, deterministic
baseline outputs, independent evaluator JSON summaries, Markdown summaries, and
artifact validation. The evaluator is `demo\evaluate_results.py`; stored
precomputed outputs are under `artifacts\demo_runs\` and
`artifacts\baseline_runs\`. The runtime uses the Python standard library only
and has no stochastic model call, sampling, shuffling, or randomized search.
Therefore no runtime random seed is required for the reported deterministic
metrics.

The benchmark cases are synthetic. The artifact does not contain real patient
records, real athlete telemetry, private credentials, or deployment data. Code
is intended for MIT release; synthetic data and documentation are intended for
CC BY 4.0 release.
