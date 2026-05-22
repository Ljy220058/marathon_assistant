from pathlib import Path


FRONTEND_ROOT = Path(__file__).resolve().parents[1] / "apps" / "web"
FRONTEND_INDEX = FRONTEND_ROOT / "src" / "pages" / "index.astro"
FRONTEND_STYLE = FRONTEND_ROOT / "src" / "styles" / "global.css"
FRONTEND_SCRIPTS = FRONTEND_ROOT / "src" / "scripts"
FRONTEND_STYLES = FRONTEND_ROOT / "src" / "styles"


def _index_source() -> str:
    parts = [FRONTEND_INDEX.read_text(encoding="utf-8")]
    if FRONTEND_SCRIPTS.exists():
        for path in sorted(FRONTEND_SCRIPTS.glob("*.js")):
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def _style_source() -> str:
    parts = [FRONTEND_STYLE.read_text(encoding="utf-8")]
    for path in sorted(FRONTEND_STYLES.glob("*.css")):
        if path.name != "global.css":
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def test_astro_frontend_entry_is_split_into_scripts_and_style_domains():
    index_text = FRONTEND_INDEX.read_text(encoding="utf-8")
    global_style = FRONTEND_STYLE.read_text(encoding="utf-8")

    assert '<script src="../scripts/app.js"></script>' in index_text
    assert len(index_text.splitlines()) < 700
    assert len(global_style.splitlines()) < 80

    expected_scripts = {
        "app.js",
        "apiClient.js",
        "calendarRenderer.js",
        "evidenceDrawer.js",
        "feedbackModal.js",
        "statusPanel.js",
    }
    assert expected_scripts.issubset({path.name for path in FRONTEND_SCRIPTS.glob("*.js")})

    expected_styles = {
        "base.css",
        "components.css",
        "plan.css",
        "profile-status.css",
        "modal.css",
        "calendar.css",
        "evidence.css",
        "responsive.css",
        "commercial-light.css",
    }
    style_names = {path.name for path in FRONTEND_STYLES.glob("*.css")}
    assert expected_styles.issubset(style_names)


def test_astro_workspace_smoke_covers_guarded_frontend_entry_points():
    smoke = FRONTEND_ROOT / "scripts" / "smoke-workspace.mjs"
    source = smoke.read_text(encoding="utf-8")

    assert 'document.querySelector("#apiToken")' in source
    assert 'document.querySelector(\'[data-provider-choice="openai"]\')' in source
    assert "apiTokenInput: Boolean(apiToken)" in source
    assert "openaiProviderButton: Boolean(openaiProviderButton)" in source
    assert "api token input missing" in source
    assert "openai provider button missing" in source
    for path in FRONTEND_STYLES.glob("*.css"):
        assert len(path.read_text(encoding="utf-8").splitlines()) < 900, path.name


def test_astro_defaults_to_8010_and_auto_detects_fallback_port():
    source = _index_source()

    assert 'const DEFAULT_API_BASE = "http://127.0.0.1:8010"' in source
    assert "API_BASE_CANDIDATES" in source
    assert "detectApiBase" in source
    assert "http://127.0.0.1:8011" in source
    assert "http://127.0.0.1:8000" in source
    assert "requestQueryPayloadFromBase" in source
    assert "lastQueryBase" in source


def test_astro_calendar_renders_full_plan_with_view_switches():
    source = _index_source()

    assert 'data-calendar-view="week"' in source
    assert 'data-calendar-view="month"' in source
    assert 'data-calendar-view="phase"' in source
    assert 'data-calendar-view="all"' in source
    assert "已展示完整计划" in source
    assert "完整计划未截断" not in source
    assert ".slice(0, 42)" not in source


def test_astro_plan_overview_renders_phase_overview_bar():
    source = _index_source()
    styles = _style_source()

    assert "renderPhaseOverviewBar" in source
    assert "normalizePhaseSummary" in source
    assert "phase_summary" in source
    assert "阶段总览" in source
    assert "data-phase-overview-bar" in source
    assert "vertical_scroll" in source
    assert ".phase-overview-bar" in styles
    assert ".phase-step-list" in styles


def test_astro_calendar_settings_are_sent_when_saving_plan():
    source = _index_source()
    styles = _style_source()

    assert 'id="trainingStartDate"' in source
    assert 'id="defaultStartTime"' in source
    assert "getCalendarSettings" in source
    assert "calendar_settings: getCalendarSettings()" in source
    assert "training_start_date" in source
    assert "default_start_time" in source
    assert ".calendar-settings" in styles


def test_astro_saved_plan_rehydrates_calendar_event_times():
    source = _index_source()

    assert "scheduled_date: event.scheduled_date" in source
    assert "start_time: event.start_time" in source
    assert "duration_min: event.duration_min" in source
    assert "formatScheduleTime" in source
    assert "训练时间" in source


def test_astro_week_groups_are_collapsible_summary_cards():
    source = _index_source()
    styles = _style_source()

    assert "renderCalendarGroup" in source
    assert "data-week-group" in source
    assert "data-week-toggle" in source
    assert "aria-expanded" in source
    assert "weekCollapseState" in source
    assert "toggleWeekGroup" in source
    assert "return false;" in source[source.index("function isWeekGroupExpanded") : source.index("function weekGroupPanelId")]
    assert "group.days.map(({ day, index }) => renderDayCard" in source
    assert ".week-card" in styles
    assert ".week-card-toggle" in styles
    assert ".week-card-body[hidden]" in styles


def test_astro_week_navigator_and_week_explanation_summary_are_first_class():
    source = _index_source()
    styles = _style_source()

    assert "normalizeWeekNavigationItems" in source
    assert "renderWeekNavigator" in source
    assert "jumpToWeekGroup" in source
    assert "data-week-navigator" in source
    assert "data-week-nav-target" in source
    assert "WeekNavigator" in source
    assert "renderWeekExplanationSummary" in source
    assert "WeekExplanationSummary" in source
    assert "本周关键课" in source
    assert ".week-navigator" in styles
    assert ".week-explanation-summary" in styles


