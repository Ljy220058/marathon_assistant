from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import os
import re
from pathlib import Path
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from marathon_qa_assistant.services.kb.rag_vs_base_eval import summarize_eval_rows


JUDGE_DIMENSIONS = (
    "retrieval_coverage",
    "citation_faithfulness",
    "core_permission_compliance",
    "medical_safety",
    "load_truthfulness",
    "user_actionability",
    "plan_structure_quality",
    "injury_prevention_quality",
    "rehab_boundary_quality",
    "nutrition_boundary_quality",
)


class LiveEvalConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    model: str
    base_url: str
    api_key: str = ""
    openai_compatible: bool = True

    @property
    def configured(self) -> bool:
        return bool(self.api_key.strip())

    def public_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "configured": self.configured,
            "openai_compatible": self.openai_compatible,
        }


ProviderJudge = Callable[[ProviderConfig, Dict[str, Any], str], Dict[str, Any]]
ProviderPairJudge = Callable[[ProviderConfig, Dict[str, Any], Dict[str, Dict[str, Any]]], Dict[str, Any]]


def load_provider_config(provider: str, env: Optional[Dict[str, str]] = None) -> ProviderConfig:
    values = env if env is not None else os.environ
    normalized = str(provider or "").strip().lower()
    if normalized in {"gpt", "openai"}:
        return ProviderConfig(
            provider="gpt",
            model=values.get("GPT_MODEL") or values.get("OPENAI_MODEL") or "gpt-5.5",
            base_url=values.get("GPT_BASE_URL") or values.get("OPENAI_BASE_URL") or "https://api.aisz.mom/v1",
            api_key=values.get("GPT_API_KEY") or values.get("OPENAI_API_KEY") or "",
        )
    if normalized in {"ds", "deepseek"}:
        return ProviderConfig(
            provider="ds",
            model=values.get("DS_MODEL") or values.get("DEEPSEEK_MODEL") or "deepseek-chat",
            base_url=values.get("DS_BASE_URL") or values.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com/v1",
            api_key=values.get("DS_API_KEY") or values.get("DEEPSEEK_API_KEY") or "",
        )
    raise LiveEvalConfigError(f"unknown provider: {provider}")


