// riskRules.js — Testable recovery status and risk level rules [product-status][P0]
// 疲劳、睡眠、不适、训练负荷到风险等级的规则可测试
//
// Design principle: every rule is a pure function taking a plain object,
// returning a deterministic result. No DOM access, no side effects.

/** @typedef {'medical_referral'|'deescalate'|'attention'|'normal'|'unknown'} RiskLevel */
/** @typedef {'safe'|'caution'|'risk'|'medical_referral'|'unknown'} RecoveryStatus */

// --- Individual rule evaluators ---

/**
 * Evaluate medical red flags — these always produce medical_referral.
 * @param {{ medical_red_flags?: string[] }} feedback
 * @returns {{ triggered: boolean, reasons: string[] }}
 */
function evaluateMedicalRedFlags(feedback = {}) {
  const flags = Array.isArray(feedback.medical_red_flags) ? feedback.medical_red_flags : [];
  if (!flags.length) return { triggered: false, reasons: [] };
  return { triggered: true, reasons: flags.map((f) => `medical_flag:${f}`) };
}

/**
 * Evaluate pain/discomfort level.
 * @param {{ pain?: string }} feedback
 * @returns {{ level: string, riskContrib: number, reason: string|null }}
 */
function evaluatePain(feedback = {}) {
  const pain = String(feedback.pain || "").trim();
  if (!pain) return { level: "unknown", riskContrib: 0, reason: null };
  if (/疼痛风险|严重|剧烈|无法忍受|injury/i.test(pain)) {
    return { level: "pain_risk", riskContrib: 3, reason: "pain_risk" };
  }
  if (/不适|酸痛|轻微|轻度|sore|mild/i.test(pain)) {
    return { level: "discomfort", riskContrib: 1, reason: "discomfort" };
  }
  if (/没有|无|无痛|none|no pain/i.test(pain)) {
    return { level: "none", riskContrib: 0, reason: null };
  }
  return { level: "pain_risk", riskContrib: 3, reason: "pain_risk" };
}

/**
 * Evaluate fatigue level.
 * @param {{ fatigue?: string }} feedback
 * @returns {{ level: string, riskContrib: number, reason: string|null }}
 */
function evaluateFatigue(feedback = {}) {
  const fatigue = String(feedback.fatigue || "").trim();
  if (!fatigue) return { level: "unknown", riskContrib: 0, reason: null };
  if (/高疲劳|极度|严重|极高|exhausted|severe/i.test(fatigue)) {
    return { level: "high_fatigue", riskContrib: 3, reason: "high_fatigue" };
  }
  if (/明显|较累|显著|moderate_high/i.test(fatigue)) {
    return { level: "moderate_high", riskContrib: 2, reason: "moderate_fatigue" };
  }
  if (/中等|一般|moderate/i.test(fatigue)) {
    return { level: "moderate", riskContrib: 1, reason: null };
  }
  if (/轻微|轻度|低|mild|low/i.test(fatigue)) {
    return { level: "mild", riskContrib: 0, reason: null };
  }
  return { level: "moderate_high", riskContrib: 2, reason: "moderate_fatigue" };
}

/**
 * Evaluate sleep/recovery quality.
 * @param {{ sleep?: string }} feedback
 * @returns {{ level: string, riskContrib: number, reason: string|null }}
 */
function evaluateSleep(feedback = {}) {
  const sleep = String(feedback.sleep || "").trim();
  if (!sleep) return { level: "unknown", riskContrib: 0, reason: null };
  if (/较差|很差|失眠|极差|poor|very poor/i.test(sleep)) {
    return { level: "poor", riskContrib: 2, reason: "poor_sleep" };
  }
  if (/一般|普通|average|fair/i.test(sleep)) {
    return { level: "fair", riskContrib: 1, reason: null };
  }
  if (/良好|好|很好|good|well/i.test(sleep)) {
    return { level: "good", riskContrib: 0, reason: null };
  }
  return { level: "fair", riskContrib: 1, reason: "poor_sleep" };
}

/**
 * Evaluate training load risk via ACWR (acute:chronic workload ratio).
 * @param {{ acute7?: number, chronic42?: number, training_load?: number }} load
 * @returns {{ level: string, riskContrib: number, reason: string|null, acwr: number|null }}
 */