def test_astro_week_navigator_syncs_active_state_and_accessibility():
    source = _index_source()

    assert "syncWeekNavigatorActiveState" in source
    assert 'aria-current="${index === 0 ? "true" : "false"}"' in source
    assert 'button.setAttribute("aria-current", isCurrent ? "true" : "false")' in source
    assert 'button.classList.toggle("current", isCurrent)' in source
    assert "syncWeekNavigatorActiveState(stateKey)" in source
    assert "toggleWeekGroup(stateKey, { syncNavigator = true } = {})" in source


def test_astro_week_navigator_supports_long_plans_on_mobile():
    styles = _style_source()
    week_nav_styles = styles[styles.index(".week-nav-list") : styles.index(".week-nav-button")]

    assert "overflow-x: auto" in week_nav_styles
    assert "grid-auto-flow: column" in week_nav_styles
    assert "grid-auto-columns: minmax(132px, 172px)" in week_nav_styles
    assert "-webkit-overflow-scrolling: touch" in week_nav_styles


def test_astro_week_explanation_copy_matches_calendar_view_scope():
    source = _index_source()

    assert "weekExplanationCopyForView" in source
    assert "renderWeekExplanationSummary(group, view)" in source
    assert "copy.keySessionLabel" in source
    assert "copy.defaultGoal" in source
    assert "month:" in source
    assert "phase:" in source


def test_astro_week_explanation_collects_group_level_summary_values():
    source = _index_source()

    assert "collectGroupSummaryValues" in source
    assert '"week_goal"' in source
    assert '"weekly_goal"' in source
    assert '"group_goal"' in source
    assert '"phase_goal"' in source
    assert '"key_workouts"' in source
    assert '"key_sessions"' in source
    assert '"action_suggestions"' in source
    assert '"execution_tips"' in source


def test_astro_primary_workspace_has_single_default_card_and_sidebar_drawer():
    source = _index_source()
    styles = _style_source()

    assert 'data-primary-workspace-card' in source
    assert 'data-side-drawer' in source
    assert 'class="side-drawer-toggle"' in source
    assert '.focused-workspace' in styles
    assert '.workspace-card' in styles
    assert '.side-drawer[open]' in styles


def test_astro_profile_moves_to_sidebar_while_calendar_remains_primary_surface():
    source = _index_source()

    assert 'id="drawerWorkspaceSections"' in source
    assert 'class="drawer-workspace-sections"' in source
    assert 'data-drawer-section="profile"' in source
    assert 'data-drawer-section="profile-summary"' in source
    assert 'data-drawer-section="calendar"' in source
    assert 'data-drawer-section="basis"' in source
    assert "moveWorkspaceSectionsToDrawer" in source
    assert "drawerSections.appendChild(section)" not in source
    assert 'sectionId === "profile"' in source
    assert "openProfilePanel()" in source
    assert 'id="calendar-section" class="panel" data-drawer-section="calendar" hidden' in source
    assert 'data-training-basis data-drawer-section="basis" hidden' in source


def test_astro_guided_sidebar_has_search_actions_and_single_active_panel():
    source = _index_source()
    styles = _style_source()

    assert "DRAWER_SECTIONS" in source
    assert 'id="drawerSearch"' in source
    assert 'data-drawer-guide' in source
    assert ">训练导航<" in source
    assert 'class="drawer-toggle-mark"' in source
    assert 'class="drawer-toggle-copy"' in source
    assert 'class="drawer-toggle-affordance"' in source
    assert "今日 / 计划 / 依据" in source
    assert 'class="side-drawer-content" aria-label="训练导航" aria-hidden="true" inert' in source
    assert "setDrawerContentAvailability" in source
    assert "快速查找" in source
    assert 'data-drawer-action="profile"' in source
    assert 'data-drawer-action="calendar"' in source
    assert 'data-drawer-action="basis"' in source
    assert 'data-drawer-query="basis evidence source' in source
    assert 'data-drawer-empty hidden' in source
    assert "setActiveDrawerSection" in source
    assert "filterDrawerActions" in source
    assert 'normalizedQuery.includes("basis")' in source
    assert 'normalizedQuery.includes("依据")' in source
    assert 'directMatches.add("basis")' in source
    assert 'data-open-drawer-section="profile"' in source
    assert 'data-open-drawer-section="calendar"' in source
    assert 'data-open-drawer-section="basis"' in source
    assert 'document.querySelectorAll("[data-open-drawer-section]")' in source
    assert "section.hidden = !isActive" in source
    assert ".drawer-guide" in styles
    assert ".drawer-toggle-mark" in styles
    assert ".drawer-toggle-copy" in styles
    assert ".drawer-toggle-affordance" in styles


def test_astro_uses_light_commercial_navigation_theme():
    source = _index_source()
    styles = _style_source()
    global_style = FRONTEND_STYLE.read_text(encoding="utf-8")

    assert '@import "./commercial-light.css";' in global_style
    assert "color-scheme: light" in styles
    assert "小红书式轻导航" in styles
    assert ".top-nav nav a::before" in styles
    assert ".side-drawer:not([open]) .side-drawer-toggle" in styles
    assert "--bg: #f7f8fb" in styles
    assert "--tech-accent: #eafe52" in styles
    assert ".side-drawer[open] .side-drawer-toggle" in styles
    assert ".drawer-action.is-active" in styles
    assert ".drawer-empty-state" in styles
    assert "[data-drawer-section][hidden]" in styles


