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


def test_astro_profile_controls_plan_weeks_and_history_is_collapsed():
    source = _index_source()

    assert '["planWeeks", "计划周期", "例如 12 周"]' in source
    assert "plan_duration_weeks" in source
    assert "周期说明" in source
    assert "toggleHistoryList" in source
    assert ".slice(0, 3)" in source


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
    assert '["recentFourWeekMileage", "近4周平均周跑量", "例如 70 km"]' in source
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
