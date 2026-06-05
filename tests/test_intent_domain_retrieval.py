from marathon_qa_assistant.nodes.profile_and_retrieval import filter_hits_for_intent_domain


def test_nutrition_query_prioritizes_nutrition_domain_hits():
    hits = [
        {"chunk_id": "a", "text": "膝盖疼痛处理", "domain_pack": "medical_risk", "score": 0.92},
        {"chunk_id": "b", "text": "能量胶和碳水补给", "domain_pack": "nutrition_race_fueling", "score": 0.70},
        {"chunk_id": "c", "text": "赛前补水", "evidence_domain": "nutrition_race_fueling", "score": 0.68},
    ]

    filtered = filter_hits_for_intent_domain(hits, category="nutritionist", query="半马赛前怎么补给", top_k=2)

    assert [item["chunk_id"] for item in filtered] == ["b", "c"]
    assert all(item["retrieval_domain_match"] == "nutrition" for item in filtered)


def test_injury_query_prioritizes_medical_domain_hits():
    hits = [
        {"chunk_id": "a", "text": "赛中能量胶", "domain_pack": "nutrition_race_fueling", "score": 0.95},
        {"chunk_id": "b", "text": "跑者膝疼痛", "domain_pack": "medical_risk", "score": 0.60},
        {"chunk_id": "c", "text": "伤病恢复", "evidence_domain": "injury_prevention", "score": 0.58},
    ]

    filtered = filter_hits_for_intent_domain(hits, category="therapist", query="膝盖外侧疼还能跑吗", top_k=2)

    assert [item["chunk_id"] for item in filtered] == ["b", "c"]
    assert all(item["retrieval_domain_match"] == "injury_safety" for item in filtered)


def test_general_query_keeps_original_order_when_no_domain_policy():
    hits = [
        {"chunk_id": "a", "text": "配速", "domain_pack": "training_protocols", "score": 0.9},
        {"chunk_id": "b", "text": "力量", "domain_pack": "action_library", "score": 0.8},
    ]

    filtered = filter_hits_for_intent_domain(hits, category="coach", query="节奏跑怎么跑", top_k=2)

    assert [item["chunk_id"] for item in filtered] == ["a", "b"]
    assert "retrieval_domain_match" not in filtered[0]
