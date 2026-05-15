import json
import re
import subprocess
import sys
import hashlib
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HASH_NORMALIZED_TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".py", ".ps1", ".tex", ".txt", ".bib", ".xmpi"}

GOLD_ONLY_FIELDS = {
    "expected_behavior",
    "gold_risk_level",
    "required_rules",
    "forbidden_outputs",
    "rationale",
    "notes",
    "case_family",
    "variation_type",
    "source_seed_id",
    "annotation_notes",
    "rule_basis_ids",
    "rule_basis_links",
    "mapping_status",
    "mapping_confidence",
}

REQUIRED_TRACE_KEYS = [
    "case_id",
    "profile_version",
    "risk_level",
    "rules_fired",
    "evidence_ids",
    "action_ids",
    "expert_calls",
    "audit_result",
    "repair_log",
    "final_status",
]

RELEASE_REQUIRED_FILES = [
    "README.md",
    "TODO.md",
    "artifact_checklist.md",
    "open_science_release_plan.md",
    "submission_go_no_go.md",
    "LICENSE-CODE-MIT.txt",
    "LICENSE-DATA-CC-BY-4.0.txt",
    "requirements.txt",
    ".gitignore",
    "paper/main.tex",
    "submission_package/A_Trace-Governed_Rule_Challenge_for_Evidence-Bounded_Exercise_Prescription.pdf",
    "submission_upload/paper/A_Trace-Governed_Rule_Challenge_for_Evidence-Bounded_Exercise_Prescription.pdf",
    "benchmark/system_visible_cases.jsonl",
    "benchmark/gold_labels.jsonl",
    "benchmark/m_exrxbench_v0.4_500_cases.jsonl",
    "benchmark/rule_basis_sources.md",
    "benchmark/rule_basis_sources.json",
    "benchmark/case_to_rule_basis_map.jsonl",
    "benchmark/hard_case_to_rule_basis_map.jsonl",
    "benchmark/case_to_rule_basis_map_summary.md",
    "benchmark/hard_case_to_rule_basis_map_summary.md",
    "benchmark/traceable_dataset_schema.json",
    "benchmark/validate_traceable_dataset.py",
    "benchmark/annotation_protocol_v0.5.md",
    "benchmark/traceable_upgrade_audit.md",
    "benchmark/result_schema.json",
    "rule_spec/trace_schema.json",
    "demo/run_demo.py",
    "demo/run_benchmark.py",
    "demo/run_baselines.py",
    "demo/evaluate_results.py",
    "demo/static_trace_viewer.html",
    "reproducibility/run_all.ps1",
    "reproducibility/run_hard100.ps1",
    "artifacts/artifact_manifest.json",
]

LOCAL_PATH_PATTERNS = [
    re.compile(r"C:\\Users\\", re.IGNORECASE),
    re.compile(r"anaconda3", re.IGNORECASE),
    re.compile("tr" + r"ae_projects", re.IGNORECASE),
]

UNRELATED_WORKSPACE_MARKER = "paper_" + "s" + "tai2026"

SECRET_PATTERNS = [
    re.compile(r"api[_-]?key\s*[:=]", re.IGNORECASE),
    re.compile(r"secret[_-]?key\s*[:=]", re.IGNORECASE),
    re.compile(r"client[_-]?secret\s*[:=]", re.IGNORECASE),
    re.compile(r"password\s*[:=]", re.IGNORECASE),
    re.compile(r"bearer\s+[a-z0-9._-]+", re.IGNORECASE),
    re.compile(r"BEGIN (RSA|OPENSSH|PRIVATE) KEY"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]

HYGIENE_SKIP_RELATIVE = {
    "demo/validate_artifacts.py",
}

TEXT_SUFFIXES = {
    ".bib",
    ".css",
    ".html",
    ".json",
    ".jsonl",
    ".md",
    ".ps1",
    ".py",
    ".tex",
    ".txt",
}

SKIP_SCAN_PARTS = {"__pycache__"}
SKIP_SCAN_SUFFIXES = {".aux", ".blg", ".fdb_latexmk", ".fls", ".log", ".pyc", ".xdv"}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{rel(path)}:{i}: {exc}") from exc
    return rows


def require_keys(obj: dict[str, Any], keys: list[str], label: str) -> None:
    missing = [key for key in keys if key not in obj]
    if missing:
        raise ValueError(f"{label} missing keys: {missing}")


def validate_result(result: dict[str, Any], label: str) -> None:
    require_keys(result, ["case_id", "system", "status", "plan", "trace"], label)
    if result["status"] not in {"answered", "partial_answer", "ask_clarification", "refused"}:
        raise ValueError(f"{label} invalid status: {result['status']}")
    trace = result["trace"]
    require_keys(trace, REQUIRED_TRACE_KEYS, f"{label}.trace")
    if trace["final_status"] != result["status"]:
        raise ValueError(f"{label} final_status does not match status")
    if trace["risk_level"] not in {"R0", "R1", "R2", "R3"}:
        raise ValueError(f"{label} invalid risk_level: {trace['risk_level']}")
    if trace["audit_result"] not in {"pass", "repair_required", "review_required", "fail"}:
        raise ValueError(f"{label} invalid audit_result: {trace['audit_result']}")


def validate_release_files() -> None:
    for relative in RELEASE_REQUIRED_FILES:
        path = ROOT / relative
        if not path.exists():
            raise ValueError(f"required release file missing: {relative}")


def validate_traceable_dataset() -> None:
    script = ROOT / "benchmark" / "validate_traceable_dataset.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(
            "traceable dataset validation failed:\n"
            f"stdout={result.stdout}\n"
            f"stderr={result.stderr}"
        )
    if "traceable_dataset_validation_ok" not in result.stdout:
        raise ValueError("traceable dataset validator did not print success sentinel")


