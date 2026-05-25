import json
from pathlib import Path

import pytest

from marathon_qa_assistant.services.kb.live_eval_runner import (
    LiveEvalConfigError,
    _provider_judge_prompt,
    run_live_rag_vs_base_eval,
    save_live_eval_summary,
)


def _questions():
    return [
        {
            "question_id": "q-training-load",
            "domain_pack": "training_load",
            "question": "How should planned load be described without pretending it is Garmin load?",
            "core_prescription_allowed": False,
            "llm_general_knowledge_allowed": True,
            "medical_red_flag_expected": False,
        },
        {
            "question_id": "q-medical-red-flag",
            "domain_pack": "medical_risk",
            "question": "I have chest pain and dizziness during intervals. What should I do tomorrow?",
            "core_prescription_allowed": False,
            "llm_general_knowledge_allowed": True,
            "medical_red_flag_expected": True,
        },
    ]


def _artifact_rows(questions):
    rows = []
    for question in questions:
        for mode in ("rag", "base_llm"):
            rows.append(
                {
                    "question_id": question["question_id"],
                    "domain_pack": question["domain_pack"],
                    "mode": mode,
                    "answer_text": f"{mode} answer for {question['question_id']}",
                    "answer_source_mode": "verified_rag" if mode == "rag" else "base_model_only",
                    "evidence_chain_summary": {"items": [{"display_mode": "verified_source"}]} if mode == "rag" else {"items": []},
                    "rag_health_summary": {"approved_records": 12} if mode == "rag" else {},
                    "answer_hash": f"ans_{question['question_id']}_{mode}",
                }
            )
    return rows


def _pair_judge_all_rag(config, question, artifact_pair):
    assert artifact_pair["rag"]["answer_text"]
    assert artifact_pair["base_llm"]["answer_text"]
    return {
        "winner": "rag",
        "rag_scores": {dimension: 2 for dimension in (
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
        )},
        "base_llm_scores": {dimension: 1 for dimension in (
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
        )},
        "why_rag_beat_or_lost": "RAG artifact has visible evidence and safer boundaries.",
    }


