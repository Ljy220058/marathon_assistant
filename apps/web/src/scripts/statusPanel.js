// Status Panel — StatusPanel、CycleProgressBar、PhaseTimeline、CompletedWeeksList、AdjustmentHistory 渲染。
// 使用 IIFE 隔离，通过 window.__statusPanel 暴露 API。

(function () {

  function renderStatusPanel(response) {
    // 委托给 app.js 的同名函数
    if (typeof window.renderStatusPanel === "function" && window.renderStatusPanel !== renderStatusPanel) {
      return window.renderStatusPanel(response);
    }
    const panel = document.getElementById("statusPanel");
    if (!panel) return;
    const summary = response?.execution_status_summary || response?.structured_report?.execution_status_summary || {};
    const completionRate = summary.completion_rate != null ? `${Math.round(summary.completion_rate * 100)}%` : "-";
    const missedFeedback = summary.missed_feedback_count ?? "-";
    const nextRec = summary.next_training_recommendation || "完成训练后记录反馈。";

    panel.hidden = false;
    panel.className = "status-panel";
    panel.setAttribute("data-status-risk-level", summary.risk_level || "unknown");
    panel.innerHTML = `
      <div class="status-panel-grid">
        <div class="status-card">
          <span>本周执行概览</span>
          <strong>${completionRate}</strong>
          <small>完成率</small>
        </div>
        <div class="status-card">
          <span>待反馈</span>
          <strong>${missedFeedback}</strong>
          <small>未记录反馈</small>
        </div>
        <div class="status-card">
          <span>下次训练建议</span>
          <strong>${nextRec}</strong>
        </div>
      </div>
    `;
  }

  function renderAdjustmentHistory(response) {
    if (typeof window.renderAdjustmentHistory === "function" && window.renderAdjustmentHistory !== renderAdjustmentHistory) {
      return window.renderAdjustmentHistory(response);
    }
    const history = document.getElementById("adjustmentHistory");
    if (!history) return;
    const items = response?.adjustment_history || response?.structured_report?.adjustment_history || [];
    if (!items.length) {
      history.hidden = true;
      return;
    }
    history.hidden = false;
    history.className = "adjustment-history";
    history.innerHTML = items.map((item, idx) => {
      const feedbackId = item.feedback_id || `adj-${idx}`;
      const riskGate = item.risk_gate || {};
      const protocolRecheck = item.protocol_recheck || {};
      const affected = Array.isArray(item.affected_events) ? item.affected_events.join("、") : "-";
      return `
        <div class="adjustment-history-item">
          <span>[${idx + 1}] ${feedbackId}</span>
          <dl>
            <dt>风险门</dt><dd>${riskGate.status || riskGate.result || "未评估"}</dd>
            <dt>协议复核</dt><dd>${protocolRecheck.status || protocolRecheck.result || "未评估"}</dd>
            <dt>影响训练</dt><dd>${affected}</dd>
          </dl>
        </div>
      `;
    }).join("");
  }

  function hasFeedbackRecord(day) {
    return !!(day?.latest_feedback || day?.feedback_result || day?.feedback_id);
  }

  function isFeedbackDue(day) {
    if (!day?.scheduled_date) return false;
    const trainingDate = new Date(day.scheduled_date);
    if (isNaN(trainingDate.getTime())) return false;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return trainingDate.getTime() < today.getTime();
  }

  window.__statusPanel = { renderStatusPanel, renderAdjustmentHistory, hasFeedbackRecord, isFeedbackDue };
})();
