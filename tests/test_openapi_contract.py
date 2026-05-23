from marathon_qa_assistant.apps import api_app


def test_openapi_exposes_core_training_plan_endpoints():
    spec = api_app.app.openapi()

    paths = spec["paths"]
    assert "/query" in paths
    assert "/feedback" in paths
    assert "/plans/{plan_id}" in paths

    query_post = paths["/query"]["post"]
    feedback_post = paths["/feedback"]["post"]
    plan_get = paths["/plans/{plan_id}"]["get"]

    assert query_post["responses"]["200"]["content"]["application/json"]["schema"]
    assert feedback_post["responses"]["200"]["content"]["application/json"]["schema"]
    assert plan_get["responses"]["200"]["content"]["application/json"]["schema"]


def test_openapi_uses_named_schemas_for_public_contracts():
    spec = api_app.app.openapi()
    schemas = spec["components"]["schemas"]

    expected = {
        "QueryRequest",
        "QueryResponse",
        "FeedbackRequest",
        "FeedbackResponse",
        "PlanDetailResponse",
        "OpsMetricsResponse",
        "SavePlanRequest",
        "TrainingCalendarResponse",
        "DayDetailResponse",
        "ZoneReference",
    }
    assert expected.issubset(schemas)


def test_openapi_response_schemas_match_shared_delivery_contract():
    spec = api_app.app.openapi()
    schemas = spec["components"]["schemas"]

    assert set(schemas["FeedbackResponse"]["required"]) >= {
        "workout_feedback",
        "risk_gate",
        "protocol_recheck",
        "adaptive_feedback",
        "adaptive_adjustment",
        "plan_diff",
        "generation_status",
    }
    assert set(schemas["PlanDetailResponse"]["required"]) >= {
        "plan",
        "structured_training_plan",
        "events",
        "execution_status_summary",
        "adjustment_history",
    }
    assert "training_plan_review" in schemas["QueryResponse"]["properties"]
    assert "training_plan_review" in schemas["PlanDetailResponse"]["properties"]
    assert "training_plan_review" in schemas["TrainingCalendarResponse"]["properties"]
    assert "answer_source_mode" in schemas["QueryResponse"]["properties"]
    assert "rag_health" in schemas["QueryResponse"]["properties"]
    assert "evidence_chain" in schemas["QueryResponse"]["properties"]
    assert "evidence_chain" in schemas["PlanDetailResponse"]["properties"]
    assert "evidence_chain" in schemas["TrainingCalendarResponse"]["properties"]
    assert set(schemas["OpsMetricsResponse"]["required"]) >= {
        "requests_total",
        "errors_total",
        "generation_status_counts",
        "feedback_risk_reason_counts",
        "plan_generation_duration_buckets",
        "medical_referral_total",
    }
    assert "request_route_counts" in schemas["OpsMetricsResponse"]["properties"]
    assert "llm_provider_error_counts" in schemas["OpsMetricsResponse"]["properties"]


def test_evidence_tier_reference_exposes_evidence_drawer_contract():
    import asyncio

    payload = asyncio.run(api_app.get_evidence_tier_reference())

    assert payload["evidence_drawer_contract"]["display_modes"] == [
        "verified_source",
        "model_general_knowledge",
        "needs_evidence",
        "graph_hint",
        "legacy_explanation",
        "rejected_source",
    ]
    assert payload["evidence_drawer_contract"]["answer_source_modes"] == [
        "verified_rag",
        "model_general_knowledge",
        "needs_evidence",
        "medical_referral",
        "structured_plan_rule",
    ]
    assert "source_registry_id" in payload["evidence_drawer_contract"]["expert_only_fields"]
    assert "expert_metadata" in payload["evidence_drawer_contract"]["expert_only_fields"]
    assert payload["core_prescription_permissions"]["allowed_domains"] == ["protocol", "action_library"]
    assert payload["core_prescription_permissions"]["required_permission"] == "can_write_core"