def test_astro_workspace_flow_guides_primary_path_and_calendar_handoff():
    source = _index_source()
    styles = _style_source()

    assert 'id="workspaceFlow"' in source
    assert 'data-workspace-state="profile"' in source
    assert 'id="workspaceNextAction"' in source
    assert "updateWorkspaceFlow" in source
    assert 'updateWorkspaceFlow("calendar"' in source
    assert 'setActiveDrawerSection("calendar")' in source
    assert "Generation Trace" not in source
    assert "下方画像" not in source
    assert ".workspace-flow" in styles
    assert ".workspace-flow-step.is-current" in styles


def test_astro_calendar_day_cards_prioritize_scannable_essentials():
    source = _index_source()
    styles = _style_source()

    assert 'class="day-card-essentials"' in source
    assert 'class="day-risk-pill"' in source
    assert 'class="day-card-summary"' in source
    assert '<p>${escapeHtml(mainText)}</p>' not in source
    assert ".day-card-essentials" in styles
    assert ".day-risk-pill" in styles


def test_astro_calendar_surfaces_user_action_summary_before_expert_metrics():
    source = _index_source()
    styles = _style_source()

    assert 'id="calendarActionPanel"' in source
    assert "renderCalendarActionPanel(response, days)" in source
    assert "下一次训练" in source
    assert "本周重点" in source
    assert "安全提醒" in source
    assert "反馈入口" in source
    assert "data-calendar-action=\"open-feedback\"" in source
    assert ".calendar-action-panel" in styles
    assert ".calendar-action-card" in styles


def test_astro_drawer_actions_are_step_guided_not_a_tool_dump():
    source = _index_source()
    styles = _style_source()

    assert 'data-drawer-stage="1"' in source
    assert 'data-drawer-stage="2"' in source
    assert 'data-drawer-stage="3"' in source
    assert "1 准备" in source
    assert "2 查看" in source
    assert "3 调整" in source
    assert ".drawer-stage-label" in styles
    assert ".drawer-action::before" in styles


def test_astro_visual_tokens_are_defined_for_minimal_workspace():
    styles = _style_source()

    assert "--accent-1:" in styles
    assert "--accent-2:" in styles
    assert "--accent-3:" in styles
    assert "Inter," not in styles
    assert "system-ui" not in styles
    assert "[hidden]" in styles
    assert "display: none !important" in styles


def test_astro_guided_sidebar_keeps_expert_settings_out_of_normal_flow():
    source = _index_source()

    assert 'data-drawer-action="settings" data-drawer-query="settings api model 设置 服务 接口 模型 高级" aria-controls="drawerSettingsPanel" hidden data-expert-only' in source
    assert 'id="drawerSettingsPanel" class="panel rail-panel" data-drawer-section="settings" hidden data-expert-only' in source
    assert 'targetSection?.hasAttribute("data-expert-only")' in source
    assert 'button.hasAttribute("data-expert-only")' in source
    assert '<details class="audit-panel" data-audit-trace hidden data-expert-only>' in source


def test_astro_drawer_content_is_hidden_until_user_selects_a_guided_action():
    source = _index_source()

    assert 'data-drawer-section="templates" hidden' in source
    assert 'data-drawer-section="history" hidden' in source
    assert 'data-drawer-section="settings" hidden' in source
    assert 'id="profile" class="panel" data-drawer-section="profile" hidden' in source
    assert 'id="calendar-section" class="panel" data-drawer-section="calendar" hidden' in source
    assert 'data-training-basis data-drawer-section="basis" hidden' in source


def test_astro_main_stack_keeps_only_generation_and_result_surfaces_by_default():
    source = _index_source()
    main_stack = source[source.index('<section class="main-stack">') : source.index("</section>\n      </div>\n    </main>")]

    assert 'data-primary-workspace-card' in main_stack
    assert 'class="dashboard-grid"' in main_stack
    assert 'id="profile" class="panel" data-drawer-section="profile"' in main_stack
    assert 'id="calendar-section" class="panel" data-drawer-section="calendar"' in main_stack
    assert 'data-training-basis data-drawer-section="basis"' in main_stack
    assert "moveWorkspaceSectionsToDrawer()" in source


def test_astro_normal_mode_hides_internal_diagnostics_and_connection_labels():
    source = _index_source()

    assert ">API Base<" not in source
    assert '<span class="pill">default_user</span>' not in source
    assert "<span>Token</span>" not in source
    assert "<span>审计评分</span>" not in source
    assert "FastAPI 后端" not in source
    assert "fail-closed" not in source
    assert "item.created_at || item.feedback_id" not in source
    assert 'data-expert-only' in source
    assert 'class="panel metrics-panel" hidden data-expert-only' in source


def test_astro_training_basis_replaces_evidence_dictionary_and_is_collapsed():
    source = _index_source()

    assert '<details id="evidence" class="panel training-basis" data-training-basis data-drawer-section="basis" hidden>' in source
    assert "<h2>训练依据</h2>" in source
    assert "<h2>证据分层</h2>" not in source
    assert "Evidence Preview" not in source
    assert "训练依据来源" in source


def test_astro_feedback_presets_are_day_detail_only():
    source = _index_source()

    assert 'id="feedback" class="panel rail-panel"' not in source
    assert "data-feedback-preset" not in source
    assert "data-modal-feedback" in source
    assert "modal-feedback-panel" in source


def test_astro_mobile_sidebar_uses_sheet_instead_of_stacked_long_list():
    styles = _style_source()

    assert "@media (max-width: 720px)" in styles
    assert ".side-drawer[open]" in styles
    assert "position: fixed" in styles
    assert "inset:" in styles
    assert "max-height: min(82vh, 720px)" in styles
    assert "padding-bottom: 168px" in styles


def test_frontend_workspace_smoke_script_covers_p0_to_p4():
    smoke = FRONTEND_ROOT / "scripts" / "smoke-workspace.mjs"

    assert smoke.exists()
    source = smoke.read_text(encoding="utf-8")
    assert "WORKSPACE_URL" in source
    assert "workspaceFlow" in source
    assert "side-drawer-toggle" in source
    assert "day-card-essentials" in source
    assert "mobile" in source


