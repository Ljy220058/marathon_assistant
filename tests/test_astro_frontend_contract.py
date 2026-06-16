"""Astro frontend contract tests.

Covers: index.astro DOM ids, data attributes, script entry points,
API key safety, build output integrity.
"""

import re
import sys
from pathlib import Path
from typing import List


root = Path(__file__).parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

ASTRO_PAGE = root / "apps" / "web" / "src" / "pages" / "index.astro"
APP_SCRIPT = root / "apps" / "web" / "src" / "scripts" / "app.js"
EVIDENCE_DRAWER_SCRIPT = root / "apps" / "web" / "src" / "scripts" / "evidenceDrawer.js"
EVIDENCE_STYLE = root / "apps" / "web" / "src" / "styles" / "evidence.css"
INTELLIGENT_DOCS_SCRIPT = root / "apps" / "web" / "src" / "scripts" / "intelligentDocs.js"


def _read_stripped(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _file_lines(path: Path) -> List[str]:
    return _read_stripped(path).splitlines()


# ---- P0.1: DOM id contract ----

REQUIRED_DOM_IDS = [
    "runQuery",
    "calendar",
    "dayModal",
    "evidenceDrawer",
    "statusPanel",
    "adjustmentHistory",
]


def test_astro_page_contains_all_required_dom_ids():
    content = _read_stripped(ASTRO_PAGE)
    for dom_id in REQUIRED_DOM_IDS:
        assert f'id="{dom_id}"' in content or f"id='{dom_id}'" in content, (
            f"Missing DOM id '{dom_id}' in index.astro"
        )


# ---- P0.1: Data attributes contract ----

REQUIRED_DATA_ATTRIBUTES = [
    "data-plan-generation-entry",
    "data-calendar-view",
]


def test_astro_page_contains_required_data_attributes():
    content = _read_stripped(ASTRO_PAGE)
    for attr in REQUIRED_DATA_ATTRIBUTES:
        assert attr in content, f"Missing data attribute '{attr}' in index.astro"


# ---- Script entry point ----

def test_astro_page_imports_app_js():
    content = _read_stripped(ASTRO_PAGE)
    assert 'src="../scripts/app.js"' in content or "src='../scripts/app.js'" in content, (
        "index.astro must import app.js as script entry"
    )


# ---- P1.8: No localStorage API key persistence ----

def test_frontend_script_does_not_persist_api_key():
    content = _read_stripped(APP_SCRIPT)
    assert 'localStorage.setItem("marathon_ds_api_key"' not in content
    assert "localStorage.setItem('marathon_ds_api_key'" not in content


def test_frontend_script_does_not_get_api_key_from_storage():
    content = _read_stripped(APP_SCRIPT)
    assert 'localStorage.getItem("marathon_ds_api_key"' not in content
    assert "localStorage.getItem('marathon_ds_api_key'" not in content


def test_frontend_script_clears_old_api_key_on_startup():
    content = _read_stripped(APP_SCRIPT)
    assert 'localStorage.removeItem("marathon_ds_api_key"' in content


# ---- API base endpoint references ----

def test_api_client_references_correct_endpoints():
    content = _read_stripped(APP_SCRIPT)
    endpoints = ["/query", "/feedback", "/plans", "/health", "/profile"]
    found = [ep for ep in endpoints if ep in content]
    assert len(found) >= 3, f"Missing expected API endpoints: {set(endpoints) - set(found)}"


# ---- Calendar section ----

def test_calendar_section_has_correct_layout():
    content = _read_stripped(ASTRO_PAGE)
    assert 'id="calendar-section"' in content
    assert 'id="calendarCount"' in content
    assert 'class="calendar-grid"' in content


# ---- Day modal ----

def test_day_modal_has_correct_structure():
    content = _read_stripped(ASTRO_PAGE)
    assert 'id="dayModal"' in content
    assert 'id="dayModalBackdrop"' in content
    assert 'id="dayModalContent"' in content
    assert 'id="dayModalClose"' in content


# ---- Evidence drawer ----

def test_evidence_drawer_has_correct_structure():
    content = _read_stripped(ASTRO_PAGE)
    assert 'id="evidenceDrawer"' in content
    assert 'id="evidenceDrawerContent"' in content


# ---- Feedback modal / status panel ----

def test_status_and_adjustment_sections_exist():
    content = _read_stripped(ASTRO_PAGE)
    assert 'id="statusPanel"' in content
    assert 'id="adjustmentHistory"' in content


# ---- Query input and controls ----

def test_query_input_and_controls_exist():
    content = _read_stripped(ASTRO_PAGE)
    assert 'id="queryInput"' in content
    assert 'id="dsApiKey"' in content
    assert 'id="saveDsApiKey"' in content
    assert 'id="clearDsApiKey"' in content


# ---- Nav links ----

def test_navigation_links_point_to_correct_sections():
    content = _read_stripped(ASTRO_PAGE)
    for section in ["plan", "calendar-section", "profile", "evidence"]:
        assert f'"{section}"' in content, f"Missing nav link href to {section}"


def test_api_key_label_warns_no_persistence():
    content = _read_stripped(ASTRO_PAGE)
    assert "会话" in content or "不保留" in content or "不写入" in content, (
        "API key section should warn that keys are not persisted"
    )


# ---- Product readiness: API base and first-use affordances ----


def test_frontend_defaults_to_documented_backend_port():
    content = _read_stripped(APP_SCRIPT)
    api_client = _read_stripped(root / "apps" / "web" / "src" / "scripts" / "apiClient.js")
    assert 'const LOCAL_API_BASE = "http://127.0.0.1:8000";' in content
    assert 'const LOCAL_API_BASE = "http://127.0.0.1:8000";' in api_client
    assert "当前推荐端口是 8010" not in content
    assert "当前推荐端口是 8010" not in api_client


def test_quick_actions_use_their_own_prompt():
    content = _read_stripped(ASTRO_PAGE)
    assert "data-prompt={item.prompt}" in content
    assert "data-prompt={PLAN_GENERATION_PROMPT}" not in content


def test_closed_custom_overlays_are_hidden_from_focus_order():
    content = _read_stripped(ASTRO_PAGE)
    assert 'id="dayModal" class="day-modal" hidden aria-hidden="true"' in content
    assert 'id="evidenceDrawer" class="evidence-drawer" data-evidence-drawer hidden aria-hidden="true"' in content
    assert 'id="calendarDetailDrawerBackdrop" class="calendar-detail-drawer-backdrop" data-calendar-detail-backdrop hidden' in content
    assert 'id="calendarDetailDrawer" class="calendar-detail-drawer" data-calendar-detail-drawer hidden aria-hidden="true"' in content
    assert 'aria-label="关闭训练日详情"' in content


def test_offline_banner_has_recovery_actions_and_runner_copy():
    content = _read_stripped(APP_SCRIPT)
    assert "训练服务未连接" in content
    assert "你仍可先填写我的情况" in content
    assert "重试连接" in content
    assert "查看启动命令" in content
    assert "使用示例计划体验" in content

def test_frontend_defaults_knowledge_qa_to_deepseek_provider():
    content = _read_stripped(APP_SCRIPT)
    api_client = _read_stripped(root / "apps" / "web" / "src" / "scripts" / "apiClient.js")
    page = _read_stripped(ASTRO_PAGE)
    assert 'llm_provider: llmProviderInput?.value || "ds"' in api_client
    assert 'llmProviderInput.value = savedProvider || data.default?.provider || "ds"' in content
    assert 'data-provider-choice="ds">DeepSeek</button>' in page


def test_plan_profile_missing_gate_treats_no_limitations_as_filled():
    content = _read_stripped(APP_SCRIPT)
    assert "function hasAnsweredLimitationField" in content
    assert "if (!hasAnsweredLimitationField(normalized.limitations))" in content
    assert "NO_LIMITATION_TERMS.has(item)" in content


def test_profile_api_to_draft_maps_injury_history_to_limitations():
    content = _read_stripped(APP_SCRIPT)
    mapper = content[content.index("function profileApiToDraft"):content.index("function fillProfileDraft")]
    assert "profile.injury_history" in mapper
    assert "injuryHistory || \"无\"" in mapper


def test_qa_response_does_not_force_calendar_workspace():
    content = _read_stripped(APP_SCRIPT)
    renderer = content[content.index("function renderQueryPayload"):content.index("async function runQuery")]
    calendar_renderer = content[content.index("function renderCalendar"):content.index("function renderMonthCalendarGrid")]
    assert "const hasStructuredPlan = summarizePlan(payload).hasStructuredPlan" in renderer
    assert "if (hasStructuredPlan)" in renderer
    assert 'updateWorkspaceFlow("answer"' in renderer
    assert 'setActiveDrawerSection("calendar")' in renderer
    assert "async function enrichQuery" not in content
    assert "智能对话不会改动训练日历" in calendar_renderer


def test_homepage_has_clear_plan_and_qa_entry_points():
    page = _read_stripped(ASTRO_PAGE)
    script = _read_stripped(APP_SCRIPT)
    styles = _read_stripped(root / "apps" / "web" / "src" / "styles" / "workspace-scenes.css")

    assert 'data-workspace-intent="plan"' in page
    assert 'data-workspace-intent="qa"' in page
    assert "生成训练日历" in page
    assert "问 AI 教练" in page
    assert "智能对话不会改动训练日历" in page
    assert 'document.querySelectorAll("[data-workspace-intent]")' in script
    assert "setQueryMode(intent)" in script
    assert ".intent-entry-grid" in styles
    assert ".intent-entry-card" in styles

def test_saved_plan_restore_preserves_review_and_evidence_chain():
    content = _read_stripped(APP_SCRIPT)
    load_saved_plan = content[content.index("async function loadSavedPlan"):content.index("async function saveCurrentPlanSnapshot")]
    assert "training_plan_review: detail.training_plan_review ||" in load_saved_plan
    assert "evidence_chain: detail.evidence_chain ||" in load_saved_plan


def test_profile_panel_saves_in_single_profile_request():
    content = _read_stripped(APP_SCRIPT)
    save_profile_panel = content[content.index("async function saveProfilePanel"):content.index("function compactJson")]

    assert 'window.__apiClient.apiFetch("/profile"' in save_profile_panel
    assert 'method: "POST"' in save_profile_panel
    assert "/profile/default_user/fields/" not in save_profile_panel
    assert 'method: "PATCH"' not in save_profile_panel


def test_frontend_prioritizes_answer_card_and_policy_over_raw_report_truncation():
    content = _read_stripped(APP_SCRIPT)
    styles = _read_stripped(root / "apps" / "web" / "src" / "styles" / "report.css")
    assert "function renderAnswerCard" in content
    assert "function renderFullReportDetails" in content
    assert "function renderReportMarkdown" in content
    assert "response?.answer_card" in content
    assert "must_not_truncate" in content
    assert "default_collapsed" in content
    assert 'data-severity="${escapeHtml(answerCard.severity || "info")}"' in content
    assert 'data-intent="${escapeHtml(answerCard.intent || "qa_card")}"' in content
    assert "renderReportMarkdown(markdown)" in content
    assert "answer-card-hero" in styles
    assert "answer-card[data-severity=\"medical_referral\"]" in styles
    assert "report-markdown" in styles
    render_report = content[content.index("function renderReport"):content.index("function dayKeyCandidates")]
    assert "renderAnswerCard(response.answer_card" in render_report
    assert ".slice(0," not in render_report


def test_evidence_source_indicator_treats_evidence_chain_as_object_contract():
    content = _read_stripped(APP_SCRIPT)
    indicator = content[content.index("function renderEvidenceSourceIndicator"):content.index("function renderQueryPayload")]
    assert "response?.evidence_chain?.items" in indicator
    assert "Array.isArray(response?.evidence_chain)" not in indicator


def test_evidence_drawer_answer_source_mode_accepts_needs_evidence():
    content = _read_stripped(EVIDENCE_DRAWER_SCRIPT)
    mode_info = content[content.index("function getAnswerSourceModeInfo"):content.index("function evidenceChainItems")]
    assert "needs_evidence:" in mode_info
    assert "证据不足，建议仅供参考" in mode_info


def test_runner_projection_keeps_public_day_card_contract_fields():
    content = _read_stripped(root / "apps" / "backend" / "src" / "marathon_qa_assistant" / "apps" / "response_projection.py")
    for field in [
        '"field_sources"',
        '"protocol_check"',
        '"action_match"',
        '"kb_fallback"',
        '"risk_gate"',
        '"training_load_factors"',
    ]:
        assert field not in content[content.index("_RUNNER_EXPERT_ONLY_NESTED_KEYS"):content.index("def _response_payload")]
    assert "_public_day_card_contract" in content


CANONICAL_EVIDENCE_FIELDS = [
    "source_label",
    "text_span",
    "page_hint",
    "locator_hint",
    "display_mode",
    "user_facing_summary",
]

DISPLAY_MODE_LABELS = [
    "可定位来源",
    "旧知识库解释性来源",
    "图谱关联线索",
    "模型常识说明",
    "待补证据",
    "已阻断来源",
]


def test_evidence_drawer_normalizes_canonical_fields_first():
    content = _read_stripped(APP_SCRIPT) + "\n" + _read_stripped(EVIDENCE_DRAWER_SCRIPT)
    for field in CANONICAL_EVIDENCE_FIELDS:
        assert field in content, f"Evidence drawer must read canonical field {field}"
    assert "知识库片段" not in content
    assert "页码未标注" not in content


def test_evidence_drawer_maps_display_modes_to_chinese_labels():
    content = _read_stripped(APP_SCRIPT) + "\n" + _read_stripped(EVIDENCE_DRAWER_SCRIPT)
    for label in DISPLAY_MODE_LABELS:
        assert label in content, f"Missing display mode label: {label}"
    for raw_mode in [
        "verified_source",
        "legacy_explanation",
        "graph_hint",
        "model_general_knowledge",
        "needs_evidence",
        "rejected_source",
    ]:
        assert raw_mode in content, f"Missing display mode branch: {raw_mode}"


def test_evidence_drawer_uses_canonical_chain_and_day_refs():
    content = _read_stripped(APP_SCRIPT) + "\n" + _read_stripped(EVIDENCE_DRAWER_SCRIPT)
    assert "evidence_chain" in content
    assert ".items" in content
    assert "evidence_refs" in content
    assert "field_sources" in content


def test_evidence_drawer_gates_clickable_citations_and_hides_sensitive_fields():
    content = _read_stripped(APP_SCRIPT) + "\n" + _read_stripped(EVIDENCE_DRAWER_SCRIPT)
    assert "canShowCitationBadge" in content
    assert "source_url" in content
    assert "section" in content
    assert "locator_hint" in content
    assert "evidence-source-path" not in content
    assert ".source_path" not in content
    assert ".local_path" not in content
    assert ".source_registry_id" not in content
    assert ".retrieval_score" not in content


def test_evidence_style_has_status_card_classes_for_non_clickable_sources():
    content = _read_stripped(EVIDENCE_STYLE)
    assert ".evidence-status-card" in content
    assert ".evidence-locator-hint" in content
    assert ".evidence-citation-link" in content


def test_intelligent_docs_alert_is_query_aware_not_hardcoded_to_injury():
    content = _read_stripped(INTELLIGENT_DOCS_SCRIPT)
    assert "buildEvidenceCoverageAlert(payload, query)" in content
    assert "isInjuryQuery(query)" in content
    assert "请结合疼痛等级、持续时间和是否影响步态判断" not in content
    assert "当前问题需要更多可定位来源支撑" in content


def test_intelligent_docs_prefers_canonical_evidence_fields():
    content = _read_stripped(INTELLIGENT_DOCS_SCRIPT)
    for field in [
        "source_label",
        "text_span",
        "page_hint",
        "locator_hint",
        "display_mode",
        "user_facing_summary",
        "score_breakdown",
    ]:
        assert field in content
    assert "后端暂未返回摘录" not in content
    assert "相关性待核对" not in content


def test_intelligent_docs_initial_copy_uses_user_trial_copy():
    content = _read_stripped(root / "apps" / "web" / "src" / "pages" / "intelligent-docs.astro")
    assert "AI 回答" in content
    assert "输入问题后，这里会生成回答。" in content
    assert "你可以先问训练安排、专项技术、恢复或伤病风险。" in content
    assert "暂无来源" in content
    assert "回答生成后会显示可核对来源。" in content
    assert "知识源概览" in content
    assert "可回答" in content
    for developer_copy in [
        "AI 回答（等待新知识库检索）",
        "等待新知识库检索",
        "NotebookLM",
        "chunk",
        "新知识库 v2",
        "核心训练处方依据",
        "训练建议",
        "专项边界",
        "证据待核验",
        "查看风险依据",
        "打开原文片段",
    ]:
        assert developer_copy not in content


def test_intelligent_docs_runtime_copy_does_not_claim_hidden_evidence_count():
    content = _read_stripped(INTELLIGENT_DOCS_SCRIPT)
    assert "基于 ${evidenceCount} 组依据生成" not in content
    assert "正在查找来源并生成回答" in content
    assert "回答已附来源，可在右侧核对" in content
    assert "当前问题缺少可定位来源" in content
    assert "本轮未返回可展示的本地知识库证据" not in content
    assert "伤病风险依据" not in content
    assert "旧知识库解释性来源" not in content
    assert "等待新知识库检索" not in content
    assert "解释性线索" in content


def test_intelligent_docs_shows_relevance_and_collapses_low_relevance_items():
    content = _read_stripped(INTELLIGENT_DOCS_SCRIPT)
    assert "relevancePercent" in content
    assert "相关度" in content
    assert "LOW_RELEVANCE_THRESHOLD" in content
    assert "item.relevancePercent >= LOW_RELEVANCE_THRESHOLD" in content
    assert "data-relevance-percent" in content
    assert "可能不相关" in content
    assert "低于 50%" not in content
    assert "score: status" not in content


def test_evidence_ui_reads_source_status_fields():
    content = _read_stripped(EVIDENCE_DRAWER_SCRIPT) + "\n" + _read_stripped(INTELLIGENT_DOCS_SCRIPT)
    assert "source_status" in content
    assert "has_full_text" in content
    assert "evidence_kind" in content
    assert "正文证据" in content
    assert "仅登记线索" in content


def test_query_timeout_allows_slow_deepseek_rag_response():
    content = _read_stripped(APP_SCRIPT)
    api_client = _read_stripped(root / "apps" / "web" / "src" / "scripts" / "apiClient.js")
    assert "const FULL_QUERY_TIMEOUT_MS = 120000;" in content
    assert "const FULL_QUERY_TIMEOUT_MS = 120000;" in api_client
    assert "const FULL_QUERY_TIMEOUT_SEC = 120;" in content
    assert "const FULL_QUERY_TIMEOUT_SEC = 120;" in api_client
    assert "function resolveQueryTimeout(responseMode, retry = false) {" in api_client
    assert "function resolveQueryTimeoutMs(responseMode, retry = false) {" in api_client
    assert 'responseMode = "full"' in api_client
    assert 'planLike ? "skeleton" : "qa_fast"' not in api_client
    assert 'mode === "skeleton" || mode === "skeleton_first"' in api_client
    assert 'mode === "qa_fast" || mode === "quick_qa"' in api_client


def test_query_timeout_preserves_timeout_error_instead_of_masking_connection_failure():
    api_client = _read_stripped(root / "apps" / "web" / "src" / "scripts" / "apiClient.js")
    assert "isQueryTimeoutError" in api_client
    assert "if (isQueryTimeoutError(error)) {" in api_client
    assert "throw error;" in api_client
    assert "AI 生成超过等待时间" in api_client


def test_intelligent_docs_has_knowledge_source_summary_panel():
    page = _read_stripped(root / "apps" / "web" / "src" / "pages" / "intelligent-docs.astro")
    script = _read_stripped(INTELLIGENT_DOCS_SCRIPT)
    api_client = _read_stripped(root / "apps" / "web" / "src" / "scripts" / "apiClient.js")

    assert "data-source-summary" in page
    assert "data-source-summary-text" in page
    assert "data-total-source-count" in page
    assert "data-ready-source-count" in page
    assert "data-registry-only-source-count" in page
    assert "loadKnowledgeSourceSummary" in api_client
    assert "loadKnowledgeSources" in api_client
    assert "/knowledge/sources/summary" in api_client
    assert "/knowledge/sources" in api_client
    assert "renderSourceSummary" in script
    assert "知识源概览" in page
    assert "当前有" in script
    assert "知识源概览暂不可用" in script
    assert "可回答" in page
    assert "仅登记线索" in script
    assert "正文可问" not in script


def test_intelligent_docs_distinguishes_body_evidence_from_registry_lines():
    content = _read_stripped(INTELLIGENT_DOCS_SCRIPT)
    assert "sourceStatusLabel" in content
    assert "正文证据" in content
    assert "仅登记线索" in content
    assert "source_status" in content
    assert "has_full_text" in content
    assert "evidence_kind" in content
    assert "source-status" in content
    assert "source-meta" in content
    assert "source-excerpt" in content


def test_intelligent_docs_user_trial_layout_hides_admin_style_navigation_and_empty_expand_control():
    page = _read_stripped(root / "apps" / "web" / "src" / "pages" / "intelligent-docs.astro")
    style = _read_stripped(root / "apps" / "web" / "src" / "styles" / "intelligent-docs.css")
    script = _read_stripped(INTELLIGENT_DOCS_SCRIPT)

    assert 'class="docs-side"' not in page
    assert "grid-template-columns: minmax(0, 1fr) 320px;" in style
    assert "updateExpandAllVisibility" in script
    assert "expandAllButton.hidden = rows.length <= 1" in script
    assert "全部展开" in page
    assert ".docs-toggle:focus-visible" in style
    assert ".docs-send:disabled" in style
    assert ".docs-source-dot" in style


def test_generated_calendar_expands_current_or_first_week_by_default():
    content = _read_stripped(APP_SCRIPT)
    expansion_logic = content[content.index("function isWeekGroupExpanded"):content.index("function weekGroupPanelId")]

    assert "primaryTrainingDayIndex" in content
    assert "normalizeCalendarDays(state.lastResponse || {})" in expansion_logic
    assert "group.firstIndex === 0" in expansion_logic


def test_plan_generation_skeleton_first_is_not_blocked_by_deepseek_api_key_gate():
    content = _read_stripped(APP_SCRIPT)
    api_client = _read_stripped(root / "apps" / "web" / "src" / "scripts" / "apiClient.js")
    run_query = content[content.index("async function runQuery"):content.index("function clearResult")]

    assert 'const planLike = qaMode ? false : isPlanLikeQuery(query);' in run_query
    assert "!planLike" in run_query
    assert 'llmProviderInput.value === "ds"' in run_query
    assert 'payload = await window.__apiClient.requestQueryPayload(query, { responseMode: "full", controller });' in run_query
    assert "enrichQuery(query, runId, controller);" not in run_query
    assert 'responseMode = "full"' in api_client


def test_ai_coach_qa_fast_path_uses_shorter_timeout_than_full_query():
    api_client = _read_stripped(root / "apps" / "web" / "src" / "scripts" / "apiClient.js")
    assert 'const FULL_QUERY_TIMEOUT_MS = 120000;' in api_client
    assert 'function resolveQueryTimeout(responseMode, retry = false) {' in api_client
    assert 'function resolveQueryTimeoutMs(responseMode, retry = false) {' in api_client
    assert 'mode === "qa_fast" || mode === "quick_qa"' in api_client
    assert 'mode === "skeleton" || mode === "skeleton_first"' in api_client


def test_app_js_delegates_api_client_to_window_namespace():
    content = _read_stripped(APP_SCRIPT)

    assert "async function apiFetch(" not in content
    assert "async function detectApiBase(" not in content
    assert "async function requestQueryPayloadFromBase(" not in content
    assert "async function requestQueryPayload(" not in content
    assert "function buildQueryPayload(" not in content
    assert "function explainApiError(" not in content
    assert "window.__apiClient.apiFetch" in content
    assert "window.__apiClient.detectApiBase" in content
    assert "window.__apiClient.requestQueryPayload" in content
    assert "window.__apiClient.explainApiError" in content


def test_calendar_render_does_not_monkey_patch_itself_for_month_view():
    content = _read_stripped(APP_SCRIPT)
    assert "renderCalendar = function(response)" not in content
    assert "const _originalRenderCalendar = renderCalendar" not in content


def test_render_calendar_owns_month_grid_visibility_directly():
    content = _read_stripped(APP_SCRIPT)
    render_calendar = content[content.index("function renderCalendar(response)"):content.index("function modalMetric")]
    assert "renderMonthCalendarGrid(" in render_calendar
    assert "const monthGrid = document.getElementById(\"monthCalendarGrid\")" in render_calendar
    assert "monthGrid.hidden = true" in render_calendar