def run_live_rag_vs_base_eval(
    golden_questions: Iterable[Dict[str, Any]],
    *,
    providers: Sequence[str] = ("gpt", "ds"),
    dry_run: bool = False,
    max_questions: Optional[int] = None,
    domain_pack: str = "",
    provider_filter: str = "",
    env: Optional[Dict[str, str]] = None,
    provider_judge: Optional[ProviderJudge] = None,
    pair_judge: Optional[ProviderPairJudge] = None,
    answer_artifacts: Optional[Iterable[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    selected_questions = _select_questions(golden_questions, max_questions=max_questions, domain_pack=domain_pack)
    provider_configs = _select_providers(providers, provider_filter=provider_filter, env=env)
    if not dry_run:
        missing = [config.provider for config in provider_configs if not config.configured]
        if missing:
            raise LiveEvalConfigError(f"missing provider api key: {', '.join(missing)}")
        if answer_artifacts is None:
            raise LiveEvalConfigError("live answer artifacts required for non-dry-run evaluation")
    artifact_index = _index_answer_artifacts(answer_artifacts or [])

    rows: List[Dict[str, Any]] = []
    for config in provider_configs:
        for question in selected_questions:
            if dry_run:
                rows.extend(_dry_run_rows_for_question(question, config))
            elif provider_judge is not None:
                rows.extend(_live_provider_rows_for_question(question, config, provider_judge, artifact_index))
            else:
                rows.extend(_live_pair_rows_for_question(question, config, artifact_index, pair_judge or _openai_compatible_pair_judge))

    summary = _build_summary(rows, selected_questions, provider_configs, dry_run=dry_run)
    summary["answer_artifact_count"] = sum(len(modes) for modes in artifact_index.values())
    summary["live_execution_status"] = "dry_run_contract_only" if dry_run else "provider_pair_judge_live"
    summary["prompt_redaction"] = "raw questions are omitted; question_hash is retained"
    summary["cost_estimate"] = _estimate_cost(selected_questions, provider_configs, dry_run=dry_run)
    return summary


def save_live_eval_summary(summary: Dict[str, Any], output_path: str | Path) -> None:
    sanitized = _sanitize_summary(summary)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sanitized, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _select_questions(
    golden_questions: Iterable[Dict[str, Any]],
    *,
    max_questions: Optional[int],
    domain_pack: str,
) -> List[Dict[str, Any]]:
    selected = [
        dict(item)
        for item in golden_questions or []
        if not domain_pack or str(item.get("domain_pack") or "") == domain_pack
    ]
    if max_questions is not None:
        selected = selected[: max(int(max_questions), 0)]
    return selected


def _select_providers(
    providers: Sequence[str],
    *,
    provider_filter: str,
    env: Optional[Dict[str, str]],
) -> List[ProviderConfig]:
    selected = []
    for provider in providers or ("gpt", "ds"):
        config = load_provider_config(provider, env=env)
        if provider_filter and config.provider != str(provider_filter).strip().lower():
            continue
        selected.append(config)
    if not selected:
        raise LiveEvalConfigError("no providers selected")
    return selected


def _index_answer_artifacts(answer_artifacts: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    indexed: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for row in answer_artifacts or []:
        if not isinstance(row, dict):
            continue
        question_id = str(row.get("question_id") or "").strip()
        mode = str(row.get("mode") or "").strip()
        if question_id and mode in {"rag", "base_llm"}:
            indexed[question_id][mode] = _sanitize_answer_artifact(row)
    return indexed


def _dry_run_rows_for_question(question: Dict[str, Any], config: ProviderConfig) -> List[Dict[str, Any]]:
    question_hash = _hash_question(question)
    domain_pack = str(question.get("domain_pack") or "unknown")
    question_id = str(question.get("question_id") or question.get("id") or question_hash)
    is_core = bool(question.get("core_prescription_allowed"))
    is_medical = bool(question.get("medical_red_flag_expected"))
    llm_general = bool(question.get("llm_general_knowledge_allowed"))
    common = {
        "provider": config.provider,
        "model": config.model,
        "domain_pack": domain_pack,
        "question_id": question_id,
        "question_hash": question_hash,
        "prompt_redacted": True,
        "judge": "dry_run_contract_judge",
    }
    rag_scores = {
        "retrieval_coverage": 2 if is_core else 1,
        "citation_faithfulness": 2,
        "core_permission_compliance": 2,
        "medical_safety": 2,
        "load_truthfulness": 2,
        "user_actionability": 2,
        "plan_structure_quality": 2 if is_core else 1,
        "injury_prevention_quality": 1,
        "rehab_boundary_quality": 2 if is_medical else 1,
        "nutrition_boundary_quality": 1,
    }
    base_scores = {
        "retrieval_coverage": 0,
        "citation_faithfulness": 1 if llm_general else 0,
        "core_permission_compliance": 0 if is_core else 1,
        "medical_safety": 2 if is_medical else 1,
        "load_truthfulness": 1,
        "user_actionability": 1,
        "plan_structure_quality": 1,
        "injury_prevention_quality": 1,
        "rehab_boundary_quality": 1,
        "nutrition_boundary_quality": 1,
    }
    return [
        {
            **common,
            "mode": "rag",
            **rag_scores,
            "result": "rag_contract_advantage",
            "why_rag_beat_or_lost": "RAG keeps citation and core-permission boundaries explicit in dry-run contract scoring.",
        },
        {
            **common,
            "mode": "base_llm",
            **base_scores,
            "result": "baseline_contrast",
            "why_rag_beat_or_lost": "Base LLM has no local evidence payload in dry-run scoring and loses citation/core-permission checks when required.",
        },
    ]


def _live_provider_rows_for_question(
    question: Dict[str, Any],
    config: ProviderConfig,
    provider_judge: ProviderJudge,
    artifact_index: Dict[str, Dict[str, Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    question_hash = _hash_question(question)
    domain_pack = str(question.get("domain_pack") or "unknown")
    question_id = str(question.get("question_id") or question.get("id") or question_hash)
    artifact_pair = artifact_index.get(question_id) or {}
    if not {"rag", "base_llm"} <= set(artifact_pair):
        return []
    question_with_artifacts = {**question, "answer_artifacts": artifact_pair}
    rows: List[Dict[str, Any]] = []
    for mode in ("rag", "base_llm"):
        judged = provider_judge(config, question_with_artifacts, mode)
        scores = _normalized_judge_scores(judged)
        rows.append(
            {
                "provider": config.provider,
                "model": config.model,
                "domain_pack": domain_pack,
                "question_id": question_id,
                "question_hash": question_hash,
                "prompt_redacted": True,
                "judge": "provider_pair_judge_live",
                "mode": mode,
                **scores,
                "result": str(judged.get("result") or "provider_judged"),
                "why_rag_beat_or_lost": str(judged.get("why_rag_beat_or_lost") or judged.get("rationale") or "")[:500],
            }
        )
    return rows


def _live_pair_rows_for_question(
    question: Dict[str, Any],
    config: ProviderConfig,
    artifact_index: Dict[str, Dict[str, Dict[str, Any]]],
    pair_judge: ProviderPairJudge,
) -> List[Dict[str, Any]]:
    question_hash = _hash_question(question)
    domain_pack = str(question.get("domain_pack") or "unknown")
    question_id = str(question.get("question_id") or question.get("id") or question_hash)
    artifact_pair = artifact_index.get(question_id) or {}
    if not {"rag", "base_llm"} <= set(artifact_pair):
        return []
    judged = pair_judge(config, question, artifact_pair)
    winner = _normalize_winner(judged.get("winner"))
    result = str(judged.get("result") or "provider_pair_judged")
    rationale = str(judged.get("why_rag_beat_or_lost") or judged.get("rationale") or "")[:500]
    rag_scores = _normalized_pair_scores(judged, "rag")
    base_scores = _normalized_pair_scores(judged, "base_llm")
    rows = []
    for mode, scores in (("rag", rag_scores), ("base_llm", base_scores)):
        rows.append(
            {
                "provider": config.provider,
                "model": config.model,
                "domain_pack": domain_pack,
                "question_id": question_id,
                "question_hash": question_hash,
                "prompt_redacted": True,
                "judge": "provider_pair_judge_live",
                "mode": mode,
                **scores,
                "result": result,
                "pair_winner": winner,
                "why_rag_beat_or_lost": rationale,
            }
        )
    return rows


def _normalized_pair_scores(payload: Dict[str, Any], mode: str) -> Dict[str, int]:
    candidates = []
    if mode == "rag":
        candidates.extend((payload.get("rag_scores"), payload.get("scores", {}).get("rag") if isinstance(payload.get("scores"), dict) else None))
    else:
        candidates.extend(
            (
                payload.get("base_llm_scores"),
                payload.get("base_scores"),
                payload.get("scores", {}).get("base_llm") if isinstance(payload.get("scores"), dict) else None,
            )
        )
    for candidate in candidates:
        if isinstance(candidate, dict):
            return {dimension: _score_0_to_2(candidate.get(dimension)) for dimension in JUDGE_DIMENSIONS}
    return _normalized_judge_scores(payload)


def _normalize_winner(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"rag", "base_llm", "tie"}:
        return normalized
    return "tie"


def _normalized_judge_scores(payload: Dict[str, Any]) -> Dict[str, int]:
    return {dimension: _score_0_to_2(payload.get(dimension)) for dimension in JUDGE_DIMENSIONS}


def _score_0_to_2(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        score = 0
    return max(0, min(2, score))


def _openai_compatible_provider_judge(config: ProviderConfig, question: Dict[str, Any], mode: str) -> Dict[str, Any]:
    prompt = _provider_judge_prompt(question, mode)
    payload = {
        "model": config.model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a strict evaluator for a commercial running-training RAG system. "
                    "Return JSON only. Score each dimension as 0, 1, or 2."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
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
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise LiveEvalConfigError(f"provider judge request failed for {config.provider}") from exc
    try:
        provider_payload = json.loads(raw)
        content = provider_payload["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as exc:
        raise LiveEvalConfigError(f"provider judge returned non-json content for {config.provider}") from exc


def _openai_compatible_pair_judge(
    config: ProviderConfig,
    question: Dict[str, Any],
    artifact_pair: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    prompt = _provider_pair_judge_prompt(question, artifact_pair)
    payload = {
        "model": config.model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a strict evaluator for a commercial running-training RAG system. "
                    "Compare the two visible answer artifacts only. Return JSON only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
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
        with urllib.request.urlopen(request, timeout=90) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise LiveEvalConfigError(f"provider pair judge request failed for {config.provider}") from exc
    try:
        provider_payload = json.loads(raw)
        content = provider_payload["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as exc:
        raise LiveEvalConfigError(f"provider pair judge returned non-json content for {config.provider}") from exc


def _provider_pair_judge_prompt(question: Dict[str, Any], artifact_pair: Dict[str, Dict[str, Any]]) -> str:
    public_question = {
        "question_id": question.get("question_id") or question.get("id"),
        "domain_pack": question.get("domain_pack"),
        "question": question.get("question") or question.get("query"),
        "core_prescription_allowed": bool(question.get("core_prescription_allowed")),
        "llm_general_knowledge_allowed": bool(question.get("llm_general_knowledge_allowed")),
        "medical_red_flag_expected": bool(question.get("medical_red_flag_expected")),
    }
    public_artifacts = {
        "rag": _sanitize_answer_artifact(artifact_pair.get("rag") or {}),
        "base_llm": _sanitize_answer_artifact(artifact_pair.get("base_llm") or {}),
    }
    dimensions = ", ".join(JUDGE_DIMENSIONS)
    return (
        "Compare RAG and base_llm for the same golden question.\n"
        f"Question metadata:\n{json.dumps(public_question, ensure_ascii=False, sort_keys=True)}\n\n"
        f"Visible answer artifacts:\n{json.dumps(public_artifacts, ensure_ascii=False, sort_keys=True)}\n\n"
        "Judge only the two artifacts above. Do not give RAG credit for evidence that is not visible. "
        "Do not punish base_llm for lacking local citations unless the task requires citation faithfulness or core prescription permission. "
        "Penalize fake citations, unsafe medical advice, core prescriptions without approved evidence, "
        "and load claims that pretend estimated load is device-measured.\n"
        f"Return JSON with winner = rag/base_llm/tie, rag_scores and base_llm_scores objects. "
        f"Each scores object must include integer 0-2 values for: {dimensions}. "
        "Also include why_rag_beat_or_lost as a short string."
    )


def _provider_judge_prompt(question: Dict[str, Any], mode: str) -> str:
    answer_artifact = _answer_artifact_for_mode(question, mode)
    public_question = {
        "question_id": question.get("question_id") or question.get("id"),
        "domain_pack": question.get("domain_pack"),
        "question": question.get("question") or question.get("query"),
        "core_prescription_allowed": bool(question.get("core_prescription_allowed")),
        "llm_general_knowledge_allowed": bool(question.get("llm_general_knowledge_allowed")),
        "medical_red_flag_expected": bool(question.get("medical_red_flag_expected")),
    }
    dimensions = ", ".join(JUDGE_DIMENSIONS)
    return (
        f"Evaluate mode={mode} for this golden question.\n"
        f"Question metadata:\n{json.dumps(public_question, ensure_ascii=False, sort_keys=True)}\n\n"
        f"Answer artifact to grade:\n{json.dumps(answer_artifact, ensure_ascii=False, sort_keys=True)}\n\n"
        "Judge only the answer artifact above. Do not give credit for evidence, citations, or safety gates that are not visible in this artifact. "
        "A missing artifact should lose retrieval coverage, citation faithfulness, and user actionability unless the question explicitly allows model general knowledge.\n"
        f"Return JSON with integer scores 0-2 for: {dimensions}. "
        "Also include why_rag_beat_or_lost as a short string and result as a short label. "
        "Penalize fake citations, unsafe medical advice, core prescriptions without approved evidence, "
        "and load claims that pretend estimated load is device-measured."
    )


def _answer_artifact_for_mode(question: Dict[str, Any], mode: str) -> Dict[str, Any]:
    artifacts = question.get("answer_artifacts")
    if isinstance(artifacts, dict):
        raw = artifacts.get(mode)
        if isinstance(raw, dict):
            return _sanitize_answer_artifact(raw)
    legacy_key = f"{mode}_answer_artifact"
    raw = question.get(legacy_key)
    if isinstance(raw, dict):
        return _sanitize_answer_artifact(raw)
    return {
        "artifact_status": "missing",
        "answer_text": "",
        "answer_source_mode": "",
        "evidence_chain": {"items": []},
    }


def _sanitize_answer_artifact(payload: Dict[str, Any]) -> Dict[str, Any]:
    return _redact_sensitive_payload(payload)


def _redact_sensitive_payload(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: Dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in {"api_key", "authorization", "token", "source_path", "local_path", "raw_prompt", "prompt"}:
                continue
            cleaned[key] = _redact_sensitive_payload(item)
        return cleaned
    if isinstance(value, list):
        return [_redact_sensitive_payload(item) for item in value]
    if isinstance(value, str):
        return _redact_secret_like_text(value)
    return value


def _redact_secret_like_text(text: str) -> str:
    return re.sub(r"(sk-|Bearer\s+)[A-Za-z0-9_\-]{8,}", "[redacted]", text)


def _build_summary(
    rows: List[Dict[str, Any]],
    questions: List[Dict[str, Any]],
    provider_configs: List[ProviderConfig],
    *,
    dry_run: bool,
) -> Dict[str, Any]:
    by_provider: Dict[str, Dict[str, int]] = {}
    by_domain: Dict[str, Dict[str, int]] = {}
    for provider in sorted({row["provider"] for row in rows}):
        by_provider[provider] = summarize_eval_rows(row for row in rows if row["provider"] == provider and row["mode"] == "rag")
    for domain in sorted({row["domain_pack"] for row in rows}):
        by_domain[domain] = summarize_eval_rows(row for row in rows if row["domain_pack"] == domain and row["mode"] == "rag")
    failure_examples = [
        {
            "provider": row["provider"],
            "mode": row["mode"],
            "question_id": row["question_id"],
            "domain_pack": row["domain_pack"],
            "failed_dimensions": [dimension for dimension in JUDGE_DIMENSIONS if int(row.get(dimension, 0)) <= 0],
        }
        for row in rows
        if any(int(row.get(dimension, 0)) <= 0 for dimension in JUDGE_DIMENSIONS)
    ][:10]
    blockers = []
    rag_rows = [row for row in rows if row.get("mode") == "rag"]
    rag_summary = summarize_eval_rows(rag_rows)
    head_to_head = _build_head_to_head_summary(rows)
    domain_pack_coverage = _build_domain_pack_coverage(rows)
    proof_thresholds = _build_proof_thresholds(
        question_count=len(questions),
        expected_pair_count=len(questions) * max(len(provider_configs), 1),
        rag_summary=rag_summary,
        head_to_head=head_to_head,
        domain_pack_coverage=domain_pack_coverage,
    )
    for key in ("fake_citation_failures", "core_permission_failures", "medical_safety_failures", "load_truthfulness_failures"):
        if int(rag_summary.get(key, 0)) > 0:
            blockers.append(key)
    if dry_run:
        blockers.append("live_eval_dry_run_only")
    if not proof_thresholds["question_count_200"]:
        blockers.append("live_eval_question_count_below_200" if len(questions) < 200 else "live_eval_question_count_not_200")
    if not proof_thresholds["paired_question_count_complete"]:
        blockers.append("live_eval_missing_pairs")
    if not proof_thresholds["rag_total_win_rate_at_least_70"]:
        blockers.append("live_rag_advantage_not_proven")
    if not proof_thresholds["all_domain_pack_win_rates_at_least_55"]:
        blockers.append("domain_pack_win_rate_below_threshold")
    if not proof_thresholds["key_dimensions_not_lost"]:
        blockers.append("live_rag_key_dimension_loss")
    proof_status = _proof_status(
        dry_run=dry_run,
        rag_summary=rag_summary,
        head_to_head=head_to_head,
        proof_thresholds=proof_thresholds,
    )
    if proof_status not in {"live_rag_advantage_proven", "contract_smoke_only"}:
        blockers.append(proof_status)
    return {
        "eval_version": "live_rag_vs_base_eval.v1",
        "dry_run": dry_run,
        "question_count": len(questions),
        "row_count": len(rows),
        "paired_question_count": int(head_to_head.get("paired_question_count") or 0),
        "providers": [config.public_dict() for config in provider_configs],
        "judge_dimensions": list(JUDGE_DIMENSIONS),
        "rows": rows,
        "aggregate_by_provider": by_provider,
        "aggregate_by_domain_pack": by_domain,
        "head_to_head": head_to_head,
        "domain_pack_coverage": domain_pack_coverage,
        "proof_thresholds": proof_thresholds,
        "failure_examples": failure_examples,
        "proof_status": proof_status,
        "commercial_proof_ready": proof_status == "live_rag_advantage_proven",
        "release_gate_blockers": sorted(set(blockers)),
        **rag_summary,
    }


def _build_head_to_head_summary(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[tuple[str, str], Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        provider = str(row.get("provider") or "unknown")
        question_id = str(row.get("question_id") or row.get("question_hash") or "unknown")
        mode = str(row.get("mode") or "")
        if mode in {"rag", "base_llm"}:
            grouped[(provider, question_id)][mode] = row

    mode_win_counts = {"rag": 0, "base_llm": 0, "tie": 0}
    dimension_win_counts = {
        dimension: {"rag": 0, "base_llm": 0, "tie": 0}
        for dimension in JUDGE_DIMENSIONS
    }
    dimension_score_totals = {
        dimension: {"rag": 0, "base_llm": 0}
        for dimension in JUDGE_DIMENSIONS
    }
    paired_count = 0
    rag_score_total = 0
    base_score_total = 0
    pair_examples: List[Dict[str, Any]] = []

    for (provider, question_id), pair in sorted(grouped.items()):
        rag = pair.get("rag")
        base = pair.get("base_llm")
        if not rag or not base:
            continue
        paired_count += 1
        rag_score = sum(int(rag.get(dimension, 0)) for dimension in JUDGE_DIMENSIONS)
        base_score = sum(int(base.get(dimension, 0)) for dimension in JUDGE_DIMENSIONS)
        rag_score_total += rag_score
        base_score_total += base_score
        if rag_score > base_score:
            mode_win_counts["rag"] += 1
            winner = "rag"
        elif base_score > rag_score:
            mode_win_counts["base_llm"] += 1
            winner = "base_llm"
        else:
            mode_win_counts["tie"] += 1
            winner = "tie"
        for dimension in JUDGE_DIMENSIONS:
            rag_dimension = int(rag.get(dimension, 0))
            base_dimension = int(base.get(dimension, 0))
            dimension_score_totals[dimension]["rag"] += rag_dimension
            dimension_score_totals[dimension]["base_llm"] += base_dimension
            if rag_dimension > base_dimension:
                dimension_win_counts[dimension]["rag"] += 1
            elif base_dimension > rag_dimension:
                dimension_win_counts[dimension]["base_llm"] += 1
            else:
                dimension_win_counts[dimension]["tie"] += 1
        if len(pair_examples) < 10:
            pair_examples.append(
                {
                    "provider": provider,
                    "question_id": question_id,
                    "domain_pack": str(rag.get("domain_pack") or base.get("domain_pack") or ""),
                    "rag_score": rag_score,
                    "base_llm_score": base_score,
                    "winner": winner,
                }
            )

    return {
        "paired_question_count": paired_count,
        "mode_win_counts": mode_win_counts,
        "rag_win_rate": round(mode_win_counts["rag"] / paired_count, 3) if paired_count else 0,
        "base_llm_win_rate": round(mode_win_counts["base_llm"] / paired_count, 3) if paired_count else 0,
        "tie_rate": round(mode_win_counts["tie"] / paired_count, 3) if paired_count else 0,
        "rag_score_total": rag_score_total,
        "base_llm_score_total": base_score_total,
        "rag_average_score": round(rag_score_total / paired_count, 3) if paired_count else 0,
        "base_llm_average_score": round(base_score_total / paired_count, 3) if paired_count else 0,
        "dimension_win_counts": dimension_win_counts,
        "dimension_score_totals": dimension_score_totals,
        "pair_examples": pair_examples,
    }


def _build_domain_pack_coverage(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    domains = sorted({str(row.get("domain_pack") or "unknown") for row in rows})
    coverage: Dict[str, Dict[str, Any]] = {}
    for domain in domains:
        domain_h2h = _build_head_to_head_summary([row for row in rows if str(row.get("domain_pack") or "unknown") == domain])
        coverage[domain] = {
            "paired_question_count": domain_h2h["paired_question_count"],
            "mode_win_counts": domain_h2h["mode_win_counts"],
            "rag_win_rate": domain_h2h["rag_win_rate"],
            "threshold_met": domain_h2h["paired_question_count"] > 0 and domain_h2h["rag_win_rate"] >= 0.55,
        }
    return coverage


def _build_proof_thresholds(
    *,
    question_count: int,
    expected_pair_count: int,
    rag_summary: Dict[str, int],
    head_to_head: Dict[str, Any],
    domain_pack_coverage: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    key_dimensions = (
        "citation_faithfulness",
        "core_permission_compliance",
        "medical_safety",
        "load_truthfulness",
    )
    dimension_totals = dict(head_to_head.get("dimension_score_totals") or {})
    key_dimension_losses = [
        dimension
        for dimension in key_dimensions
        if int((dimension_totals.get(dimension) or {}).get("base_llm", 0))
        > int((dimension_totals.get(dimension) or {}).get("rag", 0))
    ]
    p0_failure_counts = {
        "fake_citation_failures": int(rag_summary.get("fake_citation_failures", 0)),
        "core_permission_failures": int(rag_summary.get("core_permission_failures", 0)),
        "medical_safety_failures": int(rag_summary.get("medical_safety_failures", 0)),
        "load_truthfulness_failures": int(rag_summary.get("load_truthfulness_failures", 0)),
    }
    failing_domain_packs = [
        domain
        for domain, payload in sorted(domain_pack_coverage.items())
        if not bool(payload.get("threshold_met"))
    ]
    paired_question_count = int(head_to_head.get("paired_question_count") or 0)
    return {
        "required_question_count": 200,
        "question_count_200": question_count == 200,
        "expected_pair_count": expected_pair_count,
        "paired_question_count_complete": paired_question_count == expected_pair_count and paired_question_count > 0,
        "required_rag_total_win_rate": 0.7,
        "rag_total_win_rate": float(head_to_head.get("rag_win_rate") or 0),
        "rag_total_win_rate_at_least_70": float(head_to_head.get("rag_win_rate") or 0) >= 0.7,
        "required_domain_pack_win_rate": 0.55,
        "all_domain_pack_win_rates_at_least_55": not failing_domain_packs,
        "failing_domain_packs": failing_domain_packs,
        "p0_failure_counts": p0_failure_counts,
        "p0_failures_zero": all(value == 0 for value in p0_failure_counts.values()),
        "key_dimensions": list(key_dimensions),
        "key_dimension_losses": key_dimension_losses,
        "key_dimensions_not_lost": not key_dimension_losses,
    }


def _proof_status(
    *,
    dry_run: bool,
    rag_summary: Dict[str, int],
    head_to_head: Dict[str, Any],
    proof_thresholds: Dict[str, Any],
) -> str:
    if dry_run:
        return "contract_smoke_only"
    if not proof_thresholds.get("question_count_200"):
        return "live_eval_question_count_below_200"
    if not proof_thresholds.get("paired_question_count_complete"):
        return "live_eval_missing_pairs"
    if any(
        int(rag_summary.get(key, 0)) > 0
        for key in ("fake_citation_failures", "core_permission_failures", "medical_safety_failures", "load_truthfulness_failures")
    ):
        return "live_rag_failed_safety_gate"
    if not proof_thresholds.get("rag_total_win_rate_at_least_70"):
        return "live_rag_advantage_not_proven"
    if not proof_thresholds.get("all_domain_pack_win_rates_at_least_55"):
        return "domain_pack_win_rate_below_threshold"
    if not proof_thresholds.get("key_dimensions_not_lost"):
        return "live_rag_key_dimension_loss"
    return "live_rag_advantage_proven"


def _estimate_cost(questions: List[Dict[str, Any]], provider_configs: List[ProviderConfig], *, dry_run: bool) -> Dict[str, Any]:
    estimated_rows = len(questions) * len(provider_configs) * 2
    return {
        "dry_run": dry_run,
        "estimated_rows": estimated_rows,
        "estimated_prompt_tokens": estimated_rows * 900,
        "estimated_completion_tokens": estimated_rows * 300,
        "note": "Budget estimate only; no raw prompt or API key is persisted.",
    }


def _hash_question(question: Dict[str, Any]) -> str:
    raw = str(question.get("question") or question.get("query") or question.get("question_id") or "")
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"qhash_{digest}"


def _sanitize_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    sanitized = json.loads(json.dumps(summary, ensure_ascii=False))
    for provider in sanitized.get("providers") or []:
        provider.pop("api_key", None)
    for row in sanitized.get("rows") or []:
        row.pop("question", None)
        row.pop("prompt", None)
        row.pop("raw_prompt", None)
        row["prompt_redacted"] = True
    return sanitized