def test_astro_day_card_surfaces_basis_and_feedback_loop():
    source = _index_source()

    assert "describeDayBasis" in source
    assert "依据影响" in source
    assert "安全校验" in source
    assert "data-feedback-result" in source
    assert "提交反馈并计算" in source
    assert "completion," in source
    assert "pain," in source
    assert "生成调整版计划" in source


def test_astro_profile_derives_plan_weeks_and_weekly_mileage_from_race_date():
    source = _index_source()

    assert '["lastMonthMileage", "上个月月跑量", "例如 300 km"]' in source
    assert '["weeklyMileage", "当前周跑量", "例如 35 km"]' not in source
    assert '["planWeeks", "计划周期", "例如 12 周"]' not in source
    assert '["recentFourWeekMileage", "近4周平均周跑量", "例如 70 km"]' not in source
    assert "profileDerivedMetrics" in source
    assert "deriveProfileMetrics" in source
    assert "monthlyMileageToWeeklyMileage" in source
    assert "weeksUntilRace" in source
    assert "plan_duration_weeks" in source
    assert "估算周跑量" in source
    assert "建议周期" in source
    assert "toggleHistoryList" in source
    assert ".slice(0, 2)" in source


def test_astro_runner_identity_card_and_profile_editor_use_unified_profile_api():
    source = _index_source()
    styles = _style_source()

    assert "跑者画像摘要" in source
    assert "runnerIdentityCard" in source
    assert "renderRunnerIdentityCard" in source
    assert ">ProfileEditor<" not in source
    assert "我的情况" in source
    assert "来自 API" not in source
    assert "identity-summary-rows" in source
    assert "identity-metrics" not in source
    assert "profileEditorDialog" in source
    assert "PROFILE_EDITOR_GROUPS" in source
    assert 'apiFetch("/profile/default_user")' in source
    assert 'apiFetch(`/profile/default_user/fields/${field.key}`' in source
    assert "renderRunnerIdentityCard(payload.profile || {})" in source
    assert "refreshPlanStateAfterProfileSave" in source
    assert "runner-identity-card" in styles
    assert "profile-editor-dialog" in styles
    assert "profile-editor-group" in styles


def test_astro_evidence_preview_falls_back_to_hmp_protocol_rules():
    source = _index_source()

    assert "内置 HMP 协议规则说明" in source
    assert "protocol_rule_hmp" in source
    assert "protocol_rule" in source
    assert "内置协议规则，非外部检索证据" in source
    assert "不是本次检索证据" in source
    assert "docs/product/half_marathon_hmp_protocol.md" in source
    assert "日卡会先展示结构化规则和内置 HMP 协议规则依据" in source


def test_astro_has_shared_evidence_drawer_for_clickable_evidence():
    source = _index_source()
    styles = _style_source()

    assert 'id="evidenceDrawer"' in source
    assert "证据抽屉" not in source
    assert "为什么这样练" in source
    assert "data-evidence-drawer" in source
    assert "data-evidence-open" in source
    assert "data-evidence-id" in source
    assert "openEvidenceDrawer" in source
    assert "closeEvidenceDrawer" in source
    assert "resolveEvidenceItemsForDrawer" in source
    assert "查看证据" in source
    assert ".evidence-drawer" in styles
    assert ".evidence-badge-button" in styles


def test_astro_no_evidence_uses_model_knowledge_without_faking_sources():
    source = _index_source()

    assert "llm_general_knowledge" in source
    assert "模型知识说明（未绑定外部证据）" in source
    assert "不能作为核心处方依据" in source
    assert "不生成伪引用" in source
    assert "extractModelKnowledgeAnswer" in source


def test_astro_day_modal_surfaces_auditable_generation_trace():
    source = _index_source()

    assert "workflow_trace" in source
    assert "resolveWorkflowTrace" in source
    assert "legacy_missing" in source
    assert "field_sources" in source
    assert "protocol_check" in source
    assert "action_match" in source
    assert "kb_fallback" in source
    assert "data-audit-trace" in source
    assert '<details class="audit-panel" data-audit-trace hidden data-expert-only>' in source
    assert "sourceTypeLabel" in source
    assert "blocked_core_candidates" in source
    assert "needs_protocol_recheck" in source


def test_astro_saved_plan_rehydrates_event_content_trace():
    source = _index_source()

    assert "parseEventContent" in source
    assert "event.content_json" in source
    assert "...eventContent" in source
    assert "eventContent.workflow_trace" in source
    assert "eventContent.field_sources" in source
    assert "eventContent.action_match" in source
    assert "eventContent.trace" in source


def test_astro_saved_plan_rehydrates_full_product_state_contract():
    source = _index_source()

    for field in [
        "eventContent.field_sources",
        "eventContent.trace",
        "eventContent.risk_gate",
        "eventContent.protocol_check",
        "eventContent.action_match",
        "eventContent.kb_fallback",
        "eventContent.workflow_trace",
        "eventContent.latest_feedback",
        "eventContent.adaptive_adjustment",
    ]:
        assert field in source
    assert "calendar_days: normalizeCalendarDays(state.lastResponse)" in source


def test_astro_day_card_and_modal_surface_non_generated_product_states():
    source = _index_source()

    assert "productStateLabel" in source
    assert "dayProductStatus" in source
    assert "sourceStateLabel" in source
    assert "buildProductStateHtml" in source
    assert "action_library" in source
    assert "needs_evidence" in source
    assert "needs_protocol_recheck" in source
    assert "partial_generated" in source
    assert "待补证据" in source
    assert "待协议复核" in source
    assert "部分生成" in source
    assert "已生成训练安排" in source
    assert 'status === "generated"' in source
    assert "statusLabel(day?.card_status || day?.generation_status)" in source
    assert "field_sources" in source
    assert "evidence_tier" in source
    assert "card_status" in source
    assert "protocol_check" in source
    assert "action_match" in source
    assert "kb_fallback" in source
    assert 'class="day-product-state"' in source
    assert "buildProductStateHtml(day)" in source


