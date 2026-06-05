# Codex Task Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Codex-native task automation layer inside the global `codex-work-team` plugin so Codex can scan Markdown task lists, normalize them into SQLite, plan approved work, update status, write safe Markdown completion notes, and expose everything through MCP.

**Architecture:** Add a focused `todo_automation` Python package under the existing global plugin. Keep the existing `codex_work_team_mcp.py` MCP runtime and register a new `todo-automation` server that delegates to package functions. SQLite is the automation state source; Markdown remains the human-readable source and writeback surface.

**Tech Stack:** Python standard library only (`sqlite3`, `json`, `pathlib`, `re`, `hashlib`, `datetime`, `unittest`), existing stdio MCP shim, global Codex plugin at `C:\Users\26318\plugins\codex-work-team`.

---

## File Structure

Create:

- `C:\Users\26318\plugins\codex-work-team\scripts\todo_automation\__init__.py`: Package exports.
- `C:\Users\26318\plugins\codex-work-team\scripts\todo_automation\models.py`: Dataclasses and allowed status/risk constants.
- `C:\Users\26318\plugins\codex-work-team\scripts\todo_automation\paths.py`: Global data directory and path safety helpers.
- `C:\Users\26318\plugins\codex-work-team\scripts\todo_automation\audit.py`: JSONL audit writer and reader.
- `C:\Users\26318\plugins\codex-work-team\scripts\todo_automation\store.py`: SQLite schema, upsert, query, status, plan, verification storage.
- `C:\Users\26318\plugins\codex-work-team\scripts\todo_automation\scanner.py`: Markdown checkbox scanner with heading context.
- `C:\Users\26318\plugins\codex-work-team\scripts\todo_automation\normalizer.py`: Candidate normalization, stable ID generation, risk and priority inference.
- `C:\Users\26318\plugins\codex-work-team\scripts\todo_automation\planner.py`: Deterministic plan and role recommendation generator.
- `C:\Users\26318\plugins\codex-work-team\scripts\todo_automation\writer.py`: Safe Markdown writeback with source-line guard.
- `C:\Users\26318\plugins\codex-work-team\scripts\todo_automation\mcp_tools.py`: MCP tool definitions and handlers.
- `C:\Users\26318\plugins\codex-work-team\scripts\tests\test_todo_automation.py`: Unit tests using temporary directories.
- `C:\Users\26318\plugins\codex-work-team\skills\codex-todo-automation\SKILL.md`: Skill workflow for using the task automation tools.
- `C:\Users\26318\plugins\codex-work-team\skills\codex-todo-automation\agents\openai.yaml`: UI metadata.

Modify:

- `C:\Users\26318\plugins\codex-work-team\scripts\codex_work_team_mcp.py`: Import task automation tools and register `todo-automation`.
- `C:\Users\26318\plugins\codex-work-team\.mcp.json`: Add `todo-automation` MCP server entry.
- `C:\Users\26318\plugins\codex-work-team\.codex-plugin\plugin.json`: Mention task automation in plugin metadata.

Verification commands:

- `python -m unittest discover -s scripts\tests -p "test_*.py" -v`
- `python -m py_compile scripts\codex_work_team_mcp.py scripts\todo_automation\*.py`
- MCP smoke test through `scripts\codex_work_team_mcp.py --server todo-automation`.

---

### Task 1: Data Models And Paths

**Files:**

- Create: `C:\Users\26318\plugins\codex-work-team\scripts\todo_automation\__init__.py`
- Create: `C:\Users\26318\plugins\codex-work-team\scripts\todo_automation\models.py`
- Create: `C:\Users\26318\plugins\codex-work-team\scripts\todo_automation\paths.py`
- Create: `C:\Users\26318\plugins\codex-work-team\scripts\tests\test_todo_automation.py`

- [ ] **Step 1: Write failing tests for model defaults and data paths**

Add this initial test content to `C:\Users\26318\plugins\codex-work-team\scripts\tests\test_todo_automation.py`:

```python
import tempfile
import unittest
from pathlib import Path

from todo_automation.models import TaskCandidate, TaskRecord, normalize_status, normalize_risk
from todo_automation.paths import data_dir, ensure_data_dir, safe_project_root


class TodoAutomationModelTests(unittest.TestCase):
    def test_task_candidate_preserves_source_location(self):
        candidate = TaskCandidate(
            project_root="C:/project",
            source_file="TODO.md",
            source_line=7,
            checked=False,
            title="落地 RunnerIdentityCard",
            heading_path=["用户画像模块"],
            raw_line="- [ ] 落地 RunnerIdentityCard",
        )

        self.assertEqual(candidate.source_line, 7)
        self.assertEqual(candidate.module, "用户画像模块")
        self.assertEqual(candidate.status_hint, "discovered")

    def test_task_record_status_and_risk_are_normalized(self):
        record = TaskRecord(
            task_id="task_1",
            project_root="C:/project",
            source_file="TODO.md",
            source_line=3,
            title="更新文档",
            module="文档",
            priority="P2",
            status="unknown",
            risk_level="strange",
            source_refs=[],
            acceptance_hint="Markdown task exists",
            verification_hint="Review markdown diff",
            raw_line="- [ ] 更新文档",
            created_at="2026-05-11T00:00:00Z",
            updated_at="2026-05-11T00:00:00Z",
        )

        self.assertEqual(normalize_status(record.status), "discovered")
        self.assertEqual(normalize_risk(record.risk_level), "medium")

    def test_data_dir_can_be_overridden_for_tests(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = data_dir(tmp)
            ensure_data_dir(tmp)
            self.assertEqual(path, Path(tmp))
            self.assertTrue(path.exists())

    def test_safe_project_root_rejects_missing_paths(self):
        with self.assertRaises(ValueError):
            safe_project_root("C:/definitely/missing/project")
```

