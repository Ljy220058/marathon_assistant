# Repository Split Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the STAI 2026 manuscript package and the M-EXRxBench RuleML artifact into separate clean repositories, while preparing the current marathon assistant repository to become an index shell.

**Architecture:** Use clean snapshot repositories instead of history-preserving splits. Copy reviewer-facing assets from the current dirty workspace into sibling local repositories, rewrite public-facing README and manifest paths, then prepare an isolated worktree branch for the current repository index shell. Do not run `git push`; provide push commands for the user.

**Tech Stack:** PowerShell, Git, LaTeX source packages, markdown release manifests.

---

### Task 1: Create Clean Local Repository Directories

**Files:**
- Create directory: `C:\Users\26318\Documents\trae_projects\ollama_pro\stai2026-evidence-gated-rag`
- Create directory: `C:\Users\26318\Documents\trae_projects\ollama_pro\m-exrxbench`
- Create worktree directory: `C:\Users\26318\Documents\trae_projects\ollama_pro\marathon_assistant-index-worktree`

- [ ] **Step 1: Verify source repository root**

Run:

```powershell
git rev-parse --show-toplevel
git status -sb
```

Expected:

```text
C:/Users/26318/Documents/trae_projects/ollama_pro/马拉松助手
## codex/5/13
```

- [ ] **Step 2: Create sibling directories only if absent**

Run:

```powershell
$base = 'C:\Users\26318\Documents\trae_projects\ollama_pro'
$targets = @(
  Join-Path $base 'stai2026-evidence-gated-rag',
  Join-Path $base 'm-exrxbench'
)
foreach ($target in $targets) {
  if (Test-Path -LiteralPath $target) {
    throw "Target already exists: $target"
  }
  New-Item -ItemType Directory -Path $target | Out-Null
}
```

Expected: two empty sibling directories are created.

- [ ] **Step 3: Initialize independent Git repositories**

Run:

```powershell
git -C C:\Users\26318\Documents\trae_projects\ollama_pro\stai2026-evidence-gated-rag init
git -C C:\Users\26318\Documents\trae_projects\ollama_pro\m-exrxbench init
git -C C:\Users\26318\Documents\trae_projects\ollama_pro\stai2026-evidence-gated-rag branch -M main
git -C C:\Users\26318\Documents\trae_projects\ollama_pro\m-exrxbench branch -M main
```

Expected: both directories contain their own `.git` directories and use `main` as the local branch name.

### Task 2: Build the STAI Repository Snapshot