def test_astro_feedback_surfaces_risk_gate_and_protocol_recheck():
    source = _index_source()

    assert "risk_gate" in source
    assert "protocol_recheck" in source
    assert "adjustment_action" in source
    assert "generation_status" in source
    assert "data-feedback-risk-gate" in source


def test_astro_feedback_quick_actions_prefill_full_feedback_state():
    source = _index_source()

    assert "FEEDBACK_QUICK_PRESETS" in source
    assert "feedback_done" in source
    assert "feedback_partial" in source
    assert "feedback_skipped" in source
    assert 'data-modal-feedback="feedback_done"' in source
    assert 'data-modal-feedback="feedback_partial"' in source
    assert 'data-modal-feedback="feedback_skipped"' in source
    assert "applyFeedbackPreset(dayModalContent, FEEDBACK_QUICK_PRESETS[presetKey])" in source
    assert "syncFeedbackQuickChoiceUi" in source
    assert "data-feedback-selected" in source
    assert "data-feedback-quick-first" in source
    assert "resetDayModalScrollPosition" in source
    assert 'selectDayModalTab("feedback");' in source
    assert 'selectDayModalTab("feedback", { focus: true });' not in source


def test_astro_feedback_api_carries_day_context_and_preserves_latest_feedback():
    source = _index_source()

    assert "buildFeedbackContext" in source
    assert "plan_id: feedbackContext.plan_id" in source
    assert "event_id: feedbackContext.event_id" in source
    assert "day_key: feedbackContext.day_key" in source
    assert "state.lastFeedbackResult = payload" in source
    assert "function applyLatestFeedbackToLastResponse" in source
    assert "applyLatestFeedbackToDayList(calendar.days" in source
    assert "applyLatestFeedbackToDayList(response.daily_schedule_cards" in source
    assert "structuredPlan.week_plans" in source
    assert "mergeLatestFeedbackIntoAdjustmentHistory" in source
    assert "const latestFeedback = applyLatestFeedbackToLastResponse(payload, state.selectedDay, feedbackContext)" in source
    assert "state.selectedDay.latest_feedback = buildLatestFeedbackSummary(payload)" in source
    assert "adaptive_adjustment: feedbackSummary" in source
    assert "adaptive_adjustment: day.adaptive_adjustment || feedbackSummary" not in source
    assert "adaptive_adjustment: state.selectedDay.adaptive_adjustment || feedbackSummary" not in source
    assert "latest_feedback: eventContent.latest_feedback || event.latest_feedback" in source
    assert "adaptive_adjustment: eventContent.adaptive_adjustment || event.adaptive_adjustment" in source
    assert "buildLatestFeedbackHtml(day)" in source
    assert "data-latest-feedback" in source
    assert "最近一次反馈" in source


def test_astro_feedback_result_card_has_closed_loop_fields_and_product_states():
    source = _index_source()

    assert "feedbackStatusLabel" in source
    assert "feedback_id" in source
    assert "save_status" in source
    assert "data-feedback-product-state" in source
    assert "generated" in source
    assert "partial_generated" in source
    assert "risk_refused" in source
    assert "medical_referral" in source
    assert "停止训练" in source
    assert "专业评估" in source
    assert "评估前安排" in source
    assert "禁止事项" in source
    assert "isMedicalReferralFeedback" in source
    assert "data-feedback-medical-referral" in source
    assert "MEDICAL_RED_FLAGS" in source
    assert "data-medical-red-flag" in source
    assert "buildLocalMedicalReferralPayload" in source
    assert "出于安全边界" in source
    assert "不显示普通已生成" not in source


def test_astro_feedback_requires_saveable_context_before_normal_submit():
    source = _index_source()

    assert "feedbackContextIsSaveable" in source
    assert "先保存这份日历" in source
    assert "反馈需要绑定到具体训练日" in source
    assert "if (!feedbackContextIsSaveable(feedbackContext) && !medical_red_flags.length)" in source


def test_astro_feedback_regenerate_runs_existing_query_flow_with_structured_context():
    source = _index_source()

    assert "buildRegenerationQueryFromFeedback" in source
    assert "feedbackSummaryForPrompt" in source
    assert "adaptiveAdjustmentForPrompt" in source
    assert "affectedDaysForPrompt" in source
    assert "明确列出受影响训练日" in source
    assert "当前反馈摘要" in source
    assert "当前训练日" in source
    assert "原计划主课" in source
    assert "adaptive_adjustment 五段式结果" in source
    assert "await runQuery(regenerationQuery)" in source
    assert "regenerateButton.disabled = false" in source
    assert "if (isMedicalReferralFeedback(payload)) return;" in source


def test_astro_status_panel_and_adjustment_history_render_execution_loop():
    source = _index_source()
    styles = _style_source()

    assert 'id="statusPanel"' in source
    assert 'data-status-panel' in source
    assert 'data-status-risk-level' in source
    assert 'data-missed-feedback-reminder' in source
    assert "renderStatusPanel" in source
    assert "function hasFeedbackRecord" in source
    assert "function isFeedbackDue" in source
    assert "if (!isFeedbackDue(day)) return;" in source
    assert "return trainingDate.getTime() < today.getTime();" in source
    assert "execution_status_summary" in source
    assert "completion_rate" in source
    assert "missed_feedback_count" in source
    assert "next_training_recommendation" in source
    assert "本周执行概览" in source
    assert "下次训练建议" in source
    assert 'attention: "需要关注"' in source
    assert 'unknown: "待反馈确认"' in source
    assert 'deescalate: "建议降级"' in source
    assert "runnerFacingText(summary.next_training_recommendation" in source
    assert "完成第一次训练后记录反馈，再判断是否调整。" in source
    assert "训练后记录反馈，再判断是否调整。" in source
    assert "CycleProgressBar" not in source
    assert "PhaseTimeline" not in source
    assert "CompletedWeeksList" not in source
    assert "medical_referral" in source
    assert ".status-panel" in styles
    assert ".status-panel-grid,\n  .adjustment-history-item dl {\n    grid-template-columns: 1fr;" in styles

    assert 'id="adjustmentHistory"' in source
    assert 'data-adjustment-history' in source
    assert "renderAdjustmentHistory" in source
    assert "adjustment_history" in source
    assert "affected_events" in source
    assert "risk_gate" in source
    assert "protocol_recheck" in source
    assert ".adjustment-history" in styles


