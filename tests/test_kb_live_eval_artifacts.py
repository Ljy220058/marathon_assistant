import json
import urllib.error
from pathlib import Path

import pytest

from marathon_qa_assistant.services.kb.live_eval_artifacts import (
    LiveEvalArtifactConfigError,
    _post_json,
    collect_live_eval_answer_artifacts,
    load_live_eval_answer_artifacts,
)


def _questions():
    return [
        {
            "question_id": "q-load",
            "domain_pack": "training_load",
            "question": "How should planned load be described?",
            "user_profile": {"goal": "half_marathon", "weekly_mileage": 32},
        },
        {
            "question_id": "q-risk",
            "domain_pack": "medical_risk",
            "question": "I felt chest pain during intervals. What should I do tomorrow?",
            "user_profile": {"goal": "10K", "weekly_mileage": 25},
            "medical_red_flag_expected": True,
        },
    ]


def test_live_eval_artifact_collection_requires_gpt_key(monkeypatch, tmp_path):
    monkeypatch.delenv("GPT_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(LiveEvalArtifactConfigError, match="missing provider api key: gpt"):
        collect_live_eval_answer_artifacts(
            _questions(),
            provider="gpt",
            output_path=tmp_path / "artifacts.jsonl",
            post_json=lambda *args, **kwargs: {},
            base_answer_fn=lambda *args, **kwargs: "base",
        )


def test_live_eval_artifact_collection_writes_paired_sanitized_artifacts(monkeypatch, tmp_path):
    monkeypatch.setenv("GPT_API_KEY", "test-artifact-key")

    def fake_post_json(api_url, payload, headers, timeout):
        assert payload["llm_provider"] == "gpt"
        assert payload["user_id"] == "default_user"
        assert payload["query"]
        return {
            "report": "RAG answer with verified source",
            "answer_source_mode": "verified_rag",
            "generation_status": "complete",
            "evidence_chain": {
                "items": [
                    {
                        "display_mode": "verified_source",
                        "source_url": "https://example.test/source",
                        "source_path": "C:/Users/private/source.pdf",
                        "local_path": "C:/Users/private/source.pdf",
                    }
                ]
            },
            "rag_health": {
                "can_replace_runtime": True,
                "approved_records": 19,
                "local_path": "C:/Users/private/vector",
            },
        }

    output_path = tmp_path / "artifacts.jsonl"
    summary = collect_live_eval_answer_artifacts(
        _questions(),
        provider="gpt",
        output_path=output_path,
        post_json=fake_post_json,
        base_answer_fn=lambda config, question, prompt: f"Base answer for {question['question_id']}",
    )
    rows = load_live_eval_answer_artifacts(output_path)

    assert summary["artifact_count"] == 4
    assert summary["paired_question_count"] == 2
    assert {(row["question_id"], row["mode"]) for row in rows} == {
        ("q-load", "rag"),
        ("q-load", "base_llm"),
        ("q-risk", "rag"),
        ("q-risk", "base_llm"),
    }
    assert all(row["answer_hash"].startswith("ans_") for row in rows)
    rendered = output_path.read_text(encoding="utf-8")
    assert "test-artifact-key" not in rendered
    assert "C:/Users/private" not in rendered
    assert "source_path" not in rendered
    assert "local_path" not in rendered


def test_live_eval_artifact_collection_accepts_explicit_query_user_id(monkeypatch, tmp_path):
    monkeypatch.setenv("GPT_API_KEY", "test-artifact-key")
    seen_payloads = []

    def fake_post_json(api_url, payload, headers, timeout):
        seen_payloads.append(payload)
        return {
            "report": "RAG answer",
            "answer_source_mode": "model_general_knowledge",
            "generation_status": "complete",
            "evidence_chain": {"items": []},
            "rag_health": {},
        }

    collect_live_eval_answer_artifacts(
        _questions()[:1],
        provider="gpt",
        output_path=tmp_path / "artifacts.jsonl",
        query_user_id="default_user",
        post_json=fake_post_json,
        base_answer_fn=lambda *args, **kwargs: "base answer",
    )

    assert [payload["user_id"] for payload in seen_payloads] == ["default_user"]


def test_live_eval_artifact_resume_does_not_duplicate_existing_pairs(monkeypatch, tmp_path):
    monkeypatch.setenv("GPT_API_KEY", "test-artifact-key")
    output_path = tmp_path / "artifacts.jsonl"
    output_path.write_text(
        json.dumps(
            {
                "question_id": "q-load",
                "mode": "rag",
                "answer_text": "existing rag",
                "answer_source_mode": "verified_rag",
                "evidence_chain_summary": {"items": []},
                "rag_health_summary": {},
                "answer_hash": "ans_existing",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    summary = collect_live_eval_answer_artifacts(
        _questions()[:1],
        provider="gpt",
        output_path=output_path,
        resume=True,
        post_json=lambda *args, **kwargs: {"report": "new rag", "evidence_chain": {}, "rag_health": {}},
        base_answer_fn=lambda *args, **kwargs: "new base",
    )
    rows = load_live_eval_answer_artifacts(output_path)

    assert summary["artifact_count"] == 2
    assert [row["mode"] for row in rows].count("rag") == 1
    assert [row["mode"] for row in rows].count("base_llm") == 1


def test_live_eval_post_json_reports_http_status_without_response_body_leak(monkeypatch):
    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(
            url=request.full_url,
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=None,
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    with pytest.raises(LiveEvalArtifactConfigError, match="rag answer artifact request failed with HTTP 400"):
        _post_json(
            "http://127.0.0.1:8010/query",
            {"query": "x"},
            {"Content-Type": "application/json"},
            5,
        )


def test_live_eval_artifact_cli_passes_query_user_id(monkeypatch, tmp_path, capsys):
    from tools.kb import build_live_eval_answer_artifacts as cli

    captured = {}

    def fake_collect(questions, **kwargs):
        captured["question_count"] = len(list(questions))
        captured.update(kwargs)
        return {
            "artifact_schema_version": "live_rag_vs_base_answer_artifact.v1",
            "provider": kwargs["provider"],
            "model": "gpt-5.5",
            "question_count": 1,
            "artifact_count": 2,
            "paired_question_count": 1,
            "written_count": 2,
            "skipped_existing_count": 0,
            "output_file": Path(kwargs["output_path"]).name,
        }

    monkeypatch.setattr(cli, "collect_live_eval_answer_artifacts", fake_collect)
    monkeypatch.setattr(
        "sys.argv",
        [
            "build_live_eval_answer_artifacts.py",
            "--provider",
            "gpt",
            "--max-questions",
            "1",
            "--user-id",
            "default_user",
            "--output",
            str(tmp_path / "artifacts.jsonl"),
        ],
    )

    exit_code = cli.main()
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert captured["query_user_id"] == "default_user"
    assert captured["max_questions"] == 1