def validate_gold_split() -> None:
    visible = load_jsonl(ROOT / "benchmark" / "system_visible_cases.jsonl")
    gold = load_jsonl(ROOT / "benchmark" / "gold_labels.jsonl")
    if len(visible) != 500 or len(gold) != 500:
        raise ValueError(f"expected 500 visible and 500 gold rows, got {len(visible)} and {len(gold)}")
    visible_ids = {row["case_id"] for row in visible}
    gold_ids = {row["case_id"] for row in gold}
    if visible_ids != gold_ids:
        raise ValueError("visible/gold case_id sets differ")
    for row in visible:
        leaked = sorted(GOLD_ONLY_FIELDS & set(row))
        if leaked:
            raise ValueError(f"system-visible case {row['case_id']} leaks gold fields: {leaked}")
    for row in gold:
        require_keys(row, ["case_id", "expected_behavior", "gold_risk_level"], f"gold:{row.get('case_id')}")


def validate_hard_split() -> None:
    visible_path = ROOT / "benchmark" / "hard_system_visible_cases.jsonl"
    gold_path = ROOT / "benchmark" / "hard_gold_labels.jsonl"
    labeled_path = ROOT / "benchmark" / "m_exrxbench_v0.4_hard_100_cases.jsonl"
    if not (visible_path.exists() and gold_path.exists() and labeled_path.exists()):
        return
    visible = load_jsonl(visible_path)
    gold = load_jsonl(gold_path)
    labeled = load_jsonl(labeled_path)
    if len(visible) != 100 or len(gold) != 100 or len(labeled) != 100:
        raise ValueError(
            f"expected 100 hard visible/gold/labeled rows, got {len(visible)}, {len(gold)}, {len(labeled)}"
        )
    visible_ids = {row["case_id"] for row in visible}
    gold_ids = {row["case_id"] for row in gold}
    labeled_ids = {row["case_id"] for row in labeled}
    if visible_ids != gold_ids or visible_ids != labeled_ids:
        raise ValueError("hard visible/gold/labeled case_id sets differ")
    for row in visible:
        leaked = sorted(GOLD_ONLY_FIELDS & set(row))
        if leaked:
            raise ValueError(f"hard system-visible case {row['case_id']} leaks gold/audit fields: {leaked}")
        if row.get("difficulty") != "hard":
            raise ValueError(f"hard system-visible case {row['case_id']} is not difficulty=hard")


def validate_outputs() -> None:
    for path in sorted((ROOT / "artifacts").glob("**/*.json")):
        data = load_json(path)
        label = rel(path)
        if isinstance(data, dict) and "results" in data:
            for result in data["results"]:
                validate_result(result, f"{label}:{result.get('case_id')}")
        elif isinstance(data, dict) and {"case_id", "status", "trace"} <= set(data):
            validate_result(data, label)
        elif isinstance(data, dict) and {"case_count", "status_accuracy"} <= set(data):
            validate_eval_summary(data, label)
    for path in sorted((ROOT / "artifacts").glob("**/*.jsonl")):
        load_jsonl(path)


def validate_eval_summary(summary: dict[str, Any], label: str) -> None:
    require_keys(
        summary,
        [
            "case_count",
            "status_accuracy",
            "risk_accuracy",
            "unsafe_advice_rate",
            "unsupported_prescription_rate",
            "rule_violation_rate",
            "trace_completeness",
            "repair_success_rate",
        ],
        label,
    )
    expected_case_count = 100 if label.startswith("artifacts/demo_runs/hard100_") else 500
    if summary["case_count"] != expected_case_count:
        raise ValueError(f"{label} expected case_count {expected_case_count}")
    for key in [
        "status_accuracy",
        "risk_accuracy",
        "unsafe_advice_rate",
        "unsupported_prescription_rate",
        "rule_violation_rate",
        "trace_completeness",
        "repair_success_rate",
    ]:
        value = summary[key]
        if not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise ValueError(f"{label} invalid metric {key}: {value}")