def test_astro_normal_user_layer_localizes_english_and_raw_slugs():
    source = _index_source()

    assert "Marathon Assistant" not in source
    assert "Training Calendar Builder" not in source
    assert ">ProfileEditor<" not in source
    assert "Half marathon finish" not in source
    assert "function runnerFacingText" in source
    assert "function looksLikeRawFieldOrEnglish" in source
    assert "runnerFacingEnglishFallbacks" in source
    assert "半马完赛" in source
    assert "训练压力" in source
    assert "安排来源" in source
    assert 'hmp_interval: "半马配速间歇"' in source
    assert 'easy_run: "轻松跑"' in source
    assert 'recovery_run: "恢复跑"' in source
    assert 'long_run: "长距离跑"' in source
    assert "hmpWorkoutLabels[trainingType]" in source
    assert "day.title" in source
    assert "trainingDayLabel(primaryDay)" in source
    assert 'raw.match(/^day\\s*(\\d+)$/i)' in source
    assert "return `第 ${dayMatch[1]} 天`;" in source
    assert "runnerFacingText(weekGoal" in source
    assert "runnerFacingText(summary.weekGoal" in source
    assert "day.training_objective || day.why_scheduled || day.decision_summary || day.week_goal" in source
    assert "day.warmup || day.warmup_text" in source
    assert "day.zone_range || day.zone_label || day.zone || day.intensity_zone" in source
    assert "runnerFacingText(raw.replace" in source
    assert "formatDuration(value)" in source
    assert "`${Math.round(parsed)} 分钟`" in source
    assert "`${distance.toFixed(1)} 公里`" in source
    assert "有效预算跑量 ${protocolCheck.effective_weekly_volume_km} 公里" in source
    assert "Record feedback after the first workout" not in source


def test_astro_rest_days_and_high_loads_are_not_shown_as_unfinished_templates():
    source = _index_source()

    assert "isRestDay" in source
    assert "恢复日，无主课安排。" in source
    assert "loadStatus" in source
    assert "high-load" in source


def test_astro_training_load_copy_makes_proxy_scope_explicit():
    source = _index_source()
    styles = _style_source()

    assert "训练压力" in source
    assert "计划代理负荷" in source
    assert "7日累计代理负荷" in source
    assert "42日折算代理周负荷" in source
    assert "不等同于设备" in source
    assert "frontend_estimated_duration_type" in source
    assert "论文侧负荷证据" not in source
    assert 'not_device_metric: true' in source
    assert 'is_estimated: true' in source
    assert "负荷口径" in source
    assert "近期负荷约为长期承载参考的" in source
    assert "阅读提示" in source
    assert "查看安排" in source
    assert "load-source-list" in source
    assert "横向滑动查看完整趋势" in styles


def test_astro_training_load_summary_surfaces_weekly_quantification():
    source = _index_source()
    styles = _style_source()

    assert "renderWeeklyLoadChanges" in source
    assert "周代理负荷变化" in source
    assert "较上周" in source
    assert "负荷递进" in source
    assert "weekly_load_changes" in source
    assert ".weekly-load-change-list" in styles


def test_astro_day_card_hover_shows_estimated_load_ratio():
    source = _index_source()
    styles = _style_source()

    assert "buildTrainingLoadPointMap" in source
    assert "当日预估负荷比" in source
    assert "占7日累计" in source
    assert "占42日折算代理周负荷" in source
    assert "day-load-tooltip" in source
    assert ".day-card:hover .day-load-tooltip" in styles
    assert ".day-card:focus-visible .day-load-tooltip" in styles


def test_astro_supports_session_only_api_token_for_guarded_backend():
    source = _index_source()

    assert 'id="apiToken"' in source
    assert '"X-Marathon-API-Key": token' in source
    assert "state.apiToken = apiTokenInput.value.trim();" in source
    assert 'localStorage.setItem("marathon-api-token"' not in source
    assert 'sessionStorage.setItem("marathon-api-token"' not in source


def test_astro_openai_provider_uses_server_side_key_status():
    source = _index_source()

    assert 'data-provider-choice="openai"' in source
    assert "api_key_configured" in source
    assert "providerConfig" in source
    assert 'llmProviderInput.value === "openai"' in source
    assert "OPENAI_API_KEY" in source


def test_astro_day_card_always_shows_load_ratio_and_protocol_recheck_state():
    source = _index_source()
    styles = _style_source()

    assert "day-load-ratio-row" in source
    assert "占7日累计" in source
    assert "占42日折算代理周负荷" in source
    assert "requiresProtocolRecheck" in source
    assert "needs-recheck" in source
    assert "待协议复核" in source
    assert ".day-load-ratio-row" in styles
    assert ".day-card.needs-recheck" in styles


