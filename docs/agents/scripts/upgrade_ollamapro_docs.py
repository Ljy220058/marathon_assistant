from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
KH_ROOT = Path(r"C:\Users\26318\KnowledgeHub\01_Projects\OllamaPro")
INDEX_PATH = KH_ROOT / "99_索引" / "OllamaPro索引.md"
BACKUP_ROOT = KH_ROOT / "99_索引" / "doc_upgrade_2026-06-04_backup"
TASKLIST_PATH = REPO_ROOT / "docs" / "agents" / "ollamapro-doc-upgrade-tasklist.md"
REPORT_PATH = REPO_ROOT / "docs" / "agents" / "ollamapro-doc-upgrade-report.md"
MARKER_START = "<!-- OLLAMAPRO_DOC_UPGRADE_START -->"
MARKER_END = "<!-- OLLAMAPRO_DOC_UPGRADE_END -->"


@dataclass
class TargetDoc:
    name: str
    path: Path
    rel_dir: str
    size: int
    doc_type: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def strip_upgrade_block(text: str) -> str:
    pattern = re.compile(
        rf"\n?{re.escape(MARKER_START)}.*?{re.escape(MARKER_END)}\n?",
        re.DOTALL,
    )
    return pattern.sub("\n", text).rstrip() + "\n"


def extract_frontmatter_title(text: str, fallback: str) -> str:
    if text.startswith("---"):
        match = re.match(r"---\n(.*?)\n---", text, re.DOTALL)
        if match:
            for line in match.group(1).splitlines():
                if line.strip().startswith("title:"):
                    return line.split(":", 1)[1].strip().strip('"')
    heading = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return heading.group(1).strip() if heading else fallback


def wiki_links(text: str) -> list[str]:
    links = []
    for match in re.finditer(r"\[\[([^\]]+)\]\]", text):
        value = match.group(1).split("|", 1)[0].strip()
        if value and value not in links:
            links.append(value)
    return links


def headings(text: str) -> list[str]:
    result = []
    for line in text.splitlines():
        if line.startswith("#"):
            result.append(line.strip())
    return result[:12]


def local_paths(text: str) -> list[str]:
    patterns = [
        r"(?:apps|tests|docs|tools|data|configs|scripts|packages|research|archive)[\\/][A-Za-z0-9_\-./\\\u4e00-\u9fff]+",
    ]
    found: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            candidate = match.group(0).rstrip("`。，、；;:)）]")
            if candidate not in found:
                found.append(candidate)
    return found[:16]


def rel_exists(path: str) -> bool:
    return (REPO_ROOT / path.replace("/", "\\")).exists()


def add_existing(candidates: list[str], *paths: str) -> None:
    for path in paths:
        normalized = path.replace("\\", "/")
        if normalized not in candidates and rel_exists(normalized):
            candidates.append(normalized)


def keyword_hit(name: str, *keywords: str) -> bool:
    lower = name.lower()
    return any(keyword.lower() in lower for keyword in keywords)


