from pathlib import Path


FRONTEND_INDEX = Path(__file__).resolve().parents[1] / "frontend" / "src" / "pages" / "index.astro"
FRONTEND_STYLE = Path(__file__).resolve().parents[1] / "frontend" / "src" / "styles" / "global.css"


def _index_source() -> str:
    return FRONTEND_INDEX.read_text(encoding="utf-8")


def _style_source() -> str:
    return FRONTEND_STYLE.read_text(encoding="utf-8")


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
    assert "完整计划未截断" in source
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


def test_astro_profile_calendar_and_basis_are_moved_into_sidebar_drawer():
    source = _index_source()

    assert 'id="drawerWorkspaceSections"' in source
    assert 'class="drawer-workspace-sections"' in source
    assert 'data-drawer-section="profile"' in source
    assert 'data-drawer-section="calendar"' in source
    assert 'data-drawer-section="basis"' in source
    assert "moveWorkspaceSectionsToDrawer" in source
    assert '["profile", "calendar-section", "evidence"]' in source
    assert "drawerSections.appendChild(section)" in source


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
    assert "画像 / 日历 / 依据" in source
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
    assert 'class="day-card-summary"' not in source
    assert '<p>${escapeHtml(mainText)}</p>' not in source
    assert ".day-card-essentials" in styles
    assert ".day-risk-pill" in styles


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
    assert "padding-bottom: 132px" in styles


def test_frontend_workspace_smoke_script_covers_p0_to_p4():
    smoke = Path("frontend/scripts/smoke-workspace.mjs")

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
    assert "系统估算平均周跑量" in source
    assert "系统倒推计划周期" in source
    assert "toggleHistoryList" in source
    assert ".slice(0, 3)" in source


def test_astro_runner_identity_card_and_profile_editor_use_unified_profile_api():
    source = _index_source()
    styles = _style_source()

    assert "RunnerIdentityCard" in source
    assert "runnerIdentityCard" in source
    assert "renderRunnerIdentityCard" in source
    assert "ProfileEditor" in source
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

    assert "半马 HMP 基石协议" in source
    assert "protocol_rule" in source
    assert "日卡会优先展示结构化规则和 HMP 基石协议依据" in source


def test_astro_day_modal_surfaces_auditable_generation_trace():
    source = _index_source()

    assert "field_sources" in source
    assert "protocol_check" in source
    assert "action_match" in source
    assert "kb_fallback" in source
    assert "data-audit-trace" in source
    assert "sourceTypeLabel" in source
    assert "blocked_core_candidates" in source
    assert "needs_protocol_recheck" in source


def test_astro_saved_plan_rehydrates_event_content_trace():
    source = _index_source()

    assert "parseEventContent" in source
    assert "event.content_json" in source
    assert "...eventContent" in source
    assert "eventContent.field_sources" in source
    assert "eventContent.action_match" in source
    assert "eventContent.trace" in source


def test_astro_feedback_surfaces_risk_gate_and_protocol_recheck():
    source = _index_source()

    assert "risk_gate" in source
    assert "protocol_recheck" in source
    assert "adjustment_action" in source
    assert "generation_status" in source
    assert "data-feedback-risk-gate" in source


def test_astro_rest_days_and_high_loads_are_not_shown_as_unfinished_templates():
    source = _index_source()

    assert "isRestDay" in source
    assert "恢复日，无主课安排。" in source
    assert "loadStatus" in source
    assert "high-load" in source


def test_astro_training_load_copy_makes_proxy_scope_explicit():
    source = _index_source()
    styles = _style_source()

    assert "计划代理负荷" in source
    assert "7日累计负荷" in source
    assert "42日折算周负荷" in source
    assert "不等同于设备" in source
    assert "frontend_estimated_duration_type" in source
    assert "负荷口径" in source
    assert "近期负荷约为长期承载参考的" in source
    assert "阅读提示" in source
    assert "查看详情" in source
    assert "load-source-list" in source
    assert "横向滑动查看完整趋势" in styles


def test_astro_training_load_summary_surfaces_weekly_quantification():
    source = _index_source()
    styles = _style_source()

    assert "renderWeeklyLoadChanges" in source
    assert "周负荷变化" in source
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
    assert "占42日折算周负荷" in source
    assert "day-load-tooltip" in source
    assert ".day-card:hover .day-load-tooltip" in styles
    assert ".day-card:focus-visible .day-load-tooltip" in styles


def test_astro_day_card_always_shows_load_ratio_and_protocol_recheck_state():
    source = _index_source()
    styles = _style_source()

    assert "day-load-ratio-row" in source
    assert "占7日累计" in source
    assert "占42日折算周负荷" in source
    assert "requiresProtocolRecheck" in source
    assert "needs-recheck" in source
    assert "待协议复核" in source
    assert ".day-load-ratio-row" in styles
    assert ".day-card.needs-recheck" in styles


def test_astro_day_modal_surfaces_trust_status_strip():
    source = _index_source()
    styles = _style_source()

    assert "buildTrustStatusHtml" in source
    assert "可信状态" in source
    assert "动作库命中" in source
    assert "协议通过" in source
    assert "风险状态" in source
    assert "trust-status-strip" in source
    assert ".trust-status-strip" in styles


def test_astro_mobile_quick_navigation_and_profile_generation_waits_for_save():
    source = _index_source()
    styles = _style_source()

    assert "mobile-quick-nav" in source
    assert 'href="#profile"' in source
    assert 'href="#plan"' in source
    assert 'href="#calendar-section"' in source
    assert 'href="#evidence"' in source
    assert ".mobile-quick-nav" in styles
    assert "await buildProfilePrompt();" in source
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
    assert "long_run_exceed_cap" in source
    assert "duration_main_set_mismatch" in source
    assert "复核动作" in source
    assert "待复核日" in source
    assert "下一步行动" in source
    assert "只看待复核" in source
    assert "只看关键课" in source
    assert "calendar-filter" in source
    assert "action-guidance" in styles
