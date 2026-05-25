from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from marathon_qa_assistant.services.kb.live_eval_runner import ProviderConfig, load_provider_config


class LiveEvalArtifactConfigError(RuntimeError):
    pass


PostJson = Callable[[str, Dict[str, Any], Dict[str, str], int], Dict[str, Any]]
BaseAnswerFn = Callable[[ProviderConfig, Dict[str, Any], str], str | Dict[str, Any]]


def collect_live_eval_answer_artifacts(
    golden_questions: Iterable[Dict[str, Any]],
    *,
    provider: str = "gpt",
    output_path: str | Path,
    api_url: str = "http://127.0.0.1:8010/query",
    query_user_id: str = "default_user",
    max_questions: Optional[int] = None,
    resume: bool = False,
    timeout: int = 120,
    env: Optional[Dict[str, str]] = None,
    post_json: Optional[PostJson] = None,
    base_answer_fn: Optional[BaseAnswerFn] = None,
) -> Dict[str, Any]:
    config = load_provider_config(provider, env=env)
    if not config.configured:
        raise LiveEvalArtifactConfigError(f"missing provider api key: {config.provider}")

    selected = list(golden_questions or [])
    if max_questions is not None:
        selected = selected[: max(int(max_questions), 0)]

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = load_live_eval_answer_artifacts(path) if resume and path.exists() else []
    existing = {(str(row.get("question_id") or ""), str(row.get("mode") or "")) for row in rows}
    writer_post_json = post_json or _post_json
    writer_base_answer = base_answer_fn or _base_answer_from_provider
    written_count = 0
    skipped_existing_count = 0

    for question in selected:
        question_id = _question_id(question)
        prompt = _question_prompt(question)
        if (question_id, "rag") in existing:
            skipped_existing_count += 1
        else:
            rows.append(
                _rag_artifact_row(
                    config,
                    question,
                    prompt,
                    api_url=api_url,
                    query_user_id=query_user_id,
                    timeout=timeout,
                    post_json=writer_post_json,
                )
            )
            existing.add((question_id, "rag"))
            written_count += 1
        if (question_id, "base_llm") in existing:
            skipped_existing_count += 1
        else:
            rows.append(_base_artifact_row(config, question, prompt, writer_base_answer))
            existing.add((question_id, "base_llm"))
            written_count += 1

    path.write_text(
        "".join(json.dumps(_safe_payload(row), ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    paired_question_count = _paired_question_count(rows)
    return {
        "artifact_schema_version": "live_rag_vs_base_answer_artifact.v1",
        "provider": config.provider,
        "model": config.model,
        "question_count": len(selected),
        "artifact_count": len(rows),
        "paired_question_count": paired_question_count,
        "written_count": written_count,
        "skipped_existing_count": skipped_existing_count,
        "output_file": path.name,
    }


def load_live_eval_answer_artifacts(path: str | Path) -> List[Dict[str, Any]]:
    artifact_path = Path(path)
    if not artifact_path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for raw_line in artifact_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            rows.append(_safe_payload(payload))
    return rows


def _rag_artifact_row(
    config: ProviderConfig,
    question: Dict[str, Any],
    prompt: str,
    *,
    api_url: str,
    query_user_id: str,
    timeout: int,
    post_json: PostJson,
) -> Dict[str, Any]:
    payload = {
        "query": prompt,
        "mode": "team",
        "user_id": str(query_user_id or "default_user"),
        "stream": False,
        "llm_provider": config.provider,
        "llm_model": config.model,
        "response_mode": "full",
        "timeout_sec": min(max(int(timeout), 5), 180),
    }
    response = post_json(_query_endpoint(api_url), payload, {"Content-Type": "application/json"}, int(timeout))
    answer_text = str(response.get("report") or response.get("answer") or response.get("message") or "")
    row = _artifact_row_common(config, question, "rag", answer_text)
    row.update(
        {
            "answer_source_mode": str(response.get("answer_source_mode") or ""),
            "generation_status": str(response.get("generation_status") or ""),
            "evidence_chain_summary": _evidence_chain_summary(response.get("evidence_chain") or {}),
            "rag_health_summary": _rag_health_summary(response.get("rag_health") or {}),
        }
    )
    return _safe_payload(row)


def _base_artifact_row(
    config: ProviderConfig,
    question: Dict[str, Any],
    prompt: str,
    base_answer_fn: BaseAnswerFn,
) -> Dict[str, Any]:
    raw_answer = base_answer_fn(config, question, prompt)
    if isinstance(raw_answer, dict):
        answer_text = str(raw_answer.get("answer_text") or raw_answer.get("content") or raw_answer.get("report") or "")
    else:
        answer_text = str(raw_answer or "")
    row = _artifact_row_common(config, question, "base_llm", answer_text)
    row.update(
        {
            "answer_source_mode": "base_model_only",
            "generation_status": "complete",
            "evidence_chain_summary": {"items": [], "verified_source_count": 0, "candidate_evidence_count": 0},
            "rag_health_summary": {},
        }
    )
    return _safe_payload(row)


def _artifact_row_common(
    config: ProviderConfig,
    question: Dict[str, Any],
    mode: str,
    answer_text: str,
) -> Dict[str, Any]:
    question_id = _question_id(question)
    cleaned_answer = _redact_text(answer_text)
    return {
        "artifact_schema_version": "live_rag_vs_base_answer_artifact.v1",
        "question_id": question_id,
        "question_hash": _question_hash(question),
        "domain_pack": str(question.get("domain_pack") or "unknown"),
        "mode": mode,
        "provider": config.provider,
        "model": config.model,
        "answer_text": cleaned_answer,
        "answer_hash": _answer_hash(question_id, mode, cleaned_answer),
    }


def _post_json(api_url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: int) -> Dict[str, Any]:
    request = urllib.request.Request(
        url=api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise LiveEvalArtifactConfigError(f"rag answer artifact request failed with HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise LiveEvalArtifactConfigError("rag answer artifact request failed") from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LiveEvalArtifactConfigError("rag answer artifact response was not json") from exc
    if not isinstance(parsed, dict):
        raise LiveEvalArtifactConfigError("rag answer artifact response must be an object")
    return parsed


def _base_answer_from_provider(config: ProviderConfig, question: Dict[str, Any], prompt: str) -> str:
    payload = {
        "model": config.model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the base model in a RAG-vs-base evaluation. "
                    "Answer from general model knowledge only. Do not claim access to local KB, source registry, "
                    "evidence_chain, or approved prescription permissions."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
    }
    request = urllib.request.Request(
        url=config.base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise LiveEvalArtifactConfigError(f"base answer request failed for {config.provider}") from exc
    try:
        provider_payload = json.loads(raw)
        return str(provider_payload["choices"][0]["message"]["content"] or "")
    except Exception as exc:
        raise LiveEvalArtifactConfigError(f"base answer response was not usable for {config.provider}") from exc


def _question_prompt(question: Dict[str, Any]) -> str:
    public_payload = {
        "question_id": question.get("question_id") or question.get("id"),
        "domain_pack": question.get("domain_pack"),
        "question": question.get("question") or question.get("query"),
        "user_profile": question.get("user_profile") or {},
        "core_prescription_allowed": bool(question.get("core_prescription_allowed")),
        "llm_general_knowledge_allowed": bool(question.get("llm_general_knowledge_allowed")),
        "medical_red_flag_expected": bool(question.get("medical_red_flag_expected")),
    }
    return (
        "Answer this running-training evaluation question for a commercial RAG-vs-base proof.\n"
        "Use the user profile only as context.\n"
        f"{json.dumps(public_payload, ensure_ascii=False, sort_keys=True)}"
    )


def _evidence_chain_summary(evidence_chain: Dict[str, Any]) -> Dict[str, Any]:
    items = evidence_chain.get("items") if isinstance(evidence_chain, dict) else []
    summarized_items: List[Dict[str, Any]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        summarized_items.append(
            _safe_payload(
                {
                    "display_mode": item.get("display_mode"),
                    "source_url": item.get("source_url"),
                    "source_title": item.get("source_title") or item.get("title"),
                    "evidence_tier": item.get("evidence_tier"),
                    "source_type": item.get("source_type"),
                    "citation_label": item.get("citation_label"),
                }
            )
        )
    return {
        "items": summarized_items,
        "verified_source_count": sum(1 for item in summarized_items if item.get("display_mode") == "verified_source"),
        "candidate_evidence_count": sum(1 for item in summarized_items if item.get("display_mode") == "candidate_evidence"),
        "needs_evidence_count": sum(1 for item in summarized_items if item.get("display_mode") == "needs_evidence"),
    }


def _rag_health_summary(rag_health: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(rag_health, dict):
        return {}
    allowed_keys = {
        "status",
        "ready",
        "mode",
        "source",
        "runtime_chunk_count",
        "chunks_count",
        "approved_records",
        "ready_records",
        "ready_core_records",
        "can_replace_runtime",
        "runtime_index_schema_version",
    }
    return _safe_payload({key: rag_health[key] for key in allowed_keys if key in rag_health})


def _query_endpoint(api_url: str) -> str:
    normalized = str(api_url or "").strip().rstrip("/")
    if not normalized:
        return "http://127.0.0.1:8010/query"
    return normalized if normalized.endswith("/query") else normalized + "/query"


def _question_id(question: Dict[str, Any]) -> str:
    return str(question.get("question_id") or question.get("id") or _question_hash(question))


def _question_hash(question: Dict[str, Any]) -> str:
    raw = json.dumps(
        {
            "question": question.get("question") or question.get("query") or "",
            "user_profile": question.get("user_profile") or {},
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return "qhash_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _answer_hash(question_id: str, mode: str, answer_text: str) -> str:
    digest = hashlib.sha256(f"{question_id}\n{mode}\n{answer_text}".encode("utf-8")).hexdigest()[:16]
    return "ans_" + digest


def _paired_question_count(rows: Iterable[Dict[str, Any]]) -> int:
    grouped: Dict[str, set[str]] = {}
    for row in rows or []:
        question_id = str(row.get("question_id") or "")
        mode = str(row.get("mode") or "")
        if question_id:
            grouped.setdefault(question_id, set()).add(mode)
    return sum(1 for modes in grouped.values() if {"rag", "base_llm"} <= modes)


def _safe_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        cleaned: Dict[str, Any] = {}
        for key, value in payload.items():
            lowered = str(key).lower()
            if lowered in {"api_key", "authorization", "token", "source_path", "local_path", "raw_prompt", "prompt"}:
                continue
            cleaned[str(key)] = _safe_payload(value)
        return cleaned
    if isinstance(payload, list):
        return [_safe_payload(item) for item in payload]
    if isinstance(payload, str):
        return _redact_text(payload)
    return payload


def _redact_text(text: str) -> str:
    redacted = re.sub(r"(sk-|Bearer\s+)[A-Za-z0-9_\-]{8,}", "[redacted]", str(text))
    redacted = re.sub(r"[A-Za-z]:[\\/](?:Users|Documents|Windows|Program Files)[^\"'\s,}]*", "[redacted_path]", redacted)
    return redacted
