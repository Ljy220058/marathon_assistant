from marathon_qa_assistant.apps.response_builders import _build_answer_card
from marathon_qa_assistant.apps.schemas import QueryRequest


def test_answer_card_safety_fallback_blocks_red_flag_training_advice():
    card = _build_answer_card(
        request=QueryRequest(query="跑步时胸痛头晕，还能继续跑间歇吗？"),
        result={"category": "coach", "user_profile": {}},
        report="可以先休息一下，状态好就继续完成间歇。",
        generation_status="complete",
        answer_source_mode="verified_rag",
        evidence_chain={"answer_source_mode": "verified_rag", "items": []},
    )

    assert card["intent"] == "injury_safety"
    assert card["severity"] == "medical_referral"
    assert any(section.get("type") == "safety_gate" for section in card["must_show"])
    assert any("立即停止训练" in item for item in card["do_not_do"])
    assert "状态好就继续完成间歇" not in str(card)
