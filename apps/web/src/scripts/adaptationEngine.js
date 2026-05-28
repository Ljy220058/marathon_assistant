// adaptationEngine.js — Adaptive explanation engine [product-explanation][P1]
// 用户提交高疲劳、未完成或不适反馈后，生成计划调整说明
// Uses globally-exposed evaluateSingleFeedbackRisk and riskLevelLabel_riskRules from riskRules.js

/**
 * Build an adaptive explanation from a feedback submission result.
 * @param {{ feedback: object, riskResult: object, replan: object|null, affectedDays: object[] }} input
 * @returns {{ title: string, riskBanner: string, adjustmentSummary: string, details: object[], nextActions: string[] }}
 */
function buildAdaptiveExplanation(input = {}) {
  const { feedback = {}, riskResult = null, replan = null, affectedDays = [] } = input;
  const risk = riskResult || evaluateSingleFeedbackRisk(feedback);
  const { riskLevel, reasons, totalRiskScore } = risk;

  const title = riskLevel === "medical_referral"
    ? "需要专业评估"
    : riskLevel === "deescalate"
      ? "计划已调整"
      : riskLevel === "attention"
        ? "请关注恢复"
        : "按计划执行";

  const riskBanner = riskLevel === "medical_referral"
    ? "检测到需要先停止训练并进行专业医疗评估的异常信号。"
    : riskLevel === "deescalate"
      ? `风险等级：${riskLevelLabel(riskLevel)} — 系统已根据你的反馈自动降低后续训练强度。`
      : riskLevel === "attention"
        ? `风险等级：${riskLevelLabel(riskLevel)} — 建议在下次训练前评估疲劳和疼痛状态。`
        : `风险等级：${riskLevelLabel(riskLevel)} — 当前安排可正常执行。`;

  let adjustmentSummary = "";
  const details = [];
  const nextActions = [];

  // Decode reasons into human-readable detail items
  const reasonDetails = decodeRiskReasons(reasons);
  details.push(...reasonDetails);

  // Check replan information
  if (replan) {
    if (replan.protocol_recheck) {
      const check = replan.protocol_recheck;
      details.push({
        label: "安全校验",
        value: check.allowed === false
          ? "协议复核未通过，当前计划需重新评估。"
          : check.allowed === true
            ? "协议复核通过，可在降级范围内继续训练。"
            : "协议状态待定。",
      });
    }
    if (replan.risk_gate) {
      const gate = replan.risk_gate;
      details.push({
        label: "风险评估",
        value: gate.product_status === "medical_referral"
          ? "触发医疗转诊建议，应停止训练。"
          : gate.status === "deescalate"
            ? "触发降级建议，后续训练应降低强度或减量。"
            : "风险在可控范围内。",
      });
    }
    if (replan.adaptive_adjustment) {
      const adj = replan.adaptive_adjustment;
      if (adj.rationale) {
        details.push({ label: "调整原因", value: adj.rationale });
      }
      if (adj.next_day_adjustment) {
        details.push({ label: "下次训练", value: adj.next_day_adjustment });
      }
      if (adj.plan_diff) {
        details.push({ label: "计划变更", value: typeof adj.plan_diff === "string" ? adj.plan_diff : JSON.stringify(adj.plan_diff) });
      }
    }
  }

  // Affected days
  if (affectedDays.length) {
    const dayLabels = affectedDays
      .slice(0, 5)
      .map((d) => d.day_label || d.event_id || d.day_key || "训练日")
      .join("、");
    adjustmentSummary = `已影响 ${affectedDays.length} 个后续训练日：${dayLabels}${affectedDays.length > 5 ? "等" : ""}。`;
    details.push({ label: "影响范围", value: `${affectedDays.length} 个训练日已调整` });
  } else if (riskLevel === "deescalate") {
    adjustmentSummary = "后续训练已降级，请查看日历中的更新安排。";
  } else if (riskLevel === "attention") {
    adjustmentSummary = "当前计划未大幅调整，但建议关注恢复状态。";
  } else {
    adjustmentSummary = "当前计划保持不变。";
  }

  // Next actions
  if (riskLevel === "medical_referral") {
    nextActions.push("立即咨询医生或运动康复专业人士。");
    nextActions.push("在专业评估完成前，不要恢复训练。");
  } else if (riskLevel === "deescalate") {
    nextActions.push("下次训练优先降低强度或缩短时长。");
    nextActions.push("连续两次降级后，考虑减少本周总训练次数。");
    nextActions.push("训练后及时记录反馈以持续评估恢复。");
  } else if (riskLevel === "attention") {
    nextActions.push("训练前评估疲劳和疼痛状态。");
    nextActions.push("确保睡眠充足（建议 7-8 小时）。");
    nextActions.push("如有不适，及时降级为轻松跑或休息。");
  } else {
    nextActions.push("按计划执行训练。");
    nextActions.push("训练后记录完成度和体感反馈。");
  }

  return { title, riskBanner, adjustmentSummary, details, nextActions, riskLevel, totalRiskScore };
}