- [ ] **Step 2: Run tests to verify they fail**

Run from `C:\Users\26318\plugins\codex-work-team`:

```powershell
python -m unittest discover -s scripts\tests -p "test_*.py" -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'todo_automation'`.

- [ ] **Step 3: Create package exports**

Create `C:\Users\26318\plugins\codex-work-team\scripts\todo_automation\__init__.py`:

```python
"""Codex task automation helpers for the codex-work-team plugin."""
```

- [ ] **Step 4: Implement data models**

Create `C:\Users\26318\plugins\codex-work-team\scripts\todo_automation\models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field


STATUSES = {
    "discovered",
    "normalized",
    "planned",
    "ready",
    "in_progress",
    "blocked",
    "verification",
    "done",
    "failed",
    "deferred",
}

RISK_LEVELS = {"low", "medium", "high"}


def normalize_status(value: str | None) -> str:
    text = (value or "").strip()
    return text if text in STATUSES else "discovered"


def normalize_risk(value: str | None) -> str:
    text = (value or "").strip()
    return text if text in RISK_LEVELS else "medium"


@dataclass(frozen=True)
class TaskCandidate:
    project_root: str
    source_file: str
    source_line: int
    checked: bool
    title: str
    heading_path: list[str]
    raw_line: str

    @property
    def module(self) -> str:
        return self.heading_path[-1] if self.heading_path else "未分组"

    @property
    def status_hint(self) -> str:
        return "done" if self.checked else "discovered"


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    project_root: str
    source_file: str
    source_line: int
    title: str
    module: str
    priority: str
    status: str
    risk_level: str
    source_refs: list[str] = field(default_factory=list)
    acceptance_hint: str = ""
    verification_hint: str = ""
    raw_line: str = ""
    created_at: str = ""
    updated_at: str = ""
```

- [ ] **Step 5: Implement path helpers**

Create `C:\Users\26318\plugins\codex-work-team\scripts\todo_automation\paths.py`:

```python
from __future__ import annotations

import os
from pathlib import Path


DEFAULT_DATA_DIR = Path.home() / ".codex" / "todo-automation"


def data_dir(override: str | None = None) -> Path:
    return Path(override).expanduser().resolve() if override else DEFAULT_DATA_DIR


def ensure_data_dir(override: str | None = None) -> Path:
    path = data_dir(override)
    path.mkdir(parents=True, exist_ok=True)
    return path


def sqlite_path(override: str | None = None) -> Path:
    return ensure_data_dir(override) / "todo.sqlite"


def audit_path(override: str | None = None) -> Path:
    return ensure_data_dir(override) / "audit.jsonl"


def safe_project_root(value: str | None) -> Path:
    root = Path(value or os.getcwd()).expanduser().resolve()
    if not root.exists():
        raise ValueError(f"Project root does not exist: {root}")
    if not root.is_dir():
        raise ValueError(f"Project root is not a directory: {root}")
    return root
```

- [ ] **Step 6: Run tests to verify they pass**

Run:

```powershell
python -m unittest discover -s scripts\tests -p "test_*.py" -v
```

Expected: PASS for 4 tests.

---

### Task 2: Markdown Scanner And Normalizer

**Files:**

- Modify: `C:\Users\26318\plugins\codex-work-team\scripts\tests\test_todo_automation.py`
- Create: `C:\Users\26318\plugins\codex-work-team\scripts\todo_automation\scanner.py`
- Create: `C:\Users\26318\plugins\codex-work-team\scripts\todo_automation\normalizer.py`

- [ ] **Step 1: Add failing scanner and normalizer tests**

Append to `test_todo_automation.py`:

```python
from todo_automation.normalizer import normalize_candidates
from todo_automation.scanner import scan_project


class TodoAutomationScannerTests(unittest.TestCase):
    def test_scan_project_finds_markdown_checkboxes_with_headings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "TODO.md").write_text(
                "# Project Tasks\n\n"
                "## 用户画像模块\n\n"
                "- [ ] 落地 RunnerIdentityCard。来源：docs/ui.md\n"
                "- [x] 已完成旧任务\n",
                encoding="utf-8",
            )

            candidates = scan_project(str(root))

            self.assertEqual(len(candidates), 2)
            self.assertEqual(candidates[0].title, "落地 RunnerIdentityCard。来源：docs/ui.md")
            self.assertEqual(candidates[0].module, "用户画像模块")
            self.assertFalse(candidates[0].checked)
            self.assertTrue(candidates[1].checked)

    def test_normalize_candidates_generates_stable_ids_and_risk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "TODO.md").write_text(
                "## API 模块\n\n"
                "- [ ] 修改 API 数据模型并补测试。来源：TECH_REQUIREMENTS_V2.md\n"
                "- [ ] 更新 README 文档说明\n",
                encoding="utf-8",
            )
            records = normalize_candidates(scan_project(str(root)))

            self.assertEqual(len(records), 2)
            self.assertTrue(records[0].task_id.startswith("task_"))
            self.assertEqual(records[0].risk_level, "high")
            self.assertEqual(records[1].risk_level, "low")
            self.assertEqual(records[0].status, "discovered")
            self.assertIn("TECH_REQUIREMENTS_V2.md", records[0].source_refs)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m unittest discover -s scripts\tests -p "test_*.py" -v
```

Expected: FAIL with `ModuleNotFoundError` for `todo_automation.scanner` or `todo_automation.normalizer`.

- [ ] **Step 3: Implement scanner**

Create `scanner.py`:

