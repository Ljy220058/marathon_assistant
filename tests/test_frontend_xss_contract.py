import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FEEDBACK_MODAL = ROOT / "apps" / "web" / "src" / "scripts" / "feedbackModal.js"
CALENDAR_RENDERER = ROOT / "apps" / "web" / "src" / "scripts" / "calendarRenderer.js"


def _run_node(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", "-e", script],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_feedback_modal_escapes_dynamic_html_fields():
    payload = {
        "generation_status": "medical_referral",
        "pre_evaluation_plan": '<script>alert("owned")</script>',
        "prohibited_activities": '<img src=x onerror="alert(1)">',
        "next_day_adjustment": 'javascript:alert("next")',
        "weekly_adjustment": '<svg onload="alert(2)"></svg>',
        "affected_events": [
            {"day_label": '<a href="javascript:alert(3)">Day 2</a>'},
        ],
        "feedback_replan": {
            "patches": [
                {
                    "original": {"main_set": '<img src=x onerror="alert(4)">'},  # nosec B703
                    "suggested": {"main_set": '<script>alert("patch")</script>'},
                }
            ]
        },
    }
    node_script = f"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync({json.dumps(str(FEEDBACK_MODAL))}, "utf8");
const sandbox = {{ window: {{}}, console }};
vm.createContext(sandbox);
vm.runInContext(code, sandbox);
const payload = {json.dumps(payload, ensure_ascii=False)};
const html = sandbox.window.__feedbackModal.buildFeedbackResultHtml(payload);
console.log(JSON.stringify({{ html }}));
"""

    result = _run_node(node_script)
    assert result.returncode == 0, result.stderr
    html = json.loads(result.stdout)["html"]

    assert "<script>" not in html
    assert "<img" not in html
    assert "<svg" not in html
    assert "javascript:alert" not in html
    assert "&lt;script&gt;alert(&quot;owned&quot;)&lt;/script&gt;" in html
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in html
    assert "&lt;a href=&quot;javascript&#058;alert(3)&quot;&gt;Day 2&lt;/a&gt;" in html


def test_calendar_renderer_fallback_escapes_day_card_content():
    response = {
        "monthly_training_calendar": {
            "days": [
                {
                    "day_label": '<img src=x onerror="alert(1)">',
                    "training_type": '<script>alert("run")</script>',
                }
            ]
        }
    }
    node_script = f"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync({json.dumps(str(CALENDAR_RENDERER))}, "utf8");
const calendarEl = {{ innerHTML: "" }};
const sandbox = {{
  window: {{}},
  console,
  document: {{
    getElementById(id) {{
      if (id === "calendar") return calendarEl;
      return null;
    }}
  }}
}};
vm.createContext(sandbox);
vm.runInContext(code, sandbox);
const response = {json.dumps(response, ensure_ascii=False)};
sandbox.window.__calendarRenderer.renderCalendar(response);
console.log(JSON.stringify({{ html: calendarEl.innerHTML }}));
"""

    result = _run_node(node_script)
    assert result.returncode == 0, result.stderr
    html = json.loads(result.stdout)["html"]

    assert "<script>" not in html
    assert "<img" not in html
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in html
    assert "&lt;script&gt;alert(&quot;run&quot;)&lt;/script&gt;" in html
