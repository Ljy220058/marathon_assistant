"""Repository hygiene checks for the marathon assistant monorepo."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

CACHE_PATTERNS = (
    "node_modules",
    ".npm-cache",
    ".pytest_cache",
    "__pycache__",
    "archive/local_caches",
    "apps/web/dist",
)

VERSION_EXCLUDED_PATHS = (
    "data/vector_kb/default/user_profile.json",
    "data/vector_kb/default/knowledge_graph.json",
    "papers/",
    "artifacts/frontend-audit/",
)

VERSION_EXCLUDED_ROOT_PATTERNS = (
    re.compile(r"^Sub-70.*OCR.*\.md$"),
)

OLD_PATH_PATTERNS = (
    # Pre-monorepo paper project path (migrated to research/stai2026/).
    "docs/paper_project",
    # Old frontend flat structure (migrated to apps/web/src).
    "frontend/src",
    "frontend/node_modules",
    # Old upload/docs root dirs (migrated to data/uploads/, data/domain_docs/).
    "uploaded_docs",
)

ROOT_ALLOWLIST = {
    # Git and search config.
    ".git",
    ".github",
    ".gitignore",
    ".rgignore",
    # Project-level config and entry files.
    "pytest.ini",
    ".env.example",
    # README and long-term index.
    "README.md",
    "TODO.md",
    "CONTRIBUTING.md",
    "requirements.txt",
    # Agent instructions (Claude, CI, etc.).
    ".claude",
    "AGENTS.md",
    "CLAUDE.md",
    # First-level functional directories.
    "apps",
    "archive",
    "artifacts",
    "configs",
    "data",
    "docs",
    "packages",
    "research",
    "scripts",
    "tests",
    "tools",
    # Build/generated outputs (already in .gitignore, tolerated on disk).
    "outputs",
    ".pytest_cache",
}

MANIFEST_FILES = (
    "artifacts/MANIFEST.md",
    "data/uploads/seed/manifest.md",
    "research/mexrxbench/analysis/exercise_health_cross_research_2026/manifest.md",
    "docs/architecture/naming_and_discovery.md",
    "docs/architecture/module_boundary_audit.md",
    "docs/architecture/repository_governance.md",
)

DOC_SCOPE_FILES = (
    "TODO.md",
    "CONTRIBUTING.md",
    "README.md",
    "docs",
    ".github",
)

LARGE_FILE_SUFFIXES = {
    ".pdf",
    ".zip",
    ".faiss",
    ".pkl",
    ".npz",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}


@dataclass
class CheckResult:
    name: str
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def run_git(args: list[str], timeout: int = 20) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 99, "", str(exc)
    return completed.returncode, completed.stdout, completed.stderr


def git_status_porcelain() -> list[str]:
    code, stdout, stderr = run_git(["-c", "core.quotePath=false", "status", "--porcelain=v1"])
    if code != 0:
        raise RuntimeError(f"git status failed: {stderr.strip()}")
    return [line for line in stdout.splitlines() if line.strip()]


def git_ls_files() -> list[str]:
    code, stdout, stderr = run_git(["-c", "core.quotePath=false", "ls-files"])
    if code != 0:
        raise RuntimeError(f"git ls-files failed: {stderr.strip()}")
    return [line.strip() for line in stdout.splitlines() if line.strip()]


def iter_files_under(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.exists():
        return []
    files: list[Path] = []
    for root, dirs, names in os.walk(path):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__", ".pytest_cache"}]
        for name in names:
            files.append(Path(root) / name)
    return files


def check_root_clean() -> CheckResult:
    errors: list[str] = []
    warnings: list[str] = []
    for item in REPO_ROOT.iterdir():
        name = item.name
        if name not in ROOT_ALLOWLIST:
            warnings.append(f"unexpected root item: {name}")
    return CheckResult("root-clean", errors, warnings)


def check_cache_noise() -> CheckResult:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        files = git_ls_files()
    except RuntimeError as exc:
        return CheckResult("cache-noise", [str(exc)], warnings)
    for file_name in files:
        normalized = file_name.replace("\\", "/")
        if any(pattern in normalized for pattern in CACHE_PATTERNS):
            errors.append(f"tracked cache/build path: {normalized}")
    return CheckResult("cache-noise", errors, warnings)


def _status_path(line: str) -> str:
    value = line[3:] if len(line) >= 4 else line
    if " -> " in value:
        value = value.split(" -> ", 1)[1]
    return value.strip().strip('"').replace("\\", "/")


def _is_version_excluded(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return (
        normalized in VERSION_EXCLUDED_PATHS
        or any(normalized.startswith(prefix) for prefix in VERSION_EXCLUDED_PATHS if prefix.endswith("/"))
        or any(pattern.match(normalized) for pattern in VERSION_EXCLUDED_ROOT_PATTERNS)
    )


def check_version_exclusions() -> CheckResult:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        status_lines = git_status_porcelain()
    except RuntimeError as exc:
        return CheckResult("version-exclusions", [str(exc)], warnings)

    for line in status_lines:
        path = _status_path(line)
        if not _is_version_excluded(path):
            continue
        staged = line[:2] != "??" and line[0] != " "
        message = f"version-excluded path is dirty: {path}"
        if staged:
            errors.append(f"staged excluded path: {path}")
        else:
            warnings.append(message)
    return CheckResult("version-exclusions", errors, warnings)


def check_old_paths() -> CheckResult:
    errors: list[str] = []
    warnings: list[str] = []
    targets: list[Path] = []
    for entry in DOC_SCOPE_FILES:
        targets.extend(iter_files_under(REPO_ROOT / entry))
    for path in targets:
        if path.suffix.lower() not in {".md", ".txt", ".toml", ".yml", ".yaml", ".json"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in OLD_PATH_PATTERNS:
            if pattern in text and "<old paper project path>" not in text:
                warnings.append(f"{rel(path)} contains legacy path literal: {pattern}")
    return CheckResult("old-path-literals", errors, warnings)


def markdown_links(text: str) -> list[str]:
    return [match.group(1).strip() for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text)]


def check_manifest_links() -> CheckResult:
    errors: list[str] = []
    warnings: list[str] = []
    for file_name in MANIFEST_FILES:
        path = REPO_ROOT / file_name
        if not path.exists():
            warnings.append(f"manifest/doc missing: {file_name}")
            continue
        text = path.read_text(encoding="utf-8")
        for target in markdown_links(text):
            if re.match(r"^(https?:|mailto:)", target):
                continue
            clean = target.strip("<>").split("#", 1)[0].strip()
            if not clean:
                continue
            if not (path.parent / clean).exists():
                errors.append(f"{file_name} -> missing link target: {target}")
    return CheckResult("manifest-links", errors, warnings)


def check_large_files(warn_mb: int, fail_mb: int) -> CheckResult:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        files = git_ls_files()
    except RuntimeError as exc:
        return CheckResult("large-files", [str(exc)], warnings)
    for file_name in files:
        path = REPO_ROOT / file_name
        if not path.exists() or not path.is_file():
            continue
        suffix = path.suffix.lower()
        size_mb = path.stat().st_size / (1024 * 1024)
        if suffix in LARGE_FILE_SUFFIXES or size_mb >= warn_mb:
            message = f"{file_name} ({size_mb:.1f} MiB)"
            if size_mb >= fail_mb:
                errors.append(f"large file over {fail_mb} MiB: {message}")
            elif size_mb >= warn_mb:
                warnings.append(f"large file candidate: {message}")
    return CheckResult("large-files", errors, warnings)


def check_git_diff() -> CheckResult:
    code, stdout, stderr = run_git(["diff", "--check"])
    errors: list[str] = []
    warnings: list[str] = []
    output = "\n".join(part for part in (stdout.strip(), stderr.strip()) if part)
    if code != 0:
        errors.append(output or "git diff --check failed")
    elif output:
        warnings.append(output)
    return CheckResult("git-diff-check", errors, warnings)


def collect_checks(scope: str, warn_mb: int, fail_mb: int) -> list[CheckResult]:
    checks: list[CheckResult] = []
    if scope in {"all", "hygiene", "docs"}:
        checks.extend([check_root_clean(), check_cache_noise(), check_version_exclusions(), check_old_paths(), check_manifest_links()])
    if scope in {"all", "large-files", "hygiene"}:
        checks.append(check_large_files(warn_mb=warn_mb, fail_mb=fail_mb))
    if scope in {"all", "docs", "hygiene"}:
        checks.append(check_git_diff())
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run repository governance checks.")
    parser.add_argument(
        "--scope",
        choices=("all", "docs", "hygiene", "large-files"),
        default="all",
        help="Subset of checks to run.",
    )
    parser.add_argument("--large-warn-mb", type=int, default=10)
    parser.add_argument("--large-fail-mb", type=int, default=100)
    args = parser.parse_args(argv)

    results = collect_checks(args.scope, args.large_warn_mb, args.large_fail_mb)
    failed = False
    for result in results:
        status = "OK" if result.ok else "FAIL"
        print(f"[{status}] {result.name}")
        for warning in result.warnings:
            print(f"  WARN: {warning}")
        for error in result.errors:
            print(f"  ERROR: {error}")
        failed = failed or not result.ok
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