def inferred_sources(target: TargetDoc, original_text: str) -> list[str]:
    candidates: list[str] = []
    for path in local_paths(original_text):
        normalized = path.replace("\\", "/")
        if rel_exists(normalized):
            candidates.append(normalized)

    name = target.name
    doc_type = target.doc_type
    add_existing(
        candidates,
        "apps/backend/src/marathon_qa_assistant/apps/api_app.py",
        "apps/backend/src/marathon_qa_assistant/apps/schemas.py",
        "apps/backend/src/marathon_qa_assistant/apps/response_builders.py",
    )

    if keyword_hit(name, "Query"):
        add_existing(candidates, "apps/backend/src/marathon_qa_assistant/apps/routers/query.py", "apps/web/src/scripts/apiClient.js")
    if keyword_hit(name, "Plans", "计划", "训练计划", "日历"):
        add_existing(candidates, "apps/backend/src/marathon_qa_assistant/apps/routers/plans.py", "apps/backend/src/marathon_qa_assistant/services/daily_schedule_generator.py")
    if keyword_hit(name, "Feedback", "反馈"):
        add_existing(candidates, "apps/backend/src/marathon_qa_assistant/apps/routers/feedback.py", "apps/web/src/scripts/feedbackModal.js")
    if keyword_hit(name, "Profile", "画像", "用户"):
        add_existing(candidates, "apps/backend/src/marathon_qa_assistant/apps/routers/profile.py", "apps/backend/src/marathon_qa_assistant/core/profile_store.py", "apps/web/src/scripts/profileState.js")
    if keyword_hit(name, "Reference", "证据", "知识源", "Chunks"):
        add_existing(candidates, "apps/backend/src/marathon_qa_assistant/apps/routers/reference.py", "apps/backend/src/marathon_qa_assistant/services/kb/evidence_chain.py", "apps/web/src/scripts/evidenceDrawer.js")
    if keyword_hit(name, "Health", "Admin", "Ops", "健康", "运维", "日志", "观测"):
        add_existing(candidates, "apps/backend/src/marathon_qa_assistant/core/observability.py", "apps/backend/src/marathon_qa_assistant/core/logging_middleware.py", "apps/backend/src/marathon_qa_assistant/apps/security/response_role.py")
    if keyword_hit(name, "FastAPI", "API总览", "API分层", "认证"):
        add_existing(candidates, "apps/backend/src/marathon_qa_assistant/apps/routers/_shared.py", "apps/backend/src/marathon_qa_assistant/apps/response_projection.py")
    if keyword_hit(name, "Astro", "前端", "工作台"):
        add_existing(candidates, "apps/web/src/pages/index.astro", "apps/web/src/scripts/app.js", "apps/web/src/scripts/apiClient.js")
    if keyword_hit(name, "日历"):
        add_existing(candidates, "apps/web/src/scripts/calendarRenderer.js", "apps/web/src/styles/calendar.css")
    if keyword_hit(name, "状态面板"):
        add_existing(candidates, "apps/web/src/scripts/statusPanel.js", "apps/web/src/styles/status-panel.css")
    if keyword_hit(name, "证据抽屉"):
        add_existing(candidates, "apps/web/src/scripts/evidenceDrawer.js", "apps/web/src/styles/evidence.css")
    if keyword_hit(name, "LangGraph", "Workflow", "系统结构", "端到端"):
        add_existing(candidates, "apps/backend/src/marathon_qa_assistant/core/workflow.py", "apps/backend/src/marathon_qa_assistant/core/workflow_graph.py", "apps/backend/src/marathon_qa_assistant/core/state_models.py")
    if keyword_hit(name, "security_gate"):
        add_existing(candidates, "apps/backend/src/marathon_qa_assistant/nodes/security.py", "apps/backend/src/marathon_qa_assistant/services/security_guards.py")
    if keyword_hit(name, "router节点", "router"):
        add_existing(candidates, "apps/backend/src/marathon_qa_assistant/nodes/router.py", "apps/backend/src/marathon_qa_assistant/nodes/routing/__init__.py")
    if keyword_hit(name, "profile与retrieval", "retrieval"):
        add_existing(candidates, "apps/backend/src/marathon_qa_assistant/nodes/profile_and_retrieval.py", "apps/backend/src/marathon_qa_assistant/services/vector_store.py")
    if keyword_hit(name, "planner_executor", "planner", "executor"):
        add_existing(candidates, "apps/backend/src/marathon_qa_assistant/nodes/plan_nodes.py", "apps/backend/src/marathon_qa_assistant/core/training_plan_skeleton.py")
    if keyword_hit(name, "coach", "nutritionist", "therapist", "critic", "auditor"):
        add_existing(candidates, "apps/backend/src/marathon_qa_assistant/nodes/expert_nodes.py", "apps/backend/src/marathon_qa_assistant/nodes/output_nodes.py")
    if keyword_hit(name, "formatter", "guided"):
        add_existing(candidates, "apps/backend/src/marathon_qa_assistant/nodes/output_nodes.py")
    if keyword_hit(name, "missing_info", "adaptive"):
        add_existing(candidates, "apps/backend/src/marathon_qa_assistant/nodes/profile_and_retrieval.py", "apps/backend/src/marathon_qa_assistant/core/state_models.py")
    if keyword_hit(name, "FAISS", "向量", "RAG", "KB_Runtime", "KB与RAG", "KB_"):
        add_existing(candidates, "apps/backend/src/marathon_qa_assistant/services/vector_store.py", "apps/backend/src/marathon_qa_assistant/services/kb/runtime_v2.py", "apps/backend/src/marathon_qa_assistant/core/kb_bootstrap.py")
    if keyword_hit(name, "KnowledgeGraph", "图谱"):
        add_existing(candidates, "apps/backend/src/marathon_qa_assistant/services/knowledge_graph.py", "apps/backend/src/marathon_qa_assistant/services/kb/graph_evidence.py")
    if keyword_hit(name, "OllamaEmbeddings", "LLM_Provider"):
        add_existing(candidates, "apps/backend/src/marathon_qa_assistant/nodes/common.py", "apps/backend/src/marathon_qa_assistant/core/settings.py")
    if keyword_hit(name, "SQLite", "运行时状态"):
        add_existing(candidates, "apps/backend/src/marathon_qa_assistant/services/database.py", "apps/backend/src/marathon_qa_assistant/apps/async_db.py")
    if doc_type == "runbook":
        add_existing(candidates, ".env.example", "apps/backend/requirements-runtime.txt", "apps/web/package.json")

    return candidates[:18]


def inferred_tests(target: TargetDoc) -> list[str]:
    tests: list[str] = []
    name = target.name
    add_existing(tests, "tests/test_import_smoke.py")
    if target.doc_type == "api" or keyword_hit(name, "API", "Query", "Plans", "Feedback", "Profile", "Reference"):
        add_existing(tests, "tests/test_openapi_contract.py", "tests/test_api_app.py", "tests/test_api_cli_startup_contract.py")
    if keyword_hit(name, "Query"):
        add_existing(tests, "tests/test_answer_contract_v2.py", "tests/test_plan_query_classifier.py")
    if keyword_hit(name, "Plans", "计划", "日历"):
        add_existing(tests, "tests/test_training_calendar_persistence.py", "tests/test_daily_schedule_generator.py", "tests/test_training_plan_skeleton.py")
    if keyword_hit(name, "Feedback", "反馈"):
        add_existing(tests, "tests/test_plan_workflow_expectations.py", "tests/test_working_state_audit_loop.py")
    if keyword_hit(name, "Profile", "画像", "用户"):
        add_existing(tests, "tests/test_profile_field_gating.py", "tests/test_profile_context_filter.py")
    if keyword_hit(name, "前端", "Astro", "工作台", "日历", "状态", "证据抽屉"):
        add_existing(tests, "tests/test_astro_frontend_contract.py", "tests/test_frontend_xss_contract.py", "apps/web/tests/frontend-scripts.test.mjs")
    if keyword_hit(name, "RAG", "KB", "FAISS", "知识源", "Chunks", "证据"):
        add_existing(tests, "tests/test_kb_v2_runtime_contract.py", "tests/test_kb_health.py", "tests/test_evidence_chain_contract.py", "tests/test_kb_source_registry.py")
    if keyword_hit(name, "安全", "security", "医疗", "认证"):
        add_existing(tests, "tests/test_security_guards.py", "tests/test_answer_card_safety.py", "tests/test_provider_secret_contract.py", "tests/test_response_trace_boundary.py")
    if keyword_hit(name, "LangGraph", "Workflow", "节点", "router"):
        add_existing(tests, "tests/test_router_behavior.py", "tests/integration_workflow_test.py", "tests/test_state_models.py")
    if keyword_hit(name, "日志", "观测", "Health", "Admin", "Ops", "健康"):
        add_existing(tests, "tests/test_observability_contract.py", "tests/test_health_contract.py", "tests/test_logging_contract.py")
    if keyword_hit(name, "运行", "本地", "发布", "回滚", "环境变量"):
        add_existing(tests, "tests/test_settings_contract.py", "tests/test_backend_packaging_contract.py", "tests/test_api_cli_startup_contract.py")
    return tests[:10]