function evaluateTrainingLoadRisk(load = {}) {
  const acute7 = Number(load.acute7) || 0;
  const chronic42 = Number(load.chronic42) || 0;
  if (chronic42 <= 0) {
    // No chronic baseline — can't compute ACWR
    if (acute7 > 100) return { level: "high_acute", riskContrib: 2, reason: "high_acute_load", acwr: null };
    return { level: "normal", riskContrib: 0, reason: null, acwr: null };
  }
  const acwr = acute7 / chronic42;
  if (acwr > 1.5) return { level: "high_risk", riskContrib: 3, reason: "acwr_high", acwr };
  if (acwr > 1.3) return { level: "elevated", riskContrib: 2, reason: "acwr_elevated", acwr };
  if (acwr > 1.0) return { level: "normal_high", riskContrib: 1, reason: null, acwr };
  if (acwr < 0.8 && acute7 > 30) return { level: "detraining_risk", riskContrib: 1, reason: "load_drop", acwr };
  return { level: "normal", riskContrib: 0, reason: null, acwr };
}

/**
 * Evaluate completion status impact on risk.
 * @param {{ completion?: string }} feedback
 * @returns {{ level: string, riskContrib: number, reason: string|null }}
 */
function evaluateCompletion(feedback = {}) {
  const completion = String(feedback.completion || "").trim();
  if (!completion) return { level: "unknown", riskContrib: 0, reason: null };
  if (/未完成|跳过|skipped|missed/i.test(completion)) {
    return { level: "missed", riskContrib: 2, reason: "session_missed" };
  }
  if (/部分|partial/i.test(completion)) {
    return { level: "partial", riskContrib: 1, reason: "session_partial" };
  }
  if (/完成|done|completed/i.test(completion)) {
    return { level: "completed", riskContrib: 0, reason: null };
  }
  return { level: "unknown", riskContrib: 0, reason: null };
}

// --- Composite evaluation ---

/**
 * Aggregate risk from a single feedback entry.
 * @param {object} feedback — { pain, fatigue, sleep, completion, medical_red_flags, training_load }
 * @returns {{ riskLevel: RiskLevel, recoveryStatus: RecoveryStatus, reasons: string[], totalRiskScore: number }}
 */
function evaluateSingleFeedbackRisk(feedback = {}) {
  const medical = evaluateMedicalRedFlags(feedback);
  if (medical.triggered) {
    return {
      riskLevel: "medical_referral",
      recoveryStatus: "medical_referral",
      reasons: medical.reasons,
      totalRiskScore: 99,
    };
  }

  const pain = evaluatePain(feedback);
  const fatigue = evaluateFatigue(feedback);
  const sleep = evaluateSleep(feedback);
  const completion = evaluateCompletion(feedback);
  const load = evaluateTrainingLoadRisk(feedback);

  const totalScore = pain.riskContrib + fatigue.riskContrib + sleep.riskContrib + completion.riskContrib + load.riskContrib;
  const reasons = [pain.reason, fatigue.reason, sleep.reason, completion.reason, load.reason].filter(Boolean);

  let riskLevel = "normal";
  let recoveryStatus = "safe";

  if (totalScore >= 6 || pain.level === "pain_risk" || fatigue.level === "high_fatigue") {
    riskLevel = "deescalate";
    recoveryStatus = "risk";
  } else if (totalScore >= 4) {
    riskLevel = "attention";
    recoveryStatus = "caution";
  } else if (totalScore >= 2) {
    riskLevel = "attention";
    recoveryStatus = "caution";
  } else {
    riskLevel = "normal";
    recoveryStatus = "safe";
  }

  return { riskLevel, recoveryStatus, reasons, totalRiskScore: totalScore };
}

/**
 * Aggregate risk across multiple training days.
 * @param {object[]} daysWithFeedback — array of { ...day, latest_feedback: {...}, training_load, acute7, chronic42 }
 * @returns {{ riskLevel: RiskLevel, recoveryStatus: RecoveryStatus,
 *             reasons: string[], totalRiskScore: number,
 *             perDayResults: object[], completionRate: number,
 *             missedFeedbackCount: number, nextTrainingRecommendation: string }}
 */