/**
 * Decode risk reason codes into human-readable labels.
 */
function decodeRiskReasons(reasons = []) {
  const reasonMap = {
    medical_flag: { label: "医疗警示", value: "检测到需要专业医疗评估的异常信号。" },
    pain_risk: { label: "疼痛风险", value: "训练中出现疼痛信号，建议降级或休息。" },
    discomfort: { label: "轻微不适", value: "有轻微不适，继续训练时注意观察。" },
    high_fatigue: { label: "高疲劳", value: "疲劳水平较高，建议降低训练强度或增加恢复时间。" },
    moderate_fatigue: { label: "中度疲劳", value: "疲劳水平中等，注意恢复。" },
    poor_sleep: { label: "睡眠不佳", value: "最近睡眠质量较差，可能影响训练效果和恢复。" },
    session_missed: { label: "训练未完成", value: "训练未按计划完成，需评估是否因疲劳或不适。" },
    session_partial: { label: "训练部分完成", value: "训练部分完成，建议关注下次训练的体感。" },
    high_acute_load: { label: "短期负荷偏高", value: "近 7 日训练负荷较高，需注意恢复窗口。" },
    acwr_high: { label: "负荷比过高", value: "急性负荷与慢性负荷比值偏高（ACWR > 1.5），受伤风险增加。" },
    acwr_elevated: { label: "负荷比偏高", value: "急性负荷与慢性负荷比值偏高（ACWR > 1.3），建议关注恢复。" },
    load_drop: { label: "负荷骤降", value: "负荷下降较快，可能影响训练适应，但通常有利于短期恢复。" },
  };

  return reasons.map((reason) => {
    // Handle prefixed reasons like "medical_flag:chest_pain"
    const baseReason = reason.split(":")[0];
    const extra = reason.includes(":") ? reason.split(":").slice(1).join(":") : "";
    const mapping = reasonMap[baseReason] || reasonMap[reason];
    if (mapping) {
      return {
        ...mapping,
        value: extra ? `${mapping.value} (${extra})` : mapping.value,
      };
    }
    return { label: reason, value: "系统检测到此风险信号。" };
  });
}

/**
 * Generate HTML for the AdaptiveExplanationCard.
 */
function renderAdaptiveExplanationCard(explanation) {
  if (!explanation || !explanation.riskLevel) {
    return `<div class="adaptive-explanation-empty empty-state">尚未生成调整说明。提交反馈后可查看。</div>`;
  }

  const { title, riskBanner, adjustmentSummary, details, nextActions, riskLevel } = explanation;
  const riskClass = `adaptive-risk-${riskLevel || "unknown"}`;

  return `
    <section class="adaptive-explanation-card ${riskClass}" aria-label="计划调整说明" data-adaptive-explanation-card>
      <div class="adaptive-explanation-head">
        <div>
          <p class="section-kicker">计划调整</p>
          <h3>${escapeHtml(title)}</h3>
        </div>
        <span class="adaptive-risk-badge">${escapeHtml(riskLevelLabel(riskLevel))}</span>
      </div>
      <div class="adaptive-risk-banner">
        <p>${escapeHtml(riskBanner)}</p>
      </div>
      ${adjustmentSummary ? `<p class="adaptive-summary">${escapeHtml(adjustmentSummary)}</p>` : ""}
      ${details.length ? `
        <dl class="adaptive-detail-list">
          ${details.map((d) => `
            <div>
              <dt>${escapeHtml(d.label)}</dt>
              <dd>${escapeHtml(d.value)}</dd>
            </div>
          `).join("")}
        </dl>
      ` : ""}
      ${nextActions.length ? `
        <div class="adaptive-next-actions">
          <strong>建议下一步</strong>
          <ul>
            ${nextActions.map((action) => `<li>${escapeHtml(action)}</li>`).join("")}
          </ul>
        </div>
      ` : ""}
    </section>
  `;
}

function escapeHtml(str) {
  if (typeof str !== "string") return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

// Expose globally for non-module usage
if (typeof window !== "undefined") {
  Object.assign(window, {
    buildAdaptiveExplanation,
    decodeRiskReasons,
    renderAdaptiveExplanationCard,
  });
}