def inferred_project_docs(target: TargetDoc) -> list[str]:
    docs: list[str] = []
    add_existing(
        docs,
        "README.md",
        "docs/architecture/backend_technical_overview.md",
        "docs/architecture/TECH_REQUIREMENTS_V2.md",
        "docs/adr/2026-06-02-auth-and-expert-response-boundary.md",
        "docs/adr/2026-06-02-faiss-trusted-loader-boundary.md",
        "docs/adr/2026-06-02-production-persistence-boundary.md",
    )
    if keyword_hit(target.name, "观测", "日志", "Ops", "Health"):
        add_existing(docs, "docs/architecture/observability_baseline.md")
    if keyword_hit(target.name, "测试", "验证", "发布"):
        add_existing(docs, "docs/architecture/testing_and_delivery_governance.md")
    if keyword_hit(target.name, "系统结构", "LangGraph", "节点"):
        add_existing(docs, "docs/architecture/workflow_node_glossary.md")
    return docs[:8]


def markdown_list(items: list[str], empty: str) -> str:
    if not items:
        return f"- {empty}"
    return "\n".join(f"- `{item}`" for item in items)


def source_status_table(items: list[str]) -> str:
    if not items:
        return "| 路径 | 状态 |\n|---|---|\n| 待补充 | 未推断到 canonical source |"
    lines = ["| 路径 | 状态 | 用途 |", "|---|---|---|"]
    for item in items:
        status = "存在" if rel_exists(item) else "待确认"
        purpose = source_purpose(item)
        lines.append(f"| `{item}` | {status} | {purpose} |")
    return "\n".join(lines)


def source_purpose(item: str) -> str:
    if "/routers/" in item:
        return "API 路由与请求处理"
    if item.endswith("schemas.py"):
        return "请求/响应 DTO 契约"
    if "response_builders" in item or "response_projection" in item:
        return "响应组装与角色投影"
    if "/nodes/" in item:
        return "工作流节点逻辑"
    if "/services/kb/" in item or "vector_store" in item or "knowledge_graph" in item:
        return "知识库、证据或图谱服务"
    if "/core/" in item:
        return "核心状态、配置或运行时边界"
    if "/apps/web/" in item or item.startswith("apps/web/"):
        return "前端页面、脚本或样式"
    if item.startswith("tests/") or "/tests/" in item:
        return "自动化验证"
    return "项目依据"


def route_summary(source_paths: list[str]) -> str:
    rows = []
    for item in source_paths:
        path = REPO_ROOT / item.replace("/", "\\")
        if not path.exists() or not item.endswith(".py"):
            continue
        text = read_text(path)
        for method, route in re.findall(r"@(?:router|app)\.(get|post|put|patch|delete)\(\s*['\"]([^'\"]+)['\"]", text):
            rows.append((method.upper(), route, item))
    if not rows:
        return "- 未从推断源码中解析到 FastAPI decorator；需要人工对照 router 文件补充。"
    lines = ["| Method | Path | Source |", "|---|---|---|"]
    for method, route, source in rows[:12]:
        lines.append(f"| `{method}` | `{route}` | `{source}` |")
    return "\n".join(lines)


def validation_commands(target: TargetDoc, tests: list[str]) -> str:
    commands = []
    python_tests = [test for test in tests if test.startswith("tests/")]
    frontend_tests = [test for test in tests if test.startswith("apps/web/")]
    if python_tests:
        tests_arg = " ".join(python_tests[:5])
        commands.append(f"$env:PYTHONPATH=\"apps/backend/src\"; python -m pytest {tests_arg} -q")
    if target.doc_type == "frontend_module" or frontend_tests:
        commands.append("cd apps/web; npm test")
    if target.doc_type == "api":
        commands.append("$env:PYTHONPATH=\"apps/backend/src\"; python -m pytest tests/test_openapi_contract.py tests/test_api_app.py -q")
    if target.doc_type == "runbook":
        commands.append("$env:PYTHONPATH=\"apps/backend/src\"; python -m uvicorn marathon_qa_assistant.apps.api_app:app --host 127.0.0.1 --port 8000")
        commands.append("cd apps/web; npm run dev")
    if not commands:
        commands.append("$env:PYTHONPATH=\"apps/backend/src\"; python -m pytest tests/test_import_smoke.py -q")
    return "\n".join(f"- `{cmd}`" for cmd in dict.fromkeys(commands))


