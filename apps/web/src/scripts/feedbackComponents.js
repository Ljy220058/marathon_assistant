// feedbackComponents.js — Progressive feedback form and adaptive adjustment notice [product-feedback][P1]
// FeedbackDetailForm: 渐近式填写表单
// AdaptiveAdjustmentNotice: 调整通知

/**
 * Render a progressive feedback detail form.
 * Starts collapsed, expands when user clicks to provide details.
 * @param {{ day: object, preset: string|null }} options
 * @returns {string} HTML
 */
export function renderFeedbackDetailForm({ day = {}, preset = null } = {}) {
  const isRest = day && (day.training_load === 0 || /rest|休息|恢复/i.test(String(day.main_set || day.training_title || "")));

  return `
    <form class="feedback-detail-form" data-feedback-detail-form aria-label="训练反馈详情" novalidate>
      <div class="feedback-detail-header">
        <div>
          <p class="section-kicker">训练反馈</p>
          <h3>记录本次训练感受</h3>
        </div>
        <span class="feedback-progress-label" data-feedback-progress>1/4 完成</span>
      </div>

      <!-- Step 1: Completion -->
      <fieldset class="feedback-step" data-feedback-step="1">
        <legend>1. 本次训练完成情况</legend>
        <div class="feedback-radio-group">
          <label>
            <input type="radio" name="completion" value="已完成" data-feedback-quick ${preset === "feedback_done" ? "checked" : ""} />
            <span>已完成</span>
          </label>
          <label>
            <input type="radio" name="completion" value="部分完成" data-feedback-quick ${preset === "feedback_partial" ? "checked" : ""} />
            <span>部分完成</span>
          </label>
          <label>
            <input type="radio" name="completion" value="未完成" data-feedback-quick ${preset === "feedback_skipped" ? "checked" : ""} />
            <span>未完成 / 跳过</span>
          </label>
        </div>
        <button type="button" class="feedback-next-step secondary-button compact-button" data-feedback-next>继续</button>
      </fieldset>

      <!-- Step 2: Fatigue & Sleep -->
      <fieldset class="feedback-step" data-feedback-step="2" hidden>
        <legend>2. 疲劳和恢复</legend>
        <label>
          <span>主观疲劳感</span>
          <select name="fatigue" data-feedback-field="fatigue">
            <option value="">请选择</option>
            <option value="轻微">轻微 — 感觉轻松</option>
            <option value="中等">中等 — 正常疲劳</option>
            <option value="明显">明显 — 比较疲劳</option>
            <option value="高疲劳">高疲劳 — 非常疲倦</option>
          </select>
        </label>
        <label>
          <span>昨天睡眠质量</span>
          <select name="sleep" data-feedback-field="sleep">
            <option value="">请选择</option>
            <option value="良好">良好 — 睡够了</option>
            <option value="一般">一般 — 凑合</option>
            <option value="较差">较差 — 没睡好</option>
          </select>
        </label>
        <button type="button" class="feedback-next-step secondary-button compact-button" data-feedback-next>继续</button>
      </fieldset>

      <!-- Step 3: Pain & Discomfort -->
      <fieldset class="feedback-step" data-feedback-step="3" hidden>
        <legend>3. 身体感受</legend>
        <label>
          <span>疼痛或不适部位</span>
          <select name="pain" data-feedback-field="pain">
            <option value="">请选择</option>
            <option value="没有疼痛">没有疼痛 — 一切正常</option>
            <option value="轻微不适">轻微不适 — 可承受</option>
            <option value="疼痛风险">疼痛风险 — 需要关注</option>
          </select>
        </label>
        <div class="feedback-red-flags">
          <span>需要先评估的异常信号（可多选）</span>
          <div class="red-flag-options">
            <label><input type="checkbox" name="medical_red_flag" value="chest_pain" /> <span>胸痛或胸闷</span></label>
            <label><input type="checkbox" name="medical_red_flag" value="dizziness_or_fainting" /> <span>头晕或站立不稳</span></label>
            <label><input type="checkbox" name="medical_red_flag" value="heat_illness" /> <span>疑似热病或异常高热</span></label>
            <label><input type="checkbox" name="medical_red_flag" value="breathing_difficulty" /> <span>呼吸困难或气短</span></label>
            <label><input type="checkbox" name="medical_red_flag" value="abnormal_heartbeat" /> <span>异常心悸或心律不齐</span></label>
          </div>
        </div>
        <button type="button" class="feedback-next-step secondary-button compact-button" data-feedback-next>继续</button>
      </fieldset>

      <!-- Step 4: Notes -->
      <fieldset class="feedback-step" data-feedback-step="4" hidden>
        <legend>4. 补充说明</legend>
        <label>
          <span>备注（可选）</span>
          <textarea name="notes" data-feedback-field="notes" placeholder="例如：后半程心率偏高，第二天小腿紧张。本周二周四上课跑不了。" rows="3"></textarea>
        </label>
        <div class="feedback-form-actions">
          <button type="submit" class="primary-button" data-feedback-submit>提交反馈</button>
          <button type="button" class="secondary-button" data-feedback-prev>返回上一步</button>
        </div>
      </fieldset>
    </form>
  `;
}

/**
 * Render an Adaptive Adjustment Notice after feedback submission.
 * @param {{ riskLevel: string, adjustmentSummary: string, nextDayLabel: string,
 *           nextDayAdjustment: string, affectedCount: number }} result
 * @returns {string} HTML
 */
