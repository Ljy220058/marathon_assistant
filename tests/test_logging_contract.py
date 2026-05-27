"""Contract tests for structured logging middleware."""

import json
import logging


def test_json_formatter_emits_valid_json():
    from marathon_qa_assistant.core.logging_middleware import JSONFormatter

    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=1,
        msg="hello", args=(), exc_info=None,
    )
    record.request_id = "abc-123"
    record.method = "GET"
    record.path = "/health"
    record.status_code = 200
    record.duration_ms = 12.5
    record.client_ip = "127.0.0.1"

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "INFO"
    assert parsed["message"] == "hello"
    assert parsed["request_id"] == "abc-123"
    assert parsed["method"] == "GET"
    assert parsed["path"] == "/health"
    assert parsed["status_code"] == 200
    assert parsed["duration_ms"] == 12.5
    assert parsed["client_ip"] == "127.0.0.1"
    assert "timestamp" in parsed
    # Ensure no extraneous internal keys leak
    assert "exception" not in parsed


def test_formatter_handles_exception():
    from marathon_qa_assistant.core.logging_middleware import JSONFormatter

    formatter = JSONFormatter()
    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="", lineno=1,
            msg="failure", args=(), exc_info=None,
        )
        record.exc_info = (ValueError, ValueError("boom"), None)
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "ERROR"
        assert "exception" in parsed
        assert "boom" in parsed["exception"]