function evaluateMultiDayRisk(daysWithFeedback = []) {
  if (!daysWithFeedback.length) {
    return {
      riskLevel: "unknown",
      recoveryStatus: "unknown",
      reasons: [],
      totalRiskScore: 0,
      perDayResults: [],
      completionRate: 0,
      missedFeedbackCount: 0,
      nextTrainingRecommendation: "先生成训练日历，再根据执行反馈评估风险和调整。",
    };
  }

  let totalScore = 0;
  let completedCount = 0;
  let partialCount = 0;
  let skippedCount = 0;
  let missedFeedbackCount = 0;
  const allReasons = [];
  const perDayResults = [];

  daysWithFeedback.forEach((day) => {
    const feedback = day.latest_feedback || {};
    const hasFeedback = Boolean(feedback.id || feedback.feedback_id || feedback.risk_gate || feedback.completion_status);
    if (!hasFeedback) {
      missedFeedbackCount += 1;
      return;
    }
    const result = evaluateSingleFeedbackRisk({
      ...feedback,
      training_load: day.training_load,
      acute7: day.acute7,
      chronic42: day.chronic42,
    });
    perDayResults.push({ dayKey: day.day_key || day.day_label || day.date, ...result });
    totalScore += result.totalRiskScore;

    const completion = feedback.completion || feedback.completion_status || "";
    if (/完成|done|completed/i.test(completion)) completedCount++;
    else if (/部分|partial/i.test(completion)) partialCount++;
    else if (/未|跳过|skipped|missed/i.test(completion)) skippedCount++;

    result.reasons.forEach((r) => {
      if (!allReasons.includes(r)) allReasons.push(r);
    });
  });

  const plannedCount = daysWithFeedback.length;
  const completionRate = plannedCount > 0
    ? Math.round(((completedCount + partialCount * 0.5) / plannedCount) * 100)
    : 0;

  let riskLevel = "normal";
  let recoveryStatus = "safe";
  let nextTrainingRecommendation = "按计划执行下一次训练。";

  if (allReasons.includes("medical_referral") || allReasons.some((r) => r.startsWith("medical_flag:"))) {
    riskLevel = "medical_referral";
    recoveryStatus = "medical_referral";
    nextTrainingRecommendation = "停止训练并先做专业评估。";
  } else if (allReasons.includes("pain_risk") || allReasons.includes("high_fatigue") || totalScore >= 8) {
    riskLevel = "deescalate";
    recoveryStatus = "risk";
    nextTrainingRecommendation = "下次训练先降级，优先恢复。";
  } else if (missedFeedbackCount > 0 || totalScore >= 4) {
    riskLevel = "attention";
    recoveryStatus = "caution";
    nextTrainingRecommendation = missedFeedbackCount > 0
      ? "先补录遗漏反馈，再判断是否调整。"
      : "注意观察恢复状态，下次训练前自检疲劳和疼痛。";
  } else {
    riskLevel = "normal";
    recoveryStatus = "safe";
    nextTrainingRecommendation = "按计划执行下一次训练。";
  }

  return {
    riskLevel,
    recoveryStatus,
    reasons: allReasons,
    totalRiskScore: totalScore,
    perDayResults,
    completionRate,
    missedFeedbackCount,
    nextTrainingRecommendation,
    riskRuleSource: "deterministic_feedback_rules",
  };
}

// --- Labels and display helpers ---

const RISK_LABELS = {
  medical_referral: "需就医评估",
  deescalate: "需降级调整",
  attention: "需关注",
  normal: "正常",
  unknown: "未知",
};

const RECOVERY_LABELS = {
  medical_referral: "需就医",
  risk: "高风险",
  caution: "需关注",
  safe: "恢复良好",
  unknown: "未知",
};

function riskLevelLabel(level) {
  return RISK_LABELS[level] || level || "未知";
}

function recoveryStatusLabel(status) {
  return RECOVERY_LABELS[status] || status || "未知";
}

function riskLevelToCssClass(level) {
  return `risk-${level || "unknown"}`;
}

// Expose globally for non-module usage
if (typeof window !== "undefined") {
  Object.assign(window, {
    evaluateMedicalRedFlags,
    evaluatePain,
    evaluateFatigue,
    evaluateSleep,
    evaluateTrainingLoadRisk,
    evaluateCompletion,
    evaluateSingleFeedbackRisk,
    evaluateMultiDayRisk,
    riskLevelLabel_Rules: riskLevelLabel,
    recoveryStatusLabel_Rules: recoveryStatusLabel,
    riskLevelToCssClass,
  });
}
