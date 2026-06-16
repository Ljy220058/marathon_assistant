"""GLM-5.1 compatibility proxy for Hermes.

Hermes sends OpenAI-compatible requests with tool schemas and developer-role
messages. The school GLM endpoint accepts minimal chat requests but returns 500
for the current Hermes tool schema, so this proxy normalizes requests before
forwarding them through the local SSH reverse tunnel.
"""
from __future__ import annotations

from flask import Flask, request, Response
import ast
import json
import os
import re
import requests
from typing import Any

app = Flask(__name__)

# VPS /etc/hosts maps apiai.sztu.edu.cn to 127.0.0.1. Port 14430 is expected to
# be an SSH reverse tunnel from the user's local/campus network to the school API.
UPSTREAM = "https://apiai.sztu.edu.cn:14430"
TIMEOUT = 600
ERROR_LOG = "/tmp/glm_compat_proxy_errors.log"
KANBAN_LOG = "/tmp/glm_compat_proxy_kanban.log"
DEFAULT_MAX_TOKENS = int(os.environ.get("GLM_PROXY_DEFAULT_MAX_TOKENS", "8192"))

# Optional runtime fallback. Prefer passing the key from Hermes config; do not
# bake secrets into this script.
FALLBACK_API_KEY = os.environ.get("SCHOOL_GLM_API_KEY") or os.environ.get("GLM_API_KEY")

DROP_TOP_LEVEL = {
    "tools",
    "tool_choice",
    "parallel_tool_calls",
}
DROP_MESSAGE_FIELDS = {
    "reasoning_content",
    "reasoning",
    "annotations",
    "audio",
    "refusal",
}

KANBAN_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "hermes_kanban_decomposition",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "fanout": {"type": "boolean"},
                "rationale": {"type": "string"},
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "body": {"type": "string"},
                            "assignee": {"type": ["string", "null"]},
                            "parents": {
                                "type": "array",
                                "items": {"type": "integer"},
                            },
                        },
                        "required": ["title", "body", "assignee", "parents"],
                        "additionalProperties": False,
                    },
                },
                "title": {"type": "string"},
                "body": {"type": "string"},
                "assignee": {"type": ["string", "null"]},
            },
            "required": ["fanout", "rationale", "tasks", "title", "body", "assignee"],
            "additionalProperties": False,
        },
    },
}

KANBAN_RETRY_INSTRUCTION = (
    "The previous Kanban decomposer response was invalid. Return ONLY one valid "
    "JSON object. For fanout=true include a non-empty tasks array; every task "
    "must include title, body, assignee, and parents. For fanout=false include "
    "title or body. No markdown, no code fences, no commentary."
)

KANBAN_MARKERS = (
    "Kanban decomposer",
    "Available profiles (assignees you may pick from)",
    "Default assignee (used when no profile fits a task)",
    '"fanout"',
    '"parents"',
)

TOOL_RESULT_LIMIT = int(os.environ.get("GLM_PROXY_TOOL_RESULT_LIMIT", "12000"))
TOOL_ARG_LIMIT = int(os.environ.get("GLM_PROXY_TOOL_ARG_LIMIT", "20000"))

TOOL_BRIDGE_INSTRUCTION = (
    "Tool bridge: if you need to use a tool, do not answer in prose. Return exactly "
    'one tag: <tool_call>{"name":"tool_name","arguments":{}}</tool_call>. '
    "Use valid JSON arguments. After a tool result is shown, continue the task or "
    "request the next tool with the same tag format."
)


def _log(path: str, line: str) -> None:
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif isinstance(item.get("content"), str):
                    parts.append(item["content"])
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    if content is None:
        return ""
    return str(content)


def _extract_tool_specs(body: dict[str, Any]) -> dict[str, dict[str, Any]]:
    tools = body.get("tools")
    if not isinstance(tools, list):
        return {}
    specs: dict[str, dict[str, Any]] = {}
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        fn = tool.get("function")
        if not isinstance(fn, dict):
            continue
        name = fn.get("name")
        if isinstance(name, str) and name:
            specs[name] = fn
    return specs


def _tool_bridge_prompt(tool_specs: dict[str, dict[str, Any]]) -> str:
    lines = [TOOL_BRIDGE_INSTRUCTION, "Available tools:"]
    for name, fn in sorted(tool_specs.items()):
        desc = _content_to_text(fn.get("description")).replace("\n", " ").strip()
        if len(desc) > 180:
            desc = desc[:177] + "..."
        params = fn.get("parameters")
        arg_names = ""
        if isinstance(params, dict):
            props = params.get("properties")
            if isinstance(props, dict) and props:
                arg_names = " args: " + ", ".join(str(k) for k in props.keys())
        lines.append(f"- {name}{arg_names}: {desc}")
    return "\n".join(lines)


