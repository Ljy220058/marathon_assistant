// workspaceScenes.js — Workspace scene management [product-workspace][P1]
// 按四类场景调整入口主操作区：首次进入、训练周期中、训练后反馈、自由探索

/**
 * Scene types for the main workspace.
 * @enum {string}
 */
const WORKSPACE_SCENES = {
  FIRST_TIME: "first_time",       // 首次进入 — 引导完善画像
  IN_CYCLE: "in_cycle",           // 训练周期中 — 展示当前状态和下一步
  POST_FEEDBACK: "post_feedback", // 训练后反馈 — 显示调整结果和恢复建议
  FREE_EXPLORE: "free_explore",   // 自由探索 — 查看历史、依据和设置
};

/**
 * Determine the current workspace scene based on application state.
 * @param {{ hasPlan: boolean, hasProfile: boolean, hasFeedbackToday: boolean,
 *           hasRecentAdjustment: boolean, lastResponse: object|null }} state
 * @returns {WORKSPACE_SCENES}
 */
function determineWorkspaceScene(state = {}) {
  const { hasPlan, hasProfile, hasFeedbackToday, hasRecentAdjustment } = state;

  if (hasRecentAdjustment) return WORKSPACE_SCENES.POST_FEEDBACK;
  if (hasPlan) return WORKSPACE_SCENES.IN_CYCLE;
  if (hasProfile) return WORKSPACE_SCENES.FREE_EXPLORE;
  return WORKSPACE_SCENES.FIRST_TIME;
}

/**
 * Build the workspace flow steps based on the current scene.
 */
function buildWorkspaceFlowSteps(scene) {
  const allSteps = [
    { step: 1, label: "完善画像", section: "profile" },
    { step: 2, label: "生成计划", section: "generate" },
    { step: 3, label: "查看日历", section: "calendar" },
    { step: 4, label: "反馈调整", section: "feedback" },
  ];

  switch (scene) {
    case WORKSPACE_SCENES.FIRST_TIME:
      return {
        steps: allSteps,
        currentStep: 1,
        nextAction: "先完善画像，或直接补充目标赛事后生成训练日历。",
      };
    case WORKSPACE_SCENES.IN_CYCLE:
      return {
        steps: allSteps,
        currentStep: 3,
        nextAction: "查看今日训练安排，训练完成后记录反馈。",
      };
    case WORKSPACE_SCENES.POST_FEEDBACK:
      return {
        steps: allSteps,
        currentStep: 4,
        nextAction: "反馈已保存，请查看调整后的训练安排。",
      };
    case WORKSPACE_SCENES.FREE_EXPLORE:
      return {
        steps: allSteps,
        currentStep: 2,
        nextAction: "完善画像后可生成新训练计划。",
      };
    default:
      return { steps: allSteps, currentStep: 1, nextAction: "开始你的训练之旅。" };
  }
}

/**
 * Build first-screen status information for the workspace.
 */
function buildFirstScreenStatus(scene, data = {}) {
  const { todayTask, weekProgress, nextWorkout, riskLevel, recoveryStatus } = data;

  switch (scene) {
    case WORKSPACE_SCENES.FIRST_TIME:
      return {
        title: "欢迎使用马拉松助手",
        subtitle: "开始设置你的训练计划",
        items: [
          { label: "步骤 1", value: "完善跑者画像（目标、能力、可训练日）" },
          { label: "步骤 2", value: "一键生成结构化的训练日历" },
          { label: "步骤 3", value: "逐天查看训练安排、依据和风险调整" },
        ],
      };
    case WORKSPACE_SCENES.IN_CYCLE:
      return {
        title: todayTask || "查看今日训练",
        subtitle: weekProgress || "本周进度正常",
        items: [
          { label: "今日任务", value: todayTask || "按计划执行训练" },
          { label: "本周进度", value: weekProgress || "等待反馈更新" },
          { label: "下一步训练", value: nextWorkout || "查看日历" },
          { label: "风险状态", value: riskLevel || "正常" },
          { label: "恢复状态", value: recoveryStatus || "良好" },
        ].filter((item) => item.value),
      };
    case WORKSPACE_SCENES.POST_FEEDBACK:
      return {
        title: "反馈已记录",
        subtitle: "查看调整后的安排",
        items: [
          { label: "调整状态", value: riskLevel || "已评估" },
          { label: "下次训练", value: nextWorkout || "查看更新后的日历" },
          { label: "恢复建议", value: recoveryStatus || "注意观察恢复" },
        ],
      };
    default:
      return {
        title: "训练助手就绪",
        subtitle: "选择操作继续",
        items: [
          { label: "状态", value: "请完善画像或生成计划" },
        ],
      };
  }
}

/**
 * Render workspace scene status HTML.
 */
function renderWorkspaceSceneStatus(scene, data = {}) {
  const status = buildFirstScreenStatus(scene, data);
  if (!status) return "";

  return `
    <div class="workspace-scene-status" data-workspace-scene="${scene}" aria-label="工作台状态">
      <div class="workspace-scene-head">
        <p class="section-kicker">当前状态</p>
        <h3>${escapeHtml(status.title)}</h3>
        <span>${escapeHtml(status.subtitle)}</span>
      </div>
      ${status.items.length ? `
        <div class="workspace-scene-items">
          ${status.items.map((item) => `
            <div>
              <span>${escapeHtml(item.label)}</span>
              <strong>${escapeHtml(item.value)}</strong>
            </div>
          `).join("")}
        </div>
      ` : ""}
    </div>
  `;
}

function escapeHtml(str) {
  if (typeof str !== "string") return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

// Expose globally for non-module usage
if (typeof window !== "undefined") {
  Object.assign(window, {
    WORKSPACE_SCENES,
    determineWorkspaceScene,
    buildWorkspaceFlowSteps,
    buildFirstScreenStatus,
    renderWorkspaceSceneStatus,
  });
}