def deep_detail_sections(target: TargetDoc, title: str, sources: list[str], tests: list[str], docs: list[str]) -> str:
    source_table = source_status_table(sources)
    test_list = markdown_list(tests, "未推断到专属测试；至少保留 import smoke 和人工审阅。")
    doc_list = markdown_list(docs, "未推断到额外项目文档。")
    commands = validation_commands(target, tests)
    if target.doc_type == "api":
        contract = route_summary(sources)
        return f"""### Canonical source map
{source_table}

### API 字段与行为细化
{contract}

- 请求字段以 `QueryRequest`、`SavePlanRequest`、`FeedbackRequest`、`ProfileRequest` 等 schema 为准；本文后续人工补充时应把字段用途、默认值、缺失处理和前端来源写到表格里。
- 响应字段要区分：业务可见结果、证据链、RAG/KB 健康、训练日历、调试 trace、专家/管理员投影字段。
- 认证和角色投影需要同时检查普通 runner、expert/admin、未认证本地开发三种路径。

### 失败模式与恢复
- `401/403`：优先检查 API token、expert token、公共白名单和 response role。
- `429`：检查写类请求是否命中 rate limit prefix。
- `503/504`：区分生产配置缺失、LLM workflow 超时、KB/DB/Ollama 降级和 router 内部异常。
- plan-like 请求失败时，应确认是否回退到 skeleton-first，而不是让前端长时间空等。

### 测试映射
{test_list}

### 建议验证命令
{commands}

### 相关项目依据
{doc_list}
"""
    if target.doc_type == "runbook":
        return f"""### Canonical source map
{source_table}

### 运行步骤细化
- 后端：确认 `.env.example`、`settings.py`、依赖文件和 `PYTHONPATH=apps/backend/src` 后启动 FastAPI。
- 前端：确认 `apps/web/package.json`、API base、端口探测和中文路径兼容脚本。
- 健康：先访问 `/health`，再按需要访问 `/admin/health`、`/ops/metrics`、KB governance 摘要。
- 降级：LLM、KB、DB、Ollama 任一不可用时，需要区分“可用但降级”和“阻断发布”的状态。

### 故障模式
- 配置缺失：生产模式缺少 API token、Fernet key 或专家 token 时不得静默通过。
- 端口冲突：FastAPI 与 Astro 端口变化后要同步前端 API base。
- KB 失败：优先看 runtime manifest、source registry、quarantine、FAISS trusted loader 边界。
- 数据写入失败：先确认 SQLite 持久化边界和 runtime data 路径，不直接删除用户数据。

### 测试映射
{test_list}

### 建议验证命令
{commands}

### 相关项目依据
{doc_list}
"""
    if target.doc_type == "requirement_process":
        return f"""### Canonical source map
{source_table}

### 用户故事与成功标准
- 用户故事：作为跑者/训练计划使用者，我希望该流程能把画像、目标、训练状态或问题转成可理解、可追踪、可调整的结果。
- 成功标准：前端有明确状态，后端有结构化字段，证据或风险边界可见，失败时有下一步动作。
- 非目标：不提供医学诊断、不承诺比赛成绩、不把 LLM 通用知识当作核心处方证据、不默认支持未实现的多用户生产隔离。

### 流程状态细化
- `ready`：输入足够，生成结构化结果或明确回答。
- `needs_user_info`：画像、目标或上下文字段不足，前端应引导补齐。
- `needs_evidence`：核心处方证据不足，允许解释但不升级为已验证训练安排。
- `risk_refused/medical_referral`：医疗红旗或高风险反馈触发阻断。
- `degraded`：KB/LLM/DB 部分不可用但仍能提供受限结果。

### 测试映射
{test_list}

### 建议验证命令
{commands}

### 相关项目依据
{doc_list}
"""
    if target.doc_type == "frontend_module":
        return f"""### Canonical source map
{source_table}

### 前端职责细化
- 输入层：只收集用户画像、问题、计划操作和反馈，不自行编造后端字段。
- 渲染层：优先消费结构化响应；Markdown 或文本仅作为兜底展示。
- 状态层：必须区分加载中、空状态、部分生成、失败、鉴权失败、服务降级。
- 证据层：证据抽屉、日卡、解释面板应显示 source/page/chunk/evidence tier，不伪造引用编号。

### UI 失败模式
- API 不可达：展示本地服务连接失败和当前 API base。
- 字段缺失：显示可读空态，不让 undefined/null 进入界面。
- 长文本/移动端：避免遮挡训练日历、反馈按钮和证据入口。
- XSS/HTML：后端返回文本渲染前需要经过约束或转义。

### 测试映射
{test_list}

### 建议验证命令
{commands}

### 相关项目依据
{doc_list}
"""
    if target.doc_type == "data_asset":
        return f"""### Canonical source map
{source_table}

### 数据生命周期细化
- 生成：说明数据由 API、workflow、KB 构建脚本、用户反馈或前端提交产生。
- 存储：区分 SQLite、JSON/JSONL、FAISS index、runtime manifest、source registry 和测试 fixture。
- 消费：标明前端、API、workflow、测试或治理报告读取哪些字段。
- 治理：缺 source/page/chunk_id、权限越界或证据层级不一致时进入 review、quarantine 或 release gate。

### 数据风险
- 用户画像和训练反馈属于隐私敏感数据，文档中不得暴露真实 token 或个人记录。
- 可重建索引和持久化事实要分开，避免误删 source registry 或训练计划。
- 核心处方字段必须能追溯到 protocol/action library/KB evidence 或显式标为 `needs_evidence`。

### 测试映射
{test_list}

### 建议验证命令
{commands}

### 相关项目依据
{doc_list}
"""
    if target.doc_type == "langgraph_node":
        return f"""### Canonical source map
{source_table}

### 节点输入输出细化
- 输入：`IntegratedState`、用户画像、问题意图、检索证据、风险标记、上游专家输出。
- 输出：写回结构化字段、路由标记、证据上下文、审计信息、guided questions 或前端展示字段。
- 下游影响：节点输出可能影响 formatter、critic/auditor、response builder、训练日历和证据抽屉。
- 安全边界：节点不能绕过 security gate、医疗红旗、secret/prompt 风险和证据权限。

### 节点失败模式
- LLM 不可用：走 fallback 或返回可见降级状态。
- 检索为空：保留 `needs_evidence` 或一般解释边界。
- 画像缺失：进入 missing info 流程。
- 风险触发：进入阻断、降级或 medical referral，而不是继续生成高强度建议。

### 测试映射
{test_list}

### 建议验证命令
{commands}

### 相关项目依据
{doc_list}
"""
    if target.doc_type == "test_verification":
        return f"""### Canonical source map
{source_table}

### 测试目标细化
- 契约类：保护 API schema、DTO 字段、响应投影、前端消费字段不漂移。
- 安全类：保护输入/输出守卫、医疗红旗、token、secret 和证据权限。
- 数据类：保护 source registry、KB runtime、SQLite、FAISS 和 evidence chain 不丢字段。
- UI 类：保护 Astro 脚本、状态面板、日历、反馈、证据抽屉和 XSS 处理。

### 测试映射
{test_list}

### 建议验证命令
{commands}

### 相关项目依据
{doc_list}
"""
    if target.doc_type == "project_state":
        return f"""### Canonical source map
{source_table}

### 当前状态细化
- 当前项目事实应以 OllamaPro 仓库、KnowledgeHub 当前索引、ADR 和近期质量/运行态审计为准。
- 历史 Marathon_Assistant 材料只用于解释迁移背景，不能覆盖当前 FastAPI/Astro/KB v2 架构。
- 若 README、旧架构文档和源码不一致，优先核对源码、ADR 和测试。

### 需要持续澄清的状态
- 生产就绪：需要配置、认证、持久化、观测、回滚和安全测试共同支撑。
- 科学有效性：训练处方质量需要专家审计和基准测试，不由文档直接背书。
- 多用户边界：只记录当前实现，不推断未完成的隔离能力。

### 测试映射
{test_list}

### 建议验证命令
{commands}

### 相关项目依据
{doc_list}
"""
    return f"""### Canonical source map
{source_table}

### 架构职责细化
- 入口：说明该层从 API、workflow、前端、KB 构建脚本或测试进入。
- 处理：说明该层拥有的核心决策、状态转换、数据结构或服务边界。
- 输出：说明该层向下游暴露哪些字段、对象、事件或持久化结果。
- 回退：说明依赖缺失、配置缺失、证据不足、LLM/KB 不可用时如何 fail-visible。

### 依赖与风险
- 依赖方向应保持单向，避免 UI、API、workflow、KB 服务互相循环引用。
- 结构化字段优先于 Markdown 文本，训练处方字段优先受 protocol/action library/evidence 约束。
- 涉及生产路径时，应同步配置、认证、日志、metrics 和回滚说明。

### 测试映射
{test_list}

### 建议验证命令
{commands}

### 相关项目依据
{doc_list}
"""