def _tool_calls_to_text(tool_calls: Any) -> str:
    if not isinstance(tool_calls, list):
        return ""
    parts: list[str] = []
    for call in tool_calls:
        if not isinstance(call, dict):
            continue
        fn = call.get("function")
        if not isinstance(fn, dict):
            continue
        name = fn.get("name")
        args = fn.get("arguments")
        if isinstance(name, str):
            parts.append(f'<tool_call>{{"name":{json.dumps(name)},"arguments":{args or "{}"}}}</tool_call>')
    return "\n".join(parts)


def _is_kanban_decompose(body: dict[str, Any]) -> bool:
    messages = body.get("messages")
    if not isinstance(messages, list):
        return False
    text_parts: list[str] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if isinstance(content, str):
            text_parts.append(content)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    text_parts.append(item["text"])
    combined = "\n".join(text_parts)
    return any(marker in combined for marker in KANBAN_MARKERS[:3]) and "fanout" in combined


def _extract_json_blob(raw: str) -> dict[str, Any] | None:
    if not raw:
        return None
    stripped = raw.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    first = stripped.find("{")
    last = stripped.rfind("}")
    if first < 0 or last <= first:
        return None
    try:
        value = json.loads(stripped[first:last + 1])
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _normalize_kanban_payload(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    fanout = bool(payload.get("fanout"))
    rationale = payload.get("rationale")
    if not isinstance(rationale, str):
        rationale = ""

    if not fanout:
        title = payload.get("title")
        body = payload.get("body")
        title = title.strip() if isinstance(title, str) else ""
        body = body.strip() if isinstance(body, str) else ""
        if not title and not body:
            return None, "fanout=false missing title/body"
        assignee = payload.get("assignee")
        if not isinstance(assignee, str) or not assignee.strip():
            assignee = None
        return {
            "fanout": False,
            "rationale": rationale,
            "tasks": [],
            "title": title,
            "body": body,
            "assignee": assignee,
        }, "ok"

    raw_tasks = payload.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        return None, "fanout=true missing tasks"

    tasks: list[dict[str, Any]] = []
    for idx, item in enumerate(raw_tasks):
        if not isinstance(item, dict):
            return None, f"tasks[{idx}] is not an object"
        title = item.get("title")
        if not isinstance(title, str) or not title.strip():
            return None, f"tasks[{idx}].title missing"
        body = item.get("body")
        if not isinstance(body, str):
            body = ""
        assignee = item.get("assignee")
        if not isinstance(assignee, str) or not assignee.strip():
            assignee = None
        parents = item.get("parents")
        if not isinstance(parents, list):
            parents = []
        clean_parents = [
            p for p in parents
            if isinstance(p, int) and 0 <= p < len(raw_tasks) and p != idx
        ]
        tasks.append({
            "title": title.strip()[:200],
            "body": body.strip(),
            "assignee": assignee,
            "parents": clean_parents,
        })

    return {
        "fanout": True,
        "rationale": rationale,
        "tasks": tasks,
        "title": "",
        "body": "",
        "assignee": None,
    }, "ok"


def _validated_kanban_content(resp: requests.Response) -> tuple[str | None, str]:
    try:
        envelope = resp.json()
    except ValueError:
        return None, "upstream response is not JSON"
    try:
        content = envelope["choices"][0]["message"].get("content") or ""
    except Exception:
        return None, "missing choices[0].message.content"
    parsed = _extract_json_blob(content)
    if parsed is None:
        return None, "message content is not a JSON object"
    normalized, reason = _normalize_kanban_payload(parsed)
    if normalized is None:
        return None, reason
    envelope["choices"][0]["message"]["content"] = json.dumps(
        normalized,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return json.dumps(envelope, ensure_ascii=False).encode("utf-8").decode("utf-8"), "ok"


def _downgrade_to_json_object(data: bytes) -> bytes:
    try:
        body = json.loads(data.decode("utf-8"))
    except Exception:
        return data
    if isinstance(body, dict):
        body["response_format"] = {"type": "json_object"}
    return json.dumps(body, ensure_ascii=False).encode("utf-8")


def _add_kanban_retry_instruction(data: bytes) -> bytes:
    try:
        body = json.loads(data.decode("utf-8"))
    except Exception:
        return data
    if isinstance(body, dict):
        body["response_format"] = {"type": "json_object"}
        body["temperature"] = 0
        body["stream"] = False
        messages = body.get("messages")
        if isinstance(messages, list):
            messages.append({"role": "user", "content": KANBAN_RETRY_INSTRUCTION})
    return json.dumps(body, ensure_ascii=False).encode("utf-8")


def _coerce_tool_arg(value: ast.AST) -> Any:
    try:
        return ast.literal_eval(value)
    except Exception:
        if isinstance(value, ast.Name):
            lowered = value.id.lower()
            if lowered == "true":
                return True
            if lowered == "false":
                return False
            if lowered in {"none", "null"}:
                return None
        return None


def _parse_function_style_tool_call(raw: str) -> tuple[str, dict[str, Any]] | None:
    text = raw.strip()
    text = re.split(r"</?tool_call>", text, maxsplit=1)[0].strip()
    text = re.sub(r"</?[^>]+>", "", text).strip()
    text = text.strip("`[] \t\r\n")
    # GLM sometimes adds stray punctuation between the tool name and the
    # argument list, e.g. kanban_show`() or kanban_show]().
    text = re.sub(r"^([A-Za-z_][A-Za-z0-9_]*)[^A-Za-z0-9_\s(]+(?=\s*\()", r"\1", text)
    match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?:\((.*)\))?\s*$", text, re.S)
    if not match:
        first_name = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)", text)
        if first_name:
            return first_name.group(1), {}
        return None
    name = match.group(1)
    arg_text = (match.group(2) or "").strip()
    if not arg_text:
        return name, {}
    if len(arg_text) > TOOL_ARG_LIMIT:
        arg_text = arg_text[:TOOL_ARG_LIMIT]
    try:
        expr = ast.parse(f"_f({arg_text})", mode="eval")
    except SyntaxError:
        # Do not execute malformed large file-writing calls. A truncated
        # write_file(...) is worse than no call; let the model try again.
        if name in {"write_file", "edit_file"}:
            return None
        return name, {"input": arg_text}
    call = expr.body
    if not isinstance(call, ast.Call):
        return name, {}
    args: dict[str, Any] = {}
    if call.args:
        values = [_coerce_tool_arg(arg) for arg in call.args]
        args["args"] = values
    for kw in call.keywords:
        if kw.arg:
            args[kw.arg] = _coerce_tool_arg(kw.value)
    return name, args