```python
from __future__ import annotations

import os
import re
from pathlib import Path

from .models import TaskCandidate
from .paths import safe_project_root


TASK_RE = re.compile(r"^\s*[-*]\s+\[(?P<mark>[ xX])\]\s+(?P<title>.+?)\s*$")
HEADING_RE = re.compile(r"^(?P<marks>#{1,6})\s+(?P<title>.+?)\s*$")
SCAN_NAMES = {"TODO.md", "README.md", "AGENTS.md"}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"}


def _iter_markdown_files(root: Path):
    for name in SCAN_NAMES:
        path = root / name
        if path.exists() and path.is_file():
            yield path
    docs = root / "docs"
    if docs.exists():
        for current, dirs, files in os.walk(docs):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for file_name in files:
                if file_name.lower().endswith(".md"):
                    yield Path(current) / file_name


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def scan_project(root_value: str | None = None) -> list[TaskCandidate]:
    root = safe_project_root(root_value)
    candidates: list[TaskCandidate] = []

    for path in _iter_markdown_files(root):
        heading_stack: list[tuple[int, str]] = []
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines, start=1):
            heading_match = HEADING_RE.match(line)
            if heading_match:
                level = len(heading_match.group("marks"))
                title = heading_match.group("title").strip()
                heading_stack = [(l, t) for l, t in heading_stack if l < level]
                heading_stack.append((level, title))
                continue

            task_match = TASK_RE.match(line)
            if not task_match:
                continue
            candidates.append(
                TaskCandidate(
                    project_root=str(root),
                    source_file=_relative(path, root),
                    source_line=line_no,
                    checked=task_match.group("mark").lower() == "x",
                    title=task_match.group("title").strip(),
                    heading_path=[title for _, title in heading_stack],
                    raw_line=line,
                )
            )

    return candidates
```

- [ ] **Step 4: Implement normalizer**

Create `normalizer.py`:

```python
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

from .models import TaskCandidate, TaskRecord


HIGH_RISK_TERMS = ("架构", "api", "数据库", "schema", "依赖", "删除", "跨项目", "git", "迁移", "全局配置")
LOW_RISK_TERMS = ("文档", "readme", "说明", "整理", "记录")
SOURCE_RE = re.compile(r"来源[:：]\s*`?([^`\n。；;]+)`?")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_task_id(candidate: TaskCandidate) -> str:
    raw = "|".join(
        [
            candidate.project_root,
            candidate.source_file,
            str(candidate.source_line),
            candidate.title,
        ]
    )
    return "task_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def infer_priority(title: str) -> str:
    upper = title.upper()
    for priority in ("P0", "P1", "P2"):
        if priority in upper:
            return priority
    return "P2"


def infer_risk(title: str) -> str:
    lower = title.lower()
    if any(term in lower for term in HIGH_RISK_TERMS):
        return "high"
    if any(term in lower for term in LOW_RISK_TERMS):
        return "low"
    return "medium"


def extract_source_refs(title: str) -> list[str]:
    refs: list[str] = []
    for match in SOURCE_RE.finditer(title):
        refs.append(match.group(1).strip())
    return refs


def normalize_candidates(candidates: list[TaskCandidate]) -> list[TaskRecord]:
    now = utc_now()
    records: list[TaskRecord] = []
    for candidate in candidates:
        status = "done" if candidate.checked else "discovered"
        records.append(
            TaskRecord(
                task_id=stable_task_id(candidate),
                project_root=candidate.project_root,
                source_file=candidate.source_file,
                source_line=candidate.source_line,
                title=candidate.title,
                module=candidate.module,
                priority=infer_priority(candidate.title),
                status=status,
                risk_level=infer_risk(candidate.title),
                source_refs=extract_source_refs(candidate.title),
                acceptance_hint="Source Markdown checkbox remains traceable",
                verification_hint="Use project-specific tests or markdown diff review",
                raw_line=candidate.raw_line,
                created_at=now,
                updated_at=now,
            )
        )
    return records
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```powershell
python -m unittest discover -s scripts\tests -p "test_*.py" -v
```

Expected: PASS for model, path, scanner, and normalizer tests.

---

### Task 3: SQLite Store And Audit Log

**Files:**

- Modify: `C:\Users\26318\plugins\codex-work-team\scripts\tests\test_todo_automation.py`
- Create: `C:\Users\26318\plugins\codex-work-team\scripts\todo_automation\audit.py`
- Create: `C:\Users\26318\plugins\codex-work-team\scripts\todo_automation\store.py`

- [ ] **Step 1: Add failing store and audit tests**

Append:

```python
from todo_automation.audit import append_event, read_events
from todo_automation.store import TodoStore


class TodoAutomationStoreTests(unittest.TestCase):
    def test_store_upserts_and_queries_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            (root / "TODO.md").write_text("- [ ] 更新 README 文档说明\n", encoding="utf-8")
            records = normalize_candidates(scan_project(str(root)))

            store = TodoStore(data_root=str(Path(tmp) / "data"))
            store.upsert_tasks(records)
            stored = store.list_tasks(project_root=str(root))

            self.assertEqual(len(stored), 1)
            self.assertEqual(stored[0]["title"], "更新 README 文档说明")
            self.assertEqual(stored[0]["status"], "discovered")

    def test_store_status_update_and_audit_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            (root / "TODO.md").write_text("- [ ] 更新 README 文档说明\n", encoding="utf-8")
            record = normalize_candidates(scan_project(str(root)))[0]

            store = TodoStore(data_root=str(Path(tmp) / "data"))
            store.upsert_tasks([record])
            store.update_status(record.task_id, "ready", "approved for execution")

            updated = store.get_task(record.task_id)
            self.assertEqual(updated["status"], "ready")

    def test_audit_jsonl_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            append_event(
                path,
                project_root="C:/project",
                task_id="task_1",
                event_type="scan",
                actor="test",
                summary="scanned",
                details={"count": 1},
            )

            events = read_events(path, task_id="task_1")
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["details"]["count"], 1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m unittest discover -s scripts\tests -p "test_*.py" -v
```

Expected: FAIL with missing `audit` or `store` modules.

- [ ] **Step 3: Implement audit log**

Create `audit.py`:

```python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def append_event(
    path: Path,
    *,
    project_root: str,
    task_id: str,
    event_type: str,
    actor: str,
    summary: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": _now(),
        "project_root": project_root,
        "task_id": task_id,
        "event_type": event_type,
        "actor": actor,
        "summary": summary,
        "details": details or {},
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def read_events(path: Path, task_id: str | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if task_id is None or event.get("task_id") == task_id:
            events.append(event)
    return events
```

- [ ] **Step 4: Implement SQLite store**

Create `store.py`:

```python
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import TaskRecord, normalize_status
from .paths import audit_path, sqlite_path
from .audit import append_event, read_events


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class TodoStore:
    def __init__(self, data_root: str | None = None):
        self.data_root = data_root
        self.db_path = sqlite_path(data_root)
        self.audit_file = audit_path(data_root)
        self._init_schema()

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def _init_schema(self) -> None:
        with self.connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    project_root TEXT NOT NULL,
                    source_file TEXT NOT NULL,
                    source_line INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    module TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    source_refs_json TEXT NOT NULL,
                    acceptance_hint TEXT NOT NULL,
                    verification_hint TEXT NOT NULL,
                    raw_line TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_root);
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                CREATE TABLE IF NOT EXISTS task_plans (
                    task_id TEXT PRIMARY KEY,
                    plan_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS task_verifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    command_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def upsert_tasks(self, records: list[TaskRecord]) -> None:
        with self.connect() as con:
            for record in records:
                existing = con.execute("SELECT task_id, status, created_at FROM tasks WHERE task_id = ?", (record.task_id,)).fetchone()
                created_at = existing["created_at"] if existing else record.created_at
                status = existing["status"] if existing and existing["status"] != "discovered" else record.status
                con.execute(
                    """
                    INSERT INTO tasks (
                        task_id, project_root, source_file, source_line, title, module, priority,
                        status, risk_level, source_refs_json, acceptance_hint, verification_hint,
                        raw_line, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(task_id) DO UPDATE SET
                        title=excluded.title,
                        module=excluded.module,
                        priority=excluded.priority,
                        risk_level=excluded.risk_level,
                        source_refs_json=excluded.source_refs_json,
                        acceptance_hint=excluded.acceptance_hint,
                        verification_hint=excluded.verification_hint,
                        raw_line=excluded.raw_line,
                        updated_at=excluded.updated_at
                    """,
                    (
                        record.task_id,
                        record.project_root,
                        record.source_file,
                        record.source_line,
                        record.title,
                        record.module,
                        record.priority,
                        status,
                        record.risk_level,
                        json.dumps(record.source_refs, ensure_ascii=False),
                        record.acceptance_hint,
                        record.verification_hint,
                        record.raw_line,
                        created_at,
                        _now(),
                    ),
                )

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["source_refs"] = json.loads(item.pop("source_refs_json"))
        return item

    def list_tasks(
        self,
        *,
        project_root: str | None = None,
        status: str | None = None,
        module: str | None = None,
        risk_level: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        for name, value in (
            ("project_root", project_root),
            ("status", status),
            ("module", module),
            ("risk_level", risk_level),
        ):
            if value:
                clauses.append(f"{name} = ?")
                params.append(value)
        sql = "SELECT * FROM tasks"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY project_root, source_file, source_line"
        with self.connect() as con:
            return [self._row_to_dict(row) for row in con.execute(sql, params).fetchall()]

    def get_task(self, task_id: str) -> dict[str, Any]:
        with self.connect() as con:
            row = con.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        if row is None:
            raise ValueError(f"Task not found: {task_id}")
        return self._row_to_dict(row)

    def update_status(self, task_id: str, status: str, note: str = "", actor: str = "codex") -> dict[str, Any]:
        normalized = normalize_status(status)
        task = self.get_task(task_id)
        with self.connect() as con:
            con.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE task_id = ?", (normalized, _now(), task_id))
        append_event(
            self.audit_file,
            project_root=task["project_root"],
            task_id=task_id,
            event_type="status",
            actor=actor,
            summary=f"status -> {normalized}",
            details={"note": note},
        )
        return self.get_task(task_id)

    def audit(self, task_id: str) -> list[dict[str, Any]]:
        return read_events(self.audit_file, task_id=task_id)
```

- [ ] **Step 5: Run tests**

Run:

```powershell
python -m unittest discover -s scripts\tests -p "test_*.py" -v
```

Expected: PASS.

---

### Task 4: Planner And Markdown Writer

**Files:**

- Modify: `C:\Users\26318\plugins\codex-work-team\scripts\tests\test_todo_automation.py`
- Create: `C:\Users\26318\plugins\codex-work-team\scripts\todo_automation\planner.py`
- Create: `C:\Users\26318\plugins\codex-work-team\scripts\todo_automation\writer.py`

- [ ] **Step 1: Add failing planner and writer tests**

Append:

```python
from todo_automation.planner import build_plan
from todo_automation.writer import writeback_task


class TodoAutomationPlannerWriterTests(unittest.TestCase):
    def test_build_plan_recommends_roles_by_risk_and_module(self):
        task = {
            "task_id": "task_1",
            "title": "落地 ProfileEditor 画像编辑器",
            "module": "用户画像模块",
            "risk_level": "medium",
            "verification_hint": "Use project-specific tests",
        }

        plan = build_plan(task)

        self.assertEqual(plan["task_id"], "task_1")
        self.assertIn("frontend", plan["roles"])
        self.assertIn("reviewer", plan["roles"])
        self.assertEqual(plan["approval_required"], False)

    def test_writeback_checks_source_line_before_modifying(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            todo = root / "TODO.md"
            todo.write_text("- [ ] 更新 README 文档说明\n", encoding="utf-8")
            task = {
                "task_id": "task_1",
                "project_root": str(root),
                "source_file": "TODO.md",
                "source_line": 1,
                "raw_line": "- [ ] 更新 README 文档说明",
            }

            result = writeback_task(task, verification_note="验证：markdown diff review", completed_date="2026-05-11")

            self.assertTrue(result["changed"])
            self.assertIn("- [x] 更新 README 文档说明", todo.read_text(encoding="utf-8"))
            self.assertIn("完成：2026-05-11", todo.read_text(encoding="utf-8"))

    def test_writeback_refuses_when_source_line_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            todo = root / "TODO.md"
            todo.write_text("- [ ] 另一条任务\n", encoding="utf-8")
            task = {
                "task_id": "task_1",
                "project_root": str(root),
                "source_file": "TODO.md",
                "source_line": 1,
                "raw_line": "- [ ] 更新 README 文档说明",
            }

            with self.assertRaises(ValueError):
                writeback_task(task, verification_note="验证：markdown diff review", completed_date="2026-05-11")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m unittest discover -s scripts\tests -p "test_*.py" -v
```

Expected: FAIL with missing `planner` or `writer` modules.

- [ ] **Step 3: Implement planner**

Create `planner.py`:

```python
from __future__ import annotations

from typing import Any


def _roles_for(task: dict[str, Any]) -> list[str]:
    text = f"{task.get('title', '')} {task.get('module', '')}".lower()
    roles = ["coordinator"]
    if any(term in text for term in ("ui", "前端", "卡", "页面", "画像", "表单", "抽屉")):
        roles.append("frontend")
    if any(term in text for term in ("api", "后端", "数据库", "schema", "持久化", "服务")):
        roles.append("backend")
    if any(term in text for term in ("bug", "修复", "异常", "失败", "回归")):
        roles.append("debugger")
    if task.get("risk_level") in {"medium", "high"}:
        roles.append("reviewer")
    return list(dict.fromkeys(roles))


def build_plan(task: dict[str, Any]) -> dict[str, Any]:
    risk = task.get("risk_level", "medium")
    approval_required = risk == "high"
    return {
        "task_id": task["task_id"],
        "title": task["title"],
        "roles": _roles_for(task),
        "approval_required": approval_required,
        "steps": [
            "Inspect source references and related code.",
            "Confirm acceptance and verification hints.",
            "Make the smallest scoped change.",
            "Run the most relevant existing verification.",
            "Update task status and write audit event.",
            "Write back Markdown only after verification passes.",
        ],
        "verification_hint": task.get("verification_hint", "Use project-specific verification"),
        "blocked_reason": "high risk requires user approval" if approval_required else "",
    }
```

- [ ] **Step 4: Implement safe Markdown writer**

Create `writer.py`:

```python
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any


def writeback_task(
    task: dict[str, Any],
    *,
    verification_note: str,
    completed_date: str | None = None,
) -> dict[str, Any]:
    root = Path(task["project_root"]).expanduser().resolve()
    source = (root / task["source_file"]).resolve()
    if not str(source).startswith(str(root)):
        raise ValueError(f"Source file escapes project root: {source}")
    if not source.exists():
        raise ValueError(f"Source file does not exist: {source}")

    lines = source.read_text(encoding="utf-8").splitlines()
    index = int(task["source_line"]) - 1
    if index < 0 or index >= len(lines):
        raise ValueError(f"Source line is out of range: {task['source_line']}")

    current = lines[index]
    expected = task.get("raw_line", "")
    if current.strip() != expected.strip():
        raise ValueError("Source line changed since scan; rescan before writeback")
    if "[x]" in current.lower():
        return {"changed": False, "source_file": str(source), "line": task["source_line"]}
    if "[ ]" not in current:
        raise ValueError("Source line is not an unchecked Markdown task")

    stamp = completed_date or date.today().isoformat()
    suffix = f" 完成：{stamp}；{verification_note}"
    lines[index] = current.replace("[ ]", "[x]", 1) + suffix
    source.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"changed": True, "source_file": str(source), "line": task["source_line"]}
```

- [ ] **Step 5: Run tests**

Run:

```powershell
python -m unittest discover -s scripts\tests -p "test_*.py" -v
```

Expected: PASS.

---

### Task 5: MCP Tool Layer

**Files:**

- Modify: `C:\Users\26318\plugins\codex-work-team\scripts\tests\test_todo_automation.py`
- Create: `C:\Users\26318\plugins\codex-work-team\scripts\todo_automation\mcp_tools.py`
- Modify: `C:\Users\26318\plugins\codex-work-team\scripts\codex_work_team_mcp.py`
- Modify: `C:\Users\26318\plugins\codex-work-team\.mcp.json`

- [ ] **Step 1: Add failing MCP tool tests**

Append:

```python
from todo_automation.mcp_tools import TODO_TOOLS, todo_scan_project, todo_normalize, todo_list, todo_plan, todo_approve, todo_update_status, todo_writeback, todo_audit


class TodoAutomationMcpToolTests(unittest.TestCase):
    def test_mcp_scan_normalize_list_plan_and_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            data = Path(tmp) / "data"
            root.mkdir()
            (root / "TODO.md").write_text("- [ ] 更新 README 文档说明\n", encoding="utf-8")

            scan = todo_scan_project({"root": str(root), "data_root": str(data)})
            normalize = todo_normalize({"root": str(root), "data_root": str(data)})
            listing = todo_list({"root": str(root), "data_root": str(data)})
            task_id = listing["tasks"][0]["task_id"]
            plan = todo_plan({"task_id": task_id, "data_root": str(data)})
            approved = todo_approve({"task_id": task_id, "data_root": str(data)})
            audit = todo_audit({"task_id": task_id, "data_root": str(data)})

            self.assertEqual(scan["candidate_count"], 1)
            self.assertEqual(normalize["task_count"], 1)
            self.assertEqual(plan["plan"]["task_id"], task_id)
            self.assertEqual(approved["task"]["status"], "ready")
            self.assertGreaterEqual(len(audit["events"]), 1)
            self.assertIn("todo_scan_project", [tool["name"] for tool in TODO_TOOLS])

    def test_mcp_update_and_writeback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            data = Path(tmp) / "data"
            root.mkdir()
            (root / "TODO.md").write_text("- [ ] 更新 README 文档说明\n", encoding="utf-8")

            todo_normalize({"root": str(root), "data_root": str(data)})
            task = todo_list({"root": str(root), "data_root": str(data)})["tasks"][0]
            todo_update_status({"task_id": task["task_id"], "status": "done", "note": "verified", "data_root": str(data)})
            result = todo_writeback({"task_id": task["task_id"], "verification_note": "验证：markdown diff review", "data_root": str(data)})

            self.assertTrue(result["result"]["changed"])
            self.assertIn("[x]", (root / "TODO.md").read_text(encoding="utf-8"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m unittest discover -s scripts\tests -p "test_*.py" -v
```

Expected: FAIL with missing `mcp_tools`.

- [ ] **Step 3: Implement MCP handlers**

Create `mcp_tools.py`:

```python
from __future__ import annotations

from typing import Any

from .audit import append_event
from .normalizer import normalize_candidates
from .planner import build_plan
from .scanner import scan_project
from .store import TodoStore
from .writer import writeback_task


def _store(args: dict[str, Any]) -> TodoStore:
    return TodoStore(data_root=args.get("data_root"))


def todo_scan_project(args: dict[str, Any]) -> dict[str, Any]:
    candidates = scan_project(args.get("root"))
    store = _store(args)
    for candidate in candidates:
        append_event(
            store.audit_file,
            project_root=candidate.project_root,
            task_id=f"{candidate.source_file}:{candidate.source_line}",
            event_type="scan",
            actor="codex",
            summary="candidate discovered",
            details={"title": candidate.title},
        )
    return {"candidate_count": len(candidates), "candidates": [candidate.__dict__ for candidate in candidates]}


def todo_normalize(args: dict[str, Any]) -> dict[str, Any]:
    candidates = scan_project(args.get("root"))
    records = normalize_candidates(candidates)
    store = _store(args)
    store.upsert_tasks(records)
    for record in records:
        append_event(
            store.audit_file,
            project_root=record.project_root,
            task_id=record.task_id,
            event_type="normalize",
            actor="codex",
            summary="task normalized",
            details={"status": record.status, "risk_level": record.risk_level},
        )
    return {"task_count": len(records), "tasks": [record.__dict__ for record in records]}


def todo_list(args: dict[str, Any]) -> dict[str, Any]:
    tasks = _store(args).list_tasks(
        project_root=args.get("root"),
        status=args.get("status"),
        module=args.get("module"),
        risk_level=args.get("risk_level"),
    )
    return {"tasks": tasks}


def todo_plan(args: dict[str, Any]) -> dict[str, Any]:
    store = _store(args)
    task = store.get_task(args["task_id"])
    plan = build_plan(task)
    store.update_status(task["task_id"], "planned", "plan generated")
    append_event(
        store.audit_file,
        project_root=task["project_root"],
        task_id=task["task_id"],
        event_type="plan",
        actor="codex",
        summary="execution plan generated",
        details=plan,
    )
    return {"plan": plan}


def todo_approve(args: dict[str, Any]) -> dict[str, Any]:
    task = _store(args).update_status(args["task_id"], "ready", args.get("note", "approved for controlled automation"))
    return {"task": task}


def todo_update_status(args: dict[str, Any]) -> dict[str, Any]:
    task = _store(args).update_status(args["task_id"], args["status"], args.get("note", ""))
    return {"task": task}


def todo_writeback(args: dict[str, Any]) -> dict[str, Any]:
    store = _store(args)
    task = store.get_task(args["task_id"])
    if task["status"] != "done":
        raise ValueError("Only done tasks can be written back")
    result = writeback_task(task, verification_note=args.get("verification_note", "验证：manual review"))
    append_event(
        store.audit_file,
        project_root=task["project_root"],
        task_id=task["task_id"],
        event_type="writeback",
        actor="codex",
        summary="markdown source updated",
        details=result,
    )
    return {"result": result}


def todo_audit(args: dict[str, Any]) -> dict[str, Any]:
    return {"events": _store(args).audit(args["task_id"])}


TODO_TOOLS = [
    {
        "name": "todo_scan_project",
        "description": "Scan Markdown task sources in a project and return task candidates.",
        "inputSchema": {"type": "object", "properties": {"root": {"type": "string"}, "data_root": {"type": "string"}}},
        "handler": todo_scan_project,
    },
    {
        "name": "todo_normalize",
        "description": "Scan and normalize Markdown tasks into the SQLite task store.",
        "inputSchema": {"type": "object", "properties": {"root": {"type": "string"}, "data_root": {"type": "string"}}},
        "handler": todo_normalize,
    },
    {
        "name": "todo_list",
        "description": "List structured tasks with optional filters.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string"},
                "status": {"type": "string"},
                "module": {"type": "string"},
                "risk_level": {"type": "string"},
                "data_root": {"type": "string"},
            },
        },
        "handler": todo_list,
    },
    {
        "name": "todo_plan",
        "description": "Create a deterministic execution plan for a task.",
        "inputSchema": {"type": "object", "required": ["task_id"], "properties": {"task_id": {"type": "string"}, "data_root": {"type": "string"}}},
        "handler": todo_plan,
    },
    {
        "name": "todo_approve",
        "description": "Mark a task as ready for controlled automation.",
        "inputSchema": {"type": "object", "required": ["task_id"], "properties": {"task_id": {"type": "string"}, "note": {"type": "string"}, "data_root": {"type": "string"}}},
        "handler": todo_approve,
    },
    {
        "name": "todo_update_status",
        "description": "Update task status and append an audit event.",
        "inputSchema": {
            "type": "object",
            "required": ["task_id", "status"],
            "properties": {"task_id": {"type": "string"}, "status": {"type": "string"}, "note": {"type": "string"}, "data_root": {"type": "string"}},
        },
        "handler": todo_update_status,
    },
    {
        "name": "todo_writeback",
        "description": "Safely mark a completed Markdown task as checked with a verification note.",
        "inputSchema": {
            "type": "object",
            "required": ["task_id"],
            "properties": {"task_id": {"type": "string"}, "verification_note": {"type": "string"}, "data_root": {"type": "string"}},
        },
        "handler": todo_writeback,
    },
    {
        "name": "todo_audit",
        "description": "Return audit events for a task.",
        "inputSchema": {"type": "object", "required": ["task_id"], "properties": {"task_id": {"type": "string"}, "data_root": {"type": "string"}}},
        "handler": todo_audit,
    },
]
```

- [ ] **Step 4: Register the tool list in the MCP server**

Modify `codex_work_team_mcp.py`:

```python
from todo_automation.mcp_tools import TODO_TOOLS
```

Add to the `TOOLS` dictionary:

```python
    "todo-automation": TODO_TOOLS,
```

No other existing server entries should be changed.

- [ ] **Step 5: Register MCP server in `.mcp.json`**

Add this sibling entry under `mcpServers`:

```json
    "todo-automation": {
      "command": "python",
      "args": [
        "./scripts/codex_work_team_mcp.py",
        "--server",
        "todo-automation"
      ]
    }
```

- [ ] **Step 6: Run tests and py_compile**

Run:

```powershell
python -m unittest discover -s scripts\tests -p "test_*.py" -v
python -m py_compile scripts\codex_work_team_mcp.py scripts\todo_automation\__init__.py scripts\todo_automation\models.py scripts\todo_automation\paths.py scripts\todo_automation\audit.py scripts\todo_automation\store.py scripts\todo_automation\scanner.py scripts\todo_automation\normalizer.py scripts\todo_automation\planner.py scripts\todo_automation\writer.py scripts\todo_automation\mcp_tools.py
```

Expected: all tests PASS and py_compile exits with code 0.

---

### Task 6: Skill And Plugin Metadata

**Files:**

- Create: `C:\Users\26318\plugins\codex-work-team\skills\codex-todo-automation\SKILL.md`
- Create: `C:\Users\26318\plugins\codex-work-team\skills\codex-todo-automation\agents\openai.yaml`
- Modify: `C:\Users\26318\plugins\codex-work-team\.codex-plugin\plugin.json`

- [ ] **Step 1: Create skill directory**

Run:

```powershell
New-Item -ItemType Directory -Force C:\Users\26318\plugins\codex-work-team\skills\codex-todo-automation\agents
```

Expected: directory exists.

- [ ] **Step 2: Write the task automation skill**

Create `SKILL.md`:

```markdown
---
name: codex-todo-automation
description: Global Codex task automation workflow for scanning Markdown TODO lists, normalizing tasks into SQLite, approving controlled automation, planning work, updating task status, writing safe Markdown completion notes, and reviewing audit trails. Use when the user asks Codex to automate TODOs, scan project tasks, execute approved tasks, update task status, or use the todo-automation MCP tools.
---

# Codex Task Automation

## Purpose

Use this skill when Codex needs to operate a project task list through the `todo-automation` MCP tools. Markdown remains the human-readable surface. SQLite is the automation state source.

## Workflow

1. Call `todo_scan_project` for the target project root.
2. Call `todo_normalize` to store structured task records.
3. Call `todo_list` to show the user tasks grouped by module, status, and risk.
4. Ask the user to approve tasks before marking them `ready`.
5. Call `todo_plan` for each approved task.
6. Use `codex-work-team` roles for execution.
7. Run the relevant verification before marking a task `done`.
8. Call `todo_update_status` after every meaningful state transition.
9. Call `todo_writeback` only for tasks with status `done`.
10. Call `todo_audit` when the user asks what happened or when verification fails.

## Controlled Automation Rules

Codex may scan, normalize, plan, run low-risk edits, run existing verification commands, update task state, and write audit events.

Codex must ask before installing dependencies, changing global configuration, deleting files, changing architecture, changing APIs, changing database schemas, doing cross-project edits, or running Git commit/push/PR.

## Status Meanings

- `discovered`: found in Markdown.
- `normalized`: structured in SQLite.
- `planned`: execution plan exists.
- `ready`: user approved controlled execution.
- `in_progress`: Codex is working.
- `blocked`: user decision or missing context needed.
- `verification`: implementation finished and verification is running.
- `done`: verified and eligible for writeback.
- `failed`: execution or verification failed.
- `deferred`: intentionally postponed.
```

- [ ] **Step 3: Write skill UI metadata**

Create `agents/openai.yaml`:

```yaml
interface:
  display_name: "Codex Task Automation"
  short_description: "Scan, plan, execute, verify, and write back project tasks"
  default_prompt: "Use codex-todo-automation to scan this project and list approved automation candidates."
```

- [ ] **Step 4: Update plugin metadata**

In `.codex-plugin/plugin.json`, update:

```json
"description": "Global Codex team workflow with role-based subagent coordination, local MCP tools, and task automation.",
```

Update `keywords` so it includes:

```json
"task-automation"
```

Update `interface.longDescription` so it mentions task automation:

```json
"A local Codex plugin that packages the codex-work-team skill with MCP tools for repository inspection, verification command running, document search, workflow memory, and controlled task automation."
```

- [ ] **Step 5: Validate skill and JSON**

Run:

```powershell
$env:PYTHONUTF8='1'
python C:\Users\26318\.codex\skills\.system\skill-creator\scripts\quick_validate.py C:\Users\26318\plugins\codex-work-team\skills\codex-todo-automation
python -m json.tool C:\Users\26318\plugins\codex-work-team\.codex-plugin\plugin.json > $null
python -m json.tool C:\Users\26318\plugins\codex-work-team\.mcp.json > $null
```

Expected: skill valid and JSON valid.

---

### Task 7: End-to-End MCP Smoke Test

**Files:**

- No source file changes expected.

- [ ] **Step 1: Run todo-automation MCP initialize and tools/list**

Run from `C:\Users\26318\plugins\codex-work-team`:

```powershell
$payload = @(
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}',
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
) -join "`n"
$payload | python .\scripts\codex_work_team_mcp.py --server todo-automation
```

Expected: response id 1 has `serverInfo.name = codex-work-team-todo-automation`; response id 2 lists all eight tools.

- [ ] **Step 2: Run scan and normalize against a fixture project**

Run:

```powershell
$fixture = Join-Path $env:TEMP "codex-todo-fixture"
$data = Join-Path $env:TEMP "codex-todo-data"
Remove-Item -Recurse -Force $fixture,$data -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $fixture | Out-Null
Set-Content -Encoding UTF8 (Join-Path $fixture "TODO.md") "## 文档模块`n`n- [ ] 更新 README 文档说明"
$scan = "{`"jsonrpc`":`"2.0`",`"id`":1,`"method`":`"tools/call`",`"params`":{`"name`":`"todo_normalize`",`"arguments`":{`"root`":`"$($fixture.Replace('\','\\'))`",`"data_root`":`"$($data.Replace('\','\\'))`"}}}}"
$list = "{`"jsonrpc`":`"2.0`",`"id`":2,`"method`":`"tools/call`",`"params`":{`"name`":`"todo_list`",`"arguments`":{`"root`":`"$($fixture.Replace('\','\\'))`",`"data_root`":`"$($data.Replace('\','\\'))`"}}}}"
($scan, $list) | python .\scripts\codex_work_team_mcp.py --server todo-automation
```

Expected: `todo_normalize` reports `task_count: 1`; `todo_list` returns one task with module `文档模块`.

- [ ] **Step 3: Run controlled writeback on the fixture**

Use the task id from Step 2 and run:

```powershell
$taskId = "<task id returned by Step 2>"
$update = "{`"jsonrpc`":`"2.0`",`"id`":3,`"method`":`"tools/call`",`"params`":{`"name`":`"todo_update_status`",`"arguments`":{`"task_id`":`"$taskId`",`"status`":`"done`",`"note`":`"fixture verification passed`",`"data_root`":`"$($data.Replace('\','\\'))`"}}}}"
$write = "{`"jsonrpc`":`"2.0`",`"id`":4,`"method`":`"tools/call`",`"params`":{`"name`":`"todo_writeback`",`"arguments`":{`"task_id`":`"$taskId`",`"verification_note`":`"验证：fixture smoke test`",`"data_root`":`"$($data.Replace('\','\\'))`"}}}}"
($update, $write) | python .\scripts\codex_work_team_mcp.py --server todo-automation
Get-Content -Encoding UTF8 (Join-Path $fixture "TODO.md")
```

Expected: fixture `TODO.md` contains `[x]` and `验证：fixture smoke test`.

- [ ] **Step 4: Scan the real current project without writeback**

Run:

```powershell
$project = "C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手"
$data = Join-Path $env:TEMP "codex-todo-real-scan"
Remove-Item -Recurse -Force $data -ErrorAction SilentlyContinue
$normalize = "{`"jsonrpc`":`"2.0`",`"id`":5,`"method`":`"tools/call`",`"params`":{`"name`":`"todo_normalize`",`"arguments`":{`"root`":`"$($project.Replace('\','\\'))`",`"data_root`":`"$($data.Replace('\','\\'))`"}}}}"
$list = "{`"jsonrpc`":`"2.0`",`"id`":6,`"method`":`"tools/call`",`"params`":{`"name`":`"todo_list`",`"arguments`":{`"root`":`"$($project.Replace('\','\\'))`",`"data_root`":`"$($data.Replace('\','\\'))`"}}}}"
($normalize, $list) | python C:\Users\26318\plugins\codex-work-team\scripts\codex_work_team_mcp.py --server todo-automation
```

Expected: returns structured tasks from the real project. Do not call `todo_writeback` on the real project during this smoke test.

---

## Self-Review Checklist

- Spec coverage: The plan covers scanner, normalizer, SQLite state, audit JSONL, MCP registration, skill workflow, status transitions, safe writeback, and smoke verification.
- Scope control: The plan does not add a Web UI, long-running service, Git automation, dependency installation, or cross-project writeback.
- Type consistency: `TaskCandidate`, `TaskRecord`, `TodoStore`, `TODO_TOOLS`, and MCP handler names are defined before use.
- Verification: Unit tests use temporary directories; real project scan is read-only; writeback is verified only on a fixture.