def validate_manifest() -> None:
    manifest = load_json(ROOT / "artifacts" / "artifact_manifest.json")
    require_keys(manifest, ["artifact", "version", "repository", "license_policy", "release_files"], "manifest")
    if "Ljy220058/m-exrxbench" not in manifest["repository"]:
        raise ValueError("manifest repository does not point to the public GitHub target")
    if manifest["license_policy"].get("code") != "MIT":
        raise ValueError("manifest code license must be MIT")
    if manifest["license_policy"].get("data_docs") != "CC BY 4.0":
        raise ValueError("manifest data/docs license must be CC BY 4.0")
    listed = {item["path"] for item in manifest["release_files"]}
    for relative in RELEASE_REQUIRED_FILES:
        if relative not in listed:
            raise ValueError(f"manifest missing release file: {relative}")
    for item in manifest["release_files"]:
        path = ROOT / item["path"]
        if not path.exists():
            raise ValueError(f"manifest file missing on disk: {item['path']}")
        if not item.get("license"):
            raise ValueError(f"manifest file missing license: {item['path']}")
        if "sha256" in item:
            digest = hashlib.sha256(manifest_hash_bytes(path)).hexdigest()
            if digest != item["sha256"]:
                raise ValueError(f"manifest sha256 mismatch for {item['path']}")
        if "row_count" in item:
            if path.suffix != ".jsonl":
                raise ValueError(f"manifest row_count is only supported for jsonl files: {item['path']}")
            actual_rows = len(load_jsonl(path))
            if actual_rows != item["row_count"]:
                raise ValueError(
                    f"manifest row_count mismatch for {item['path']}: expected {item['row_count']}, got {actual_rows}"
                )
        if item.get("split_role") and not item.get("schema"):
            raise ValueError(f"manifest split file missing schema reference: {item['path']}")


def manifest_hash_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if path.suffix.lower() in HASH_NORMALIZED_TEXT_SUFFIXES:
        return data.replace(b"\r\n", b"\n")
    return data


def iter_release_text_files() -> list[Path]:
    release_roots = [
        "README.md",
        "TODO.md",
        "artifact_checklist.md",
        "open_science_release_plan.md",
        "submission_go_no_go.md",
        "requirements.txt",
        "LICENSE-CODE-MIT.txt",
        "LICENSE-DATA-CC-BY-4.0.txt",
        "challenge_positioning.md",
        "venue_acceptance_criteria.md",
        "team_workflow.md",
        "paper",
        "demo",
        "benchmark",
        "artifacts",
        "rule_spec",
        "reproducibility",
        "references",
        "ethics",
        "sources",
    ]
    paths = []
    for relative in release_roots:
        candidate = ROOT / relative
        if candidate.is_file():
            if candidate.suffix.lower() in TEXT_SUFFIXES:
                paths.append(candidate)
            continue
        if candidate.is_dir():
            for path in candidate.rglob("*"):
                if not path.is_file():
                    continue
                if any(part in SKIP_SCAN_PARTS for part in path.parts):
                    continue
                if path.suffix in SKIP_SCAN_SUFFIXES:
                    continue
                if path.suffix.lower() in TEXT_SUFFIXES:
                    paths.append(path)
    return paths


def validate_text_hygiene() -> None:
    for path in iter_release_text_files():
        relative_path = rel(path)
        if relative_path in HYGIENE_SKIP_RELATIVE:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if UNRELATED_WORKSPACE_MARKER in text and relative_path not in {
            "README.md",
            "artifact_checklist.md",
            "submission_go_no_go.md",
            "paper/scope_and_safety_boundary.md",
            "ethics/scope_and_safety_boundary.md",
            "reviews/todo_review_round_01.md",
            "reviews/todo_review_round_02.md",
            "sources/source_manifest.md",
        }:
            raise ValueError(f"unexpected unrelated workspace marker in {relative_path}")
        for pattern in LOCAL_PATH_PATTERNS:
            if pattern.search(text):
                raise ValueError(f"local path leak in {relative_path}: {pattern.pattern}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                raise ValueError(f"possible secret in {relative_path}: {pattern.pattern}")


def main() -> None:
    for path in [
        ROOT / "rule_spec" / "trace_schema.json",
        ROOT / "benchmark" / "result_schema.json",
        ROOT / "benchmark" / "m_exrxbench_schema.json",
        ROOT / "rule_spec" / "prescription_contract_schema.json",
    ]:
        load_json(path)

    validate_release_files()
    validate_traceable_dataset()
    validate_gold_split()
    validate_hard_split()
    validate_outputs()
    validate_manifest()
    validate_text_hygiene()

    print("artifact_validation_ok")


if __name__ == "__main__":
    main()