def _extract_text_tool_calls(content: str, tool_specs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    if "<tool_call>" not in content:
        return []
    valid_names = set(tool_specs)
    calls: list[dict[str, Any]] = []
    for fragment in re.split(r"<tool_call>", content)[1:]:
        fragment = fragment.split("</tool_call>", 1)[0].strip()
        if not fragment:
            continue
        parsed: tuple[str, dict[str, Any]] | None = None
        if fragment.startswith("{"):
            try:
                value = json.loads(fragment)
            except json.JSONDecodeError:
                value = None
            if isinstance(value, dict) and isinstance(value.get("name"), str):
                args = value.get("arguments")
                parsed = (value["name"], args if isinstance(args, dict) else {})
        if parsed is None:
            parsed = _parse_function_style_tool_call(fragment)
        if parsed is None:
            continue
        name, args = parsed
        if valid_names and name not in valid_names:
            continue
        calls.append({
            "id": f"call_glm_{len(calls) + 1}",
            "type": "function",
            "function": {
                "name": name,
                "arguments": json.dumps(args, ensure_ascii=False),
            },
        })
    return calls


def _adapt_text_tool_call_response(resp: requests.Response, tool_specs: dict[str, dict[str, Any]]) -> bytes | None:
    if not tool_specs:
        return None
    try:
        data = resp.json()
    except Exception:
        return None
    choices = data.get("choices")
    if not isinstance(choices, list):
        return None
    changed = False
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, str):
            continue
        calls = _extract_text_tool_calls(content, tool_specs)
        if not calls:
            continue
        message["content"] = None
        message["tool_calls"] = calls
        choice["finish_reason"] = "tool_calls"
        changed = True
    if not changed:
        return None
    _log(KANBAN_LOG, "adapted text tool_call response")
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