def classify(path: Path, name: str) -> str:
    rel = str(path.relative_to(KH_ROOT))
    if "00_项目中枢" in rel:
        return "project_state"
    if "01_需求与范围" in rel:
        return "requirement_process"
    if "02_页面与交互" in rel:
        return "frontend_module"
    if "04_数据与资产" in rel:
        return "data_asset"
    if "06_API与流程" in rel or "API" in name:
        return "api"
    if "07_运行与维护" in rel or "Runbook" in name or "发布" in name or "回滚" in name:
        return "runbook"
    if "08_限制与验证" in rel or "测试" in name or "验证" in name:
        return "test_verification"
    if "节点" in name:
        return "langgraph_node"
    return "architecture_layer"


def doc_type_label(doc_type: str) -> str:
    return {
        "project_state": "项目状态文档",
        "requirement_process": "需求/流程文档",
        "frontend_module": "前端模块文档",
        "data_asset": "数据资产文档",
        "api": "API 文档",
        "runbook": "运行维护文档",
        "test_verification": "测试验证文档",
        "langgraph_node": "LangGraph 节点文档",
        "architecture_layer": "架构/技术层文档",
    }[doc_type]


def discover_targets() -> list[TargetDoc]:
    text = read_text(INDEX_PATH)
    raw_links = sorted(
        {
            match.group(1).split("|", 1)[0].strip()
            for match in re.finditer(r"\[\[([^\]]+)\]\]", text)
        }
    )
    all_md = [
        p
        for p in KH_ROOT.rglob("*.md")
        if BACKUP_ROOT not in p.parents and p != INDEX_PATH
    ]
    by_stem: dict[str, list[Path]] = {}
    for path in all_md:
        by_stem.setdefault(path.stem, []).append(path)

    missing: list[str] = []
    duplicates: dict[str, list[str]] = {}
    targets: list[TargetDoc] = []
    for link in raw_links:
        if link.endswith("/") or link.startswith(".."):
            continue
        matches = by_stem.get(link, [])
        if not matches:
            missing.append(link)
            continue
        if len(matches) > 1:
            duplicates[link] = [str(p) for p in matches]
            continue
        path = matches[0]
        rel_dir = str(path.parent.relative_to(KH_ROOT))
        targets.append(
            TargetDoc(
                name=link,
                path=path,
                rel_dir=rel_dir,
                size=path.stat().st_size,
                doc_type=classify(path, link),
            )
        )
    if missing or duplicates:
        raise RuntimeError(
            json.dumps(
                {"missing": missing, "duplicates": duplicates},
                ensure_ascii=False,
                indent=2,
            )
        )
    return targets


