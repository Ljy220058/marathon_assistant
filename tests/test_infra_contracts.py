"""Infrastructure contract tests: startup guards, health check shape, env validation."""

import os
import sys
import importlib


def test_graphrag_api_key_must_not_default_to_dev():
    """knowledge_graph must not accept default_token_for_dev as GRAPHRAG_API_KEY."""
    saved = os.environ.pop("GRAPHRAG_API_KEY", None)
    os.environ["GRAPHRAG_API_KEY"] = "default_token_for_dev"
    try:
        import marathon_qa_assistant.services.knowledge_graph as kg
        importlib.reload(kg)
    except RuntimeError as e:
        assert "GRAPHRAG_API_KEY" in str(e)
        return
    finally:
        if saved is not None:
            os.environ["GRAPHRAG_API_KEY"] = saved
        else:
            os.environ.pop("GRAPHRAG_API_KEY", None)
    raise AssertionError("Expected RuntimeError for dev default token but none was raised")


def test_graphrag_api_key_valid_allows_import():
    """knowledge_graph should import successfully with a valid token."""
    saved = os.environ.pop("GRAPHRAG_API_KEY", None)
    os.environ["GRAPHRAG_API_KEY"] = "ci_test_token"
    try:
        import marathon_qa_assistant.services.knowledge_graph as kg
        importlib.reload(kg)
    except RuntimeError as e:
        raise AssertionError(f"Unexpected RuntimeError with valid token: {e}")
    finally:
        if saved is not None:
            os.environ["GRAPHRAG_API_KEY"] = saved
        else:
            os.environ.pop("GRAPHRAG_API_KEY", None)
