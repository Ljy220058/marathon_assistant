from marathon_qa_assistant.apps.response_builders import _build_answer_card, _build_ui_policy
from marathon_qa_assistant.apps.schemas import QueryRequest


def test_answer_card_contract_v2_contains_required_sections_and_policy_paths():
    card = _build_answer_card(
        request=QueryRequest(query="半马比赛前怎么补给？"),
        result={"category": "nutritionist", "user_profile": {}},
        report="## 结论\n赛前补给要先在训练中验证。",
        generation_status="complete",
        answer_source_mode="verified_rag",
        evidence_chain={"items": []},
    )
    policy = _build_ui_policy(card["ui_render_mode"])

    assert card["version"] == "answer_card.v2"
    assert card["intent"] == "nutrition"
    assert card["title"]
    assert card["one_line"]
    assert card["must_show"]
    assert set(card["personalization"]) >= {"used_profile_fields", "assumptions", "missing_fields"}
    assert "answer_card.must_show" in policy["must_not_truncate"]
    assert "answer_card.do_not_do" in policy["must_not_truncate"]
    assert "full_report.markdown" in policy["default_collapsed"]
    assert policy["evidence_display"] == "drawer"


def test_answer_card_marks_missing_profile_resume_prompt():
    card = _build_answer_card(
        request=QueryRequest(query="帮我生成全马计划"),
        result={
            "missing_info_status": "awaiting_profile",
            "workflow_pause": {
                "status": "awaiting_user_input",
                "resume_target": "router",
                "field_labels": ["当前周跑量", "可用训练日"],
            },
            "user_profile": {},
        },
        report="__FILL_FIELDS__",
        generation_status="complete",
        answer_source_mode="",
        evidence_chain={"items": []},
    )

    assert card["intent"] == "missing_profile"
    assert card["ui_render_mode"] == "required_profile_prompt"
    assert card["must_show"][1]["text"] == "补齐后从 router 重新处理原始请求。"