**Files:**
- Copy from: `C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手\docs\paper_project\paper_stai2026\`
- Copy selected release files from: `C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手\docs\paper_project\`
- Create: `C:\Users\26318\Documents\trae_projects\ollama_pro\stai2026-evidence-gated-rag\README.md`
- Create: `C:\Users\26318\Documents\trae_projects\ollama_pro\stai2026-evidence-gated-rag\release\`

- [ ] **Step 1: Copy manuscript source without local build directories**

Run:

```powershell
$src = 'C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手\docs\paper_project\paper_stai2026'
$dst = 'C:\Users\26318\Documents\trae_projects\ollama_pro\stai2026-evidence-gated-rag'
robocopy $src $dst /E /XD build build_8p /XF *.aux *.bbl *.blg *.log *.out *.fls *.fdb_latexmk
if ($LASTEXITCODE -le 7) { $global:LASTEXITCODE = 0 } else { exit $LASTEXITCODE }
```

Expected: `main.tex`, `main_8p.tex`, `sections/`, `figures/`, `references.bib`, `llncs.cls`, and `splncs04.bst` are present in the STAI repository root.

- [ ] **Step 2: Copy current submitted PDFs and anonymous source zip**

Run:

```powershell
$release = 'C:\Users\26318\Documents\trae_projects\ollama_pro\stai2026-evidence-gated-rag\release'
New-Item -ItemType Directory -Force -Path $release | Out-Null
Copy-Item -LiteralPath 'C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手\docs\paper_project\stai2026_submission_main_8p_anonymous.pdf' -Destination $release
Copy-Item -LiteralPath 'C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手\docs\paper_project\stai2026_submission_main_full_anonymous.pdf' -Destination $release
Copy-Item -LiteralPath 'C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手\docs\paper_project\stai2026_anonymous_source_package_v0.2.zip' -Destination $release
```

Expected: `release/` contains the two anonymous PDFs and the anonymous source package.

- [ ] **Step 3: Replace the STAI root README with standalone repository wording**

Write `C:\Users\26318\Documents\trae_projects\ollama_pro\stai2026-evidence-gated-rag\README.md` with a standalone STAI package description, local build commands from the repository root, anonymous review hygiene, and a clear note that M-EXRxBench lives in a separate repository.

- [ ] **Step 4: Commit the STAI snapshot locally**

Run:

```powershell
git -C C:\Users\26318\Documents\trae_projects\ollama_pro\stai2026-evidence-gated-rag status --short
git -C C:\Users\26318\Documents\trae_projects\ollama_pro\stai2026-evidence-gated-rag add .
git -C C:\Users\26318\Documents\trae_projects\ollama_pro\stai2026-evidence-gated-rag commit -m "chore: publish clean STAI 2026 package"
```

Expected: one local commit containing only STAI materials.

### Task 3: Build the M-EXRxBench Repository Snapshot

**Files:**
- Copy from: `C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手\docs\paper_project\marathon_exrx_ruleml2026\`
- Modify: `C:\Users\26318\Documents\trae_projects\ollama_pro\m-exrxbench\README.md`
- Modify: `C:\Users\26318\Documents\trae_projects\ollama_pro\m-exrxbench\artifacts\artifact_manifest.json`
- Modify: release documents that mention `docs/paper_project/marathon_exrx_ruleml2026/`

- [ ] **Step 1: Copy the M-EXRxBench artifact to repository root**

Run:

```powershell
$src = 'C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手\docs\paper_project\marathon_exrx_ruleml2026'
$dst = 'C:\Users\26318\Documents\trae_projects\ollama_pro\m-exrxbench'
robocopy $src $dst /E
if ($LASTEXITCODE -le 7) { $global:LASTEXITCODE = 0 } else { exit $LASTEXITCODE }
```

Expected: `benchmark/`, `demo/`, `rule_spec/`, `paper/`, `references/`, `artifacts/`, `reproducibility/`, and licenses are present in the M-EXRxBench repository root.

- [ ] **Step 2: Rewrite public repository metadata**

Update:

```text
README.md
artifacts/artifact_manifest.json
artifacts/final_file_inventory.md
open_science_release_plan.md
paper/main.tex
```

Use:

```text
https://github.com/Ljy220058/m-exrxbench
```

Replace old artifact path references with repository-root paths such as `benchmark/`, `demo/`, `paper/`, and `artifacts/`.

- [ ] **Step 3: Run the artifact validator from the new repository**

Run:

```powershell
conda run -n torch2.5.1 python C:\Users\26318\Documents\trae_projects\ollama_pro\m-exrxbench\demo\validate_artifacts.py
```

Expected: validator passes or reports only path wording issues introduced by the repository-root relocation. Fix path wording issues before committing.

- [ ] **Step 4: Commit the M-EXRxBench snapshot locally**

Run:

```powershell
git -C C:\Users\26318\Documents\trae_projects\ollama_pro\m-exrxbench status --short
git -C C:\Users\26318\Documents\trae_projects\ollama_pro\m-exrxbench add .
git -C C:\Users\26318\Documents\trae_projects\ollama_pro\m-exrxbench commit -m "chore: publish clean M-EXRxBench artifact"
```

Expected: one local commit containing only M-EXRxBench materials.

### Task 4: Prepare the Current Repository Index Shell Safely

**Files:**
- Create isolated worktree: `C:\Users\26318\Documents\trae_projects\ollama_pro\marathon_assistant-index-worktree`
- Modify: `C:\Users\26318\Documents\trae_projects\ollama_pro\marathon_assistant-index-worktree\README.md`

- [ ] **Step 1: Create an isolated branch worktree**

Run from the current repository:

```powershell
git worktree add -b codex/index-shell C:\Users\26318\Documents\trae_projects\ollama_pro\marathon_assistant-index-worktree HEAD
```

Expected: new worktree checks out branch `codex/index-shell` without touching the dirty current workspace.

- [ ] **Step 2: Remove tracked source files only inside the index worktree**

Run:

```powershell
git -C C:\Users\26318\Documents\trae_projects\ollama_pro\marathon_assistant-index-worktree rm -r -- .
```

Expected: all tracked files in the index worktree are staged for deletion.

- [ ] **Step 3: Create a root index README**

Write `C:\Users\26318\Documents\trae_projects\ollama_pro\marathon_assistant-index-worktree\README.md` with links to:

```text
https://github.com/Ljy220058/stai2026-evidence-gated-rag
https://github.com/Ljy220058/m-exrxbench
```

The README must state that the repository is now an index shell and does not contain submission artifacts.

- [ ] **Step 4: Commit the index shell locally**

Run:

```powershell
git -C C:\Users\26318\Documents\trae_projects\ollama_pro\marathon_assistant-index-worktree add README.md
git -C C:\Users\26318\Documents\trae_projects\ollama_pro\marathon_assistant-index-worktree commit -m "docs: convert repository to project index"
```

Expected: one local commit on `codex/index-shell`.

### Task 5: Provide User-Executed GitHub Commands

**Files:**
- No file changes.

- [ ] **Step 1: Provide create-repo commands**

Commands for the user:

```powershell
gh repo create Ljy220058/stai2026-evidence-gated-rag --public --source C:\Users\26318\Documents\trae_projects\ollama_pro\stai2026-evidence-gated-rag --remote origin
gh repo create Ljy220058/m-exrxbench --public --source C:\Users\26318\Documents\trae_projects\ollama_pro\m-exrxbench --remote origin
```

- [ ] **Step 2: Provide push commands only**

Commands for the user:

```powershell
git -C C:\Users\26318\Documents\trae_projects\ollama_pro\stai2026-evidence-gated-rag push -u origin main
git -C C:\Users\26318\Documents\trae_projects\ollama_pro\m-exrxbench push -u origin main
git -C C:\Users\26318\Documents\trae_projects\ollama_pro\marathon_assistant-index-worktree push -u origin codex/index-shell
```

Expected: user pushes the two new public repositories and the index branch for the existing repository. The existing repository default branch should be changed on GitHub only after the user confirms the index shell branch looks correct.

---

## Self-Review

Spec coverage: the plan creates two clean local repositories, keeps STAI and M-EXRxBench separate, updates public-facing paths, and prepares the current repository as an index shell without mutating the dirty working tree.

Placeholder scan: the plan contains concrete paths, commands, repository names, and commit messages.

Risk controls: no remote push is executed by the agent, no force push is recommended, and deletion occurs only in an isolated worktree created for the index shell.