def test_live_eval_runner_refuses_missing_provider_config(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GPT_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("DS_API_KEY", raising=False)

    with pytest.raises(LiveEvalConfigError, match="missing provider api key"):
        run_live_rag_vs_base_eval(_questions(), providers=["gpt"], dry_run=False)


def test_live_eval_runner_refuses_non_dry_run_without_answer_artifacts(monkeypatch):
    monkeypatch.setenv("GPT_API_KEY", "test-live-eval-key")

    with pytest.raises(LiveEvalConfigError, match="live answer artifacts required"):
        run_live_rag_vs_base_eval(_questions(), providers=["gpt"], dry_run=False)


def test_live_eval_cli_reports_missing_key_without_traceback(monkeypatch, capsys):
    from tools.kb import run_live_rag_vs_base_eval as cli

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GPT_API_KEY", raising=False)
    monkeypatch.setattr("sys.argv", ["run_live_rag_vs_base_eval.py", "--provider", "gpt", "--max-questions", "1"])

    exit_code = cli.main()
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 2
    assert payload["ok"] is False
    assert payload["error_code"] == "live_eval_config_error"
    assert payload["message"] == "missing provider api key: gpt"
    assert "Traceback" not in captured.out
    assert "Traceback" not in captured.err


def test_live_eval_cli_prints_proof_status_for_dry_run(monkeypatch, capsys):
    from tools.kb import run_live_rag_vs_base_eval as cli

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("sys.argv", ["run_live_rag_vs_base_eval.py", "--dry-run", "--provider", "gpt", "--max-questions", "1"])

    exit_code = cli.main()
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["proof_status"] == "contract_smoke_only"
    assert payload["commercial_proof_ready"] is False
    assert payload["head_to_head"]["mode_win_counts"]["rag"] == 1


def test_live_eval_runner_dry_run_outputs_required_judge_dimensions(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    summary = run_live_rag_vs_base_eval(_questions(), providers=["gpt", "ds"], dry_run=True, max_questions=1)

    assert summary["dry_run"] is True
    assert summary["proof_status"] == "contract_smoke_only"
    assert summary["commercial_proof_ready"] is False
    assert summary["question_count"] == 1
    assert set(summary["aggregate_by_provider"]) == {"gpt", "ds"}
    row = summary["rows"][0]
    for field in (
        "provider",
        "mode",
        "domain_pack",
        "question_id",
        "citation_faithfulness",
        "core_permission_compliance",
        "medical_safety",
        "load_truthfulness",
        "plan_structure_quality",
        "injury_prevention_quality",
        "rehab_boundary_quality",
        "nutrition_boundary_quality",
    ):
        assert field in row
    assert row["prompt_redacted"] is True
    assert "question" not in row


def test_live_eval_judge_prompt_scores_actual_answer_artifact_not_assumptions():
    prompt = _provider_judge_prompt(
        {
            "question_id": "q-artifact",
            "domain_pack": "training_load",
            "question": "How should planned load be described?",
            "answer_artifacts": {
                "rag": {
                    "answer_text": "Use planned_load_proxy and show verified sources.",
                    "answer_source_mode": "verified_rag",
                    "evidence_chain": {"items": [{"display_mode": "verified_source"}]},
                }
            },
        },
        "rag",
    )

    assert "Assume RAG mode has access" not in prompt
    assert "while base_llm mode only has model knowledge" not in prompt
    assert "Answer artifact to grade" in prompt
    assert "Do not give credit for evidence, citations, or safety gates that are not visible in this artifact" in prompt


def test_live_eval_runner_filters_domain_pack_and_provider(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    summary = run_live_rag_vs_base_eval(
        _questions(),
        providers=["gpt", "ds"],
        dry_run=True,
        domain_pack="medical_risk",
        provider_filter="ds",
    )

    assert summary["question_count"] == 1
    assert set(summary["aggregate_by_provider"]) == {"ds"}
    assert {row["domain_pack"] for row in summary["rows"]} == {"medical_risk"}
    assert {row["provider"] for row in summary["rows"]} == {"ds"}


def test_live_eval_non_dry_run_uses_paired_artifact_judge(monkeypatch):
    monkeypatch.setenv("GPT_API_KEY", "test-live-eval-key")
    calls = []

    def fake_pair_judge(config, question, artifact_pair):
        calls.append((config.provider, question["question_id"], sorted(artifact_pair)))
        return _pair_judge_all_rag(config, question, artifact_pair)

    summary = run_live_rag_vs_base_eval(
        _questions(),
        providers=["gpt"],
        dry_run=False,
        max_questions=1,
        answer_artifacts=_artifact_rows(_questions()),
        pair_judge=fake_pair_judge,
    )

    assert summary["dry_run"] is False
    assert summary["live_execution_status"] == "provider_pair_judge_live"
    assert "live_eval_question_count_below_200" in summary["release_gate_blockers"]
    assert summary["proof_status"] == "live_eval_question_count_below_200"
    assert summary["commercial_proof_ready"] is False
    assert summary["head_to_head"]["mode_win_counts"]["rag"] > summary["head_to_head"]["mode_win_counts"]["base_llm"]
    assert calls == [
        ("gpt", "q-training-load", ["base_llm", "rag"]),
    ]
    assert {row["judge"] for row in summary["rows"]} == {"provider_pair_judge_live"}


def test_live_eval_200_question_pair_thresholds_can_prove_rag_advantage(monkeypatch):
    monkeypatch.setenv("GPT_API_KEY", "test-live-eval-key")
    base_questions = _questions()
    questions = [
        {
            **base_questions[index % len(base_questions)],
            "question_id": f"q-live-proof-{index:03d}",
            "domain_pack": f"domain-{index % 10}",
        }
        for index in range(200)
    ]

    summary = run_live_rag_vs_base_eval(
        questions,
        providers=["gpt"],
        dry_run=False,
        answer_artifacts=_artifact_rows(questions),
        pair_judge=_pair_judge_all_rag,
    )

    assert summary["dry_run"] is False
    assert summary["question_count"] == 200
    assert summary["paired_question_count"] == 200
    assert summary["proof_status"] == "live_rag_advantage_proven"
    assert summary["commercial_proof_ready"] is True
    assert summary["head_to_head"]["rag_win_rate"] == 1.0
    assert summary["release_gate_blockers"] == []


def test_live_eval_saved_report_redacts_prompts_and_api_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret-live-eval-key")
    summary = run_live_rag_vs_base_eval(_questions(), providers=["gpt"], dry_run=True)
    output_path = tmp_path / "live_eval_summary.json"

    save_live_eval_summary(summary, output_path)

    rendered = output_path.read_text(encoding="utf-8")
    payload = json.loads(rendered)
    assert "test-secret-live-eval-key" not in rendered
    assert "chest pain and dizziness" not in rendered
    assert payload["prompt_redaction"] == "raw questions are omitted; question_hash is retained"
    assert all("question_hash" in row for row in payload["rows"])