def normalize_body(raw: bytes, tool_specs: dict[str, dict[str, Any]] | None = None) -> tuple[bytes, bool]:
    if not raw:
        return raw, False
    try:
        body = json.loads(raw.decode("utf-8"))
    except Exception:
        return raw, False
    if not isinstance(body, dict):
        return raw, False

    # Force GLM model and non-thinking mode to avoid reasoning fields in history.
    body["model"] = "glm-5.1"
    body["chat_template_kwargs"] = {"enable_thinking": False}
    if not isinstance(body.get("max_tokens"), int) or body.get("max_tokens", 0) <= 0:
        body["max_tokens"] = DEFAULT_MAX_TOKENS

    # Current school GLM route 500s on Hermes' generated tool schema. Strip it
    # for text-only WeChat recovery; Kanban tool support can be reintroduced later.
    for key in DROP_TOP_LEVEL:
        body.pop(key, None)

    tool_specs = tool_specs or {}
    messages = body.get("messages")
    if isinstance(messages, list):
        normalized = []
        if tool_specs:
            normalized.append({"role": "system", "content": _tool_bridge_prompt(tool_specs)})
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            msg = dict(msg)
            if msg.get("role") == "developer":
                msg["role"] = "system"
            if msg.get("role") == "tool":
                content = _content_to_text(msg.get("content"))
                if len(content) > TOOL_RESULT_LIMIT:
                    content = content[:TOOL_RESULT_LIMIT] + "\n...[tool result truncated]"
                name = msg.get("name") or msg.get("tool_call_id") or "tool"
                normalized.append({
                    "role": "user",
                    "content": f"Tool result from {name}:\n{content}",
                })
                continue
            for key in DROP_MESSAGE_FIELDS:
                msg.pop(key, None)
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                existing = _content_to_text(msg.get("content"))
                calls_text = _tool_calls_to_text(msg.get("tool_calls"))
                msg["content"] = "\n".join(part for part in [existing, calls_text] if part)
                msg.pop("tool_calls", None)
            else:
                msg.pop("tool_calls", None)
            normalized.append(msg)
        body["messages"] = normalized

    is_kanban = _is_kanban_decompose(body)
    if is_kanban:
        body["response_format"] = KANBAN_RESPONSE_FORMAT
        body["temperature"] = 0
        body["stream"] = False

    return json.dumps(body, ensure_ascii=False).encode("utf-8"), is_kanban


def upstream_request(path: str, headers: dict[str, str], data: bytes) -> requests.Response:
    return requests.request(
        method=request.method,
        url=f"{UPSTREAM}/{path}",
        headers=headers,
        data=data,
        timeout=TIMEOUT,
        allow_redirects=False,
    )


def _has_usable_bearer(headers: dict[str, str]) -> bool:
    auth = headers.get("Authorization") or headers.get("authorization") or ""
    if not auth.startswith("Bearer "):
        return False
    return bool(auth.removeprefix("Bearer ").strip())


@app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def proxy(path: str):
    headers = {k: v for k, v in request.headers if k.lower() != "host"}
    if FALLBACK_API_KEY and not _has_usable_bearer(headers):
        headers["Authorization"] = f"Bearer {FALLBACK_API_KEY}"
    raw = request.get_data()
    tool_specs: dict[str, dict[str, Any]] = {}
    try:
        original_body = json.loads(raw.decode("utf-8")) if raw else {}
        if isinstance(original_body, dict):
            tool_specs = _extract_tool_specs(original_body)
    except Exception:
        tool_specs = {}
    data, is_kanban = normalize_body(raw, tool_specs)

    resp = upstream_request(path, headers, data)

    if is_kanban and resp.status_code in {400, 422, 500}:
        _log(KANBAN_LOG, f"schema request failed status={resp.status_code}; retrying with json_object")
        data = _downgrade_to_json_object(data)
        resp = upstream_request(path, headers, data)

    if is_kanban and resp.status_code == 200:
        content, reason = _validated_kanban_content(resp)
        if content is None:
            _log(KANBAN_LOG, f"validation failed: {reason}; retrying once")
            retry_data = _add_kanban_retry_instruction(data)
            resp = upstream_request(path, headers, retry_data)
            if resp.status_code == 200:
                content, reason = _validated_kanban_content(resp)
        if content is not None:
            excluded = {"content-encoding", "transfer-encoding", "connection", "content-length"}
            resp_headers = [(k, v) for k, v in resp.raw.headers.items() if k.lower() not in excluded]
            _log(KANBAN_LOG, "validated kanban response")
            return Response(content.encode("utf-8"), resp.status_code, resp_headers)
        _log(KANBAN_LOG, f"validation failed after retry: {reason}")
        return Response(
            json.dumps({"error": "invalid_kanban_json", "detail": reason}, ensure_ascii=False),
            502,
            [("Content-Type", "application/json")],
        )

    if resp.status_code >= 400:
        _log(ERROR_LOG, f"[{resp.status_code}] {path} request={data[:1000]!r} response={resp.text[:1000]!r}\n---")

    excluded = {"content-encoding", "transfer-encoding", "connection", "content-length"}
    resp_headers = [(k, v) for k, v in resp.raw.headers.items() if k.lower() not in excluded]
    if resp.status_code == 200 and not is_kanban:
        adapted = _adapt_text_tool_call_response(resp, tool_specs)
        if adapted is not None:
            return Response(adapted, resp.status_code, resp_headers)
    return Response(resp.content, resp.status_code, resp_headers)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=18180, debug=False)