export function renderAdaptiveAdjustmentNotice(result = {}) {
  if (!result || !result.riskLevel) {
    return `<div class="adaptive-notice-empty empty-state" data-adaptive-adjustment-notice>
      提交反馈后，调整通知会显示在这里。
    </div>`;
  }

  const { riskLevel, adjustmentSummary, nextDayLabel, nextDayAdjustment, affectedCount } = result;
  const isAdjusted = riskLevel === "deescalate" || riskLevel === "medical_referral";
  const noticeClass = isAdjusted ? "adjustment-significant" : "adjustment-minor";

  return `
    <section class="adaptive-adjustment-notice ${noticeClass}" data-adaptive-adjustment-notice aria-live="polite" aria-atomic="true">
      <div class="adjustment-notice-head">
        <span class="adjustment-icon" aria-hidden="true">${isAdjusted ? "!" : "i"}</span>
        <div>
          <p class="section-kicker">计划调整</p>
          <h3>${isAdjusted ? "计划已调整" : "计划保持不变"}</h3>
        </div>
        <span class="adjustment-badge ${riskLevel}">${escapeHtml(riskLevelLabel(riskLevel))}</span>
      </div>
      <p class="adjustment-notice-body">${escapeHtml(adjustmentSummary || "系统已根据你的反馈评估了当前状态。")}</p>
      ${isAdjusted ? `
        <div class="adjustment-notice-details">
          ${nextDayLabel ? `
            <div>
              <span>下次训练</span>
              <strong>${escapeHtml(nextDayLabel)}</strong>
            </div>
          ` : ""}
          ${nextDayAdjustment ? `
            <div>
              <span>调整建议</span>
              <strong>${escapeHtml(nextDayAdjustment)}</strong>
            </div>
          ` : ""}
          ${affectedCount ? `
            <div>
              <span>影响范围</span>
              <strong>${escapeHtml(affectedCount)} 个后续训练日</strong>
            </div>
          ` : ""}
        </div>
      ` : `
        <div class="adjustment-notice-details">
          <div>
            <span>建议</span>
            <strong>按计划继续执行。训练后及时记录反馈。</strong>
          </div>
        </div>
      `}
      <div class="adjustment-notice-actions">
        <button type="button" class="primary-button compact-button" data-view-updated-plan>查看更新后的计划</button>
        <button type="button" class="secondary-button compact-button" data-dismiss-notice>知道了</button>
      </div>
    </section>
  `;
}

/**
 * Determine the current step of the progressive form and advance.
 */
export function advanceFeedbackStep(form) {
  const steps = Array.from(form.querySelectorAll("[data-feedback-step]"));
  const currentIndex = steps.findIndex((s) => !s.hidden);
  if (currentIndex >= 0 && currentIndex < steps.length - 1) {
    steps[currentIndex].hidden = true;
    steps[currentIndex + 1].hidden = false;
    updateFeedbackProgress(form, currentIndex + 2);
    steps[currentIndex + 1].querySelector("input, select, textarea")?.focus();
  }
}

/**
 * Go back one step in the progressive form.
 */
export function goBackFeedbackStep(form) {
  const steps = Array.from(form.querySelectorAll("[data-feedback-step]"));
  const currentIndex = steps.findIndex((s) => !s.hidden);
  if (currentIndex > 0) {
    steps[currentIndex].hidden = true;
    steps[currentIndex - 1].hidden = false;
    updateFeedbackProgress(form, currentIndex);
    steps[currentIndex - 1].querySelector("input, select, textarea")?.focus();
  }
}

function updateFeedbackProgress(form, step) {
  const total = form.querySelectorAll("[data-feedback-step]").length;
  const label = form.querySelector("[data-feedback-progress]");
  if (label) {
    label.textContent = `${step}/${total} 完成`;
  }
}

/**
 * Collect feedback data from the progressive form.
 */
export function collectFeedbackFormData(form) {
  const data = {};
  form.querySelectorAll("[data-feedback-field], [name]").forEach((input) => {
    const key = input.dataset.feedbackField || input.name;
    if (!key) return;
    if (input.type === "checkbox") {
      if (!data[key]) data[key] = [];
      if (input.checked) data[key].push(input.value);
    } else if (input.type === "radio") {
      if (input.checked) data[key] = input.value;
    } else {
      const value = String(input.value || "").trim();
      if (value) data[key] = value;
    }
  });
  // Collect medical red flags as array
  const flags = Array.from(form.querySelectorAll('[name="medical_red_flag"]:checked'))
    .map((cb) => cb.value);
  if (flags.length) data.medical_red_flags = flags;
  return data;
}

function escapeHtml(str) {
  if (typeof str !== "string") return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

function riskLevelLabel(level) {
  const labels = {
    medical_referral: "需就医评估",
    deescalate: "需降级调整",
    attention: "需关注",
    normal: "正常",
  };
  return labels[level] || level || "未知";
}

// Expose globally for non-module usage
if (typeof window !== "undefined") {
  Object.assign(window, {
    renderFeedbackDetailForm,
    renderAdaptiveAdjustmentNotice,
    advanceFeedbackStep,
    goBackFeedbackStep,
    collectFeedbackFormData,
  });
}
