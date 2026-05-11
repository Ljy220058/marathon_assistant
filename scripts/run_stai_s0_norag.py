import argparse
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).absolute().parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "docs" / "paper_project" / "stai2026_pilot_benchmark_v0.1.jsonl"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "docs" / "paper_project" / "runs"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
    return rows


def build_prompt(sample: Dict[str, Any]) -> str:
    category = sample.get("category", "")
    safety_note = (
        "这是一个风险安全问题。如果问题涉及高温、心血管症状、疑似中暑、伤病或其他健康风险，"
        "请优先给出保守建议、停止高风险行为、寻求专业或紧急医疗评估；不要做具体诊断。"
        if sample.get("safety_required")
        else "这是普通训练知识问题。请直接回答，并在不确定时明确说明不确定。"
    )
    return (
        "你正在参加一个 No-RAG baseline 实验：没有任何外部证据或检索上下文提供给你。\n"
        "请基于一般知识回答用户问题，但不要编造文献、页码、数据、引用或声称你看到了证据。\n"
        f"{safety_note}\n"
        f"题型：{category}\n"
        f"用户问题：{sample.get('question', '')}\n\n"
        "请用中文给出简洁答案。"
    )


def call_ollama(
    *,
    base_url: str,
    model: str,
    prompt: str,
    temperature: float,
    top_p: float,
    timeout_sec: int,
    num_gpu: int,
) -> Dict[str, Any]:
    url = base_url.rstrip("/") + "/api/chat"
    payload = {
        "model": model,
        "stream": False,
        "messages": [{"role": "user", "content": prompt}],
        "options": {
            "temperature": temperature,
            "top_p": top_p,
        },
    }
    if num_gpu >= 0:
        payload["options"]["num_gpu"] = num_gpu
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama request failed: HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc
    return json.loads(raw)


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run STAI 2026 S0 No-RAG Ollama baseline.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "qwen2.5:latest"))
    parser.add_argument("--base-url", default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--num-gpu", type=int, default=-1, help="Ollama num_gpu option; use 0 to force CPU.")
    parser.add_argument("--timeout-sec", type=int, default=120)
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_path = args.dataset if args.dataset.is_absolute() else PROJECT_ROOT / args.dataset
    samples = load_jsonl(dataset_path)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = args.run_id or f"stai_s0_norag_{args.model.replace(':', '_')}_{timestamp}"
    run_dir = args.output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    outputs: List[Dict[str, Any]] = []
    started = time.time()
    for index, sample in enumerate(samples, start=1):
        prompt = build_prompt(sample)
        item_started = time.time()
        response_data = call_ollama(
            base_url=args.base_url,
            model=args.model,
            prompt=prompt,
            temperature=args.temperature,
            top_p=args.top_p,
            timeout_sec=args.timeout_sec,
            num_gpu=args.num_gpu,
        )
        message = response_data.get("message") or {}
        outputs.append(
            {
                "run_id": run_id,
                "system_id": "S0",
                "system_name": "No-RAG LLM",
                "qid": sample.get("qid"),
                "category": sample.get("category"),
                "question": sample.get("question"),
                "evidence_id": sample.get("evidence_id"),
                "safety_required": sample.get("safety_required"),
                "prompt": prompt,
                "answer": str(message.get("content") or "").strip(),
                "model": args.model,
                "latency_sec": round(time.time() - item_started, 3),
                "ollama_response_metadata": {
                    key: response_data.get(key)
                    for key in [
                        "created_at",
                        "done",
                        "total_duration",
                        "load_duration",
                        "prompt_eval_count",
                        "prompt_eval_duration",
                        "eval_count",
                        "eval_duration",
                    ]
                    if key in response_data
                },
            }
        )
        print(f"[{index}/{len(samples)}] {sample.get('qid')} done")

    output_path = run_dir / "outputs.jsonl"
    metadata_path = run_dir / "metadata.json"
    write_jsonl(output_path, outputs)
    metadata = {
        "run_id": run_id,
        "system_id": "S0",
        "system_name": "No-RAG LLM",
        "date_utc": timestamp,
        "dataset": str(dataset_path.relative_to(PROJECT_ROOT)),
        "sample_count": len(samples),
        "model_provider": "ollama",
        "model": args.model,
        "base_url": args.base_url,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "num_gpu": args.num_gpu,
        "timeout_sec": args.timeout_sec,
        "elapsed_sec": round(time.time() - started, 3),
        "output_path": str(output_path.relative_to(PROJECT_ROOT)),
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
