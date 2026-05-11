import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


PROJECT_ROOT = Path(__file__).absolute().parents[1]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "docs" / "paper_project" / "runs"


RUNNER_BY_SYSTEM = {
    "S0": PROJECT_ROOT / "scripts" / "run_stai_s0_norag.py",
    "S1": PROJECT_ROOT / "scripts" / "run_stai_s1_vanilla_rag.py",
    "S3": PROJECT_ROOT / "scripts" / "run_stai_s3_full_workflow.py",
}


ARG_NAME_BY_KEY = {
    "base_url": "base-url",
    "benchmark_kb_dir": "benchmark-kb-dir",
    "context_max_chars": "context-max-chars",
    "evidence_mode": "evidence-mode",
    "gold_context_max_chars": "gold-context-max-chars",
    "keep_embedding_model": "keep-embedding-model",
    "keep_models": "keep-models",
    "num_batch": "num-batch",
    "num_ctx": "num-ctx",
    "num_gpu": "num-gpu",
    "num_predict": "num-predict",
    "output_root": "output-root",
    "pre_gate_mode": "pre-gate-mode",
    "qid_evidence_map": "qid-evidence-map",
    "retrieval_backend": "retrieval-backend",
    "retrieval_only": "retrieval-only",
    "run_id": "run-id",
    "timeout_sec": "timeout-sec",
    "top_k": "top-k",
    "top_p": "top-p",
    "vector_dir": "vector-dir",
}


SKIP_KEYS = {
    "name",
    "system_id",
    "runner",
    "run_id_prefix",
    "notes",
}


def load_config(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON config {path}: {exc}") from exc


def normalize_qids(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    raise SystemExit("Config field 'qids' must be a string or a list.")


def default_run_id(config: Dict[str, Any]) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prefix = str(config.get("run_id_prefix") or config.get("name") or config.get("system_id") or "stai_run")
    return f"{prefix}_{timestamp}"


def iter_cli_args(config: Dict[str, Any]) -> Iterable[str]:
    for key, value in config.items():
        if key in SKIP_KEYS or value is None:
            continue
        arg_name = ARG_NAME_BY_KEY.get(key, key.replace("_", "-"))
        if key == "qids":
            value = normalize_qids(value)
        if isinstance(value, bool):
            if value:
                yield f"--{arg_name}"
            continue
        yield f"--{arg_name}"
        yield str(value)


def resolve_output_root(config: Dict[str, Any]) -> Path:
    value = config.get("output_root")
    if not value:
        return DEFAULT_OUTPUT_ROOT
    path = Path(str(value))
    return path if path.is_absolute() else PROJECT_ROOT / path


def build_command(config: Dict[str, Any], run_id: str) -> List[str]:
    system_id = str(config.get("system_id", "")).upper()
    runner = RUNNER_BY_SYSTEM.get(system_id)
    if config.get("runner"):
        runner = Path(str(config["runner"]))
        runner = runner if runner.is_absolute() else PROJECT_ROOT / runner
    if not runner:
        supported = ", ".join(sorted(RUNNER_BY_SYSTEM))
        raise SystemExit(f"Unsupported system_id={system_id!r}. Supported: {supported}")
    if not runner.exists():
        raise SystemExit(f"Runner not found: {runner}")

    command_config = dict(config)
    command_config["run_id"] = run_id
    return [sys.executable, "-u", str(runner), *iter_cli_args(command_config)]


def format_windows_command(command: List[str]) -> str:
    def quote(part: str) -> str:
        if not part:
            return '""'
        if any(ch.isspace() for ch in part) or any(ch in part for ch in '&()[]{}^=;!\'+,`~'):
            return f'"{part}"'
        return part

    return " ".join(quote(part) for part in command)


def stream_run(command: List[str], log_path: Path | None) -> int:
    log_handle = None
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_handle = log_path.open("w", encoding="utf-8", newline="\n")
        log_handle.write(format_windows_command(command) + "\n\n")
        log_handle.flush()
    try:
        process = subprocess.Popen(
            command,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            try:
                print(line, end="")
            except (OSError, UnicodeError):
                pass
            if log_handle is not None:
                log_handle.write(line)
                log_handle.flush()
        return process.wait()
    finally:
        if log_handle is not None:
            log_handle.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a configured STAI experiment.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-id", default="", help="Override config/default run id.")
    parser.add_argument("--resume", action="store_true", help="Resume an existing run when the underlying runner supports --resume.")
    parser.add_argument("--dry-run", action="store_true", help="Print command without running it.")
    parser.add_argument("--print-cmd", action="store_true", help="Print a Windows cmd-friendly command.")
    parser.add_argument("--log-file", type=Path, default=None, help="Optional stdout log path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = load_config(config_path)
    if args.resume:
        config["resume"] = True
    run_id = args.run_id or str(config.get("run_id") or "") or default_run_id(config)
    output_root = resolve_output_root(config)
    run_dir = output_root / run_id
    if run_dir.exists() and not args.resume and not args.dry_run:
        raise SystemExit(f"Run directory already exists; choose a new --run-id: {run_dir}")

    command = build_command(config, run_id)
    if args.print_cmd or args.dry_run:
        print(format_windows_command(command))
    if args.dry_run:
        return

    log_path = args.log_file
    if log_path is not None and not log_path.is_absolute():
        log_path = PROJECT_ROOT / log_path
    return_code = stream_run(command, log_path)
    if return_code != 0:
        raise SystemExit(return_code)

    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "experiment_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / "command.txt").write_text(format_windows_command(command) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