def test_astro_calendar_prioritizes_daily_cards_and_restores_day_modal_focus():
    source = _index_source()

    assert "const baseDays = dailyCards.length ? dailyCards : days.length ? days : weekDays;" in source
    assert "return { ...day, ...matchingWeekDay, ...matchingCard };" in source
    assert "lastDayModalTrigger" in source
    assert "state.lastDayModalTrigger = opener instanceof HTMLElement ? opener : document.activeElement;" in source
    assert "dayModalClose.focus();" in source
    assert "state.lastDayModalTrigger?.focus();" in source
    assert "state.lastDayModalTrigger = null;" in source
    assert "openDayModal(days[index], null, button)" in source
    assert "activateFocusTrap(dayModal, closeDayModal)" in source
    assert "deactivateFocusTrap(dayModal)" in source
    assert "activateFocusTrap(evidenceDrawer, closeEvidenceDrawer)" in source
    assert "deactivateFocusTrap(evidenceDrawer)" in source
    assert "handleFocusTrapKeydown(event)" in source
    assert 'event.key === "Tab"' in source
    assert 'event.key === "Escape"' in source
    assert "root.contains(activeLayer)" in source


def test_astro_day_modal_surfaces_trust_status_strip():
    source = _index_source()
    styles = _style_source()
    modal_renderer = source[source.index("function buildDayModalHtml") : source.index("function closeDayModal")]
    plan_panel = modal_renderer[modal_renderer.index('data-day-modal-panel="plan"') : modal_renderer.index('data-day-modal-panel="audit"')]
    audit_panel = modal_renderer[modal_renderer.index('data-day-modal-panel="audit"') : modal_renderer.index('data-day-modal-panel="feedback"')]

    assert "buildTrustStatusHtml" in source
    assert "可信状态" in source
    assert "动作库命中" not in source
    assert "协议通过" not in source
    assert "安排来源" in source
    assert "安全检查" in source
    assert "风险状态" in source
    assert "未完成风险自检" in source
    assert "trust-status-strip" in source
    assert ".trust-status-strip" in styles
    assert "modal-primary-summary" in plan_panel
    assert "buildTrustStatusHtml(day)" not in plan_panel
    assert "modal-metric-grid" not in plan_panel
    assert "buildTrustStatusHtml(day)" in audit_panel
    assert "modal-metric-grid" in audit_panel


def test_astro_mobile_quick_navigation_and_profile_generation_waits_for_save():
    source = _index_source()
    styles = _style_source()

    assert "mobile-quick-nav" in source
    assert 'href="#profile"' in source
    assert 'href="#plan"' in source
    assert 'href="#calendar-section"' in source
    assert 'href="#evidence"' in source
    assert ".mobile-quick-nav" in styles
    assert "await saveProfileDraft();" in source
    assert "formatPlanWeeksForPrompt" in source


def test_astro_surfaces_competitive_runner_calibration_fields():
    source = _index_source()
    styles = _style_source()

    assert '["currentHalfTime", "当前半马 PB", "例如 1:25"]' in source
    assert '["lastMonthMileage", "上个月月跑量", "例如 300 km"]' in source
    assert "current_half_time" in source
    assert "recent_four_week_mileage" in source
    assert "performance_calibration" in source
    assert "能力差距" in source
    assert "当前半马 PB" in source
    assert "目标半马" in source
    assert "秒/公里" in source
    assert "performance-card" in styles


def test_astro_profile_payload_and_calibration_treat_no_limitation_as_safe():
    source = _index_source()

    for field in [
        '["currentHalfTime", "当前半马 PB", "例如 1:25"]',
        '["targetPace", "目标配速/成绩", "例如 半马 1:45 或 5:00/km"]',
        '["lastMonthMileage", "上个月月跑量", "例如 300 km"]',
        '["raceDate", "比赛日期", "例如 2026-10-18"]',
        '["limitations", "伤病/疲劳限制", "例如 膝盖不适，近期疲劳偏高"]',
    ]:
        assert field in source

    assert "function normalizeLimitationText" in source
    assert "function hasProfileLimitation" in source
    for no_limitation in ["无", "无伤病", "无疲劳", "none", "no", "false"]:
        assert no_limitation in source
    assert "const limitationText = normalizeLimitationText(draft.limitations);" in source
    assert "injury: limitationText" in source
    assert "recovery_state: limitationText" in source
    assert "injury_or_fatigue: hasProfileLimitation(draft.limitations)" in source
    assert "target_time: draft.targetPace || \"\"" in source

    performance_renderer = source[
        source.index("function renderPerformanceCalibration") : source.index("function renderRacePrepOverview")
    ]
    assert "state.lastPlanIntent?.currentHalfTime" in performance_renderer
    assert "state.lastPlanIntent?.targetPace" in performance_renderer
    assert "hasCalibrationPair" in performance_renderer
    assert "target_(half_)?(time|pace)" in performance_renderer
    assert "|goal" not in performance_renderer
    assert "formatCalibrationField" in performance_renderer
    assert "待校准" in performance_renderer
    assert "待补充目标成绩" in performance_renderer
    assert "calibration.target_hmp_pace || \"-\"" not in performance_renderer
    assert "calibration.decision_reason ||" not in performance_renderer


def test_astro_day_modal_surfaces_recent_four_week_capacity_basis():
    source = _index_source()

    assert "volume_basis" in source
    assert "recent_four_week_mileage" in source
    assert "容量依据" in source
    assert "有效预算跑量" in source
    assert "近4周跑量" in source


def test_astro_race_prep_overview_and_plan_diff_are_first_class():
    source = _index_source()
    styles = _style_source()

    assert "renderRacePrepOverview" in source
    assert "备赛总览" in source
    assert "本周关键课" in source
    assert "目标可行性" in source
    assert "证据覆盖" in source
    assert "plan_diff" in source
    assert "计划差异" in source
    assert "race-prep-overview" in styles
    assert "key-session-list" in styles


def test_astro_surfaces_protocol_recheck_action_guidance():
    source = _index_source()
    styles = _style_source()

    assert "protocolRecheckActionText" in source
    assert "protocolViolationLabels" in source
    assert "执行前完成疲劳/疼痛自检" in source
    assert "剂量依据待补" in source
    assert "long_run_exceed_cap" in source
    assert "duration_main_set_mismatch" in source
    assert "复核动作" in source
    assert "待复核日" in source
    assert "下一步行动" in source
    assert "只看待复核" in source
    assert "只看关键课" in source
    assert "calendar-filter" in source
    assert "action-guidance" in styles


