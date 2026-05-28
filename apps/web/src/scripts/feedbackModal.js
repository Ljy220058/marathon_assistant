// Feedback Modal — 快捷反馈、反馈表单、反馈结果卡和生成调整版计划入口。
// 使用 IIFE 隔离，通过 window.__feedbackModal 暴露 API。

(function () {

  const FEEDBACK_QUICK_PRESETS = {
    feedback_done: { completion: "已完成", fatigue: "轻微", pain: "没有疼痛", sleep: "良好", notes: "" },
    feedback_partial: { completion: "部分完成", fatigue: "明显", pain: "轻微不适", sleep: "一般", notes: "训练部分完成，需要下调后续负荷。" },
    feedback_skipped: { completion: "未完成", fatigue: "高疲劳", pain: "疼痛风险", sleep: "较差", notes: "训练中出现不适或疼痛信号，需要保守调整后续安排。" },
  };

  function applyFeedbackPreset(formContainer, preset) {
    if (!formContainer || !preset) return;
    const completionEl = formContainer.querySelector('[name="completion"]');
    const fatigueEl = formContainer.querySelector('[name="fatigue"]');
    const painEl = formContainer.querySelector('[name="pain"]');
    const sleepEl = formContainer.querySelector('[name="sleep"]');
    const notesEl = formContainer.querySelector('[name="notes"]');
    if (completionEl) completionEl.value = preset.completion || "";
    if (fatigueEl) fatigueEl.value = preset.fatigue || "";
    if (painEl) painEl.value = preset.pain || "";
    if (sleepEl) sleepEl.value = preset.sleep || "";
    if (notesEl && preset.notes) notesEl.value = preset.notes;
  }

  function buildFeedbackResultHtml(payload) {
    const status = payload?.generation_status || payload?.save_status || "unknown";
    const statusLabel = {
      generated: "已生成调整建议",
      partial_generated: "部分生成调整建议",
      medical_referral: "停止训练，建议专业医疗评估",
      risk_refused: "安全阻断，未生成调整建议",
      suggested: "已生成本周调整建议",
      applied: "已应用到日历",
      dismissed: "已暂不采用",
      needs_manual_choice: "本周没有可安全安排的训练日",
      blocked_medical: "不能直接恢复跑步训练",
    }[status] || status;

    const isMedical = status === "medical_referral";
    const nextDayAdj = payload?.next_day_adjustment || "";
    const weeklyAdj = payload?.weekly_adjustment || "";
    const affectedEvents = payload?.affected_events || [];
    const replan = payload?.feedback_replan || null;

    let html = `<div class="feedback-result-card" data-feedback-product-state="${status}"${isMedical ? ' data-feedback-medical-referral' : ''}>`;
    html += `<strong>${statusLabel}</strong>`;

    if (isMedical) {
      html += `<p class="medical-referral-notice">出于安全边界，建议暂停训练并寻求专业医疗评估。评估前安排：${payload?.pre_evaluation_plan || "暂不提供训练安排"}</p>`;
      html += `<p class="medical-prohibition">禁止事项：${payload?.prohibited_activities || "不进行高强度或长距离训练"}</p>`;
    }

    if (nextDayAdj) html += `<p><span>明日调整：</span>${nextDayAdj}</p>`;
    if (weeklyAdj) html += `<p><span>本周微调：</span>${weeklyAdj}</p>`;
    if (affectedEvents.length) {
      html += `<p><span>可能影响的后续训练：</span>${affectedEvents.map(e => e.day_label || e.event_id).join("、")}</p>`;
    }

    if (replan?.patches?.length) {
      html += `<div class="feedback-replan" data-feedback-replan>`;
      html += replan.patches.map((patch, i) => `
        <div class="replan-patch">
          <p>原安排：${patch.original?.main_set || "-"}</p>
          <p>建议：${patch.suggested?.main_set || "-"}</p>
          <div class="replan-actions">
            <button type="button" data-feedback-replan-action="accept" data-patch-index="${i}">按调整执行</button>
            <button type="button" data-feedback-replan-action="replan" data-patch-index="${i}">重新排本周</button>
            <button type="button" data-feedback-replan-action="dismiss" data-patch-index="${i}">暂不采用</button>
          </div>
        </div>
      `).join("");
      html += `</div>`;
    }

    html += `</div>`;
    return html;
  }

  async function submitFeedbackApi(root) {
    // 委托给 app.js 中的 submitFeedbackApi
    if (typeof window.submitFeedbackApi === "function" && window.submitFeedbackApi !== submitFeedbackApi) {
      return window.submitFeedbackApi(root);
    }
    throw new Error("反馈提交模块尚未完全加载，请刷新页面后重试。");
  }

  function isMedicalReferralFeedback(payload) {
    return (payload?.generation_status || payload?.save_status) === "medical_referral";
  }

  window.__feedbackModal = {
    applyFeedbackPreset, buildFeedbackResultHtml, submitFeedbackApi,
    isMedicalReferralFeedback, FEEDBACK_QUICK_PRESETS,
  };
})();
