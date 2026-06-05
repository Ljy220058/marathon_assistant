from pathlib import Path


def test_plan_and_feedback_routers_use_async_db_threadpool_helper():
    root = Path(__file__).parents[1]
    plans_router = (root / "apps" / "backend" / "src" / "marathon_qa_assistant" / "apps" / "routers" / "plans.py").read_text(encoding="utf-8")
    feedback_router = (root / "apps" / "backend" / "src" / "marathon_qa_assistant" / "apps" / "routers" / "feedback.py").read_text(encoding="utf-8")

    assert "from marathon_qa_assistant.apps.async_db import run_db" in plans_router
    assert "from marathon_qa_assistant.apps.async_db import run_db" in feedback_router
    assert "await run_db(" in plans_router
    assert "get_db().save_training_plan" in plans_router
    assert "get_db().get_plan" in plans_router
    assert "get_db().list_events" in plans_router
    assert "await run_db(" in feedback_router
    assert "get_db().save_training_event_feedback" in feedback_router
    assert "get_db().save_feedback_replan" in feedback_router