def test_astro_day_modal_tabs_are_accessible_and_keyboard_driven():
    source = _index_source()

    assert 'role="tablist"' in source
    assert 'role="tab"' in source
    assert 'role="tabpanel"' in source
    assert 'aria-controls="dayModalPanelPlan"' in source
    assert 'aria-labelledby="dayModalTabPlan"' in source
    assert "selectDayModalTab" in source
    assert "handleDayModalTabKeydown" in source
    assert '"ArrowLeft"' in source
    assert '"ArrowRight"' in source
    assert '"Home"' in source
    assert '"End"' in source
    assert "handleSegmentedControlKeydown" in source
    assert 'aria-selected="true" data-calendar-view="week"' in source
    assert 'aria-selected="false" data-calendar-filter="key"' in source


def test_astro_mobile_side_drawer_behaves_like_modal_drawer():
    source = _index_source()
    styles = _style_source()

    assert "side-drawer-backdrop" in source
    assert "side-drawer-close" in source
    assert "data-side-drawer-close" in source
    assert "activateSideDrawerModal" in source
    assert "closeSideDrawer" in source
    assert "setSideDrawerModalInert" in source
    assert "lastSideDrawerTrigger" in source
    assert "side-drawer-modal-open" in source
    assert "closeSideDrawer()" in source
    assert ".side-drawer-backdrop" in styles
    assert ".side-drawer-close" in styles
    assert ".day-modal {\n  z-index: 60;" in styles
    assert ".evidence-drawer {\n  z-index: 70;" in styles


def test_astro_personalized_training_calendar_generation_contract():
    source = _index_source()
    styles = _style_source()

    assert 'const PLAN_GENERATION_PROMPT' in source
    assert 'id="runQuery" class="primary-button" data-plan-generation-entry' in source
    assert '<button id="runProfilePlan" class="primary-button" data-plan-generation-entry>生成训练日历</button>' in source
    assert "复核训练负荷" not in source
    assert "本周降载调整" not in source
    assert "解释单日训练" not in source
    assert 'data-prompt={PLAN_GENERATION_PROMPT}' in source
    assert "profileDraftToPrompt(draft)" in source
    assert 'queryInput.value = query;' in source
    assert 'localStorage.setItem("marathon-profile-draft", JSON.stringify(draft));' in source
    assert "actionableProfileMissingFields" in source
    assert "当前能力或月跑量" in source
    assert "伤病/疲劳限制" in source

    for label in ["准备计划", "解析画像", "生成初稿", "安全校验", "排布日历", "绑定依据", "补全解释"]:
        assert label in source
    assert "连接后端" not in source
    assert "生成骨架" not in source
    assert ".progress-steps" in styles
    assert "repeat(7, minmax(0, 1fr))" in styles

    for stat in ["total-days", "total-weeks", "rest-days", "key-sessions"]:
        assert f'data-calendar-stat="{stat}"' in source
    assert "updateCalendarStat(\"total-days\"" in source
    assert "updateCalendarStat(\"total-weeks\"" in source
    assert "updateCalendarStat(\"rest-days\"" in source
    assert "updateCalendarStat(\"key-sessions\"" in source
    assert ".calendar-stat-strip" in styles

    assert "画像已先保存到本地，本次生成不会被阻塞" in source
    assert "超时" in source
    assert "自动重试" in source
    assert "本地训练服务不可用" in source
    assert "后端不可用" not in source
    assert "缺少我的情况" in source


def test_astro_reading_fatigue_guard_prioritizes_calendar_over_long_reports():
    index_text = FRONTEND_INDEX.read_text(encoding="utf-8")
    source = _index_source()
    styles = _style_source()

    assert 'data-reading-fatigue-guard' in index_text
    assert 'data-secondary-reading-layer' in index_text
    assert '<details class="panel report-panel compact-report-panel" data-reading-fatigue-guard>' in index_text
    assert '<details class="panel report-panel compact-report-panel" data-reading-fatigue-guard open>' not in index_text
    assert "为什么这样安排" in index_text
    assert "按需查看" in index_text

    assert ".main-stack > #calendar-section {\n  order: 2;" in styles
    assert ".main-stack > .dashboard-grid {\n  order: 3;" in styles
    assert ".compact-report-panel #report" in styles
    assert ".report-panel-summary::-webkit-details-marker" in styles

    assert "calendar-action-secondary" in source
    assert "calendar-action-mini" in source
    assert "calendar-action-next" in source
    assert "modal-primary-summary" in source
    assert "return false;" in source[source.index("function isWeekGroupExpanded") : source.index("function weekGroupPanelId")]
    assert "const safetyAction = safety.filter ? \"filter-recheck\" : \"open-day\";" in source
    assert 'data-calendar-action="open-day"' in source
    assert 'data-calendar-action="open-feedback"' in source
    assert 'data-calendar-action="${safetyAction}"' in source
    assert "grid-template-columns: minmax(260px, 1.15fr) minmax(0, 1fr);" in styles
    assert ".calendar-action-mini p {\n  display: none;" in styles
    assert ".calendar-action-mini strong {\n    white-space: normal;" in styles
    assert '<details class="modal-feedback-detail" data-feedback-detail>' in source
    assert '<details class="modal-feedback-detail" data-feedback-detail open>' not in source
    assert "compact-feedback-actions" in source
    assert ".feedback-selected-summary" in styles
    assert ".modal-feedback-detail[open]" in styles
    assert ".day-modal.open {\n    display: flex;" in styles
    assert "max-height: min(92svh, 760px);" in styles
    assert ".day-modal-sticky-actions {\n  border-top-color: #dbe6ea;" in styles
    assert ".day-modal-tab-nav button.active {\n  border-color: rgba(15, 143, 165, 0.42);" in styles
