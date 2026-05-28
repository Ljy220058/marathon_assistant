// progressComponents.js — Progress visualization components [product-progress][P1]
// CycleProgressBar, PhaseTimeline, CompletedWeeksList, AdjustmentHistory

/**
 * Render a cycle progress bar showing weeks completed / total.
 * @param {{ currentWeek: number, totalWeeks: number, completedWeeks: number[] }} params
 * @returns {string} HTML
 */
function renderCycleProgressBar({ currentWeek = 1, totalWeeks = 0, completedWeeks = [] } = {}) {
  if (!totalWeeks) {
    return `<div class="cycle-progress-bar empty-state" data-cycle-progress-bar>尚未生成训练计划。</div>`;
  }
  const progress = Math.max(0, Math.min(100, totalWeeks > 0 ? (currentWeek / totalWeeks) * 100 : 0));
  const completedCount = completedWeeks.length;

  return `
    <section class="cycle-progress-bar" data-cycle-progress-bar aria-label="训练周期进度">
      <div class="cycle-progress-head">
        <div>
          <p class="section-kicker">训练进度</p>
          <h3>周期进度</h3>
        </div>
        <span>${escapeHtml(currentWeek)} / ${escapeHtml(totalWeeks)} 周</span>
      </div>
      <div class="cycle-progress-track" aria-hidden="true">
        <div class="cycle-progress-fill" style="width: ${progress}%"></div>
      </div>
      <div class="cycle-progress-meta">
        <span>已完成 ${escapeHtml(completedCount)} 周</span>
        <span>剩余 ${escapeHtml(Math.max(0, totalWeeks - currentWeek))} 周</span>
      </div>
    </section>
  `;
}

/**
 * Render a phase timeline showing training phases across weeks.
 * @param {Array<{ name: string, startWeek: number, endWeek: number, weekCount: number,
 *                 objective: string, current?: boolean, completed?: boolean }>} phases
 * @returns {string} HTML
 */
function renderPhaseTimeline(phases = []) {
  if (!phases.length) {
    return `<div class="phase-timeline empty-state" data-phase-timeline>暂无阶段信息。</div>`;
  }

  const totalWeeks = phases.length ? phases[phases.length - 1].endWeek : 0;

  return `
    <section class="phase-timeline" data-phase-timeline aria-label="训练阶段时间线">
      <div class="phase-timeline-head">
        <p class="section-kicker">训练阶段</p>
        <h3>阶段划分</h3>
      </div>
      <div class="phase-timeline-track">
        ${phases.map((phase, index) => {
          const width = totalWeeks > 0 ? ((phase.weekCount / totalWeeks) * 100) : 0;
          const statusClass = phase.current ? "current" : phase.completed ? "completed" : "upcoming";
          return `
            <div class="phase-timeline-segment ${statusClass}" style="flex: ${Math.max(1, phase.weekCount)}" data-phase-segment>
              <div class="phase-timeline-bar"></div>
              <div class="phase-timeline-label">
                <strong>${escapeHtml(phase.name)}</strong>
                <span>W${escapeHtml(phase.startWeek)}-W${escapeHtml(phase.endWeek)} (${escapeHtml(phase.weekCount)}周)</span>
                ${phase.objective ? `<small>${escapeHtml(phase.objective)}</small>` : ""}
              </div>
            </div>
          `;
        }).join("")}
      </div>
    </section>
  `;
}

/**
 * Render completed weeks list with summary cards.
 * @param {Array<{ weekIndex: number, label: string, completionRate: number,
 *                 keyWorkouts: string[], goalSummary: string, phase: string }>} weeks
 * @returns {string} HTML
 */
function renderCompletedWeeksList(weeks = []) {
  if (!weeks.length) {
    return `<div class="completed-weeks-list empty-state" data-completed-weeks-list>暂无已完成周记录。</div>`;
  }

  return `
    <section class="completed-weeks-list" data-completed-weeks-list aria-label="已完成训练周">
      <div class="completed-weeks-head">
        <p class="section-kicker">训练历史</p>
        <h3>已完成训练周</h3>
      </div>
      <div class="completed-weeks-grid">
        ${weeks.map((week) => `
          <article class="completed-week-card" data-week-card="${week.weekIndex}">
            <div class="completed-week-head">
              <strong>${escapeHtml(week.label || `第 ${week.weekIndex} 周`)}</strong>
              <span class="completion-badge completion-${completionClass(week.completionRate)}">
                ${escapeHtml(week.completionRate)}%
              </span>
            </div>
            <span class="completed-week-phase">${escapeHtml(week.phase || "训练期")}</span>
            ${week.keyWorkouts && week.keyWorkouts.length ? `
              <div class="completed-week-workouts">
                <span>关键训练</span>
                <p>${escapeHtml(week.keyWorkouts.join("、"))}</p>
              </div>
            ` : ""}
            ${week.goalSummary ? `<p class="completed-week-goal">${escapeHtml(week.goalSummary)}</p>` : ""}
            <div class="completed-week-progress">
              <div class="completed-week-fill" style="width: ${week.completionRate}%"></div>
            </div>
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

/**
 * Render adjustment history as a standalone component.
 * @param {Array<{ date: string, reason: string, content: string, riskLevel: string,
 *                 affectedDays: string[] }>} history
 * @returns {string} HTML
 */
function renderAdjustmentHistoryList(history = []) {
  if (!history.length) {
    return `<div class="adjustment-history-list empty-state" data-adjustment-history-list>
      暂无调整记录。保存反馈后，调整历史会在这里显示。
    </div>`;
  }

  return `
    <section class="adjustment-history-list" data-adjustment-history-list aria-label="调整历史">
      <div class="adjustment-history-head">
        <p class="section-kicker">反馈调整</p>
        <h3>调整历史</h3>
      </div>
      <div class="adjustment-history-items">
        ${history.slice(0, 10).map((item) => `
          <article class="adjustment-history-card">
            <div class="adjustment-history-card-head">
              <strong>${escapeHtml(item.date || "调整记录")}</strong>
              <span class="risk-badge risk-${item.riskLevel || "unknown"}">${escapeHtml(item.riskLevel || "未知")}</span>
            </div>
            <p>${escapeHtml(item.reason || item.content || "已根据反馈自动调整计划。")}</p>
            ${item.affectedDays && item.affectedDays.length ? `
              <div class="adjustment-affected-days">
                <span>影响训练日</span>
                <small>${escapeHtml(item.affectedDays.slice(0, 5).join("、"))}${item.affectedDays.length > 5 ? " 等" : ""}</small>
              </div>
            ` : ""}
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

function completionClass(rate) {
  const r = Number(rate) || 0;
  if (r >= 90) return "high";
  if (r >= 60) return "medium";
  return "low";
}

function escapeHtml(str) {
  if (typeof str !== "string") return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

// Expose globally for non-module usage
if (typeof window !== "undefined") {
  Object.assign(window, {
    renderCycleProgressBar,
    renderPhaseTimeline,
    renderCompletedWeeksList,
    renderAdjustmentHistoryList,
  });
}