def backup_targets(targets: list[TargetDoc]) -> list[dict[str, object]]:
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    entries = []
    for target in targets:
        rel = target.path.relative_to(KH_ROOT)
        backup_path = BACKUP_ROOT / rel
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        if not backup_path.exists():
            shutil.copy2(target.path, backup_path)
        backup_size = backup_path.stat().st_size
        entries.append(
            {
                "name": target.name,
                "doc_type": target.doc_type,
                "source_path": str(target.path),
                "backup_path": str(backup_path),
                "relative_path": str(rel),
                "size_before": backup_size,
                "sha256_before": sha256(backup_path),
            }
        )
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_index": str(INDEX_PATH),
        "target_count": len(targets),
        "backup_root": str(BACKUP_ROOT),
        "entries": entries,
    }
    write_text(BACKUP_ROOT / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return entries


def evidence_lines(paths: list[str]) -> list[str]:
    lines = []
    for raw in paths[:10]:
        normalized = raw.replace("/", "\\")
        exists = (REPO_ROOT / normalized).exists()
        status = "存在" if exists else "待确认"
        lines.append(f"- `{raw}`：{status}。")
    return lines


def type_sections(target: TargetDoc, title: str) -> str:
    label = doc_type_label(target.doc_type)
    common_intro = (
        f"本文作为 `{label}`，服务于后续需求澄清、实现排期、代码审查和验收。"
        "阅读时应优先区分三类信息：已经由源码或现有文档支撑的事实、本文根据命名和上下文做出的推断、仍需要运行验证的假设。"
    )
    if target.doc_type == "api":
        return f"""### 读者与用途
{common_intro}本页重点帮助前端、后端和测试人员确认 API 能力边界、字段契约和调用风险。

### 接口契约补充
- Method、Path、认证、限流和错误返回应以 `apps/backend/src/marathon_qa_assistant/apps/routers/*`、`schemas.py`、`response_builders.py` 与 OpenAPI 测试为准。
- 请求字段需要说明用途、默认值、缺失时行为、前端传入来源，以及是否会改变训练计划或只产生解释性回答。
- 响应字段需要区分用户可见字段、专家/管理员可见字段、调试字段和证据链字段。
- 写类接口需要明确幂等性、重复提交、限流、鉴权失败和数据持久化失败时的表现。

### 前端消费与状态
- 标明调用方脚本，例如 `apiClient.js`、日历渲染、反馈弹窗、证据抽屉或状态面板。
- 前端应分别处理 loading、empty、partial、error、auth failed 和 degraded response。
- 若接口返回 `evidence_chain`、`rag_health`、`training_calendar` 或 `daily_schedule_cards`，文档应说明字段优先级和回退顺序。
"""
    if target.doc_type == "runbook":
        return f"""### 读者与用途
{common_intro}本页重点帮助开发者和维护者按固定顺序启动、诊断、降级和恢复系统。

### 操作顺序
1. 先确认当前工作目录、Python/Node 依赖和必要环境变量。
2. 再启动 FastAPI 后端，确认 `/health` 或相关健康检查返回可解释状态。
3. 后启动 Astro 前端，确认前端 API base URL 与后端端口一致。
4. 最后执行最小 smoke check，并记录失败阶段、日志位置和可回滚操作。

### 故障定位
- 配置缺失优先看 `.env.example`、`settings.py`、`app_state.py` 和生产配置 guard。
- KB 或 FAISS 问题优先看 source registry、runtime manifest、quarantine/health 摘要。
- API 鉴权问题优先看普通 API token、专家 token、公共白名单和响应投影边界。
- 前端异常优先看 `apiClient.js`、浏览器 network、状态面板和契约测试。
"""
    if target.doc_type == "requirement_process":
        return f"""### 读者与用途
{common_intro}本页重点帮助产品、前端、后端和测试人员把用户目标映射为可验证的流程状态。

### 需求拆解
- 用户目标：说明用户进入该流程前想完成什么，以及完成后应获得什么明确结果。
- 触发条件：说明入口按钮、API 请求、画像状态、计划状态或反馈状态如何触发流程。
- 成功标准：说明前端可见结果、后端状态变更、证据展示和审计字段。
- 非目标：明确不承诺医学诊断、教练人工审核、付费训练营、真实设备生理负荷或未实现的多用户隔离。

### 状态与分支
- 正常路径应写清用户输入、系统处理、展示结果和下一步动作。
- 缺失信息、证据不足、风险拦截、生成失败和降级运行应作为显式分支，而不是隐藏在自由文本里。
"""
    if target.doc_type == "frontend_module":
        return f"""### 读者与用途
{common_intro}本页重点帮助前端维护者理解模块职责、DOM/API 依赖和异常状态。

### 前端实现边界
- 模块应只承担渲染、交互收集、状态展示和 API 调用协调，不应自行推断训练处方或伪造证据。
- DOM 选择器、事件绑定、状态字段和后端响应字段需要在文档中保持可追踪。
- 对 loading、empty、partial、error、degraded、auth failed 状态都应给出用户可见处理策略。

### 验收重点
- 桌面和移动端布局不应遮挡关键训练信息、证据入口和反馈操作。
- 前端契约测试应覆盖 API 字段、XSS/HTML 转义、证据抽屉和状态面板显示。
"""
    if target.doc_type == "data_asset":
        return f"""### 读者与用途
{common_intro}本页重点帮助后端、数据治理和测试人员确认数据来源、生命周期和持久化边界。

### 数据治理补充
- 写清数据所有者、生成入口、读取入口、持久化位置、重建方式和清理策略。
- 区分运行态缓存、持久化事实、导出报告、测试 fixture 和可重建索引。
- 对用户画像、训练反馈、证据片段、source registry 和 SQLite 边界，应明确隐私、可追溯性和回滚影响。

### 质量门槛
- 核心处方字段不得由无证据文本直接覆盖。
- 缺 source、缺 page、缺 chunk_id 或 evidence tier 不一致时，应进入治理或 quarantine 路径。
"""
    if target.doc_type == "langgraph_node":
        return f"""### 读者与用途
{common_intro}本页重点帮助工作流维护者理解节点输入、输出、状态变更和路由影响。

### 节点契约补充
- 输入：说明节点消费的 `IntegratedState` 字段、用户画像、检索结果、风险标记或上游节点输出。
- 输出：说明节点写回的字段、下游节点依赖、结构化报告影响和前端可见结果。
- 路由：说明节点通过、拦截、降级、追问或转入下一专家节点的条件。
- 安全：说明 prompt/secret/medical risk/evidence boundary 的处理责任。

### 失败模式
- 依赖缺失、LLM 不可用、检索为空、画像不完整和风险拦截都应 fail-visible。
"""
    if target.doc_type == "test_verification":
        return f"""### 读者与用途
{common_intro}本页重点帮助测试和实现人员把约束转成可运行的检查。

### 验证边界
- 区分单元测试、契约测试、集成 smoke、前端静态检查和人工验收。
- 文档中的命令只作为建议命令；没有实际运行时不得写成已通过。
- 每个测试应说明它保护的业务风险，例如 API schema 漂移、证据链丢失、医疗风险越界或前端状态失真。
"""
    if target.doc_type == "project_state":
        return f"""### 读者与用途
{common_intro}本页重点帮助新接手者快速判断当前项目真实状态、历史混淆点和可信边界。

### 状态判断规则
- 当前事实优先来自 OllamaPro 真实仓库、KnowledgeHub 当前目录和 2026-06-02 之后的 ADR/审计材料。
- 历史 Marathon_Assistant Flask/Jinja/SQLite 项目只能作为迁移背景，不能当作当前实现。
- 若源码、测试、文档互相冲突，应标注冲突并把源码和最近 ADR 作为优先核验对象。
"""
    return f"""### 读者与用途
{common_intro}本页重点帮助工程人员理解技术层职责、依赖方向和降级边界。

### 架构补充
- 写清入口模块、核心服务、主要数据结构、下游依赖和前端/API 暴露面。
- 标明哪些职责属于该层，哪些应交给相邻层或治理流程处理。
- 对 fallback、配置缺失、依赖不可用、证据不足和生产模式差异，应给出明确处理原则。
"""


def build_upgrade_block(target: TargetDoc, original_text: str) -> str:
    title = extract_frontmatter_title(original_text, target.name)
    links = wiki_links(original_text)
    heading_list = headings(original_text)
    sources = inferred_sources(target, original_text)
    tests = inferred_tests(target)
    project_docs = inferred_project_docs(target)
    evidence = evidence_lines(sources)
    evidence_text = "\n".join(evidence) if evidence else "- 本次自动升级未从正文提取到明确源码路径；后续应按本文主题补充 canonical source。"
    links_text = "\n".join(f"- [[{link}]]" for link in links[:10]) if links else "- 暂无明确 Obsidian 关联链接。"
    headings_text = "\n".join(f"- `{h}`" for h in heading_list[:10]) if heading_list else "- 未提取到标题结构。"
    sections = type_sections(target, title).rstrip()
    deep_sections = deep_detail_sections(target, title, sources, tests, project_docs).rstrip()
    task_order = task_order_for(target.doc_type)
    caution = caution_for(target.doc_type)

    return f"""
{MARKER_START}
## 详细技术文档升级

### 文档定位
- 标题：`{title}`
- 文档类型：{doc_type_label(target.doc_type)}
- 实际路径：`{target.path}`
- 索引来源：`{INDEX_PATH}`
- 本次升级方式：保留原文，在当前文件内追加可替换的详细技术文档块。

{sections}

{deep_sections}

### 事实依据与证据等级
- `文档确认`：本文保留了原有结论、依据、限制和关联文档。
- `源码确认`：下列路径来自正文抽取、标题推断和项目结构映射，存在性仅表示路径当前可定位，不等同于行为已运行验证。
{evidence_text}
- `测试确认`：本次只建立测试映射并执行结构校验；未启动 FastAPI/Astro，也未运行业务测试全集。
- `待实测`：除非原文已经写明测试命令和结果，本次升级不声明接口、UI 或工作流已在运行态通过。

### 原有结构快照
{headings_text}

### 关联文档
{links_text}

### 后续任务顺序
{task_order}

### 注意事项
{caution}

### 质量自检
- [x] 保留 frontmatter 与原有正文。
- [x] 使用证据等级区分事实、推断和待验证事项。
- [x] 明确后续 task 顺序，方便继续实施。
- [x] 未把训练建议、医学安全或生产就绪状态写成未验证承诺。

{MARKER_END}
"""


def task_order_for(doc_type: str) -> str:
    mapping = {
        "api": """1. 对照 router 和 schema 补全 Method、Path、请求字段、响应字段和错误码。
2. 对照前端 `apiClient.js` 与相关模块补全消费点和状态处理。
3. 对照 `tests/test_openapi_contract.py`、API router 测试或前端契约测试补验证命令。
4. 若字段涉及认证、专家响应投影或证据链，补充越权和脱敏检查。""",
        "runbook": """1. 先列出前置环境、端口、环境变量和启动命令。
2. 再列出健康检查、日志位置、常见失败和诊断顺序。
3. 补充降级/回滚步骤，并说明哪些操作会改写持久化数据。
4. 用最小 smoke check 验证 Runbook 是否可执行。""",
        "requirement_process": """1. 确认用户角色、入口、目标和完成判定。
2. 补全主路径、缺失信息路径、风险拦截路径和失败恢复路径。
3. 映射到 API、前端模块、数据字段和测试用例。
4. 把未实现能力写入非目标或待办，避免产品范围漂移。""",
        "frontend_module": """1. 对照前端脚本确认 DOM 入口、事件、API 调用和状态字段。
2. 补 loading、empty、partial、error 和 degraded 状态。
3. 对照契约测试或浏览器 smoke 测试补验收点。
4. 检查移动端和长文本场景，避免遮挡训练日历、证据入口和反馈操作。""",
        "data_asset": """1. 确认数据生成入口、消费入口、持久化位置和重建方式。
2. 标注 source、page、chunk、user_id、plan_id 等关键字段的可信边界。
3. 补治理、quarantine、备份、清理和隐私注意事项。
4. 用数据契约测试或 fixture 检查字段完整性。""",
        "langgraph_node": """1. 对照节点实现确认输入 state、输出 state 和下游依赖。
2. 标注路由条件、失败模式、降级行为和安全责任。
3. 补 evidence、profile、risk、guided question 等跨节点字段的传递关系。
4. 用节点级或 workflow 契约测试确认状态不漂移。""",
        "test_verification": """1. 把测试目标映射到具体风险：schema 漂移、证据缺失、安全越界或 UI 状态异常。
2. 对照现有 `tests/` 文件补命令和覆盖范围。
3. 标注哪些检查是自动化，哪些仍需人工验收。
4. 把失败时的定位入口写清楚。""",
        "project_state": """1. 先核对 README、ADR、审计报告和当前索引的一致性。
2. 标出当前真实实现、历史遗留实现和未迁移材料。
3. 对冲突信息给出优先核验顺序。
4. 把低置信度结论转成后续验证 task。""",
        "architecture_layer": """1. 对照源码入口确认该层的边界和依赖方向。
2. 补全数据流、调用链、fallback 和配置边界。
3. 映射到 API、前端、测试和运维影响。
4. 对跨层风险增加 ADR 或测试建议。""",
    }
    return mapping[doc_type]


def caution_for(doc_type: str) -> str:
    common = [
        "- 不把历史 Marathon_Assistant 项目中的 Flask/Jinja/SQLite 实现当作当前 OllamaPro 事实。",
        "- 不把未运行的命令写成已通过；只写建议验证命令或待验证项。",
        "- 涉及训练处方、伤病、医疗红旗和安全门控时，保持辅助建议边界。",
    ]
    if doc_type == "api":
        common.append("- API 字段变更需要同步 OpenAPI、前端消费点和契约测试。")
    if doc_type == "frontend_module":
        common.append("- 前端不得用本地兜底文本伪造证据来源或核心训练处方。")
    if doc_type == "data_asset":
        common.append("- 数据清理、重建和迁移操作需要先确认是否影响用户画像、计划和证据追溯。")
    return "\n".join(common)


def upgrade_docs(targets: list[TargetDoc]) -> None:
    for target in targets:
        text = read_text(target.path)
        base = strip_upgrade_block(text)
        block = build_upgrade_block(target, base)
        write_text(target.path, base.rstrip() + "\n\n" + block.lstrip())


def tasklist(targets: list[TargetDoc], entries: list[dict[str, object]]) -> str:
    by_name = {entry["name"]: entry for entry in entries}
    groups: dict[str, list[TargetDoc]] = {}
    for target in targets:
        groups.setdefault(target.rel_dir, []).append(target)

    lines = [
        "# OllamaPro 文档升级任务清单",
        "",
        f"- 生成时间：{datetime.now().isoformat(timespec='seconds')}",
        f"- 索引文件：`{INDEX_PATH}`",
        f"- 目标文档数：{len(targets)}",
        f"- 备份目录：`{BACKUP_ROOT}`",
        "- 范围：仅索引中可递归匹配到的 Markdown 子文档；跳过目录链接和历史 Marathon 引用。",
        "",
        "## 执行批次",
        "",
        "1. 项目状态总览：`00_项目中枢`。",
        "2. 需求流程：`01_需求与范围`。",
        "3. 技术栈、架构和 LangGraph 节点：`05_技术栈与架构`。",
        "4. API：`06_API与流程`。",
        "5. 前端、数据、测试、运维：`02_页面与交互`、`04_数据与资产`、`08_限制与验证`、`07_运行与维护`。",
        "",
        "## 文档清单",
        "",
    ]
    for group in sorted(groups):
        lines.append(f"### {group}")
        lines.append("")
        lines.append("| 状态 | 文档 | 类型 | 实际路径 | 备份 | 注意事项 |")
        lines.append("|---|---|---|---|---|---|")
        for target in sorted(groups[group], key=lambda item: item.name):
            entry = by_name[target.name]
            caution = "已补 canonical source、测试映射、失败模式和验收命令；运行结果仍需执行后填写"
            lines.append(
                f"| 已细化 | `{target.name}` | {doc_type_label(target.doc_type)} | `{target.path}` | `{entry['backup_path']}` | {caution} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def verify(targets: list[TargetDoc]) -> dict[str, object]:
    failures: list[dict[str, str]] = []
    stems: dict[str, str] = {}
    for target in targets:
        text = read_text(target.path)
        if not text.startswith("---"):
            failures.append({"file": str(target.path), "issue": "missing frontmatter"})
        if not re.search(r"^#\s+", text, re.MULTILINE):
            failures.append({"file": str(target.path), "issue": "missing h1"})
        if MARKER_START not in text or MARKER_END not in text:
            failures.append({"file": str(target.path), "issue": "missing upgrade marker"})
        if "[[]]" in text:
            failures.append({"file": str(target.path), "issue": "empty wiki link"})
        if "\ufffd" in text:
            failures.append({"file": str(target.path), "issue": "replacement character found"})
        previous = stems.get(target.name)
        if previous:
            failures.append({"file": str(target.path), "issue": f"duplicate target stem with {previous}"})
        stems[target.name] = str(target.path)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_count": len(targets),
        "failure_count": len(failures),
        "failures": failures,
    }


def report(targets: list[TargetDoc], verification: dict[str, object]) -> str:
    counts: dict[str, int] = {}
    for target in targets:
        counts[doc_type_label(target.doc_type)] = counts.get(doc_type_label(target.doc_type), 0) + 1
    lines = [
        "# OllamaPro 文档升级报告",
        "",
        f"- 生成时间：{datetime.now().isoformat(timespec='seconds')}",
        f"- 目标文档：{len(targets)} 篇",
        f"- 校验失败：{verification['failure_count']} 项",
        f"- 备份目录：`{BACKUP_ROOT}`",
        f"- 任务清单：`{TASKLIST_PATH}`",
        "- 细化内容：每篇目标文档均包含 canonical source map、类型化职责说明、失败模式、测试映射、建议验证命令、项目依据、证据等级和后续任务顺序。",
        "",
        "## 类型分布",
        "",
    ]
    for label, count in sorted(counts.items()):
        lines.append(f"- {label}：{count}")
    lines.extend(
        [
            "",
            "## 校验结果",
            "",
        ]
    )
    if verification["failures"]:
        for failure in verification["failures"]:
            lines.append(f"- `{failure['file']}`：{failure['issue']}")
    else:
        lines.append("- 结构校验通过：frontmatter、一级标题、升级标记块、空链接和乱码检查均未发现问题。")
    lines.extend(
        [
            "",
            "## 仍需人工或运行态验证",
            "",
            "- API 文档中的字段级契约仍应对照 OpenAPI 输出和真实请求样例补充。",
            "- Runbook 中的命令目前作为建议步骤保留，未在本次脚本中启动服务验证。",
            "- 训练处方、医学风险、安全门控和证据链质量仍需结合测试与专家审计持续验证。",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-upgrade", action="store_true", help="Only discover, backup, tasklist, and verify.")
    args = parser.parse_args()

    targets = discover_targets()
    if len(targets) != 82:
        raise RuntimeError(f"Expected 82 targets, got {len(targets)}")
    entries = backup_targets(targets)
    if not args.no_upgrade:
        upgrade_docs(targets)
    write_text(TASKLIST_PATH, tasklist(targets, entries))
    verification = verify(targets)
    write_text(REPORT_PATH, report(targets, verification))
    write_text(REPORT_PATH.with_suffix(".json"), json.dumps(verification, ensure_ascii=False, indent=2))
    print(json.dumps(verification, ensure_ascii=False, indent=2))
    if verification["failure_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
