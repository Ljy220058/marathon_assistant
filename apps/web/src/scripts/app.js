const LOCAL_API_BASE = "http://127.0.0.1:8000";
const FULL_QUERY_TIMEOUT_SEC = 120;
const FULL_QUERY_TIMEOUT_MS = 120000;
// 生产环境可从页面注入 API 地址，本地仍保留端口自动探测。
const CONFIGURED_API_BASE = String(
  window.MARATHON_API_BASE || document.body?.dataset?.apiBase || ""
).trim().replace(/\/$/, "");
const DEFAULT_API_BASE = CONFIGURED_API_BASE || LOCAL_API_BASE;
const API_BASE_CANDIDATES = [DEFAULT_API_BASE, LOCAL_API_BASE, "http://127.0.0.1:8001", "http://127.0.0.1:8010", "http://127.0.0.1:8011"];
const state = {
  apiBase: DEFAULT_API_BASE,
  apiToken: "",
  lastQueryBase: DEFAULT_API_BASE,
  lastResponse: null,
  selectedDay: null,
  calendarView: "week",
  calendarFilter: "all",
  queryController: null,
  queryRunId: 0,
  planProgressTimer: null,
  planTipsTimer: null,
  planProgressPercent: 0,
  historyExpanded: false,
  lastPlanIntent: null,
  latestProfile: {},
  weekCollapseState: {},
  lastDayModalTrigger: null,
  lastEvidenceDrawerTrigger: null,
  evidenceDrawerItems: [],
  lastFeedbackResult: null,
  planReady: false,
  activeFocusTrap: null,
  lastSideDrawerTrigger: null,
  lastRequestId: "",
  // 缓存 /health 和 /llm-options 响应，用于 LLM 状态提示条
  lastHealthData: null,
  lastLlmOptionsData: null,
};

const FEEDBACK_QUICK_PRESETS = {
  feedback_done: {
    completion: "已完成",
    fatigue: "轻微",
    pain: "没有疼痛",
    sleep: "良好",
    notes: "",
  },
  feedback_partial: {
    completion: "部分完成",
    fatigue: "明显",
    pain: "轻微不适",
    sleep: "一般",
    notes: "训练部分完成，需要下调后续负荷。",
  },
  feedback_skipped: {
    completion: "未完成",
    fatigue: "高疲劳",
    pain: "疼痛风险",
    sleep: "较差",
    notes: "训练中出现不适或疼痛信号，需要保守调整后续安排。",
  },
};

const MEDICAL_RED_FLAGS = [
  { value: "chest_pain", label: "胸痛或胸闷" },
  { value: "dizziness_or_fainting", label: "头晕、晕厥或站立不稳" },
  { value: "heat_illness", label: "疑似热病、中暑或异常高热" },
  { value: "breathing_difficulty", label: "呼吸异常或明显气短" },
  { value: "abnormal_heartbeat", label: "异常心悸或心律不齐" },
];

const DRAWER_SECTIONS = [
  { id: "profile", label: "完善跑者资料", query: "画像 跑者资料 目标 能力 可训练日" },
  { id: "calendar", label: "查看训练日历", query: "日历 训练 周计划 单日训练" },
  { id: "templates", label: "快捷模板", query: "模板 快捷 prompt 计划入口" },
  { id: "basis", label: "训练依据", query: "依据 解释 强度 来源 训练依据" },
  { id: "history", label: "历史计划", query: "历史 保存 恢复 计划" },
  { id: "settings", label: "高级设置", query: "设置 服务 接口 模型 高级" },
];

const NO_LIMITATION_TERMS = new Set([
  "无",
  "无伤病",
  "无疲劳",
  "无伤病无疲劳",
  "没有",
  "没有伤病",
  "没有疲劳",
  "未设置",
  "暂无",
  "none",
  "no",
  "n",
  "false",
  "0",
]);

const PROFILE_EDITOR_GROUPS = [
  {
    title: "基础画像",
    fields: [
      { key: "goal", draftKey: "goal", label: "训练目标", type: "text", placeholder: "半马 sub90 / 全马 PB" },
      { key: "experience_level", draftKey: "experience", label: "训练水平", type: "text", placeholder: "新手 / 中级 / 进阶 / 精英" },
      { key: "recent_four_week_mileage", draftKey: "lastMonthMileage", label: "上个月月跑量", type: "text", placeholder: "300 km" },
      { key: "available_days", draftKey: "availableDays", label: "可用训练日", type: "text", placeholder: "周二、周四、周六、周日" },
    ],
  },
  {
    title: "强度与能力",
    fields: [
      { key: "lthr", label: "LTHR", type: "number", placeholder: "168" },
      { key: "t_pace", label: "T配速", type: "text", placeholder: "4:00/km" },
      { key: "vo2max", label: "VO₂max", type: "number", placeholder: "52" },
      { key: "max_session_minutes", draftKey: "longRun", label: "单次最长训练", type: "text", placeholder: "90 分钟" },
    ],
  },
  {
    title: "关键约束",
    fields: [
      { key: "target_race_date", draftKey: "raceDate", label: "比赛日期/倒计时", type: "text", placeholder: "2026-10-18" },
      { key: "terrain_preference", label: "场地偏好", type: "text", placeholder: "公路、田径场" },
      { key: "training_types", label: "训练类型偏好", type: "text", placeholder: "节奏跑、长距离" },
      { key: "notes", label: "补充说明", type: "text", placeholder: "近期小腿紧，避免连续强度" },
    ],
  },
];

const $ = (id) => document.getElementById(id);
const apiBaseInput = $("apiBase");
const apiTokenInput = $("apiToken");
const queryInput = $("queryInput");
const llmProviderInput = $("llmProvider");
const llmModelInput = $("llmModel");
const providerButtons = Array.from(document.querySelectorAll("[data-provider-choice]"));
const dsApiKeyInput = $("dsApiKey");
const saveDsApiKeyButton = $("saveDsApiKey");
const clearDsApiKeyButton = $("clearDsApiKey");
const dsApiKeyStatus = $("dsApiKeyStatus");
const healthBox = $("health");
const navHealth = $("navHealth");
const llmStatusBanner = $("llmStatusBanner");
const reportBox = $("report");
const resultBadge = $("resultBadge");
const cancelQueryButton = $("cancelQuery");
const queryHint = $("queryHint");
const planProgressBox = $("planProgress");
const planProgressPercent = $("planProgressPercent");
const planProgressFill = $("planProgressFill");
const planProgressRunner = $("planProgressRunner");
const planProgressSteps = $("planProgressSteps");
const planProgressPhase = $("planProgressPhase");
const planProgressSignal = $("planProgressSignal");
const calendarBox = $("calendar");
const calendarActionPanel = $("calendarActionPanel");
const loadSummaryBox = $("loadSummary");
const statusPanel = $("statusPanel");
const adjustmentHistory = $("adjustmentHistory");
const calendarCount = $("calendarCount");
const calendarScopeHint = $("calendarScopeHint");
const trainingStartDateInput = $("trainingStartDate");
const defaultStartTimeInput = $("defaultStartTime");
const calendarViewButtons = Array.from(document.querySelectorAll("[data-calendar-view]"));
const tokenUsageBox = $("tokenUsage");
const auditScoresBox = $("auditScores");
const guidedQuestionsBox = $("guidedQuestions");
const zonesBox = $("zones");
const tiersBox = $("tiers");
const profileStatus = $("profileStatus");
const runnerIdentityCard = $("runnerIdentityCard");
const profileEditorDialog = $("profileEditorDialog");
const profileEditorGroups = $("profileEditorGroups");
const closeProfilePanelButton = $("closeProfilePanel");
const cancelProfilePanelButton = $("cancelProfilePanel");
const saveProfilePanelButton = $("saveProfilePanel");
const evidencePreview = $("evidencePreview");
const evidenceCount = $("evidenceCount");
const historyList = $("historyList");
const toggleHistoryListButton = $("toggleHistoryList");
const dayModal = $("dayModal");
const dayModalContent = $("dayModalContent");
const dayModalClose = $("dayModalClose");
const dayModalBackdrop = $("dayModalBackdrop");
const evidenceDrawer = $("evidenceDrawer");
const evidenceDrawerContent = $("evidenceDrawerContent");
const evidenceDrawerClose = $("evidenceDrawerClose");
const evidenceDrawerBackdrop = $("evidenceDrawerBackdrop");
const evidenceDrawerCount = $("evidenceDrawerCount");
const calendarFilterButtons = Array.from(document.querySelectorAll("[data-calendar-filter]"));
const topNavSearchInput = $("topNavSearch");
const drawerSearchInput = $("drawerSearch");
const drawerActionButtons = Array.from(document.querySelectorAll("[data-drawer-action]"));
const drawerEmptyState = document.querySelector("[data-drawer-empty]");
const workspaceFlow = $("workspaceFlow");
const workspaceNextAction = $("workspaceNextAction");
const workspaceFlowSteps = Array.from(document.querySelectorAll("[data-workspace-state] [data-open-drawer-section], [data-workspace-generate]"));
const loadKbGovernanceButton = $("loadKbGovernance");
const kbGovernanceStatus = $("kbGovernanceStatus");
const kbGovernanceContent = $("kbGovernanceContent");

function getApiBase() {
  return (apiBaseInput.value || state.apiBase).replace(/\/$/, "");
}

function getApiAuthHeaders() {
  const token = String(state.apiToken || apiTokenInput?.value || "").trim();
  return token ? { "X-Marathon-API-Key": token } : {};
}

function getExpertBearerHeaders() {
  const token = String(state.apiToken || apiTokenInput?.value || "").trim();
  // 管理端点使用专家 Bearer token，不复用普通查询的 X-Marathon-API-Key 语义。
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function text(value, fallback = "-") {
  const normalized = String(value ?? "").trim();
  return normalized || fallback;
}

const hmpWorkoutLabels = {
  easy_run: "轻松跑",
  recovery_run: "恢复跑",
  recovery_day: "恢复日",
  rest: "休息日",
  rest_day: "休息日",
  long_run: "长距离跑",
  tempo_run: "节奏跑",
  threshold_run: "阈值跑",
  interval_run: "间歇跑",
  hmp_interval: "半马配速间歇",
  hmp_session: "半马专项训练",
  race_pace_run: "比赛配速跑",
  progression_run: "渐进跑",
  hill_run: "坡跑",
  fartlek: "法特莱克",
  strength: "力量训练",
  cross_training: "交叉训练",
  hm_intro_fartlek_hills: "导入期法特莱克/坡跑",
  hm_base_threshold_progression: "基础期阈值/渐速跑",
  hm_90_support_endurance: "半马90%HMP辅助耐力跑",
  hm_95_long_fast_run: "半马95%HMP专项耐力长距离快速跑",
  hm_100_float_intervals: "半马100%HMP核心专项巡航恢复间歇",
  hm_105_specific_speed: "半马105%HMP专项速度间歇",
  hm_110_support_speed: "半马107-110%HMP辅助速度训练",
};

const runnerFacingEnglishFallbacks = [
  {
    pattern: /record\s+feedback.*first\s+workout/i,
    text: "完成第一次训练后记录反馈，再判断是否调整。",
  },
  {
    pattern: /wait.*feedback/i,
    text: "等待训练反馈后给出下次训练建议。",
  },
  {
    pattern: /build\s+consistency/i,
    text: "本周重点是稳定完成计划，并保留恢复余量。",
  },
  {
    pattern: /half\s+marathon\s+finish/i,
    text: "半马完赛",
  },
  {
    pattern: /easy\s+warm\s*up|warm\s*up/i,
    text: "轻松热身",
  },
  {
    pattern: /cool\s*down/i,
    text: "慢跑放松",
  },
  {
    pattern: /recovery\s+only/i,
    text: "今天以恢复为主，不加练强度。",
  },
  {
    pattern: /hmp\s+session|race\s+pace\s+session/i,
    text: "半马专项训练",
  },
  {
    pattern: /recovery\s+margin/i,
    text: "注意恢复窗口，状态一般时优先降级。",
  },
  {
    pattern: /plan\s+ready/i,
    text: "计划已生成，先查看下一次训练和安全提醒。",
  },
];

function looksLikeRawFieldOrEnglish(value) {
  const raw = String(value || "").trim();
  if (!raw) return false;
  if (/[a-z]+_[a-z0-9_]+/i.test(raw)) return true;
  const letters = raw.match(/[A-Za-z]/g)?.length || 0;
  const chinese = raw.match(/[\u4e00-\u9fff]/g)?.length || 0;
  return letters >= 8 && chinese === 0;
}

function runnerFacingText(value, fallback = "-") {
  const raw = cleanUserFacingSummary(value, fallback);
  for (const item of runnerFacingEnglishFallbacks) {
    if (item.pattern.test(raw)) return item.text;
  }
  if (looksLikeRawFieldOrEnglish(raw)) return fallback;
  return raw || fallback;
}

function runnerFacingZoneLabel(value, fallback = "轻松区间") {
  const raw = runnerFacingText(value, fallback);
  const normalized = String(raw || "").trim();
  const map = {
    z1: "恢复区间",
    z2: "轻松区间",
    z3: "中等强度区间",
    z4: "高强度区间",
    z5: "冲刺强度区间",
  };
  const compact = normalized.toLowerCase().replace(/\s+/g, "");
  if (map[compact]) return map[compact];
  return normalized
    .replace(/\bZ1\b/g, "恢复区间")
    .replace(/\bZ2\b/g, "轻松区间")
    .replace(/\bZ3\b/g, "中等强度区间")
    .replace(/\bZ4\b/g, "高强度区间")
    .replace(/\bZ5\b/g, "冲刺强度区间");
}

function cleanWorkoutText(value, fallback = "-") {
  const raw = text(value, fallback);
  return runnerFacingText(raw.replace(/^\s*hm_[a-z0-9_]+\s*(?:[：:]|\?|\s+)\s*/i, ""), fallback);
}

function cleanUserFacingSummary(value, fallback = "-") {
  const raw = text(value, fallback);
  const blockedPatterns = [
    /画像\s*[=：:]/i,
    /候选课表\s*[=：:]/i,
    /HMP\s*协议\s*[=：:]/i,
    /\bHMP\b/i,
    /protocol\s*[=：:]/i,
    /archetype\s*[=：:]/i,
    /[=＝]/,
  ];
  const parts = raw
    .split(/[；;]\s*/)
    .map((item) => item.trim())
    .filter((item) => item && !blockedPatterns.some((pattern) => pattern.test(item)));
  const cleaned = parts.join("；");
  return cleaned || fallback;
}

function displayTrainingTitle(day) {
  if (!day) return "训练";
  const workoutType = String(day.workout_type || "").trim();
  const trainingType = String(day.training_type || "").trim();
  const label = text(
    hmpWorkoutLabels[workoutType] ||
      hmpWorkoutLabels[trainingType] ||
      day.training_type_label ||
      day.title ||
      day.focus ||
      day.summary,
    day.is_rest ? "休息" : "训练",
  );
  if (looksLikeRawFieldOrEnglish(label)) {
    if (/hmp|race[_\s-]*pace|specific/i.test(label)) return "半马专项训练";
    if (/easy/i.test(label)) return "轻松跑";
    if (/rest|recovery/i.test(label)) return "恢复日";
    if (/long/i.test(label)) return "长距离跑";
    if (/tempo|threshold/i.test(label)) return "节奏跑";
    if (/interval/i.test(label)) return "间歇跑";
    return day.is_rest ? "休息" : "训练";
  }
  return label;
}

function trainingDayLabel(day, fallback = "下一次训练") {
  const raw = text(day?.day_label || day?.date || day?.date_str || day?.day, fallback);
  const dayMatch = raw.match(/^day\s*(\d+)$/i);
  if (dayMatch) return `第 ${dayMatch[1]} 天`;
  return text(
    raw.replace(/^w(\d+)d(\d+)$/i, "第 $1 周第 $2 天"),
    fallback,
  );
}

const PLAN_PROGRESS_STEPS = [
  { id: "connect", label: "准备计划", detail: "确认本地训练服务可用" },
  { id: "profile", label: "解析画像", detail: "目标、周期与限制" },
  { id: "skeleton", label: "生成初稿", detail: "先产出可查看周计划" },
  { id: "validate", label: "安全校验", detail: "检查恢复、强度和容量" },
  { id: "calendar", label: "排布日历", detail: "转换为可点击训练日" },
  { id: "evidence", label: "绑定依据", detail: "保留来源与替代方案" },
  { id: "enrich", label: "补全解释", detail: "生成可读解释" },
];

// 跑步知识小贴士：等待时轮播，把"干等"变成"学一点"，是等待留存的核心杠杆。
const RUNNING_TIPS = [
  "轻松跑（E 配速）应占周跑量 70-80%，是提升有氧基础的关键，不是‘太慢’。",
  "长距离跑的目的不是练速度，而是训练身体利用脂肪供能、适应长时间负荷。",
  "赛前 3 天开始碳水负荷，能让肌糖原储备提升 50-100%，显著延缓撞墙。",
  "配速前 2/3 应感觉‘还能说话’，把余力留给最后 1/3——多数人栽在起跑太快。",
  "跑后 30 分钟内补充碳水+蛋白质（约 3:1），糖原合成效率最高。",
  "每周跑量增幅建议不超过 10%，急剧加量是过劳伤的头号诱因。",
  "每周 2 次力量训练可降低约 50% 的跑步损伤风险，重点强化臀中肌与核心。",
  "高强度间歇每周不超过 1-2 次，需 48 小时恢复，过度会抑制免疫力。",
  "睡眠是最强恢复手段：每少睡 1 小时，次日受伤风险上升约 15%。",
  "赛中补水按出汗率，每小时 400-800ml，过量饮水可能引发低钠血症。",
  "减量期（赛前 1-2 周）跑量降 40-60% 但保持强度，能消疲劳又不丢体能。",
  "跑步经济性（每公里耗氧）比最大摄氧量更能预测成绩，靠技术与力量提升。",
];

// 阶段轮播文案：每个步骤配多条信号文案，drift 时轮换，避免单调的固定文案。
const PROGRESS_PHASE_COPY = {
  connect: ["连接训练服务中…", "确认模型与知识库就绪…"],
  profile: ["解析你的目标与周期…", "结合跑量和可训练日…", "评估伤病与疲劳限制…"],
  skeleton: ["教练正在规划每周节奏…", "匹配训练模板与强度区间…", "生成可查看的周计划初稿…"],
  validate: ["安全审查：恢复是否充足…", "校验强度递进与容量上限…", "排查过劳与伤病风险…"],
  calendar: ["转换为可点击训练日历…", "安排长距离与间歇的日期…"],
  evidence: ["绑定科学依据与来源…", "为每个训练安排替代方案…"],
  enrich: ["生成可读的训练解释…", "补充每日训练要点…"],
};

function clampProgress(value) {
  return Math.max(0, Math.min(100, Math.round(Number(value) || 0)));
}

function currentPlanProgressPercent() {
  return state.planProgressPercent || 0;
}

function progressStatusLabel(status, percent) {
  if (status === "idle") return "等待";
  if (status === "running" || status === "enriching") return "生成中";
  if (status === "ready" || status === "ready_with_fallback") return "可查看";
  if (status === "complete") return "已完成";
  if (status === "fallback") return "需重试";
  if (status === "error") return "失败";
  if (status === "cancelled") return "已取消";
  return percent >= 100 ? "已完成" : "进行中";
}

function stopPlanProgressDrift() {
  if (state.planProgressTimer) {
    window.clearInterval(state.planProgressTimer);
    state.planProgressTimer = null;
  }
}

function renderPlanProgress({ percent = 0, activeStep = "connect", status = "idle", phase = "等待生成", signal = "日历尚未开始生成" } = {}) {
  // 终态统一收尾：无论哪个调用方设完成/错误/取消，都停止小贴士轮播并隐藏附加区
  if (["complete", "ready", "ready_with_fallback", "error", "cancelled", "fallback"].includes(status)) {
    stopTipsRotation();
    showProgressExtra(false);
  }
  const normalizedPercent = state.planReady && status !== "idle" && status !== "error" && status !== "cancelled"
    ? Math.max(clampProgress(percent), currentPlanProgressPercent())
    : clampProgress(percent);
  const activeIndex = Math.max(0, PLAN_PROGRESS_STEPS.findIndex((step) => step.id === activeStep));
  state.planProgressPercent = normalizedPercent;
  planProgressBox.dataset.status = status;
  planProgressPercent.dataset.progressValue = String(normalizedPercent);
  planProgressPercent.textContent = progressStatusLabel(status, normalizedPercent);
  planProgressFill.style.width = `${normalizedPercent}%`;
  planProgressRunner.style.left = `${normalizedPercent}%`;
  planProgressPhase.textContent = phase;
  planProgressSignal.textContent = signal;
  planProgressSteps.innerHTML = PLAN_PROGRESS_STEPS.map((step, index) => {
    const stateClass = index < activeIndex || normalizedPercent >= 100
      ? "done"
      : index === activeIndex
        ? "active"
        : "pending";
    return `
      <div class="progress-step ${stateClass}">
        <i aria-hidden="true"></i>
        <span>${escapeHtml(step.label)}</span>
        <small>${escapeHtml(step.detail)}</small>
      </div>
    `;
  }).join("");
}

function buildGenerationStatusViewModel(payload = {}, mode = "received") {
  const plan = getStructuredPlan(payload);
  const weeks = Array.isArray(plan.week_plans) ? plan.week_plans.length : 0;
  const days = normalizeCalendarDays(payload).length;
  const evidenceItems = collectEvidenceItems(payload).length;
  const generationStatus = String(payload?.generation_status || "").trim();
  const validationSummary = formatValidationSummary(payload);
  const hasCalendar = days > 0;
  const hasSkeleton = hasCalendar || weeks > 0;
  const calendarSignal = hasCalendar
    ? `${days} 天训练日已排布，可以先查看日历`
    : weeks
      ? `${weeks} 周计划已生成，正在整理日历卡片`
      : "计划结果已返回";
  const evidenceSignal = evidenceItems
    ? "依据可追踪，可在详情里查看"
    : "依据待补充；不会伪造来源";
  const safetySignal = validationSummary
    ? validationSummary.includes("未通过")
      ? "安全校验需要复核"
      : "安全校验已完成"
    : "执行前仍需完成疼痛和疲劳自检";
  const detailSignal = [calendarSignal, safetySignal, evidenceSignal].filter(Boolean).join("；");

  if (generationStatus === "complete") {
    return {
      badge: "已增强",
      hint: "计划与解释已生成，可继续查看日历或提交训练反馈。",
      progress: {
        percent: 100,
        activeStep: "enrich",
        status: "complete",
        phase: "计划生成完成",
        signal: detailSignal,
      },
    };
  }

  if (hasSkeleton) {
    const explanationPending = mode === "enriching";
    const explanationFallback = generationStatus.includes("timeout") || generationStatus.includes("error");
    return {
      badge: "计划可用",
      hint: explanationPending
        ? "计划可用；解释与证据补充仍在后台进行，不影响查看日历。"
        : explanationFallback
          ? "计划可用；LLM 解释补充未完成，可稍后重试。"
          : "计划可用；优先查看训练日历和当天卡片。",
      progress: {
        percent: explanationPending ? 94 : 92,
        activeStep: explanationPending ? "enrich" : hasCalendar ? "calendar" : "skeleton",
        status: explanationFallback ? "ready_with_fallback" : "ready",
        phase: "计划可用",
        signal: explanationPending
          ? `${calendarSignal}；正在补全解释，但不会阻塞你查看训练日历`
          : explanationFallback
            ? `${detailSignal}；LLM 解释稍后可重试`
            : detailSignal,
      },
    };
  }

  if (generationStatus.includes("timeout") || generationStatus.includes("error")) {
    return {
      badge: "生成受阻",
      hint: "暂时没有可执行日历，请检查我的情况或稍后重试。",
      progress: {
        percent: 68,
        activeStep: "skeleton",
        status: "fallback",
        phase: "未得到可执行日历",
        signal: detailSignal || "暂时没有返回结构化训练计划",
      },
    };
  }

  return {
    badge: "计划处理中",
    hint: "计划结果已返回，正在整理为可执行日历。",
    progress: {
      percent: 68,
      activeStep: "skeleton",
      status: "running",
      phase: "计划处理中",
      signal: detailSignal,
    },
  };
}

function applyGenerationStatusView(view) {
  if (!view) return;
  resultBadge.textContent = view.badge;
  queryHint.textContent = view.hint;
  renderPlanProgress(view.progress);
}

function startPlanProgressDrift(maxPercent = 72) {
  stopPlanProgressDrift();
  showProgressExtra(true);
  startTipsRotation();
  updateProgressEta(0);
  let phaseTick = 0;
  state.planProgressTimer = window.setInterval(() => {
    const current = currentPlanProgressPercent();
    if (current >= maxPercent) {
      // 到达模拟上限后停在"等待最终生成"：百分比不再推进，但 ETA/文案/动画继续，避免卡死观感
      updateProgressEta(current);
      return;
    }
    const nextPercent = Math.min(maxPercent, current + 3);
    const activeStep =
      nextPercent < 18 ? "connect"
      : nextPercent < 34 ? "profile"
      : nextPercent < 56 ? "skeleton"
      : nextPercent < 78 ? "validate"
      : nextPercent < 90 ? "calendar"
      : "evidence";
    const copies = PROGRESS_PHASE_COPY[activeStep] || PROGRESS_PHASE_COPY.skeleton;
    const signal = copies[Math.floor(phaseTick / 2) % copies.length];
    phaseTick += 1;
    renderPlanProgress({
      percent: nextPercent,
      activeStep,
      status: "running",
      phase: activeStep === "skeleton" ? "等待计划初稿" : activeStep === "validate" ? "等待安全校验" : "正在生成训练日历",
      signal,
    });
    updateProgressEta(nextPercent);
  }, 720);
}

// 进度区附加内容（预期时间 + 跑步知识小贴士）的显隐与轮播
function showProgressExtra(show) {
  const extra = document.querySelector("[data-plan-progress-extra]");
  if (extra) extra.hidden = !show;
}

function startTipsRotation() {
  stopTipsRotation();
  const tipEl = $("planProgressTip");
  if (!tipEl) return;
  let idx = Math.floor(Math.random() * RUNNING_TIPS.length);
  const renderTip = () => {
    tipEl.textContent = RUNNING_TIPS[idx % RUNNING_TIPS.length];
    tipEl.classList.remove("tip-fade");
    void tipEl.offsetWidth; // 触发重绘以重启淡入动画
    tipEl.classList.add("tip-fade");
    idx += 1;
  };
  renderTip();
  state.planTipsTimer = window.setInterval(renderTip, 6000);
}

function stopTipsRotation() {
  if (state.planTipsTimer) {
    window.clearInterval(state.planTipsTimer);
    state.planTipsTimer = null;
  }
}

// 预估剩余时间：百分比越高剩余越少，给用户明确预期，降低"还要多久"的不确定焦虑
function updateProgressEta(percent) {
  const etaEl = $("planProgressEta");
  if (!etaEl) return;
  const remaining = percent >= 95
    ? "即将完成"
    : `预计还需 ${Math.max(5, Math.round((100 - percent) * 0.55))} 秒`;
  etaEl.textContent = `⏱ ${remaining}`;
}

// 流式真实节点 → 进度映射：收到节点事件后停模拟 drift，按 stepId 精确推进
const STEP_ID_TO_PERCENT = {
  connect: 12, profile: 28, skeleton: 48, validate: 68, calendar: 84, evidence: 92, enrich: 96,
};
const STEP_ID_LABEL = {
  connect: "准备计划", profile: "解析画像", skeleton: "生成初稿",
  validate: "安全校验", calendar: "排布日历", evidence: "绑定依据", enrich: "补全解释",
};

function updateProgressFromNode(nodeName, stepId) {
  stopPlanProgressDrift(); // 停模拟漂移，改用真实节点驱动进度
  const percent = STEP_ID_TO_PERCENT[stepId] || currentPlanProgressPercent();
  const copies = PROGRESS_PHASE_COPY[stepId] || [];
  const signal = copies[0] || `正在执行：${nodeName}`;
  renderPlanProgress({
    percent,
    activeStep: stepId || "skeleton",
    status: "running",
    phase: STEP_ID_LABEL[stepId] || "处理中",
    signal,
  });
  updateProgressEta(percent);
}

function formatTimingSummary(payload) {
  const timings = payload?.generation_timings || {};
  const total = Number(timings.total_sec);
  if (!Number.isFinite(total)) return "";
  const skeleton = Number(timings.skeleton_build_sec);
  const save = Number(timings.save_plan_sec);
  return [
    `总耗时 ${total.toFixed(3)}s`,
    Number.isFinite(skeleton) ? `初稿 ${skeleton.toFixed(3)}s` : "",
    Number.isFinite(save) ? `保存 ${save.toFixed(3)}s` : "",
  ].filter(Boolean).join(" / ");
}

function formatValidationSummary(payload) {
  const validation = payload?.half_marathon_protocol_validation || {};
  if (!validation || typeof validation !== "object" || !validation.active) return "";
  const checked = Array.isArray(validation.checked_constraints) ? validation.checked_constraints.length : 0;
  const errors = Array.isArray(validation.errors) ? validation.errors.length : 0;
  const warnings = Array.isArray(validation.warnings) ? validation.warnings.length : 0;
  if (validation.passed) return `HMP 校验通过，检查 ${checked} 项约束`;
  return `HMP 校验未通过：${errors} 错误 / ${warnings} 警告`;
}

function syncPlanProgressFromPayload(payload, mode = "received") {
  stopPlanProgressDrift();
  state.planReady = normalizeCalendarDays(payload).length > 0 || (getStructuredPlan(payload).week_plans || []).length > 0;
  applyGenerationStatusView(buildGenerationStatusViewModel(payload, mode));
}

function resetPlanProgress() {
  stopPlanProgressDrift();
  stopTipsRotation();
  showProgressExtra(false);
  state.planReady = false;
  renderPlanProgress();
}

function setEmpty(el, message) {
  el.className = "empty-state";
  el.textContent = message;
}

function updateWorkspaceFlow(stateName = "profile", message = "") {
  const flowMessages = {
    profile: "先完善画像，或直接补充目标赛事后生成训练日历。",
    generating: "正在生成训练日历，完成后会自动引导到训练日历。",
    answer: "智能对话已返回，优先查看回答卡片和依据提示。",
    calendar: "计划已生成。下一步查看周重点，点击单日卡进入详情和反馈。",
    feedback: "根据单日反馈调整后续训练，历史计划可随时恢复。",
  };
  if (workspaceFlow) {
    workspaceFlow.dataset.workspaceState = stateName;
  }
  const stateOrder = { profile: 0, generating: 1, answer: 2, calendar: 2, feedback: 3 };
  const activeIndex = stateOrder[stateName] ?? 0;
  workspaceFlowSteps.forEach((step, index) => {
    step.classList.toggle("is-current", index === activeIndex);
    step.classList.toggle("is-complete", index < activeIndex);
    step.setAttribute("aria-current", index === activeIndex ? "step" : "false");
  });
  if (workspaceNextAction) {
    workspaceNextAction.textContent = message || flowMessages[stateName] || flowMessages.profile;
  }
}

function setBusy(message) {
  reportBox.className = "loading-state";
  reportBox.textContent = message;
  resultBadge.textContent = "处理中";
  renderPlanProgress({
    percent: 8,
    activeStep: "connect",
    status: "running",
    phase: "请求已发出",
    signal: "正在准备训练计划并识别计划类型",
  });
}

function getFocusableElements(root) {
  if (!root) return [];
  return Array.from(root.querySelectorAll([
    "a[href]",
    "button:not([disabled])",
    "textarea:not([disabled])",
    "input:not([disabled])",
    "select:not([disabled])",
    "summary",
    "[tabindex]:not([tabindex='-1'])",
  ].join(","))).filter((element) => element.offsetParent !== null);
}

function setBackgroundInert(active, activeLayer = null) {
  const roots = [
    document.querySelector(".top-nav"),
    document.querySelector(".mobile-quick-nav"),
    document.querySelector("main"),
  ].filter(Boolean);
  roots.forEach((root) => {
    if (active && activeLayer && activeLayer.contains(root)) return;
    if (active && activeLayer && root.contains(activeLayer)) return;
    if (active) {
      root.setAttribute("inert", "");
    } else {
      root.removeAttribute("inert");
    }
  });
}

function activateFocusTrap(layer, closeHandler) {
  state.activeFocusTrap = { layer, closeHandler };
  setBackgroundInert(true, layer);
}

function deactivateFocusTrap(layer) {
  if (!state.activeFocusTrap || state.activeFocusTrap.layer === layer) {
    state.activeFocusTrap = null;
  }
  if (!dayModal.classList.contains("open") && !evidenceDrawer.classList.contains("open")) {
    setBackgroundInert(false);
  }
}

function isMobileDrawerMode() {
  return window.matchMedia("(max-width: 720px)").matches;
}

function setDrawerContentAvailability(drawer, available) {
  const content = drawer?.querySelector(".side-drawer-content");
  if (!content) return;
  if (available) {
    content.removeAttribute("aria-hidden");
    content.removeAttribute("inert");
  } else {
    content.setAttribute("aria-hidden", "true");
    content.setAttribute("inert", "");
  }
}

function setSideDrawerModalInert(active, drawer = document.querySelector("[data-side-drawer]")) {
  [
    document.querySelector(".top-nav"),
    document.querySelector(".mobile-quick-nav"),
    ...Array.from(document.querySelectorAll(".app-layout > *")).filter((node) => node !== drawer),
  ].filter(Boolean).forEach((node) => {
    if (active) {
      node.setAttribute("inert", "");
    } else {
      node.removeAttribute("inert");
    }
  });
}

function activateSideDrawerModal(drawer, opener = null) {
  if (!drawer || !isMobileDrawerMode()) return;
  state.lastSideDrawerTrigger = opener instanceof HTMLElement ? opener : document.activeElement;
  document.body.classList.add("side-drawer-modal-open");
  setDrawerContentAvailability(drawer, true);
  setSideDrawerModalInert(true, drawer);
  activateFocusTrap(drawer, closeSideDrawer);
  drawer.querySelector("[data-side-drawer-close]")?.focus();
}

function closeSideDrawer() {
  const drawer = document.querySelector("[data-side-drawer]");
  if (!drawer) return;
  drawer.open = false;
  document.body.classList.remove("side-drawer-modal-open");
  setSideDrawerModalInert(false, drawer);
  deactivateFocusTrap(drawer);
  state.lastSideDrawerTrigger?.focus?.();
  state.lastSideDrawerTrigger = null;
}

function syncSideDrawerViewportState() {
  const drawer = document.querySelector("[data-side-drawer]");
  if (!drawer) return;
  if (isMobileDrawerMode()) {
    if (drawer.open && !document.body.classList.contains("side-drawer-modal-open")) {
      drawer.open = false;
      setDrawerContentAvailability(drawer, false);
    }
    return;
  }
  if (!drawer.open) {
    drawer.open = true;
  }
  setDrawerContentAvailability(drawer, true);
  document.body.classList.remove("side-drawer-modal-open");
  setSideDrawerModalInert(false, drawer);
  deactivateFocusTrap(drawer);
}

function handleFocusTrapKeydown(event) {
  const trap = state.activeFocusTrap;
  if (!trap?.layer) return false;
  if (event.key === "Escape") {
    event.preventDefault();
    trap.closeHandler?.();
    return true;
  }
  if (event.key === "Tab") {
    const focusable = getFocusableElements(trap.layer);
    if (!focusable.length) {
      event.preventDefault();
      return true;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
      return true;
    }
    if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
      return true;
    }
  }
  return false;
}

// renderHealth 接收完整 /health 响应或 error 信息
function renderHealth(status, model, provider, error, fullData) {
  // 缓存 health 数据供 LLM 状态提示条使用
  if (fullData) {
    state.lastHealthData = fullData;
  } else if (!error) {
    state.lastHealthData = { status, model, provider };
  } else {
    state.lastHealthData = null;
  }
  if (error) {
    healthBox.className = "status-note error";
    navHealth.className = "nav-health error";
    healthBox.textContent = `离线：${window.__apiClient.explainApiError(error)}`;
    navHealth.textContent = "服务离线";
    navHealth.hidden = false;
    renderLlmStatusHint();
    return;
  }
  healthBox.className = "status-note ok";
  navHealth.className = "nav-health ok";
  healthBox.textContent = `在线：${status} / ${provider || "unknown"} / ${model || "unknown"}`;
  navHealth.textContent = "服务在线";
  navHealth.hidden = true;
  renderLlmStatusHint();
}

// 根据 /health 和 /llm-options 数据在页面顶部显示 LLM 状态提示条
function renderLlmStatusHint() {
  if (!llmStatusBanner) return;
  const health = state.lastHealthData;
  const llmOpts = state.lastLlmOptionsData;

  // 后端不可达
  if (!health) {
    llmStatusBanner.className = "llm-status-banner llm-status-warning";
    llmStatusBanner.innerHTML = `
      <strong>训练服务未连接</strong>
      <span>你仍可先填写我的情况；连接本地服务后即可生成训练日历。</span>
      <span class="llm-status-actions">
        <button type="button" class="secondary-button compact-button" data-health-retry>重试连接</button>
        <button type="button" class="secondary-button compact-button" data-open-drawer-section="settings">查看启动命令</button>
        <button type="button" class="secondary-button compact-button" data-sample-plan>使用示例计划体验</button>
      </span>
    `;
    llmStatusBanner.hidden = false;
    return;
  }

  // DeepSeek API key 是否已配置
  let dsKeyConfigured = false;
  if (llmOpts && Array.isArray(llmOpts.providers)) {
    const dsProvider = llmOpts.providers.find((p) => p.id === "ds");
    if (dsProvider && dsProvider.api_key_configured) {
      dsKeyConfigured = true;
    }
  }

  // 构建提示消息
  let message = "";
  let cssClass = "llm-status-banner";

  if (health.ollama === false) {
    // Ollama 不可达
    message = "本地 LLM 不可用，可使用云端推理或骨架模式生成训练计划。";
    cssClass += " llm-status-warning";
    if (dsKeyConfigured) {
      message += " DeepSeek 云端推理已配置，可在侧栏设置中切换模型来源。";
    }
  } else if (health.ollama === true && health.status === "degraded") {
    // Ollama 可用但整体状态降级（如 KB/DB 问题，但仍可能是 LLM 慢的提示）
    message = "本地 LLM 响应较慢，建议使用 DeepSeek 云端推理获得更快体验。";
    cssClass += " llm-status-info";
    if (dsKeyConfigured) {
      message += " DeepSeek 云端推理已配置，可在侧栏设置中切换模型来源。";
    }
  } else if (health.ollama === true && health.status === "healthy") {
    // 一切正常：仅在 DS key 已配置时提示可切换
    if (dsKeyConfigured) {
      message = "DeepSeek 云端推理已配置。若本地 LLM 响应较慢，可在侧栏设置中切换至云端推理。";
      cssClass += " llm-status-info";
    }
  }

  if (message) {
    llmStatusBanner.className = cssClass;
    llmStatusBanner.innerHTML = escapeHtml(message);
    llmStatusBanner.hidden = false;
  } else {
    llmStatusBanner.hidden = true;
  }
}

async function loadLlmOptions() {
  try {
    const data = await window.__apiClient.apiFetch("/llm-options");
    const providers = Array.isArray(data.providers) ? data.providers : [];
    if (providers.length) {
      llmProviderInput.innerHTML = providers
        .map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.label || item.id)}</option>`)
        .join("");
    }
    const defaultsByProvider = {};
    const modelsByProvider = {};
    const configByProvider = {};
    providers.forEach((item) => {
      defaultsByProvider[item.id] = item.default_model || "";
      modelsByProvider[item.id] = Array.isArray(item.models) ? item.models : [item.default_model].filter(Boolean);
      configByProvider[item.id] = {
        api_key_configured: item.api_key_configured !== false,
        api_key_config_visible: item.api_key_config_visible !== false,
      };
    });
    const savedProvider = localStorage.getItem("marathon_llm_provider");
    const savedModel = localStorage.getItem("marathon_llm_model");
    llmProviderInput.value = savedProvider || data.default?.provider || "ds";
    llmProviderInput.dataset.defaults = JSON.stringify(defaultsByProvider);
    llmProviderInput.dataset.models = JSON.stringify(modelsByProvider);
    llmProviderInput.dataset.providerConfig = JSON.stringify(configByProvider);
    renderModelOptions(savedModel || data.default?.model || defaultsByProvider[llmProviderInput.value] || "");
    // 缓存 llm-options 数据供 LLM 状态提示条使用
    state.lastLlmOptionsData = data;
    renderLlmStatusHint();
  } catch (error) {
    llmProviderInput.value = localStorage.getItem("marathon_llm_provider") || "ds";
    llmProviderInput.dataset.models = JSON.stringify({
      ollama: ["qwen2.5:latest"],
      ds: ["deepseek-v4-flash"],
    });
    llmProviderInput.dataset.defaults = JSON.stringify({
      ollama: "qwen2.5:latest",
      ds: "deepseek-v4-flash",
    });
    llmProviderInput.dataset.providerConfig = JSON.stringify({
      ollama: { api_key_configured: true, api_key_config_visible: true },
      ds: { api_key_configured: false, api_key_config_visible: true },
    });
    renderModelOptions(localStorage.getItem("marathon_llm_model") || "");
    state.lastLlmOptionsData = null;
    renderLlmStatusHint();
  }
}

function renderModelOptions(preferredModel = "") {
  const modelsByProvider = JSON.parse(llmProviderInput.dataset.models || "{}");
  const defaultsByProvider = JSON.parse(llmProviderInput.dataset.defaults || "{}");
  const provider = llmProviderInput.value || "ds";
  const models = modelsByProvider[provider] || [defaultsByProvider[provider] || "deepseek-v4-flash"];
  const selected = preferredModel && models.includes(preferredModel)
    ? preferredModel
    : (defaultsByProvider[provider] || models[0] || "");
  llmModelInput.innerHTML = models
    .map((model) => `<option value="${escapeHtml(model)}">${escapeHtml(model)}</option>`)
    .join("");
  llmModelInput.value = selected;
  const providerConfig = JSON.parse(llmProviderInput.dataset.providerConfig || "{}");
  const currentConfig = providerConfig[provider] || {};
  llmProviderInput.dataset.activeProviderConfigured = String(currentConfig.api_key_configured !== false);
  syncProviderButtons();
}

function syncProviderButtons() {
  providerButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.providerChoice === llmProviderInput.value);
  });
}

function formatTokenUsage(tokenUsage) {
  if (!tokenUsage) return "-";
  const total = tokenUsage.total_tokens ?? 0;
  const prompt = tokenUsage.prompt_tokens ?? 0;
  const completion = tokenUsage.completion_tokens ?? 0;
  return `总 ${total} / 提示 ${prompt} / 输出 ${completion}`;
}

function formatAuditScores(auditScores) {
  if (!auditScores) return "-";
  const parts = [
    ["一致性", auditScores.consistency],
    ["安全", auditScores.safety],
    ["ROI", auditScores.roi],
  ];
  return parts.map(([label, value]) => `${label} ${value ?? "-"}`).join(" · ");
}

function renderQuestions(questions) {
  if (!Array.isArray(questions) || !questions.length) return "-";
  return questions.slice(0, 3).map((item) => `• ${item}`).join("\n");
}

function getStructuredReport(response) {
  return response?.structured_report || {};
}

function getStructuredPlan(response) {
  return response?.structured_training_plan || getStructuredReport(response).structured_training_plan || {};
}

function getCalendar(response) {
  const report = getStructuredReport(response);
  return response?.monthly_training_calendar || report.monthly_training_calendar || {};
}

function numberValue(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function formatLoad(value) {
  const parsed = numberValue(value, 0);
  return String(Math.round(parsed));
}

function loadStatus(value) {
  const load = numberValue(value, 0);
  if (load >= 160) return { label: "偏高，先看恢复", className: "high-load", advice: "优先检查睡眠、疼痛和疲劳，状态一般时降级为轻松跑。" };
  if (load >= 120) return { label: "较高", className: "elevated-load", advice: "注意前后恢复间隔，避免连续叠加强刺激。" };
  return { label: "稳定", className: "normal-load", advice: "按计划执行，保持常规恢复。" };
}

function weeklyPressureLabel(totalLoad, activeDays = 1) {
  const load = numberValue(totalLoad, 0);
  if (!load) return "待估";
  const averageLoad = load / Math.max(1, numberValue(activeDays, 1));
  return loadStatus(averageLoad).label.replace("，先看恢复", "");
}

function formatDuration(value) {
  const parsed = numberValue(value, 0);
  return parsed > 0 ? `${Math.round(parsed)} 分钟` : "-";
}

function getCalendarSettings() {
  return {
    training_start_date: (trainingStartDateInput?.value || "").trim(),
    default_start_time: (defaultStartTimeInput?.value || "07:00").trim(),
  };
}

function saveCalendarSettingsDraft() {
  localStorage.setItem("marathon-calendar-settings", JSON.stringify(getCalendarSettings()));
}

function loadCalendarSettingsDraft() {
  try {
    const saved = JSON.parse(localStorage.getItem("marathon-calendar-settings") || "{}");
    if (trainingStartDateInput && saved.training_start_date) {
      trainingStartDateInput.value = saved.training_start_date;
    }
    if (defaultStartTimeInput && saved.default_start_time) {
      defaultStartTimeInput.value = saved.default_start_time;
    }
  } catch {}
}

function dayDateLabel(day) {
  return text(day?.scheduled_date || day?.date || day?.date_str, "");
}

function dayTimeLabel(day) {
  return text(day?.start_time || day?.time || day?.planned_time, "");
}

function formatScheduleTime(day) {
  const date = dayDateLabel(day);
  const time = dayTimeLabel(day);
  const duration = numberValue(day?.duration_min, 0);
  return [
    date,
    time,
    duration ? `${Math.round(duration)} 分钟` : "",
  ].filter(Boolean).join(" · ");
}

function isRestDay(day) {
  const haystack = [
    day?.is_rest,
    day?.training_type,
    day?.training_type_label,
    day?.workout_type,
    day?.card_status,
    day?.main_set,
  ].map((item) => String(item || "")).join(" ");
  return Boolean(day?.is_rest) || /休息|恢复日|rest|recovery/i.test(haystack);
}

function getTrainingLoadSummary(response) {
  const report = getStructuredReport(response);
  const calendar = getCalendar(response);
  const plan = getStructuredPlan(response);
  return (
    response?.training_load_summary ||
    report.training_load_summary ||
    calendar.training_load_summary ||
    plan.training_load_summary ||
    {}
  );
}

function trendZoneLabel(value) {
  const map = {
    excessive: "偏高，需复核",
    optimized: "偏积极",
    maintaining: "稳定维持",
    resuming: "恢复建立",
    decreasing: "下降/减量",
  };
  return map[value] || text(value, "-");
}

function trendRatioLabel(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? `${parsed.toFixed(1)}%` : "-";
}

function percentLabel(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? `${parsed.toFixed(1)}%` : "-";
}

function loadMethodLabel(value) {
  const map = {
    planned_zone_duration: "计划代理负荷",
    planned_zone_duration_proxy: "计划代理负荷",
    coros_like_public_trimp_proxy: "计划代理负荷",
    rest_day: "恢复日负荷",
    hr_trimp: "心率 TRIMP",
    frontend_estimated_duration_type: "前端兜底估算",
  };
  return map[value] || text(value, "计划代理负荷");
}

function loadDisclaimerText(value) {
  const raw = text(value, "");
  if (!raw || /COROS does not publish|TRIMP\/zone-duration proxy/i.test(raw)) {
    return "这是计划代理负荷：由计划时长与强度区权重估算，用于比较课表内部负荷，不等同于设备真实生理负荷。";
  }
  return raw;
}

function loadSourceParts(day) {
  const factors = day?.training_load_factors || {};
  return {
    method: loadMethodLabel(day?.training_load_method),
    calc: [
      factors.duration_min ? `时长 ${factors.duration_min}min` : "",
      factors.intensity_zone ? `强度 ${factors.intensity_zone}` : "",
      factors.intensity_weight ? `权重 ${factors.intensity_weight}` : "",
    ].filter(Boolean).join(" × ") || "计划时长 × 强度区权重",
    note: factors.disclaimer || "计划代理负荷，不等同于设备基于心率、HRV或恢复状态计算的真实生理负荷。",
  };
}

function weeklyLoadTrendLabel(value) {
  const map = {
    baseline: "基线周",
    build: "负荷递进",
    deload: "减量周",
    stable: "稳定周",
  };
  return map[value] || text(value, "稳定周");
}

function renderWeeklyLoadChanges(weeklyLoads) {
  if (!Array.isArray(weeklyLoads) || weeklyLoads.length === 0) {
    return `<div class="weekly-load-change-empty">周代理负荷变化暂无数据。</div>`;
  }

  return `
    <div class="weekly-load-change-list">
      ${weeklyLoads.map((week, index) => {
        const load = numberValue(week?.training_load, 0);
        const delta = numberValue(week?.delta_from_previous, 0);
        const deltaPercent = numberValue(week?.delta_percent_from_previous, 0);
        const trendLabel = weeklyLoadTrendLabel(week?.trend_label);
        const deltaSign = delta > 0 ? "+" : "";
        const deltaClass = delta > 0 ? "positive" : delta < 0 ? "negative" : "neutral";
        return `
          <article class="weekly-load-change-row ${deltaClass}">
            <div class="weekly-load-change-head">
              <strong>第${escapeHtml(String(week?.week_index ?? index + 1))}周</strong>
              <span>${escapeHtml(trendLabel)}</span>
            </div>
            <div class="weekly-load-change-body">
              <span class="weekly-load-value">${escapeHtml(formatLoad(load))}</span>
              <span class="weekly-load-delta">较上周 ${escapeHtml(deltaSign + formatLoad(delta))} · ${escapeHtml(percentLabel(deltaPercent))}</span>
            </div>
          </article>
        `;
      }).join("")}
    </div>
  `;
}

function getDailyCards(response) {
  const report = getStructuredReport(response);
  return response?.daily_schedule_cards || report.daily_schedule_cards || [];
}

function getWeekPlanDays(response) {
  const plan = getStructuredPlan(response);
  const rows = [];
  (plan.week_plans || []).forEach((week) => {
    (week.days || []).forEach((day, index) => {
      const distanceKm = numberValue(day.distance_km, 0) ||
        numberValue(day.total_km, 0) ||
        numberValue(day.warmup_km, 0) + numberValue(day.main_km, 0) + numberValue(day.cooldown_km, 0);
      const isRest = isRestDay(day);
      const estimatedDuration = distanceKm ? Math.max(20, Math.round(distanceKm * 6)) : 0;
      const estimatedLoad = isRest ? 0 : Math.round(estimatedDuration * (
        /间歇|阈值|节奏|专项|长距离|渐进/.test(text(day.training_type, "")) ? 0.9 : 0.6
      ));
      const hasLoad = day.training_load !== undefined && day.training_load !== null && day.training_load !== "";
      rows.push({
        ...day,
        week_index: week.week_index,
        day_index: day.day_index || index + 1,
        day_label: day.day_label || day.day,
        phase: week.phase,
        load_level: week.load_level,
        week_goal: week.week_goal,
        distance_km: distanceKm,
        duration_min: numberValue(day.duration_min, estimatedDuration),
        training_load: hasLoad ? numberValue(day.training_load, 0) : estimatedLoad,
        training_load_method: day.training_load_method || (hasLoad ? "" : "frontend_estimated_duration_type"),
        training_load_factors: day.training_load_factors || (hasLoad ? {} : {
          load_kind: "frontend_fallback",
          source: "frontend estimated from distance and training type",
          duration_min: estimatedDuration,
          is_estimated: true,
          not_device_metric: true,
          disclaimer: "页面兜底估算，仅用于缺少负荷字段时维持展示，不等同于设备真实生理负荷。",
        }),
        evidence_tier: day.evidence_tier || "plan_only",
        evidence_tier_label: day.evidence_tier_label || "计划规则",
      });
    });
  });
  return rows;
}

function cleanEvidenceLabel(value) {
  const raw = String(value || "").trim();
  if (!raw) return "训练依据";
  const map = {
    action_library: "动作库证据",
    protocol_rule: "内置 HMP 协议规则",
    kb_fallback: "训练资料支持",
    needs_evidence: "证据不足待补全",
    plan_only: "计划规则",
    saved_plan: "已保存计划",
    training_explanation: "训练解释",
    llm_general_knowledge: "模型知识说明",
    source: "来源",
  };
  return map[raw] || raw
    .replace(/参考知识库生成/g, "")
    .replace(/知识库生成/g, "")
    .replace(/参考知识库/g, "训练资料")
    .trim() || "训练依据";
}

function readableConstraintName(value) {
  const map = {
    no_sub70_volume_copy: "不照搬超高跑量模板",
    marathon_recovery_intro: "马拉松恢复导入",
    quality_recovery_gap: "质量课恢复间隔",
    progress_long_fast_run: "长距离快速跑渐进",
    dynamic_hmp_calibration: "HMP 动态校准",
    race_specific_timing: "专项训练时机",
    environment_or_fatigue_downgrade: "环境/疲劳降级",
    capacity_budget_exceeded: "容量预算检查",
  };
  return map[value] || String(value || "").replace(/_/g, " ");
}

function describeDayBasis(day) {
  const workoutType = String(day?.workout_type || "").trim();
  const sourceList = Array.isArray(day?.source) ? day.source.filter(Boolean) : [];
  const isHmp = /^hm_/.test(workoutType) || /HMP|半马/.test(displayTrainingTitle(day));
  const evidenceLabel = cleanEvidenceLabel(day?.evidence_tier || day?.evidence_tier_label || day?.explanation_source);
  const isRest = isRestDay(day);
  const sources = sourceList.length
    ? sourceList
    : isRest
      ? ["恢复/吸收规则"]
      : isHmp
      ? ["docs/product/half_marathon_hmp_protocol.md", "Sub-70半程马拉松训练_图片OCR整理.md"]
      : [evidenceLabel || "结构化计划规则"];
  const validation = state.lastResponse?.half_marathon_protocol_validation || {};
  const checked = Array.isArray(validation.checked_constraints)
    ? validation.checked_constraints.slice(0, 4).map(readableConstraintName)
    : [];
  const title = displayTrainingTitle(day);
  const mainSet = cleanWorkoutText(day?.main_set || day?.intensity_target || day?.note, "");
  const effect = isRest
    ? "这一天主要用于恢复吸收训练刺激，避免连续高强度堆叠。"
    : /长距离|95|耐力/.test(`${title} ${mainSet}`)
      ? "这条依据主要影响长距离专项耐力、总距离上限和后续恢复安排。"
      : /间歇|阈值|节奏|105|110|坡|渐进/.test(`${title} ${mainSet}`)
        ? "这条依据主要影响质量课强度、恢复间隔和每周质量课上限。"
        : "这条依据主要影响有氧基础、训练连续性和低风险负荷积累。";
  const validationText = validation.active
    ? validation.passed
      ? `已通过半马协议校验：${checked.length ? checked.join("、") : "关键安全约束"}。`
      : `半马协议校验存在风险：${[...(validation.errors || []), ...(validation.warnings || [])].slice(0, 2).join("；") || "请降低强度并复核计划"}。`
    : "当前先展示可执行安排；完整解释补全后会提供更多证据细节。";
  return {
    badge: isRest ? "恢复安排" : isHmp ? "HMP 基石协议" : evidenceLabel,
    sourceText: sources.join(" / "),
    effectText: effect,
    validationText,
  };
}

function sourceTypeLabel(value) {
  const map = {
    protocol: "基石协议",
    protocol_rule: "基石协议",
    action_library: "动作库",
    kb_fallback: "参考知识库",
    llm_expression: "LLM 表达",
    needs_evidence: "待补证据",
    plan_only: "计划规则",
    llm_general_knowledge: "模型知识说明",
    verified_source: "可定位来源",
    legacy_explanation: "旧知识库解释性来源",
    graph_hint: "图谱关联线索",
    model_general_knowledge: "模型常识说明",
    rejected_source: "已阻断来源",
  };
  return map[value] || text(value, "未标注");
}

function confidenceLabel(value) {
  const map = {
    verified: "已验证",
    inferred: "推断",
    low: "低置信",
    medium: "中置信",
    high: "高置信",
  };
  return map[value] || text(value, "未标注");
}

function statusLabel(value) {
  const map = {
    generated: "已生成",
    partial_generated: "部分生成",
    needs_evidence: "待补证据",
    needs_protocol_recheck: "待协议复核",
    needs_user_info: "待补用户信息",
    risk_refused: "安全阻断",
    medical_referral: "建议医疗评估",
    deescalate_or_refuse: "降级或拒绝",
    pain_risk: "疼痛风险",
    high_fatigue: "高疲劳",
    mild_fatigue: "轻度疲劳",
    poor_sleep: "睡眠不足",
    missed_workout: "未完成训练",
    completed: "已完成",
    partial: "部分完成",
    missed: "未完成",
    saved: "已保存",
    not_saved: "未保存",
    proceed: "允许继续",
    passed: "通过",
    pass: "通过",
    blocked: "已阻断",
    warning: "预警",
    high: "高风险",
    medium: "中风险",
    low: "低风险",
    normal: "正常",
    attention: "需要关注",
    unknown: "待反馈确认",
    deescalate: "建议降级",
    risk_detected: "检测到风险",
    not_evaluated: "尚未提交反馈自检",
    feedback_adjusted: "已按反馈调整",
    stop_for_medical_referral: "暂停并评估",
    downgrade: "需降级执行",
    legacy_missing: "旧数据缺少审计摘要",
  };
  return map[value] || text(value, "-");
}

function feedbackStatusLabel(value) {
  const status = String(value || "").trim();
  if (status === "medical_referral") return "停止训练，建议专业评估";
  if (status === "risk_refused") return "安全阻断，未生成调整建议";
  if (status === "partial_generated") return "部分生成调整建议";
  if (status === "generated") return "已生成调整建议";
  if (status === "suggested") return "已生成本周调整建议";
  if (status === "applied") return "已应用到日历";
  if (status === "needs_manual_choice") return "本周没有可安全安排的训练日";
  if (status === "blocked_medical") return "不能直接恢复跑步训练";
  if (status === "dismissed") return "已暂不采用";
  return statusLabel(status || "-");
}

function sourceStateLabel(day) {
  const source = mainSetSource(day);
  const actionMatch = day?.action_match || day?.trace?.action_match || {};
  const kbFallback = day?.kb_fallback || day?.trace?.kb_fallback || {};
  if (source.source_type === "action_library" || actionMatch.action_id) {
    return "安排来源已确认";
  }
  if (day?.evidence_tier === "needs_evidence" || kbFallback.needs_evidence) {
    return "证据不足";
  }
  if (source.source_type || day?.evidence_tier) {
    return sourceTypeLabel(source.source_type || day.evidence_tier);
  }
  return "来源待确认";
}

function dayProductStatus(day) {
  if (requiresProtocolRecheck(day)) return "needs_protocol_recheck";
  if (day?.card_status === "needs_evidence" || day?.evidence_tier === "needs_evidence") return "needs_evidence";
  if (day?.card_status === "partial_generated" || day?.generation_status === "partial_generated") return "partial_generated";
  if (day?.card_status || day?.generation_status) return day.card_status || day.generation_status;
  return hasActionLibraryMainSet(day) || isRestDay(day) ? "generated" : "needs_evidence";
}

function productStateLabel(status) {
  if (status === "generated") return "已生成训练安排";
  return statusLabel(status);
}

function buildProductStateHtml(day) {
  const status = dayProductStatus(day);
  const protocolCheck = day?.protocol_check || day?.trace?.protocol_check || {};
  const kbFallback = day?.kb_fallback || day?.trace?.kb_fallback || {};
  const trustLabel = requiresProtocolRecheck(day)
    ? "执行前先复核"
    : hasActionLibraryMainSet(day) || isRestDay(day)
      ? "可按计划查看"
      : "依据待补充";
  const protocolLabel = protocolCheck.allowed === false
    ? "待协议复核"
    : protocolCheck.allowed === true
      ? "协议已校验"
      : "协议未校验";
  const kbLabel = kbFallback.used || kbFallback.source_id || kbFallback.needs_evidence
    ? "使用内置说明"
    : "未使用内置说明";
  return `
    <div class="day-product-state" aria-label="产品状态">
      <span>${escapeHtml(productStateLabel(status))}</span>
      <span>${escapeHtml(trustLabel)}</span>
      <span hidden data-expert-only>${escapeHtml(sourceStateLabel(day))}</span>
      <span hidden data-expert-only>${escapeHtml(sourceTypeLabel(day?.evidence_tier || mainSetSource(day).source_type))}</span>
      <span hidden data-expert-only>${escapeHtml(protocolLabel)}</span>
      <span hidden data-expert-only>${escapeHtml(kbLabel)}</span>
    </div>`;
}

function listText(value, fallback = "-") {
  if (Array.isArray(value)) return value.length ? value.map((item) => text(item, "")).filter(Boolean).join("、") : fallback;
  return text(value, fallback);
}

function splitProfileList(value) {
  if (Array.isArray(value)) return value.map((item) => text(item, "")).filter(Boolean);
  return String(value || "")
    .split(/[，、,；;|/]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeLimitationText(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  const compact = raw.replace(/\s+/g, "");
  const tokens = compact.split(/[，、,；;|/]+/).filter(Boolean);
  if (tokens.length && tokens.every((item) => NO_LIMITATION_TERMS.has(item))) {
    return "";
  }
  return raw;
}

function hasProfileLimitation(value) {
  return Boolean(normalizeLimitationText(value));
}

function hasAnsweredLimitationField(value) {
  const raw = String(value || "").trim();
  if (!raw) return false;
  // “无”代表用户已完成安全自检，只是不需要作为实际伤病约束传给后端。
  return !normalizeLimitationText(raw) || hasProfileLimitation(raw);
}

function formatWeeklyMileage(value) {
  const raw = text(value, "");
  if (!raw) return "未设置";
  return /km|公里/i.test(raw) ? raw : `${raw} km/周`;
}

function formatLthr(value) {
  const raw = text(value, "");
  if (!raw || raw === "0" || raw === "0.0") return "未设置";
  return /bpm/i.test(raw) ? raw : `${raw} bpm`;
}

function formatTPace(value) {
  const raw = text(value, "");
  if (!raw) return "未设置";
  return raw.includes("/") ? raw : `${raw}/km`;
}

function profileFieldValue(profile, field) {
  if (profile[field.key] !== undefined && profile[field.key] !== null) {
    return Array.isArray(profile[field.key]) ? profile[field.key].join("、") : String(profile[field.key]);
  }
  if (field.draftKey) {
    const draft = getProfileDraft();
    return draft[field.draftKey] || "";
  }
  return "";
}

function buildProfileConstraints(profile) {
  const constraints = [];
  const days = splitProfileList(profile.available_days);
  if (days.length) constraints.push(["可用训练日", days.join("、")]);
  const maxSession = text(profile.max_session_minutes || profile.long_run, "");
  if (maxSession) constraints.push(["单次上限", /^\d+$/.test(maxSession) ? `${maxSession} 分钟` : maxSession]);
  const terrain = splitProfileList(profile.terrain_preference);
  if (terrain.length) constraints.push(["场地偏好", terrain.join("、")]);
  const trainingTypes = splitProfileList(profile.training_types);
  if (trainingTypes.length) constraints.push(["训练偏好", trainingTypes.join("、")]);
  const injury = splitProfileList(profile.injury_history || profile.injury || profile.recovery_state || profile.fatigue);
  const visibleInjury = injury.filter((item) => hasProfileLimitation(item));
  if (visibleInjury.length) constraints.push(["关键约束", visibleInjury.slice(0, 3).join("、")]);
  return constraints;
}

const TRAINING_DAY_BADGES = [
  { label: "一", aliases: ["周一", "星期一", "mon", "monday"] },
  { label: "二", aliases: ["周二", "星期二", "tue", "tuesday"] },
  { label: "三", aliases: ["周三", "星期三", "wed", "wednesday"] },
  { label: "四", aliases: ["周四", "星期四", "thu", "thursday"] },
  { label: "五", aliases: ["周五", "星期五", "fri", "friday"] },
  { label: "六", aliases: ["周六", "星期六", "sat", "saturday"] },
  { label: "日", aliases: ["周日", "周天", "星期日", "星期天", "sun", "sunday"] },
];

function renderTrainingDayBadges(availableDays) {
  const haystack = splitProfileList(availableDays).join(" ").toLowerCase();
  return TRAINING_DAY_BADGES.map((day) => {
    const active = day.aliases.some((alias) => haystack.includes(alias.toLowerCase()));
    return `<span class="training-day-badge ${active ? "is-active" : ""}">${escapeHtml(day.label)}</span>`;
  }).join("");
}

function renderRunnerIdentityCard(profile = {}) {
  state.latestProfile = profile || {};
  const level = text(profile.experience_level || profile.experience, "未知水平");
  const goal = text(profile.goal, "未设置目标");
  const runnerType = goal === "未设置目标" ? `${level}跑者` : goal;
  const constraints = buildProfileConstraints(profile);
  const availableDays = splitProfileList(profile.available_days).slice(0, 4).join("、") || "未填写";
  const maxSession = constraints.find(([label]) => label === "单次上限")?.[1] || text(profile.max_session_minutes || profile.long_run, "未填写");
  const summaryRows = [
    ["目标", goal],
    ["水平", level],
    ["单次上限", maxSession],
  ];
  const supportingCopy = constraints.length
    ? `已记录：${constraints.slice(0, 2).map(([label, value]) => `${label} ${value}`).join("；")}`
    : "补充可训练日、单次时长和伤病限制后，计划会更贴合你的实际情况。";

  runnerIdentityCard.innerHTML = `
    <div class="identity-card-head">
      <div>
        <p class="section-kicker">我的情况</p>
        <h2>${escapeHtml(runnerType)}</h2>
      </div>
      <button id="openProfilePanel" class="secondary-button compact-button" type="button">编辑我的情况</button>
    </div>
    <div class="training-day-badges" aria-label="可训练日">
      ${renderTrainingDayBadges(profile.available_days)}
    </div>
    <div class="identity-summary-rows" aria-label="跑者情况摘要">
      ${summaryRows.map(([label, value]) => `
        <div>
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(value)}</strong>
        </div>
      `).join("")}
    </div>
    <p class="identity-available-days">可训练日：${escapeHtml(availableDays)}</p>
    <p class="identity-supporting-copy">${escapeHtml(supportingCopy)}</p>
  `;
  $("openProfilePanel")?.addEventListener("click", openProfilePanel);
}

function renderProfilePanel(profile = state.latestProfile || {}) {
  profileEditorGroups.innerHTML = PROFILE_EDITOR_GROUPS.map((group) => `
    <section class="profile-editor-group">
      <h3>${escapeHtml(group.title)}</h3>
      <div class="profile-editor-grid">
        ${group.fields.map((field) => `
          <label for="editor-${field.key}">
            <span>${escapeHtml(field.label)}</span>
            <input
              id="editor-${field.key}"
              data-profile-editor-field="${field.key}"
              type="${field.type === "number" ? "number" : "text"}"
              value="${escapeHtml(profileFieldValue(profile, field))}"
              placeholder="${escapeHtml(field.placeholder || "")}"
            />
          </label>
        `).join("")}
      </div>
    </section>
  `).join("");
}

function openProfilePanel() {
  renderProfilePanel(state.latestProfile || {});
  if (typeof profileEditorDialog.showModal === "function") {
    profileEditorDialog.showModal();
  } else {
    profileEditorDialog.setAttribute("open", "");
  }
}

function closeProfilePanel() {
  if (typeof profileEditorDialog.close === "function") {
    profileEditorDialog.close();
  } else {
    profileEditorDialog.removeAttribute("open");
  }
}

function refreshPlanStateAfterProfileSave(profile) {
  renderRunnerIdentityCard(profile);
  renderProfilePanel(profile);
  profileStatus.textContent = "已同步";
  if (state.lastResponse) {
    queryHint.textContent = "画像已更新。当前日历不会自动改写；重新生成后会按最新画像计算。";
    renderPlanProgress({
      percent: 18,
      activeStep: "profile",
      status: "idle",
      phase: "画像已刷新",
      signal: "如需应用到当前计划，请重新生成训练日历",
    });
  }
}

async function saveProfilePanel() {
  const inputs = Array.from(document.querySelectorAll("[data-profile-editor-field]"));
  let latest = { ...(state.latestProfile || {}) };
  saveProfilePanelButton.disabled = true;
  saveProfilePanelButton.textContent = "保存中";
  try {
    const patch = {};
    for (const input of inputs) {
      const field = PROFILE_EDITOR_GROUPS.flatMap((group) => group.fields).find((item) => item.key === input.dataset.profileEditorField);
      if (!field) continue;
      patch[field.key] = input.value.trim();
    }
    latest = { ...latest, ...patch };
    const payload = await window.__apiClient.apiFetch("/profile", {
      method: "POST",
      body: JSON.stringify({ profile: patch }),
      timeoutMs: 3000,
    });
    latest = payload.profile || latest;
    fillProfileDraft(profileApiToDraft(latest));
    localStorage.setItem("marathon-profile-draft", JSON.stringify(getProfileDraft()));
    refreshPlanStateAfterProfileSave(latest);
    closeProfilePanel();
  } catch (error) {
    const localDraft = profileApiToDraft(latest);
    fillProfileDraft(localDraft);
    localStorage.setItem("marathon-profile-draft", JSON.stringify(localDraft));
    renderRunnerIdentityCard(profileDraftToApi(localDraft));
    profileStatus.textContent = "已本地保存";
    queryHint.textContent = `画像已先保存到本地，本次生成不会被阻塞。线上同步失败：${error.message}`;
  } finally {
    saveProfilePanelButton.disabled = false;
    saveProfilePanelButton.textContent = "保存画像";
  }
}

function compactJson(value) {
  if (!value || typeof value !== "object") return "-";
  const keys = Object.keys(value).filter((key) => value[key] !== undefined && value[key] !== null);
  return keys.length ? keys.slice(0, 8).join("、") : "-";
}

function parseMileageKm(value) {
  const match = String(value || "").replace(/,/g, "").match(/(\d+(?:\.\d+)?)/);
  if (!match) return "";
  const km = Number.parseFloat(match[1]);
  return Number.isFinite(km) && km > 0 ? km : "";
}

function formatMileageKm(km) {
  if (!Number.isFinite(km) || km <= 0) return "";
  const rounded = Math.round(km * 10) / 10;
  return `${Number.isInteger(rounded) ? rounded : rounded.toFixed(1)} km`;
}

function monthlyMileageToWeeklyMileage(value) {
  const monthlyKm = parseMileageKm(value);
  if (!monthlyKm) return "";
  return formatMileageKm(monthlyKm / 4.345);
}

function weeklyMileageToMonthlyMileage(value) {
  const weeklyKm = parseMileageKm(value);
  if (!weeklyKm) return "";
  return formatMileageKm(weeklyKm * 4.345);
}

function normalizeMonthlyMileage(value) {
  const monthlyKm = parseMileageKm(value);
  return monthlyKm ? formatMileageKm(monthlyKm) : String(value || "").trim();
}

function normalizeProfileDraft(draft = {}) {
  return {
    ...draft,
    lastMonthMileage:
      draft.lastMonthMileage ||
      draft.last_month_mileage ||
      draft.recentFourWeekMileage ||
      draft.recent_four_week_mileage ||
      draft.recent_4_week_mileage ||
      weeklyMileageToMonthlyMileage(draft.weeklyMileage || draft.weekly_mileage) ||
      "",
  };
}

function weeksUntilRace(value) {
  const match = String(value || "").trim().match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return "";
  const raceDate = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  if (
    raceDate.getFullYear() !== Number(match[1]) ||
    raceDate.getMonth() !== Number(match[2]) - 1 ||
    raceDate.getDate() !== Number(match[3])
  ) {
    return "";
  }
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  raceDate.setHours(0, 0, 0, 0);
  const diffDays = Math.ceil((raceDate.getTime() - today.getTime()) / 86400000);
  if (diffDays <= 0) return "";
  return String(Math.max(1, Math.ceil(diffDays / 7)));
}

function deriveProfileMetrics(draft = {}) {
  return {
    weeklyMileage: monthlyMileageToWeeklyMileage(draft.lastMonthMileage),
    recentFourWeekMileage: normalizeMonthlyMileage(draft.lastMonthMileage),
    planWeeks: weeksUntilRace(draft.raceDate),
  };
}

function updateProfileDerivedMetrics(draft = getProfileDraft()) {
  const metrics = deriveProfileMetrics(draft);
  document.querySelectorAll("[data-derived-weekly-mileage]").forEach((node) => {
    node.textContent = metrics.weeklyMileage || "-";
  });
  document.querySelectorAll("[data-derived-plan-weeks]").forEach((node) => {
    node.textContent = metrics.planWeeks ? `${metrics.planWeeks} 周` : "-";
  });
}

function getProfileDraft() {
  const draft = {};
  document.querySelectorAll("[data-profile-field]").forEach((input) => {
    draft[input.dataset.profileField] = input.value.trim();
  });
  return draft;
}

function actionableProfileMissingFields(draft = getProfileDraft()) {
  const normalized = normalizeProfileDraft(draft);
  const missing = [];
  const ability = normalized.lastMonthMileage || normalized.currentHalfTime || normalized.targetPace || normalized.longRun;
  if (!normalized.goal) missing.push("目标");
  if (!ability) missing.push("当前能力或月跑量");
  if (!normalized.raceDate) missing.push("比赛日期");
  if (!normalized.availableDays) missing.push("可训练日");
  if (!hasAnsweredLimitationField(normalized.limitations)) missing.push("伤病/疲劳限制（没有可写“无”）");
  return missing;
}

function profileDraftToApi(draft) {
  const metrics = deriveProfileMetrics(draft);
  const limitationText = normalizeLimitationText(draft.limitations);
  return {
    goal: draft.goal || "",
    experience_level: draft.experience || "",
    weekly_mileage: metrics.weeklyMileage || "",
    current_half_time: draft.currentHalfTime || "",
    recent_four_week_mileage: metrics.recentFourWeekMileage || "",
    last_month_mileage: metrics.recentFourWeekMileage || "",
    plan_duration_weeks: metrics.planWeeks || "",
    target_race_date: draft.raceDate || "",
    available_days: draft.availableDays || "",
    max_session_minutes: draft.longRun || "",
    target_pace: draft.targetPace || "",
    target_time: draft.targetPace || "",
    injury: limitationText,
    recovery_state: limitationText,
    injury_or_fatigue: hasProfileLimitation(draft.limitations),
  };
}

function profileApiToDraft(profile) {
  const injuryHistory = Array.isArray(profile.injury_history)
    ? profile.injury_history.join("、")
    : profile.injury_history || "";
  return normalizeProfileDraft({
    goal: profile.goal || "",
    experience: profile.experience_level || profile.experience || "",
    lastMonthMileage:
      profile.last_month_mileage ||
      profile.recent_four_week_mileage ||
      profile.recent_4_week_mileage ||
      weeklyMileageToMonthlyMileage(profile.weekly_mileage) ||
      "",
    currentHalfTime: profile.current_half_time || profile.half_marathon_time || profile.half_pb || "",
    raceDate: profile.target_race_date || "",
    availableDays: Array.isArray(profile.available_days)
      ? profile.available_days.join("、")
      : profile.available_days || "",
    longRun: profile.max_session_minutes || profile.long_run || "",
    targetPace: profile.target_pace || profile.target_half_time || profile.target_time || "",
    limitations: profile.injury || profile.recovery_state || profile.fatigue || injuryHistory || "无",
  });
}

function fillProfileDraft(draft) {
  document.querySelectorAll("[data-profile-field]").forEach((input) => {
    input.value = draft[input.dataset.profileField] || "";
  });
  updateProfileDerivedMetrics(getProfileDraft());
}

function profileDraftToPrompt(draft) {
  const metrics = deriveProfileMetrics(draft);
  const lines = [
    "请基于以下跑者情况生成训练计划，并明确说明关键训练安排的原因：",
    `- 目标：${draft.goal || "未填写"}`,
    `- 经验：${draft.experience || "未填写"}`,
    `- 上个月月跑量：${draft.lastMonthMileage || "未填写"}`,
    `- 估算平均周跑量：${metrics.weeklyMileage || "未填写"}`,
    `- 当前半马 PB：${draft.currentHalfTime || "未填写"}`,
    `- 比赛日期：${draft.raceDate || "未填写"}`,
    `- 建议计划周期：${formatPlanWeeksForPrompt(metrics.planWeeks)}`,
    `- 可训练日：${draft.availableDays || "未填写"}`,
    `- 最长训练：${draft.longRun || "未填写"}`,
    `- 目标配速/成绩：${draft.targetPace || "未填写"}`,
    `- 伤病/疲劳限制：${draft.limitations || "未填写"}`,
    "请优先快速返回结构化周计划和可点击训练日历，再补充强度区间、关键解释、安全校验和基石文档依据。",
  ];
  return lines.join("\n");
}

function formatPlanWeeksForPrompt(value) {
  const weeks = parsePlanWeeks(value);
  return weeks ? `${weeks} 周` : (value || "未填写");
}

function parsePlanWeeks(value) {
  const match = String(value || "").match(/(\d{1,2})/);
  if (!match) return "";
  const weeks = Number.parseInt(match[1], 10);
  return weeks > 0 ? String(weeks) : "";
}

function capturePlanIntent(query = queryInput.value) {
  const draft = getProfileDraft();
  const metrics = deriveProfileMetrics(draft);
  const queryWeeks = String(query || "").match(/(\d{1,2})\s*周/);
  state.lastPlanIntent = {
    requestedWeeks: metrics.planWeeks || (queryWeeks ? queryWeeks[1] : ""),
    raceDate: draft.raceDate || "",
    goal: draft.goal || "",
    currentHalfTime: draft.currentHalfTime || "",
    targetPace: draft.targetPace || "",
  };
}

async function saveProfileDraft() {
  const draft = getProfileDraft();
  localStorage.setItem("marathon-profile-draft", JSON.stringify(draft));
  try {
    const payload = await window.__apiClient.apiFetch("/profile/default_user", {
      method: "PUT",
      body: JSON.stringify({
        user_id: "default_user",
        profile: profileDraftToApi(draft),
      }),
      timeoutMs: 3000,
    });
    renderRunnerIdentityCard(payload.profile || {});
    profileStatus.textContent = "已同步";
  } catch {
    profileStatus.textContent = "已本地保存";
    queryHint.textContent = "画像已先保存到本地，本次生成不会被阻塞。";
  }
}

async function loadProfileDraft() {
  try {
    const payload = await window.__apiClient.apiFetch("/profile/default_user");
    fillProfileDraft(profileApiToDraft(payload.profile || {}));
    renderRunnerIdentityCard(payload.profile || {});
    profileStatus.textContent = "已同步";
    return;
  } catch {}

  const raw = localStorage.getItem("marathon-profile-draft");
  if (!raw) return;
  try {
    const draft = normalizeProfileDraft(JSON.parse(raw));
    fillProfileDraft(draft);
    renderRunnerIdentityCard(profileDraftToApi(draft));
    profileStatus.textContent = "已载入";
  } catch {
    profileStatus.textContent = "草稿异常";
  }
}

async function buildProfilePrompt() {
  const prompt = profileDraftToPrompt(getProfileDraft());
  queryInput.value = prompt;
  queryInput.focus();
  await saveProfileDraft();
}

function getPlanHistory() {
  try {
    return JSON.parse(localStorage.getItem("marathon-plan-history") || "[]");
  } catch {
    return [];
  }
}

function restorePlanResponse(response, badge = "历史计划") {
  state.lastResponse = response;
  renderReport(state.lastResponse);
  renderCalendar(state.lastResponse);
  renderEvidencePreview(state.lastResponse);
  renderStatusPanel(state.lastResponse);
  renderAdjustmentHistory(state.lastResponse);
  tokenUsageBox.textContent = formatTokenUsage(state.lastResponse.token_usage);
  auditScoresBox.textContent = formatAuditScores(state.lastResponse.audit_scores);
  guidedQuestionsBox.textContent = renderQuestions(state.lastResponse.guided_questions);
  resultBadge.textContent = badge;
}

function renderLocalPlanHistory() {
  const items = getPlanHistory();
  if (!items.length) {
    historyList.innerHTML = '<div class="empty-state">暂无本地历史。</div>';
    return;
  }
  const visibleItems = state.historyExpanded ? items.slice(0, 12) : items.slice(0, 2);
  const hiddenCount = Math.max(0, items.length - visibleItems.length);
  historyList.className = "compact-list";
  historyList.innerHTML = [
    ...visibleItems
    .map((item, index) => `
      <div class="history-row ${state.historyExpanded ? "is-expanded" : "is-summary"}">
        <button class="history-item" data-history-index="${index}" type="button">
          <span class="history-row-copy">
            <strong>${escapeHtml(item.title || "训练计划")}</strong>
            <small>${escapeHtml(item.createdAt || "本地保存")}</small>
          </span>
          <span class="history-open-label">打开</span>
        </button>
        ${state.historyExpanded ? `<button class="history-delete" data-delete-history-index="${index}" type="button" aria-label="删除本地历史计划">删除</button>` : ""}
      </div>
    `),
    hiddenCount ? `<div class="history-summary">还有 ${hiddenCount} 条历史，查看全部后可继续恢复。</div>` : "",
  ].join("");
  updateHistoryToggle(items.length);
  historyList.querySelectorAll("[data-history-index]").forEach((button) => {
    button.addEventListener("click", () => {
      const item = getPlanHistory()[Number(button.dataset.historyIndex)];
      if (!item?.response) return;
      restorePlanResponse(item.response, "本地历史");
    });
  });
  historyList.querySelectorAll("[data-delete-history-index]").forEach((button) => {
    button.addEventListener("click", () => deleteLocalPlanSnapshot(Number(button.dataset.deleteHistoryIndex)));
  });
}

async function renderPlanHistory() {
  try {
    const payload = await window.__apiClient.apiFetch("/plans");
    const plans = payload.plans || [];
    if (plans.length) {
      const visiblePlans = state.historyExpanded ? plans.slice(0, 12) : plans.slice(0, 2);
      const hiddenCount = Math.max(0, plans.length - visiblePlans.length);
      historyList.className = "compact-list";
      historyList.innerHTML = [
        ...visiblePlans
        .map((plan) => `
          <div class="history-row ${state.historyExpanded ? "is-expanded" : "is-summary"}">
            <button class="history-item" data-plan-id="${escapeHtml(plan.id)}" type="button">
              <span class="history-row-copy">
                <strong>${escapeHtml(plan.goal || "训练计划")} · ${escapeHtml(plan.actual_weeks || plan.requested_weeks || "?")} 周</strong>
                <small>${escapeHtml((plan.created_at || "").slice(0, 16) || "已保存计划")}</small>
              </span>
              <span class="history-open-label">打开</span>
            </button>
            ${state.historyExpanded ? `<button class="history-delete" data-delete-plan-id="${escapeHtml(plan.id)}" type="button" aria-label="删除已保存计划">删除</button>` : ""}
          </div>
        `),
        hiddenCount ? `<div class="history-summary">还有 ${hiddenCount} 条历史，查看全部后可继续恢复。</div>` : "",
      ].join("");
      updateHistoryToggle(plans.length);
      historyList.querySelectorAll("[data-plan-id]").forEach((button) => {
        button.addEventListener("click", () => loadSavedPlan(button.dataset.planId));
      });
      historyList.querySelectorAll("[data-delete-plan-id]").forEach((button) => {
        button.addEventListener("click", () => deleteSavedPlan(button.dataset.deletePlanId));
      });
      return;
    }
  } catch {}
  renderLocalPlanHistory();
}

function updateHistoryToggle(totalCount = 0) {
  if (!toggleHistoryListButton) return;
  toggleHistoryListButton.hidden = totalCount <= 2;
  toggleHistoryListButton.textContent = state.historyExpanded ? "收起历史" : "查看全部历史";
  toggleHistoryListButton.setAttribute("aria-expanded", state.historyExpanded ? "true" : "false");
}

function deleteLocalPlanSnapshot(index) {
  if (!Number.isInteger(index) || index < 0) return;
  const items = getPlanHistory();
  if (!items[index]) return;
  if (!window.confirm("确认删除这条本地历史计划吗？")) return;
  items.splice(index, 1);
  localStorage.setItem("marathon-plan-history", JSON.stringify(items));
  renderLocalPlanHistory();
}

async function deleteSavedPlan(planId) {
  if (!planId) return;
  if (!window.confirm("确认删除这条已保存计划吗？")) return;
  try {
    await window.__apiClient.apiFetch(`/plans/${encodeURIComponent(planId)}`, { method: "DELETE" });
    if (state.lastResponse?.training_plan_id === planId) {
      clearResult();
    }
    await renderPlanHistory();
  } catch (error) {
    historyList.innerHTML = `<div class="empty-state">删除失败：${escapeHtml(error.message)}</div>`;
  }
}

function parseEventContent(event) {
  if (!event) return {};
  if (event.content && typeof event.content === "object") {
    return event.content;
  }
  if (!event.content_json || typeof event.content_json !== "string") {
    return {};
  }
  try {
    const parsed = JSON.parse(event.content_json);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

async function loadSavedPlan(planId) {
  if (!planId) return;
  try {
    const detail = await window.__apiClient.apiFetch(`/plans/${encodeURIComponent(planId)}`);
    const response = {
      structured_training_plan: detail.structured_training_plan || {},
      structured_report: {
        monthly_training_calendar: {
          days: (detail.events || []).map((event) => {
            const eventContent = parseEventContent(event);
            return ({
            ...eventContent,
            week_index: eventContent.week_index || event.week_no,
            day_index: eventContent.day_index || event.day_no,
            day_label: eventContent.day_label || event.day_label,
            scheduled_date: event.scheduled_date || eventContent.scheduled_date,
            start_time: event.start_time || eventContent.start_time,
            duration_min: event.duration_min || eventContent.duration_min,
            training_type: eventContent.training_type || event.training_type || event.title || event.workout_type,
            training_type_label: eventContent.training_type_label || event.training_type_label,
            workout_type: eventContent.workout_type || event.workout_type,
            event_id: event.id,
            plan_id: detail.plan?.id,
            warmup: eventContent.warmup || event.warmup,
            main_set: eventContent.main_set || event.main_set,
            cooldown: eventContent.cooldown || event.cooldown,
            venue: eventContent.venue || event.venue,
            notes: eventContent.notes || event.notes,
            zone_range: eventContent.zone_range || event.intensity_zone,
            evidence_ids: eventContent.evidence_ids || (event.evidence_ids ? String(event.evidence_ids).split(",").map((id) => id.trim()).filter(Boolean) : []),
            evidence_tier: eventContent.evidence_tier || event.evidence_tier || "saved_plan",
            evidence_tier_label: eventContent.evidence_tier_label || event.evidence_tier_label || "已保存计划",
            is_rest: eventContent.is_rest ?? event.workout_type === "rest",
            field_sources: eventContent.field_sources || event.field_sources || {},
            protocol_check: eventContent.protocol_check || event.protocol_check || {},
            action_match: eventContent.action_match || event.action_match || {},
            kb_fallback: eventContent.kb_fallback || event.kb_fallback || {},
            risk_gate: eventContent.risk_gate || event.risk_gate || {},
            workflow_trace: eventContent.workflow_trace || event.workflow_trace || detail.structured_training_plan?.workflow_trace || detail.workflow_trace || {},
            latest_feedback: eventContent.latest_feedback || event.latest_feedback,
            adaptive_adjustment: eventContent.adaptive_adjustment || event.adaptive_adjustment,
            feedback_effect: eventContent.feedback_effect || event.feedback_effect,
            latest_feedback_effect: eventContent.latest_feedback_effect || event.latest_feedback_effect,
            feedback_replan: eventContent.feedback_replan || event.feedback_replan,
            generation_status: eventContent.generation_status || event.generation_status,
            adjustment_hint: eventContent.adjustment_hint || event.adjustment_hint,
            card_status: eventContent.card_status || event.card_status,
            trace: eventContent.trace || event.trace || {},
          });
          }),
        },
      },
      report: detail.plan?.source_query || "",
      training_plan_id: planId,
      workflow_trace: detail.workflow_trace || detail.structured_training_plan?.workflow_trace || {},
      execution_status_summary: detail.execution_status_summary || {},
      adjustment_history: detail.adjustment_history || [],
      training_plan_review: detail.training_plan_review || detail.structured_training_plan?.training_plan_review || {},
      evidence_chain: detail.evidence_chain || detail.structured_training_plan?.evidence_chain || {},
      token_usage: {},
      audit_scores: {},
      guided_questions: [],
    };
    restorePlanResponse(response, "历史计划");
  } catch (error) {
    historyList.innerHTML = `<div class="empty-state">历史计划加载失败：${escapeHtml(error.message)}</div>`;
  }
}

async function saveCurrentPlanSnapshot() {
  if (!state.lastResponse) {
    historyList.innerHTML = '<div class="empty-state">没有可保存的计划结果。</div>';
    return;
  }
  const summary = summarizePlan(state.lastResponse);
  const structuredPlan = getStructuredPlan(state.lastResponse);
  if (state.lastResponse.training_plan_id) {
    await renderPlanHistory();
    return;
  }
  if (structuredPlan?.week_plans?.length) {
    try {
      await window.__apiClient.apiFetch("/plans", {
        method: "POST",
        body: JSON.stringify({
          user_id: "default_user",
          source_query: queryInput.value || state.lastResponse.report || "",
          structured_training_plan: structuredPlan,
          calendar_days: normalizeCalendarDays(state.lastResponse),
          calendar_settings: getCalendarSettings(),
        }),
      });
      await renderPlanHistory();
      return;
    } catch {}
  }
  const items = getPlanHistory();
  items.unshift({
    title: `${summary.goal} · ${summary.weeks} 周`,
    createdAt: new Date().toLocaleString("zh-CN"),
    response: state.lastResponse,
  });
  localStorage.setItem("marathon-plan-history", JSON.stringify(items.slice(0, 12)));
  renderLocalPlanHistory();
}

function getFeedbackField(root, name) {
  return root?.querySelector?.(`[data-feedback-field="${name}"]`);
}

function selectedMedicalRedFlags(root = dayModalContent) {
  return Array.from(root?.querySelectorAll?.("[data-medical-red-flag]:checked") || [])
    .map((input) => String(input.value || "").trim())
    .filter(Boolean);
}

function medicalRedFlagLabels(values = []) {
  const labelByValue = Object.fromEntries(MEDICAL_RED_FLAGS.map((item) => [item.value, item.label]));
  return values.map((value) => labelByValue[value] || value).filter(Boolean);
}

function buildFeedbackContext(day = state.selectedDay) {
  const week = day?.week_index || day?.week_no || "";
  const dayIndex = day?.day_index || day?.day_no || "";
  const dayToken = dayIndex || day?.day_label || day?.day || day?.scheduled_date || day?.date || "";
  return {
    plan_id: day?.plan_id || state.lastResponse?.training_plan_id || "",
    event_id: day?.event_id || day?.id || "",
    day_key: day?.day_key || [week, dayToken].filter(Boolean).join("-"),
  };
}

function collectFeedbackPayload(root = dayModalContent) {
  const completion = getFeedbackField(root, "completion")?.value || "已完成";
  const fatigue = getFeedbackField(root, "fatigue")?.value || "轻微";
  const pain = getFeedbackField(root, "pain")?.value || "没有疼痛";
  const sleep = getFeedbackField(root, "sleep")?.value || "良好";
  const notes = (getFeedbackField(root, "notes")?.value || "").trim();
  const scheduleConstraints = (getFeedbackField(root, "scheduleConstraints")?.value || "").trim();
  const medical_red_flags = selectedMedicalRedFlags(root);
  return { completion, fatigue, pain, sleep, notes, scheduleConstraints, medical_red_flags };
}

function buildFeedbackPrompt(payload, day = state.selectedDay) {
  const { completion, fatigue, pain, sleep, notes, medical_red_flags = [] } = payload;
  const redFlagText = medicalRedFlagLabels(medical_red_flags).join("、");
  const dayLabel = day ? text(day.day_label || day.date || day.day, "当前训练日") : "当前训练日";
  const title = day ? displayTrainingTitle(day) : "训练";
  const mainSet = day ? cleanWorkoutText(day.main_set || day.intensity_target || day.note, "") : "";
  return [
    "请根据这次训练反馈调整后续计划：",
    `- 训练日：${dayLabel} · ${title}`,
    mainSet ? `- 原计划主课：${mainSet}` : "",
    `- 完成状态：${completion}`,
    `- 主观疲劳：${fatigue}`,
    `- 疼痛/不适：${pain}`,
    `- 睡眠恢复：${sleep}`,
    redFlagText ? `- 医疗红旗：${redFlagText}` : "",
    notes ? `- 补充说明：${notes}` : "",
    "请给出明日调整、本周微调、替代训练和风险提醒。",
  ].filter(Boolean).join("\n");
}

function affectedDaysAfterFeedback(day = state.selectedDay) {
  if (!state.lastResponse || !day) return [];
  const days = normalizeCalendarDays(state.lastResponse);
  const selectedKeys = new Set(dayKeyCandidates(day));
  const selectedIndex = days.findIndex((item) => dayKeyCandidates(item).some((key) => selectedKeys.has(key)));
  if (selectedIndex < 0) return days.slice(0, 3);
  return days.slice(selectedIndex + 1).filter((item) => !isRestDay(item)).slice(0, 3);
}

function buildLatestFeedbackSummary(payload) {
  const adjustment = payload?.adaptive_adjustment || {};
  const workoutFeedback = payload?.workout_feedback || payload?.feedback || {};
  return {
    feedback_id: payload?.feedback_id || payload?.id || "",
    save_status: payload?.save_status || payload?.saved_status || (payload?.feedback_id ? "saved" : "not_saved"),
    generation_status: payload?.generation_status || adjustment.product_status || "",
    completion_status: workoutFeedback.completion_status || payload?.completion_status || "",
    fatigue: workoutFeedback.fatigue || workoutFeedback.subjective_fatigue || payload?.fatigue || "",
    pain: workoutFeedback.pain || workoutFeedback.pain_status || payload?.pain || "",
    sleep: workoutFeedback.sleep || workoutFeedback.sleep_quality || payload?.sleep || "",
    created_at: payload?.created_at || payload?.saved_at || "",
    summary: adjustment.rationale || payload?.summary || "",
    next_day_adjustment: adjustment.next_day_adjustment || "",
    weekly_adjustment: adjustment.weekly_adjustment || "",
    alternative_workout: adjustment.alternative_workout || "",
    risk_alert: adjustment.risk_alert || "",
    reason_codes: adjustment.reason_codes || payload?.reason_codes || [],
    risk_gate: payload?.risk_gate || {},
    protocol_recheck: payload?.protocol_recheck || {},
  };
}

function feedbackDayMatches(day, selectedDay, feedbackContext = {}) {
  if (!day) return false;
  const targetIds = [
    feedbackContext.event_id,
    selectedDay?.event_id,
    selectedDay?.id,
  ].map((item) => String(item || "").trim()).filter(Boolean);
  const dayIds = [
    day.event_id,
    day.id,
  ].map((item) => String(item || "").trim()).filter(Boolean);
  if (targetIds.length && dayIds.some((id) => targetIds.includes(id))) return true;

  const targetKeys = new Set([
    feedbackContext.day_key,
    ...dayKeyCandidates(selectedDay),
  ].map((item) => String(item || "").trim()).filter(Boolean));
  if (!targetKeys.size) return false;
  return dayKeyCandidates(day).some((key) => targetKeys.has(String(key || "").trim()));
}

function applyLatestFeedbackToDayList(days, selectedDay, feedbackSummary, feedbackContext = {}) {
  if (!Array.isArray(days)) return false;
  let updated = false;
  days.forEach((day, index) => {
    if (!feedbackDayMatches(day, selectedDay, feedbackContext)) return;
    days[index] = {
      ...day,
      latest_feedback: feedbackSummary,
      adaptive_adjustment: feedbackSummary,
    };
    updated = true;
  });
  return updated;
}

function feedbackAffectedEvents(payload, fallbackDays = []) {
  const persisted = Array.isArray(payload?.affected_events) ? payload.affected_events.filter(Boolean) : [];
  return persisted.length ? persisted : fallbackDays;
}

function feedbackEffectForDay(day) {
  const effect = day?.feedback_effect || day?.latest_feedback_effect;
  return effect && typeof effect === "object" ? effect : null;
}

function feedbackEffectStatusLabel(effect = {}) {
  if (effect.action === "stop_for_medical_referral") return "暂停并评估";
  if (effect.action === "downgrade") return "需降级执行";
  return statusLabel(effect.action || "feedback_adjusted");
}

function feedbackEventMatchesDay(affectedEvent, day) {
  if (!affectedEvent || !day) return false;
  const affectedIds = [affectedEvent.event_id, affectedEvent.id].map((item) => String(item || "").trim()).filter(Boolean);
  const dayIds = [day.event_id, day.id].map((item) => String(item || "").trim()).filter(Boolean);
  if (affectedIds.length && dayIds.some((id) => affectedIds.includes(id))) return true;
  const affectedKeys = new Set(dayKeyCandidates({
    day_key: affectedEvent.day_key,
    day_label: affectedEvent.day_label,
    date: affectedEvent.scheduled_date || affectedEvent.date,
  }).map((item) => String(item || "").trim()).filter(Boolean));
  return affectedKeys.size ? dayKeyCandidates(day).some((key) => affectedKeys.has(String(key || "").trim())) : false;
}

function applyFeedbackEffectsToDayList(days, affectedEvents = []) {
  if (!Array.isArray(days) || !affectedEvents.length) return false;
  let updated = false;
  days.forEach((day, index) => {
    const affected = affectedEvents.find((item) => feedbackEventMatchesDay(item, day));
    if (!affected?.feedback_effect) return;
    const effect = affected.feedback_effect;
    // 后端已经做过安全判断，前端只叠加可见影响层，不改写原始训练处方。
    days[index] = {
      ...day,
      feedback_effect: effect,
      latest_feedback_effect: effect,
      card_status: day.card_status || (effect.action === "stop_for_medical_referral" ? "medical_referral" : "feedback_adjusted"),
      generation_status: day.generation_status || (effect.action === "stop_for_medical_referral" ? "medical_referral" : "feedback_adjusted"),
      adjustment_hint: effect.adjusted_instruction || day.adjustment_hint,
    };
    updated = true;
  });
  return updated;
}

function buildFeedbackEffectHtml(day) {
  const effect = feedbackEffectForDay(day);
  if (!effect) return "";
  const reasons = Array.isArray(effect.reason_codes) ? effect.reason_codes.map(statusLabel).join(" / ") : statusLabel(effect.reason_codes);
  return `
    <section class="feedback-result-card feedback-effect-card" data-feedback-effect>
      <div class="day-card-top">
        <strong>已按反馈调整</strong>
        <span>${escapeHtml(feedbackEffectStatusLabel(effect))}</span>
      </div>
      <p>${escapeHtml(effect.reason || "这一天受反馈影响，执行前按调整建议处理。")}</p>
      <div class="feedback-result-grid">
        <div><span>受反馈影响</span><strong>${escapeHtml(effect.source_feedback_id || "已保存反馈")}</strong></div>
        <div><span>调整原因</span><strong>${escapeHtml(reasons || "-")}</strong></div>
        <div><span>调整后执行建议</span><strong>${escapeHtml(effect.adjusted_instruction || "按降级建议执行。")}</strong></div>
        <div hidden data-expert-only><span>原主课</span><strong>${escapeHtml(effect.original_main_set || "-")}</strong></div>
      </div>
    </section>`;
}

function buildFeedbackReplanHtml(feedback_replan = {}, feedbackId = "") {
  const patches = Array.isArray(feedback_replan.patches) ? feedback_replan.patches : [];
  if (!feedback_replan.status && !patches.length) return "";
  const status = feedback_replan.status || "suggested";
  const blockedReason = feedback_replan.audit?.blocked_reason || "";
  const patchHtml = patches.length
    ? patches.map((patch) => {
      const original = patch.original || {};
      const suggested = patch.suggested || {};
      const targetDay = patch.target_day ? ` · 目标：${patch.target_day}` : "";
      return `
        <li>
          <strong>${escapeHtml(original.title || "后续训练日")}</strong>
          <span>原计划：${escapeHtml(original.main_set || "-")}</span>
          <span>建议：${escapeHtml(suggested.main_set || "-")}${escapeHtml(targetDay)}</span>
          <em>${escapeHtml(patch.reason || suggested.reason || "根据反馈保守调整。")}</em>
        </li>`;
    }).join("")
    : `<li>${escapeHtml(blockedReason || (status === "needs_manual_choice" ? "本周没有可安全安排的训练日，请修改本周时间或先休息。" : "当前没有可执行 patch；医疗红旗不能直接恢复，请先完成专业评估。"))}</li>`;
  const disabledAttr = feedbackId ? "" : " disabled";
  const appliedAttr = status === "applied" ? " data-replan-applied-highlight" : "";
  const recoverHint = status === "blocked_medical" ? "<p>不能直接恢复跑步主课，需要专业医疗评估通过后再复核。</p>" : "";
  return `
    <section class="feedback-result-card feedback-replan-card" data-feedback-replan${appliedAttr}>
      <div class="day-card-top">
        <strong>局部重规划建议</strong>
        <span>${escapeHtml(feedbackStatusLabel(status))}</span>
      </div>
      ${recoverHint}
      <ul class="feedback-replan-patches">${patchHtml}</ul>
      <div class="modal-actions compact-feedback-actions">
        <button type="button" class="primary-button" data-feedback-replan-action="accept"${disabledAttr}>按调整执行</button>
        <button type="button" class="secondary-button" data-feedback-replan-action="replan"${disabledAttr}>重新排本周</button>
        <button type="button" class="secondary-button" data-feedback-replan-action="update_availability"${disabledAttr}>修改本周时间</button>
        <button type="button" class="secondary-button" data-feedback-replan-action="recover"${disabledAttr}>我已恢复，申请复核</button>
        <button type="button" class="secondary-button" data-feedback-replan-action="dismiss"${disabledAttr}>暂不采用</button>
      </div>
    </section>`;
}

function applyFeedbackReplanToDayList(days, feedback_replan = {}) {
  if (!Array.isArray(days) || !feedback_replan?.patches?.length) return false;
  let updated = false;
  const patchByEventId = new Map(feedback_replan.patches.map((patch) => [String(patch.event_id || ""), patch]));
  days.forEach((day) => {
    const eventId = String(day?.event_id || day?.id || "");
    const patch = patchByEventId.get(eventId);
    if (!patch) return;
    // 前端只叠加建议状态，不直接改写主课，避免用户未确认时误展示为已执行。
    day.feedback_replan = { ...feedback_replan, patches: [patch] };
    updated = true;
  });
  return updated;
}

function applyFeedbackReplanToLastResponse(feedback_replan = {}) {
  if (!state.lastResponse || !feedback_replan?.patches?.length) return;
  const response = state.lastResponse;
  const calendar = getCalendar(response);
  const structuredReport = getStructuredReport(response);
  const structuredPlan = getStructuredPlan(response);
  applyFeedbackReplanToDayList(calendar.days, feedback_replan);
  applyFeedbackReplanToDayList(structuredReport.monthly_training_calendar?.days, feedback_replan);
  applyFeedbackReplanToDayList(response.monthly_training_calendar?.days, feedback_replan);
  applyFeedbackReplanToDayList(response.daily_schedule_cards, feedback_replan);
  applyFeedbackReplanToDayList(structuredReport.daily_schedule_cards, feedback_replan);
  (structuredPlan.week_plans || []).forEach((week) => applyFeedbackReplanToDayList(week.days, feedback_replan));
}

function latestFeedbackHistoryEntry(selectedDay, feedbackSummary, payload, feedbackContext = {}) {
  return {
    feedback_id: feedbackSummary.feedback_id || payload?.feedback_id || "",
    plan_id: feedbackContext.plan_id || selectedDay?.plan_id || "",
    event_id: feedbackContext.event_id || selectedDay?.event_id || selectedDay?.id || "",
    day_key: feedbackContext.day_key || selectedDay?.day_key || selectedDay?.day_label || selectedDay?.date || "",
    created_at: feedbackSummary.created_at || new Date().toISOString(),
    reason_codes: feedbackSummary.reason_codes || [],
    risk_gate: feedbackSummary.risk_gate || payload?.risk_gate || {},
    protocol_recheck: feedbackSummary.protocol_recheck || payload?.protocol_recheck || {},
    adaptive_adjustment: feedbackSummary,
    affected_events: feedbackAffectedEvents(payload, affectedDaysAfterFeedback(selectedDay)).map((day) => ({
      event_id: day.event_id || day.id || "",
      day_key: day.day_key || day.day_label || day.date || "",
      day_label: day.day_label || day.scheduled_date || day.date || day.day || "",
      training_type: day.training_type || day.workout_type || "",
      feedback_effect: day.feedback_effect || {},
    })),
  };
}

function mergeLatestFeedbackIntoAdjustmentHistory(response, selectedDay, feedbackSummary, payload, feedbackContext = {}) {
  if (!response) return;
  const entry = latestFeedbackHistoryEntry(selectedDay, feedbackSummary, payload, feedbackContext);
  const history = Array.isArray(response.adjustment_history) ? response.adjustment_history : [];
  const identity = entry.feedback_id || `${entry.event_id}:${entry.day_key}:${entry.created_at}`;
  const existing = history.filter((item) => {
    const itemIdentity = item.feedback_id || `${item.event_id || ""}:${item.day_key || ""}:${item.created_at || ""}`;
    return itemIdentity !== identity;
  });
  response.adjustment_history = [entry, ...existing].slice(0, 20);
}

function applyLatestFeedbackToLastResponse(payload, selectedDay = state.selectedDay, feedbackContext = {}) {
  if (!state.lastResponse || !selectedDay) return null;
  const feedbackSummary = buildLatestFeedbackSummary(payload);
  const response = state.lastResponse;
  const calendar = getCalendar(response);
  const structuredReport = getStructuredReport(response);
  const structuredPlan = getStructuredPlan(response);

  applyLatestFeedbackToDayList(calendar.days, selectedDay, feedbackSummary, feedbackContext);
  applyLatestFeedbackToDayList(structuredReport.monthly_training_calendar?.days, selectedDay, feedbackSummary, feedbackContext);
  applyLatestFeedbackToDayList(response.monthly_training_calendar?.days, selectedDay, feedbackSummary, feedbackContext);
  applyLatestFeedbackToDayList(response.daily_schedule_cards, selectedDay, feedbackSummary, feedbackContext);
  applyLatestFeedbackToDayList(structuredReport.daily_schedule_cards, selectedDay, feedbackSummary, feedbackContext);
  const affectedEvents = feedbackAffectedEvents({ affected_events: payload.affected_events }, []);
  applyFeedbackEffectsToDayList(calendar.days, affectedEvents);
  applyFeedbackEffectsToDayList(structuredReport.monthly_training_calendar?.days, affectedEvents);
  applyFeedbackEffectsToDayList(response.monthly_training_calendar?.days, affectedEvents);
  applyFeedbackEffectsToDayList(response.daily_schedule_cards, affectedEvents);
  applyFeedbackEffectsToDayList(structuredReport.daily_schedule_cards, affectedEvents);
  (structuredPlan.week_plans || []).forEach((week) => {
    applyLatestFeedbackToDayList(week.days, selectedDay, feedbackSummary, feedbackContext);
    applyFeedbackEffectsToDayList(week.days, affectedEvents);
  });
  if (state.selectedDay) {
    state.selectedDay = {
      ...state.selectedDay,
      latest_feedback: feedbackSummary,
      adaptive_adjustment: feedbackSummary,
    };
  }
  if (payload?.feedback_replan) {
    applyFeedbackReplanToLastResponse(payload.feedback_replan);
  }
  mergeLatestFeedbackIntoAdjustmentHistory(response, selectedDay, feedbackSummary, payload, feedbackContext);
  return feedbackSummary;
}

function isMedicalReferralFeedback(payload) {
  const adjustment = payload?.adaptive_adjustment || {};
  const riskGate = payload?.risk_gate || {};
  const candidates = [
    payload?.generation_status,
    riskGate.product_status,
    riskGate.status,
    adjustment.product_status,
    adjustment.generation_status,
  ].map((item) => String(item || "").trim());
  return candidates.includes("medical_referral") || candidates.includes("blocked");
}

function buildLatestFeedbackHtml(day) {
  const feedback = day?.latest_feedback || {};
  const hasFeedback = Boolean(
    feedback.feedback_id ||
    feedback.id ||
    feedback.summary ||
    feedback.next_day_adjustment ||
    feedback.raw_text ||
    feedback.risk_gate?.status
  );
  if (!hasFeedback) return "";
  const riskGate = feedback.risk_gate || {};
  const protocolRecheck = feedback.protocol_recheck || {};
  const reasonCodes = Array.isArray(feedback.reason_codes) ? feedback.reason_codes.map(statusLabel).join(" / ") : statusLabel(feedback.reason_codes);
  return `
    <section class="feedback-result-card latest-feedback-card" data-latest-feedback>
      <div class="day-card-top">
        <strong>最近一次反馈</strong>
        <span>${escapeHtml(feedbackStatusLabel(feedback.generation_status || riskGate.product_status || "-"))}</span>
      </div>
      <p>${escapeHtml(feedback.summary || feedback.rationale || feedback.raw_text || "已保存反馈调整。")}</p>
      <div class="feedback-result-grid">
        <div><span>保存状态</span><strong>${escapeHtml(feedback.save_status || (feedback.id || feedback.feedback_id ? "已保存" : "未保存"))}</strong></div>
        <div><span>调整原因</span><strong>${escapeHtml(reasonCodes || "-")}</strong></div>
        <div><span>安全判断</span><strong>${escapeHtml(statusLabel(riskGate.status || "-"))}</strong></div>
        <div><span>是否继续</span><strong>${escapeHtml(protocolRecheck.allowed === false ? "不允许继续" : protocolRecheck.allowed === true ? "允许降级后继续" : "-")}</strong></div>
        <div><span>明日调整</span><strong>${escapeHtml(feedback.next_day_adjustment || "-")}</strong></div>
        <div><span>本周微调</span><strong>${escapeHtml(feedback.weekly_adjustment || "-")}</strong></div>
      </div>
    </section>
  `;
}

function feedbackSummaryForPrompt(feedback = state.lastFeedbackResult) {
  const adjustment = feedback?.adaptive_adjustment || {};
  return [
    `状态：${feedbackStatusLabel(feedback?.generation_status || adjustment.product_status || "-")}`,
    `保存状态：${feedback?.save_status || feedback?.saved_status || "-"}`,
    `摘要：${adjustment.rationale || feedback?.summary || "-"}`,
  ].join("\n");
}

function adaptiveAdjustmentForPrompt(feedback = state.lastFeedbackResult) {
  const adjustment = feedback?.adaptive_adjustment || {};
  return [
    `1. 明日调整：${adjustment.next_day_adjustment || "-"}`,
    `2. 本周微调：${adjustment.weekly_adjustment || "-"}`,
    `3. 替代训练：${adjustment.alternative_workout || "-"}`,
    `4. 风险提醒：${adjustment.risk_alert || "-"}`,
    `5. 调整动作：${adjustment.adjustment_action || feedback?.risk_gate?.adjustment_action || "-"}`,
  ].join("\n");
}

function affectedDaysForPrompt(days = affectedDaysAfterFeedback()) {
  if (!days.length) return "- 待生成调整版计划时确认";
  return days.map((day) => `- ${text(day.day_label || day.date || day.day, "后续训练日")}：${displayTrainingTitle(day)}`).join("\n");
}

function buildRegenerationQueryFromFeedback(feedback = state.lastFeedbackResult, day = state.selectedDay) {
  const feedbackPayload = collectFeedbackPayload(dayModalContent);
  const dayLabel = day ? text(day.day_label || day.date || day.day, "当前训练日") : "当前训练日";
  const mainSet = day ? cleanWorkoutText(day.main_set || day.intensity_target || day.note, "-") : "-";
  return [
    "请基于训练反馈生成调整版训练计划，并明确列出受影响训练日。",
    "当前反馈摘要",
    feedbackSummaryForPrompt(feedback),
    buildFeedbackPrompt(feedbackPayload, day),
    "当前训练日",
    dayLabel,
    "原计划主课",
    mainSet,
    "adaptive_adjustment 五段式结果",
    adaptiveAdjustmentForPrompt(feedback),
    "明确列出受影响训练日",
    affectedDaysForPrompt(),
  ].join("\n");
}

function buildFeedbackResultHtml(payload, affectedDays = []) {
  const adjustment = payload?.adaptive_adjustment || {};
  const riskGate = payload?.risk_gate || {};
  const protocolRecheck = payload?.protocol_recheck || {};
  const isMedicalReferral = isMedicalReferralFeedback(payload);
  const reasonCodes = Array.isArray(adjustment.reason_codes) ? adjustment.reason_codes : [];
  const riskTriggers = listText(riskGate.triggers || riskGate.detected_triggers, "无");
  const protocolViolations = listText(protocolRecheck.violations || protocolRecheck.errors || protocolRecheck.issues, "无");
  const planDiff = payload?.plan_diff || {};
  const action = adjustment.adjustment_action || riskGate.adjustment_action || "-";
  const actionLabel = action && action !== "-" ? statusLabel(action) : adjustment.adjustment_required ? "建议调整" : "可维持计划";
  const productStatus = payload?.generation_status || riskGate.product_status || adjustment.product_status || "-";
  const saveStatus = payload?.feedback_id ? "反馈已保存" : "仅计算未保存";
  if (isMedicalReferral) {
    const referralState = payload?.generation_status || riskGate.product_status || adjustment.product_status || "medical_referral";
    const medicalCopy = {
      rationale: "检测到胸痛、头晕、疑似热病等医疗红旗时，训练连续性必须让位于安全评估。",
      nextDay: "停止训练，优先休息并进行专业医疗评估；评估前不要安排下一次跑步训练。",
      week: "本周暂停强度训练；症状解除且专业评估允许前，不恢复训练计划。",
      preAssessment: "不生成跑步替代课；专业评估通过前只保留休息，必要活动应非常轻柔。",
      alert: "胸痛、头晕/晕厥或热病迹象需要停止运动并寻求专业医疗帮助。",
    };
    return `
      <div class="feedback-result-card medical-referral-card" data-feedback-medical-referral data-feedback-product-state>
        <div class="day-card-top">
          <strong>停止训练</strong>
          <span>${escapeHtml(feedbackStatusLabel(referralState))}</span>
        </div>
        <p>${escapeHtml(medicalCopy.rationale)}</p>
        <div class="feedback-risk-gate" data-feedback-risk-gate>
          <div><span>安全判断</span><strong>${escapeHtml(statusLabel(riskGate.status || "blocked"))}</strong></div>
          <div><span>触发信号</span><strong>${escapeHtml(riskTriggers)}</strong></div>
          <div><span>是否继续</span><strong>不允许继续原计划</strong></div>
          <div><span>下一步</span><strong>停止训练并寻求专业评估</strong></div>
        </div>
        <div class="medical-referral-actions">
          <div><span>明日安排</span><strong>${escapeHtml(medicalCopy.nextDay)}</strong></div>
          <div><span>本周安排</span><strong>${escapeHtml(medicalCopy.week)}</strong></div>
          <div><span>评估前安排</span><strong>${escapeHtml(medicalCopy.preAssessment)}</strong></div>
          <div><span>禁止事项</span><strong>不生成普通调整版计划，不提供继续训练主课。</strong></div>
          <div><span>风险提醒</span><strong>${escapeHtml(medicalCopy.alert)}</strong></div>
        </div>
        <small>出于安全边界，本次不会生成普通调整版计划，也不会提供继续训练的替代主课。</small>
      </div>
    `;
  }
  const regenerateActionHtml =
    `<button type="button" class="primary-button" data-modal-feedback-action="regenerate">生成调整版计划</button>`;
  const affectedEvents = feedbackAffectedEvents(payload, affectedDays);
  const affectedHtml = affectedEvents.length
    ? affectedEvents.map((day) => {
      const effect = day.feedback_effect || {};
      const label = text(day.day_label || day.scheduled_date || day.date || day.day, "后续训练日");
      const title = displayTrainingTitle(day);
      const instruction = effect.adjusted_instruction ? ` · 调整后执行建议：${effect.adjusted_instruction}` : "";
      return `<li>${escapeHtml(label)}：${escapeHtml(title || statusLabel(effect.action || "feedback_adjusted"))}${escapeHtml(instruction)}</li>`;
    }).join("")
    : "<li>后续影响范围待生成调整版计划后确认。</li>";
  return `
    <div class="feedback-result-card">
      <div class="day-card-top" data-feedback-product-state>
        <strong>${escapeHtml(actionLabel)}</strong>
        <span>${escapeHtml(feedbackStatusLabel(productStatus))}</span>
      </div>
      <p>${escapeHtml(adjustment.rationale || "已根据反馈生成恢复判断。")}</p>
      <div class="feedback-risk-gate" data-feedback-risk-gate>
        <div>
          <span>安全判断</span>
          <strong>${escapeHtml(statusLabel(riskGate.status || riskGate.risk_level || "proceed"))}</strong>
        </div>
        <div>
          <span>触发信号</span>
          <strong>${escapeHtml(riskTriggers)}</strong>
        </div>
        <div>
          <span>是否继续</span>
          <strong>${escapeHtml(protocolRecheck.allowed === false ? "不允许继续原计划" : protocolRecheck.allowed === true ? "允许降级后继续" : "-")}</strong>
        </div>
        <div>
          <span>需要注意</span>
          <strong>${escapeHtml(protocolViolations)}</strong>
        </div>
      </div>
      <div class="feedback-result-grid">
        <div><span>建议动作</span><strong>${escapeHtml(statusLabel(action))}</strong></div>
        <div hidden data-expert-only><span>生成状态</span><strong>${escapeHtml(statusLabel(productStatus))}</strong></div>
        <div><span>明日调整</span><strong>${escapeHtml(adjustment.next_day_adjustment || "-")}</strong></div>
        <div><span>本周微调</span><strong>${escapeHtml(adjustment.weekly_adjustment || "-")}</strong></div>
        <div><span>替代训练</span><strong>${escapeHtml(adjustment.alternative_workout || "-")}</strong></div>
        <div><span>风险提醒</span><strong>${escapeHtml(adjustment.risk_alert || "-")}</strong></div>
        <div hidden data-expert-only><span>调整原因</span><strong>${escapeHtml(reasonCodes.map(statusLabel).join(" / ") || "-")}</strong></div>
        <div><span>保存状态</span><strong>${escapeHtml(saveStatus)}</strong></div>
      </div>
      <div class="plan-diff-card" hidden data-expert-only>
        <span>计划差异</span>
        <div>
          <strong>${escapeHtml(text(planDiff.status || payload?.generation_status, "-"))}</strong>
          <em>影响 ${escapeHtml(text(planDiff.affected_days, 0))} 天 · 降级 ${escapeHtml(text(planDiff.downgraded, 0))} · 取消 ${escapeHtml(text(planDiff.cancelled, 0))}</em>
        </div>
      </div>
      <div class="affected-days">
        <span>可能影响的后续训练</span>
        <ul>${affectedHtml}</ul>
      </div>
      ${buildFeedbackReplanHtml(payload?.feedback_replan || {}, payload?.feedback_id || "")}
      ${regenerateActionHtml}
      <div data-adjustment-proposals style="display:none"></div>
    </div>
  `;
}

function focusScheduleConstraintsInput(root = dayModalContent) {
  const input = getFeedbackField(root, "scheduleConstraints");
  if (!input) return;
  // 修改可训练时间时直接聚焦输入框，避免用户点了按钮却不知道下一步在哪里填。
  input.focus();
  input.scrollIntoView?.({ block: "center", behavior: "smooth" });
}

async function submitFeedbackReplanAction(action, root = dayModalContent) {
  const feedback = state.lastFeedbackResult || {};
  const feedbackId = feedback.feedback_id || "";
  const planId = buildFeedbackContext().plan_id || state.lastResponse?.training_plan_id || "";
  if (!feedbackId || !planId) return;
  const resultTarget = root?.querySelector?.("[data-feedback-result]");
  if (action === "update_availability") {
    focusScheduleConstraintsInput(root);
  }
  const payload = collectFeedbackPayload(root);
  if (resultTarget) {
    resultTarget.className = "modal-feedback-result loading-state";
    resultTarget.textContent = "正在处理你的重规划操作...";
  }
  try {
    const response = await window.__apiClient.apiFetch(`/plans/${planId}/feedback/${feedbackId}/actions`, {
      method: "POST",
      body: JSON.stringify({
        action,
        schedule_constraints: { notes: payload.scheduleConstraints },
      }),
    });
    state.lastFeedbackResult = {
      ...feedback,
      feedback_replan: response.feedback_replan,
      affected_events: response.affected_events || feedback.affected_events || [],
      plan_diff: response.plan_diff || feedback.plan_diff || {},
    };
    applyFeedbackReplanToLastResponse(response.feedback_replan);
    if (resultTarget) {
      resultTarget.className = "modal-feedback-result";
      resultTarget.innerHTML = buildFeedbackResultHtml(state.lastFeedbackResult, affectedDaysAfterFeedback());
      bindFeedbackReplanActions(resultTarget);
    }
  } catch (error) {
    if (resultTarget) {
      resultTarget.className = "modal-feedback-result error-state";
      resultTarget.innerHTML = `<div class="feedback-result-card"><strong>操作失败</strong><p>${escapeHtml(error?.message || "请稍后重试，原计划不会被覆盖。")}</p></div>`;
    }
  }
}

function bindFeedbackReplanActions(root = dayModalContent) {
  root.querySelectorAll?.("[data-feedback-replan-action]").forEach((button) => {
    button.addEventListener("click", () => submitFeedbackReplanAction(button.dataset.feedbackReplanAction || "dismiss", dayModalContent));
  });
}

async function composeFeedbackPrompt(root = dayModalContent) {
  const payload = collectFeedbackPayload(root);
  const resultTarget = root?.querySelector?.("[data-feedback-result]");
  if (resultTarget) {
    resultTarget.className = "modal-feedback-result loading-state";
    resultTarget.textContent = "正在根据当天反馈生成调整建议...";
  }
  await submitFeedbackApi(root);
}

function composeFeedbackPromptFromPayload(payload) {
  queryInput.value = [
    "请根据这次训练反馈调整后续计划：",
    `- 完成状态：${payload.completion || "已完成"}`,
    `- 主观疲劳：${payload.fatigue || "轻微"}`,
    `- 疼痛/不适：${payload.pain || "没有疼痛"}`,
    `- 睡眠恢复：${payload.sleep || "良好"}`,
    payload.medical_red_flags?.length ? `- 医疗红旗：${medicalRedFlagLabels(payload.medical_red_flags).join("、")}` : "",
    payload.notes ? `- 补充说明：${payload.notes}` : "",
    "请给出明日调整、本周微调、替代训练和风险提醒。",
  ].filter(Boolean).join("\n");
  queryInput.focus();
}

function feedbackContextIsSaveable(context = {}) {
  return Boolean(String(context.plan_id || "").trim() && String(context.event_id || "").trim());
}

function buildLocalMedicalReferralPayload({ completion, fatigue, pain, sleep, notes, medical_red_flags = [] }, rawText = "") {
  const labels = medicalRedFlagLabels(medical_red_flags);
  return {
    generation_status: "medical_referral",
    feedback_id: "",
    save_status: "not_saved",
    workout_feedback: {
      completion_status: completion,
      fatigue,
      pain,
      sleep,
      notes,
      medical_red_flags,
    },
    risk_gate: {
      status: "blocked",
      product_status: "medical_referral",
      triggers: labels.length ? labels : ["医疗红旗"],
      adjustment_action: "medical_referral",
      fail_closed: true,
    },
    protocol_recheck: {
      allowed: false,
      status: "blocked",
      violations: ["medical_red_flag"],
    },
    adaptive_adjustment: {
      product_status: "medical_referral",
      adjustment_action: "medical_referral",
      adjustment_required: true,
      rationale: labels.length
        ? `你勾选了医疗红旗：${labels.join("、")}。训练计划必须先停止，等待专业评估。`
        : "检测到医疗红旗。训练计划必须先停止，等待专业评估。",
      next_day_adjustment: "停止训练，优先休息并进行专业医疗评估。",
      weekly_adjustment: "本周暂停强度训练；专业评估允许前不恢复跑步训练。",
      alternative_workout: "不生成跑步替代课；评估前只保留休息或非常轻柔活动。",
      risk_alert: "胸痛、头晕/晕厥、热病迹象、呼吸异常或异常心悸需要停止运动并寻求专业帮助。",
      reason_codes: ["medical_red_flag"],
    },
    plan_diff: {
      status: "medical_referral",
      affected_days: 0,
      downgraded: 0,
      cancelled: 0,
    },
    raw_text: rawText,
  };
}

function renderFeedbackContextMissing(resultTarget) {
  if (!resultTarget) return;
  resultTarget.className = "modal-feedback-result empty-state";
  resultTarget.innerHTML = `
    <div class="feedback-result-card" data-feedback-context-missing>
      <div class="day-card-top">
        <strong>先保存这份日历</strong>
        <span>反馈需要绑定到具体训练日</span>
      </div>
      <p>当前训练日还没有可保存的计划编号和日历事件编号。请先保存计划，或从历史计划重新打开这一天，再提交反馈。这样后续调整、安全判断和审计记录才能恢复。</p>
    </div>
  `;
}

async function submitFeedbackApi(root = dayModalContent) {
  const { completion, fatigue, pain, sleep, notes, scheduleConstraints, medical_red_flags } = collectFeedbackPayload(root);
  const feedbackContext = buildFeedbackContext();
  const resultTarget = root?.querySelector?.("[data-feedback-result]");
  const rawText = [
    `完成状态：${completion}`,
    `主观疲劳：${fatigue}`,
    `疼痛/不适：${pain}`,
    `睡眠恢复：${sleep}`,
    medical_red_flags.length ? `医疗红旗：${medicalRedFlagLabels(medical_red_flags).join("、")}` : "",
    notes ? `补充说明：${notes}` : "",
    scheduleConstraints ? `本周安排限制：${scheduleConstraints}` : "",
  ].filter(Boolean).join("；");
  if (medical_red_flags.length && resultTarget) {
    resultTarget.className = "modal-feedback-result";
    resultTarget.innerHTML = buildFeedbackResultHtml(
      buildLocalMedicalReferralPayload({ completion, fatigue, pain, sleep, notes, medical_red_flags }, rawText),
      [],
    );
  }
  if (!feedbackContextIsSaveable(feedbackContext) && !medical_red_flags.length) {
    renderFeedbackContextMissing(resultTarget);
    return;
  }
  if (resultTarget) {
    resultTarget.className = "modal-feedback-result loading-state";
    resultTarget.textContent = medical_red_flags.length
      ? "正在保存安全反馈..."
      : "正在提交反馈并计算调整建议...";
  }
  try {
    const payload = await window.__apiClient.apiFetch("/feedback", {
      method: "POST",
      body: JSON.stringify({
        user_id: "default_user",
        plan_id: feedbackContext.plan_id,
        event_id: feedbackContext.event_id,
        day_key: feedbackContext.day_key,
        raw_text: rawText,
        feedback: {
          completion,
          fatigue,
          pain,
          sleep,
          medical_red_flags,
          completion_status: completion,
          subjective_fatigue: fatigue,
          pain_status: pain,
          sleep_quality: sleep,
          notes,
          schedule_constraints: { notes: scheduleConstraints },
        },
        schedule_constraints: { notes: scheduleConstraints },
      }),
    });
    payload.save_status = payload.feedback_id ? "saved" : "not_saved";
    state.lastFeedbackResult = payload;
    const latestFeedback = applyLatestFeedbackToLastResponse(payload, state.selectedDay, feedbackContext);
    if (state.selectedDay && !latestFeedback) {
      state.selectedDay.latest_feedback = buildLatestFeedbackSummary(payload);
    }
    if (state.lastResponse) {
      const refreshedDays = normalizeCalendarDays(state.lastResponse);
      renderStatusPanel(state.lastResponse, refreshedDays);
      renderAdjustmentHistory(state.lastResponse, refreshedDays);
    }
    const affectedDays = affectedDaysAfterFeedback();
    if (resultTarget) {
      resultTarget.className = "modal-feedback-result";
      resultTarget.innerHTML = buildFeedbackResultHtml(payload, affectedDays);
      bindFeedbackReplanActions(resultTarget);
      // C4: 渲染调整建议 (当用户标记"未完成"时后端返回 adjustment_proposals)
      if (Array.isArray(payload.adjustment_proposals) && payload.adjustment_proposals.length) {
        const adjContainer = resultTarget.querySelector("[data-adjustment-proposals]");
        if (adjContainer) {
          adjContainer.innerHTML = window.__adjustmentRenderer?.renderAdjustmentProposals(
            payload.adjustment_proposals,
          ) || "";
          adjContainer.style.display = "";
        }
      }
      resultTarget.querySelector('[data-modal-feedback-action="regenerate"]')?.addEventListener("click", async () => {
        if (isMedicalReferralFeedback(payload)) return;
        const regenerateButton = resultTarget.querySelector('[data-modal-feedback-action="regenerate"]');
        const regenerationQuery = buildRegenerationQueryFromFeedback(payload, state.selectedDay);
        try {
          regenerateButton.disabled = true;
          regenerateButton.textContent = "正在生成调整版计划";
          await runQuery(regenerationQuery);
        } catch (error) {
          if (resultTarget) {
            resultTarget.className = "modal-feedback-result";
            resultTarget.innerHTML = buildFeedbackResultHtml(payload, affectedDays);
            bindFeedbackReplanActions(resultTarget);
          }
        } finally {
          regenerateButton.disabled = false;
          regenerateButton.textContent = "生成调整版计划";
        }
      });
    }
    reportBox.className = "report-content";
    if (isMedicalReferralFeedback(payload)) {
      reportBox.innerHTML = `
        <div class="callout-card warning-card">
          <span>医疗红旗</span>
          <p>${escapeHtml(payload.adaptive_adjustment?.rationale || "本次反馈触发医疗红旗：停止训练并建议专业医疗评估。")}</p>
        </div>
        <div class="report-summary">
          <div><span>安全判断</span><strong>${escapeHtml(statusLabel(payload.risk_gate?.status || "blocked"))}</strong></div>
          <div><span>触发信号</span><strong>${escapeHtml(listText(payload.risk_gate?.triggers || payload.risk_gate?.detected_triggers, "医疗红旗"))}</strong></div>
          <div><span>是否继续</span><strong>不允许继续原计划</strong></div>
          <div><span>下一步</span><strong>停止训练并专业评估</strong></div>
        </div>
      `;
    } else {
      reportBox.innerHTML = `
        <div class="callout-card">
          <span>反馈调整</span>
          <p>${escapeHtml(payload.adaptive_adjustment?.rationale || "已生成反馈判断。")}</p>
        </div>
        <div class="report-summary">
          <div><span>安全判断</span><strong>${escapeHtml(statusLabel(payload.risk_gate?.status || payload.risk_gate?.risk_level || "proceed"))}</strong></div>
          <div><span>建议动作</span><strong>${escapeHtml(statusLabel(payload.adaptive_adjustment?.adjustment_action || payload.risk_gate?.adjustment_action))}</strong></div>
          <div><span>是否继续</span><strong>${escapeHtml(payload.protocol_recheck?.allowed === false ? "不允许继续原计划" : payload.protocol_recheck?.allowed === true ? "允许降级后继续" : "-")}</strong></div>
          <div hidden data-expert-only><span>生成状态</span><strong>${escapeHtml(statusLabel(payload.generation_status))}</strong></div>
          <div><span>是否调整</span><strong>${payload.adaptive_adjustment?.adjustment_required ? "是" : "否"}</strong></div>
          <div><span>明日调整</span><strong>${escapeHtml(payload.adaptive_adjustment?.next_day_adjustment || "-")}</strong></div>
          <div><span>本周微调</span><strong>${escapeHtml(payload.adaptive_adjustment?.weekly_adjustment || "-")}</strong></div>
          <div><span>风险提醒</span><strong>${escapeHtml(payload.adaptive_adjustment?.risk_alert || "-")}</strong></div>
          <div hidden data-expert-only><span>计划差异</span><strong>${escapeHtml(`影响 ${payload.plan_diff?.affected_days ?? 0} 天 / 降级 ${payload.plan_diff?.downgraded ?? 0} / 取消 ${payload.plan_diff?.cancelled ?? 0}`)}</strong></div>
        </div>
      `;
    }
    resultBadge.textContent = "反馈已计算";
  } catch (error) {
    if (medical_red_flags.length && resultTarget) {
      resultTarget.className = "modal-feedback-result";
      resultTarget.innerHTML = buildFeedbackResultHtml(
        buildLocalMedicalReferralPayload({ completion, fatigue, pain, sleep, notes, medical_red_flags }, rawText),
        [],
      );
      reportBox.className = "report-content";
      reportBox.innerHTML = `
        <div class="callout-card warning-card">
          <span>医疗红旗</span>
          <p>本地已触发医疗红旗：停止训练并建议专业医疗评估。反馈同步失败：${escapeHtml(error.message)}</p>
        </div>
      `;
      resultBadge.textContent = "安全阻断";
      return;
    }
    if (resultTarget) {
      resultTarget.className = "modal-feedback-result empty-state";
      resultTarget.textContent = `反馈提交失败：${error.message}`;
    }
    setEmpty(reportBox, `反馈提交失败：${error.message}`);
    resultBadge.textContent = "反馈失败";
  }
}

function normalizeEvidencePages(item) {
  const rawPages = item?.page_hint || item?.locator_hint || item?.pages || item?.page || item?.page_range || item?.page_number || "";
  if (Array.isArray(rawPages)) return rawPages.filter(Boolean).join("-");
  return String(rawPages || "").trim();
}

function canShowCitationBadge(item) {
  return Boolean(text(item?.source_url, "") && (text(item?.page, "") || text(item?.section, "")));
}

function extractModelKnowledgeAnswer(response) {
  const report = getStructuredReport(response);
  const candidates = [
    response?.report,
    report.summary,
    report.findings?.summary,
    response?.message,
  ];
  const raw = candidates.map((item) => String(item || "").trim()).find(Boolean) || "";
  const cleaned = raw
    .replace(/```[\s\S]*?```/g, "")
    .replace(/[#>*_`~-]+/g, " ")
    .replace(/\[[0-9]+\]/g, "")
    .replace(/\s+/g, " ")
    .trim();
  return cleaned.slice(0, 320) || "当前没有绑定本地证据。系统可以基于模型通用训练知识给出一般说明，但不能把这些内容当作核心处方依据。";
}

function normalizeEvidenceItem(item, index = 0) {
  const id = item?.id || item?.evidence_id || item?.citation_label || item?.source_id || item?.chunk_id || index + 1;
  const tier = item?.display_mode || item?.evidence_tier || item?.tier || item?.evidence_type || item?.source_type || "legacy_explanation";
  const source = item?.source_label || item?.source_name || item?.document || item?.source || item?.file_name || item?.source_file || "训练依据";
  const excerpt = item?.text_span || item?.user_facing_summary || item?.snippet || item?.excerpt || item?.content || item?.text || item?.summary || item?.body || "";
  const locator = item?.locator_hint || item?.section || (item?.page_hint ? `页码提示：${item.page_hint}` : "");
  return {
    id,
    title: source,
    body: excerpt,
    excerpt,
    tier,
    display_mode: tier,
    evidence_type: item?.evidence_type || sourceTypeLabel(tier),
    page: normalizeEvidencePages(item),
    page_hint: item?.page_hint || "",
    locator_hint: locator,
    source_url: item?.source_url || "",
    section: item?.section || "",
    can_show_citation: canShowCitationBadge(item),
    relation: item?.user_facing_summary || item?.relation || item?.decision_relation || item?.note || "该证据为训练安排提供参考依据。",
    status: item?.status || (tier === "needs_evidence" ? "missing" : "verified"),
  };
}

function buildModelKnowledgeEvidenceItem(response) {
  return {
    id: "model_knowledge",
    title: "模型知识说明（未绑定外部证据）",
    body: extractModelKnowledgeAnswer(response),
    excerpt: extractModelKnowledgeAnswer(response),
    tier: "llm_general_knowledge",
    evidence_type: "模型通用知识",
    page: "",
    source_path: "",
    relation: "用于一般背景说明和执行提醒；不能作为核心处方依据，不生成伪引用。",
    status: "uncited_general_answer",
  };
}

function protocolRuleEvidenceItems(structuredPlan = {}) {
  const protocol = structuredPlan?.half_marathon_protocol || {};
  const validation = structuredPlan?.half_marathon_protocol_validation || {};
  if (!protocol.active && !validation.active) return [];
  return [{
    id: "protocol_rule_hmp",
    protocol_name: "内置 HMP 协议规则",
    title: "内置 HMP 协议规则说明",
    body: "来自半马基石规则链，用于约束质量课间隔、专项课容量、长距离上限和风险降级。",
    excerpt: "来自半马基石规则链，用于约束质量课间隔、专项课容量、长距离上限和风险降级。",
    tier: "protocol_rule",
    evidence_type: "内置协议规则，非外部检索证据",
    page: "",
    source_path: "",
    relation: "该协议影响质量课间隔、容量预算和风险降级；它是内置规则说明，不是本次检索证据。",
    status: "protocol_rule",
  }];
}

function collectEvidenceItems(response) {
  const report = getStructuredReport(response);
  const items = [];
  const canonicalChain = response?.evidence_chain;
  const canonicalItems = Array.isArray(canonicalChain?.items) ? canonicalChain.items : (Array.isArray(canonicalChain) ? canonicalChain : []);
  if (canonicalItems.length) {
    return canonicalItems.slice(0, 12).map((item, index) => normalizeEvidenceItem(item, index));
  }
  const evidenceBase = report.evidence_base || response?.rag_sources || [];
  if (Array.isArray(evidenceBase)) {
    evidenceBase.slice(0, 8).forEach((item, index) => {
      items.push(normalizeEvidenceItem(item, index));
    });
  }

  const panel = response?.training_explanation_panel || report.training_explanation_panel || {};
  const weeks = Array.isArray(panel.weeks) ? panel.weeks : [];
  weeks.forEach((week) => {
    (week.items || []).forEach((item) => {
      const ids = Array.isArray(item.evidence_ids) ? item.evidence_ids : [];
      ids.forEach((id) => {
        if (items.some((existing) => String(existing.id) === String(id))) return;
        items.push({
          id,
          title: item.title || item.day || "训练解释",
          body: item.why_scheduled || item.decision_summary || "",
          excerpt: item.why_scheduled || item.decision_summary || "",
          tier: item.explanation_source || "training_explanation",
          evidence_type: sourceTypeLabel(item.explanation_source || "training_explanation"),
          page: "",
          source_path: "",
          relation: "该证据支持当前训练解释和安排理由。",
          status: "linked_from_explanation",
        });
      });
    });
  });
  const structuredPlan = getStructuredPlan(response);
  const validation = response?.half_marathon_protocol_validation || structuredPlan?.half_marathon_protocol_validation || {};
  const protocol = structuredPlan?.half_marathon_protocol || {};
  if (!items.length && (validation.active || protocol.active)) {
    items.push(...protocolRuleEvidenceItems(structuredPlan));
  }
  if (!items.length) {
    items.push(buildModelKnowledgeEvidenceItem(response));
  }
  return items;
}

function evidenceDisplayId(item) {
  if (item.status === "protocol_rule" || item.tier === "protocol_rule") return "内置规则";
  if (item.status === "uncited_general_answer" || item.tier === "llm_general_knowledge") return "未绑定证据";
  if (item.status === "rule_based" || item.tier === "plan_only" || item.tier === "training_explanation") return "计划规则";
  if (item.tier === "action_library") return "动作库";
  return `#${text(item.id, "-")}`;
}

function renderEvidencePreview(response) {
  const items = collectEvidenceItems(response);
  state.evidenceDrawerItems = items;
  evidenceCount.textContent = `${items.length} 条`;
  if (!items.length) {
    setEmpty(evidencePreview, "本次没有返回可编号证据；日卡会先展示结构化规则和内置 HMP 协议规则依据。");
    return;
  }
  evidencePreview.className = "evidence-list";
  evidencePreview.innerHTML = items
    .slice(0, 10)
    .map((item) => `
      <article class="evidence-card">
        <div class="day-card-top">
          <strong>${escapeHtml(evidenceDisplayId(item))}</strong>
          <span>${escapeHtml(sourceTypeLabel(item.tier))}</span>
        </div>
        <h3>${escapeHtml(item.title)}</h3>
        <p>${escapeHtml(text(item.body, "暂无摘要"))}</p>
        <button class="evidence-badge-button" type="button" data-evidence-open data-evidence-id="${escapeHtml(item.id)}">查看证据</button>
      </article>
    `)
    .join("") +
    '<button class="secondary-button evidence-list-open" type="button" data-evidence-open data-evidence-scope="all">查看完整证据列表</button>';
}

function buildDayEvidenceItems(day) {
  if (!day) return collectEvidenceItems(state.lastResponse || {});
  const allItems = collectEvidenceItems(state.lastResponse || {});
  const ids = [];
  const pushId = (value) => {
    if (Array.isArray(value)) value.forEach(pushId);
    else if (value && typeof value === "object") pushId(value.id || value.evidence_id || value.source_id || value.chunk_id);
    else if (value) ids.push(String(value));
  };
  pushId(day.evidence_ids);
  pushId(day.evidence_id);
  pushId(day.evidence_refs);
  if (day.field_sources && typeof day.field_sources === "object") Object.values(day.field_sources).forEach(pushId);
  const matched = Array.from(new Set(ids))
    .map((id) => allItems.find((item) => String(item.id) === String(id)))
    .filter(Boolean);
  if (matched.length) return matched;

  const source = mainSetSource(day);
  const actionMatch = day?.action_match || day?.trace?.action_match || {};
  const basis = describeDayBasis(day);
  if (hasActionLibraryMainSet(day)) {
    return [{
      id: `DAY-${day.day_index || day.date || "main"}-ACTION`,
      title: actionMatch.source || source.source_id || "动作库.pdf",
      body: actionMatch.main_set || day.main_set || "动作库提供的主课处方。",
      excerpt: actionMatch.main_set || day.main_set || "动作库提供的主课处方。",
      tier: "action_library",
      evidence_type: "动作库",
      page: actionMatch.page || source.page || "",
      source_path: actionMatch.source || source.source_id || "",
      relation: "该证据直接决定当天用户可见主课。",
      status: "verified",
    }];
  }
  if (day?.evidence_tier === "needs_evidence" || day?.card_status === "needs_evidence") {
    return [{
      ...buildModelKnowledgeEvidenceItem(state.lastResponse || {}),
      id: `DAY-${day.day_index || day.date || "main"}-LLM`,
      relation: "可用于一般训练解释；不能作为核心处方依据，不生成伪引用，主课仍保持待补证据状态。",
    }];
  }
  return [{
    id: "day_rule_basis",
    title: basis.sourceText || "结构化计划规则",
    body: basis.validationText || basis.effectText,
    excerpt: basis.validationText || basis.effectText,
    tier: day.evidence_tier || "plan_only",
    evidence_type: sourceTypeLabel(day.evidence_tier || "plan_only"),
    page: "",
    source_path: basis.sourceText || "",
    relation: basis.effectText || "该依据影响当天训练安排。",
    status: day.evidence_tier === "needs_evidence" ? "missing" : "rule_based",
  }];
}

function resolveEvidenceItemsForDrawer(context = {}) {
  const allItems = state.evidenceDrawerItems.length
    ? state.evidenceDrawerItems
    : collectEvidenceItems(state.lastResponse || {});
  if (context.day) return buildDayEvidenceItems(context.day);
  if (context.all) return allItems;
  if (context.id) {
    const match = allItems.find((item) => String(item.id) === String(context.id));
    return match ? [match] : allItems;
  }
  return allItems;
}

function renderEvidenceDrawerItem(item) {
  const pageText = item.page ? `第 ${item.page} 页` : "页码未绑定";
  const statusText = item.status === "uncited_general_answer"
    ? "未绑定外部证据"
    : item.status === "missing"
      ? "证据不足"
      : "可追踪";
  return `
    <article class="evidence-drawer-item">
      <div class="evidence-drawer-item-head">
        <strong>${escapeHtml(evidenceDisplayId(item))}</strong>
        <span>${escapeHtml(sourceTypeLabel(item.tier))}</span>
      </div>
      <h3>${escapeHtml(item.title || "证据来源")}</h3>
      <dl class="evidence-drawer-meta">
        <div><dt>定位提示</dt><dd>${escapeHtml(item.locator_hint || pageText)}</dd></div>
        <div><dt>证据类型</dt><dd>${escapeHtml(item.evidence_type || sourceTypeLabel(item.tier))}</dd></div>
        <div><dt>状态</dt><dd>${escapeHtml(statusText)}</dd></div>
      </dl>
      ${item.can_show_citation ? `<a class="evidence-citation-link" href="${escapeHtml(item.source_url)}" target="_blank" rel="noreferrer">查看原文定位</a>` : `<div class="evidence-status-card">${escapeHtml(item.locator_hint || "当前来源不生成可点击引用，仅展示状态与定位提示。")}</div>`}
      <p class="evidence-drawer-excerpt">${escapeHtml(text(item.excerpt || item.body, "暂无摘录"))}</p>
      <p class="evidence-relation-note">${escapeHtml(item.relation || "该证据为训练安排提供参考依据。")}</p>
    </article>
  `;
}

function openEvidenceDrawer(context = {}, opener = null) {
  const items = resolveEvidenceItemsForDrawer(context);
  state.lastEvidenceDrawerTrigger = opener instanceof HTMLElement ? opener : document.activeElement;
  evidenceDrawerCount.textContent = `${items.length} 条`;
  evidenceDrawerContent.className = "evidence-drawer-content";
  evidenceDrawerContent.innerHTML = items.length
    ? items.map(renderEvidenceDrawerItem).join("")
    : '<div class="empty-state">当前没有可展示的证据或模型知识说明。</div>';
  evidenceDrawer.classList.add("open");
  evidenceDrawer.hidden = false;
  evidenceDrawer.setAttribute("aria-hidden", "false");
  activateFocusTrap(evidenceDrawer, closeEvidenceDrawer);
  evidenceDrawerClose.focus();
}

function closeEvidenceDrawer() {
  evidenceDrawer.classList.remove("open");
  evidenceDrawer.setAttribute("aria-hidden", "true");
  evidenceDrawer.hidden = true;
  deactivateFocusTrap(evidenceDrawer);
  state.lastEvidenceDrawerTrigger?.focus();
  state.lastEvidenceDrawerTrigger = null;
  if (dayModal.classList.contains("open")) {
    activateFocusTrap(dayModal, closeDayModal);
  }
}

function summarizePlan(response) {
  const plan = getStructuredPlan(response);
  const meta = plan.plan_meta || {};
  const weeks = Array.isArray(plan.week_plans) ? plan.week_plans : [];
  const firstWeek = weeks[0] || {};
  const explanation =
    response?.training_explanation_panel ||
    getStructuredReport(response).training_explanation_panel ||
    plan.training_explanation_panel ||
    {};

  return {
    hasStructuredPlan: Boolean(weeks.length || meta.goal || meta.actual_weeks),
    goal: meta.goal || "训练目标待确认",
    planType: meta.plan_type || "计划类型待确认",
    weeks: meta.actual_weeks || weeks.length || "-",
    phase: firstWeek.phase || "阶段待生成",
    load: firstWeek.load_level || "负荷待生成",
    weekGoal: firstWeek.week_goal || "本周目标待生成",
    explanationSummary: explanation.summary || "",
    performanceCalibration: meta.performance_calibration || plan.performance_calibration || {},
  };
}

function normalizePhaseSummary(response) {
  const plan = getStructuredPlan(response);
  const report = getStructuredReport(response);
  const rawPhases = Array.isArray(plan.phase_summary)
    ? plan.phase_summary
    : Array.isArray(report.phase_summary)
      ? report.phase_summary
      : [];
  const weeks = Array.isArray(plan.week_plans) ? plan.week_plans : [];
  if (rawPhases.length) {
    return rawPhases
      .map((phase, index) => {
        const startWeek = numberValue(phase.start_week, index + 1);
        const endWeek = numberValue(phase.end_week, startWeek);
        return {
          name: text(phase.phase || phase.name, `阶段 ${index + 1}`),
          startWeek,
          endWeek,
          weekCount: numberValue(phase.week_count, Math.max(1, endWeek - startWeek + 1)),
          objective: text(phase.objective || phase.goal || phase.description, ""),
        };
      })
      .filter((phase) => phase.startWeek > 0 && phase.endWeek >= phase.startWeek);
  }
  const grouped = new Map();
  weeks.forEach((week, index) => {
    const phaseName = text(week.phase, "训练期");
    const weekIndex = numberValue(week.week_index, index + 1);
    if (!grouped.has(phaseName)) {
      grouped.set(phaseName, {
        name: phaseName,
        startWeek: weekIndex,
        endWeek: weekIndex,
        weekCount: 0,
        objective: text(week.week_goal, ""),
      });
    }
    const item = grouped.get(phaseName);
    item.endWeek = Math.max(item.endWeek, weekIndex);
    item.weekCount += 1;
    if (!item.objective && week.week_goal) item.objective = week.week_goal;
  });
  return Array.from(grouped.values());
}

function renderPhaseOverviewBar(response, summary) {
  const phases = normalizePhaseSummary(response);
  if (!phases.length) return "";
  const plan = getStructuredPlan(response);
  const meta = plan.plan_meta || {};
  const totalWeeks = numberValue(meta.actual_weeks || meta.requested_weeks, numberValue(summary.weeks, phases.at(-1)?.endWeek || 1));
  const currentWeek = 1;
  const currentPhase = phases.find((phase) => currentWeek >= phase.startWeek && currentWeek <= phase.endWeek) || phases[0];
  const progress = Math.max(0, Math.min(100, totalWeeks ? (currentWeek / totalWeeks) * 100 : 0));
  return `
    <section class="phase-overview-bar" data-phase-overview-bar data-interaction-mode="vertical_scroll" aria-label="阶段总览">
      <div class="phase-overview-head">
        <div>
          <p class="section-kicker">阶段进度</p>
          <h3>阶段总览</h3>
        </div>
        <div class="phase-overview-meta">
          <span>${escapeHtml(totalWeeks)} 周</span>
          <span>当前：${escapeHtml(runnerFacingText(currentPhase.name, "训练阶段"))}</span>
        </div>
      </div>
      <div class="phase-progress-track" aria-hidden="true">
        <i style="width: ${progress}%"></i>
      </div>
      <div class="phase-step-list">
        ${phases.map((phase) => {
          const isCurrent = currentWeek >= phase.startWeek && currentWeek <= phase.endWeek;
          return `
            <button class="phase-step ${isCurrent ? "current" : ""}" type="button" data-phase-start-week="${phase.startWeek}" title="跳转到第 ${phase.startWeek} 周">
              <strong>${escapeHtml(runnerFacingText(phase.name, "训练阶段"))}</strong>
              <span>W${escapeHtml(phase.startWeek)}-W${escapeHtml(phase.endWeek)} · ${escapeHtml(phase.weekCount)} 周</span>
              ${phase.objective ? `<small>${escapeHtml(runnerFacingText(phase.objective, "本阶段以稳定完成训练并观察恢复为主。"))}</small>` : ""}
            </button>
          `;
        }).join("")}
      </div>
    </section>
  `;
}

function formatPercentText(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "-";
  return `${Math.round(numeric * 10) / 10}%`;
}

function calibrationStatusLabel(status) {
  const map = {
    ready: "已校准",
    ambitious_target: "目标有挑战",
    current_faster_than_target: "当前快于目标",
    insufficient: "信息不足",
  };
  return map[status] || text(status, "待校准");
}

function formatCalibrationField(value, fallback = "待校准") {
  return text(value, fallback);
}

function renderPerformanceCalibration(calibration) {
  if (!calibration || typeof calibration !== "object" || !Object.keys(calibration).length) {
    return "";
  }
  const sourceFieldItems = Array.isArray(calibration.source_fields)
    ? calibration.source_fields.map((item) => String(item || ""))
    : [];
  const hasCurrentSource =
    Boolean(state.lastPlanIntent?.currentHalfTime) ||
    sourceFieldItems.some((item) => /current_half_time|half_pb|current.*pb/i.test(item));
  const hasTargetSource =
    Boolean(state.lastPlanIntent?.targetPace) ||
    sourceFieldItems.some((item) => /target_(half_)?(time|pace)|target_half_time|target_hmp_pace/i.test(item));
  if (!hasCurrentSource && !hasTargetSource) {
    return `<div class="callout-card performance-card warning-card">
      <span>能力差距</span>
      <p>未提供当前成绩或目标成绩来源，暂不展示推断 PB、目标成绩或配速差距。补充半马 PB 或目标成绩后再做能力校准。</p>
    </div>`;
  }
  const hasCalibrationPair = hasCurrentSource && hasTargetSource;
  const gapSeconds = hasCalibrationPair ? calibration.gap_seconds_per_km : null;
  const timeGapMinutes = hasCalibrationPair ? Number(calibration.time_gap_seconds) / 60 : NaN;
  const gapFallback = hasCurrentSource ? "待补充目标成绩" : "待补充当前成绩";
  const gapText = Number.isFinite(Number(gapSeconds))
    ? `${Math.round(Number(gapSeconds))} 秒/公里`
    : gapFallback;
  const timeGapText = Number.isFinite(timeGapMinutes)
    ? `${Math.round(timeGapMinutes * 10) / 10} 分钟`
    : "-";
  const calibrationFallback = "待校准";
  const currentHalfTime = hasCurrentSource ? formatCalibrationField(calibration.current_half_time, calibrationFallback) : "未提供";
  const currentHmpPace = hasCurrentSource ? formatCalibrationField(calibration.current_hmp_pace, calibrationFallback) : "未校准";
  const targetHalfTime = hasTargetSource ? formatCalibrationField(calibration.target_half_time, calibrationFallback) : "未提供";
  const targetHmpPace = hasTargetSource ? formatCalibrationField(calibration.target_hmp_pace, calibrationFallback) : "未校准";
  return `<div class="callout-card performance-card">
    <span>能力差距</span>
    <div class="performance-grid">
      <div class="performance-item">
        <small>当前半马 PB</small>
        <strong>${escapeHtml(currentHalfTime)}</strong>
        <em>${escapeHtml(currentHmpPace)}</em>
      </div>
      <div class="performance-item">
        <small>目标半马</small>
        <strong>${escapeHtml(targetHalfTime)}</strong>
        <em>${escapeHtml(targetHmpPace)}</em>
      </div>
      <div class="performance-item">
        <small>能力差距</small>
        <strong>${escapeHtml(gapText)}</strong>
        <em>总差距 ${escapeHtml(timeGapText)}</em>
      </div>
      <div class="performance-item">
        <small>校准状态</small>
        <strong>${escapeHtml(calibrationStatusLabel(calibration.status))}</strong>
        <em>提升幅度 ${escapeHtml(hasCalibrationPair ? formatPercentText(calibration.improvement_percent) : "-")}</em>
      </div>
    </div>
    <p>${escapeHtml(text(calibration.decision_reason, "半马专项配速校准会随当前成绩、目标成绩和恢复状态更新。"))}</p>
  </div>`;
}

function renderRacePrepOverview(response, summary) {
  const plan = getStructuredPlan(response);
  const weeks = Array.isArray(plan.week_plans) ? plan.week_plans : [];
  const days = normalizeCalendarDays(response);
  const calendar = getCalendar(response);
  const evidenceSummary = calendar.evidence_summary || {};
  const generated = days.filter((day) => day.card_status === "generated").length;
  const recheck = days.filter((day) => requiresProtocolRecheck(day)).length;
  const needsEvidence = days.filter((day) => day.card_status === "needs_evidence" || day.evidence_tier === "needs_evidence").length;
  const actionLibraryCount = days.filter((day) => hasActionLibraryMainSet(day)).length;
  const firstKeySessions = days
    .filter((day) => !isRestDay(day) && hasActionLibraryMainSet(day))
    .slice(0, 4);
  const recheckDays = days.filter((day) => requiresProtocolRecheck(day)).slice(0, 3);
  const keySessionHtml = firstKeySessions.length
    ? firstKeySessions.map((day) => `
        <li>
          <strong>${escapeHtml(text(day.day_label || day.date, "训练日"))}</strong>
          <span>${escapeHtml(displayTrainingTitle(day))}</span>
          <em>${escapeHtml(runnerFacingText(day.main_set, "训练细节待补充"))}</em>
        </li>
      `).join("")
    : "<li><strong>安排依据待补充</strong><span>先保守查看训练安排</span><em>缺少依据时不展示高强度细节</em></li>";
  const recheckHtml = recheckDays.length
    ? recheckDays.map((day) => `
        <li>
          <strong>${escapeHtml(text(day.day_label || day.date, "待复核日"))}</strong>
          <span>${escapeHtml(protocolRecheckActionText(day))}</span>
          <em>${escapeHtml(runnerFacingText(day.main_set || day.note || day.training_objective, "先完成安全复核"))}</em>
        </li>
      `).join("")
    : "<li><strong>无待复核日</strong><span>当前卡片均可直接执行</span><em>如果仍有疑问，请优先看关键课</em></li>";
  const calibration = summary.performanceCalibration || {};
  const feasibility = calibration.status
    ? calibrationStatusLabel(calibration.status)
    : (needsEvidence || recheck ? "待补证据" : "可推进");
  const phaseText = weeks.length
    ? `${escapeHtml(runnerFacingText(weeks[0]?.phase, "起始阶段"))} → ${escapeHtml(runnerFacingText(weeks[weeks.length - 1]?.phase, "结束阶段"))}`
    : escapeHtml(runnerFacingText(summary.phase, "阶段待生成"));
  return `
    <section class="race-prep-overview" aria-label="备赛总览">
      <div class="race-prep-header">
        <span>备赛总览</span>
        <strong>${escapeHtml(runnerFacingText(summary.goal, "训练目标待确认"))}</strong>
      </div>
      <div class="race-prep-grid">
        <div><span>周期 / 阶段</span><strong>${escapeHtml(summary.weeks)} 周</strong><em>${phaseText}</em></div>
        <div><span>目标可行性</span><strong>${escapeHtml(feasibility)}</strong><em>${escapeHtml(runnerFacingText(calibration.decision_reason, "基于当前画像和训练容量判断"))}</em></div>
        <div><span>可信状态</span><strong>${generated} 已生成 / ${recheck} 待复核</strong><em>${needsEvidence} 天待补证据</em></div>
        <div hidden data-expert-only><span>证据覆盖</span><strong>${actionLibraryCount} 天安排来源</strong><em>动作库 ${evidenceSummary.action_library || 0} / 内置规则 ${evidenceSummary.protocol_rule || 0}</em></div>
        <div><span>下一步行动</span><strong>${recheck ? "先复核待复核日" : needsEvidence ? "补证据再生成" : "直接查看关键课"}</strong><em>${recheck ? "先点开待复核卡片确认协议动作" : needsEvidence ? "优先补齐动作库或知识库证据" : "关键课卡片已可直接查看"}</em></div>
      </div>
      <div class="key-session-list">
        <span>本周关键课</span>
        <ul>${keySessionHtml}</ul>
      </div>
      <div class="key-session-list">
        <span>待复核日</span>
        <ul>${recheckHtml}</ul>
      </div>
    </section>`;
}

function protocolRecheckActionText(day) {
  if (isRestDay(day)) {
    return "恢复日";
  }
  if (day?.card_status === "needs_evidence" || day?.evidence_tier === "needs_evidence") {
    return "安排依据不足：先保守查看，不展示高强度细节";
  }
  if (requiresProtocolRecheck(day)) {
    const reasons = protocolViolationLabels(day);
    return reasons ? `待复核：${reasons}` : "待复核：先降级或跳过高风险主课";
  }
  if (hasActionLibraryMainSet(day)) {
    return "已自检";
  }
  return "待复核：先补齐安排依据";
}

function protocolViolationLabels(day) {
  const protocolCheck = day?.protocol_check || day?.trace?.protocol_check || {};
  const violations = Array.isArray(protocolCheck.violations) ? protocolCheck.violations : [];
  const labels = {
    long_run_exceed_cap: "长跑超过容量上限",
    quality_sessions_exceed_cap: "质量课超过周上限",
    duration_main_set_mismatch: "主课时长与分配距离不一致",
  };
  return violations
    .map((item) => labels[item] || item)
    .filter(Boolean)
    .join(" / ");
}

function formatInlineText(text) {
  // 先转义 HTML，再还原行内 markdown 加粗（** 不是 HTML 特殊字符，escapeHtml 不会转义，
  // 因此顺序安全）。支持 **加粗**；斜体/链接等暂不处理以避免误伤医学文本。
  let s = escapeHtml(text);
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  return s;
}

function renderReportMarkdown(markdown) {
  const source = String(markdown || "").trim();
  if (!source) return "";
  const lines = source.split(/\r?\n/);
  const blocks = [];
  let unorderedItems = [];
  // 有序列表项：{ text, subItems } —— 支持有序项携带缩进的无序子项（嵌套），
  // 避免 "1. A / -a1 / 2. B" 被拆成多个 <ol> 导致编号重置为 1,1。
  let orderedEntries = [];
  let currentOrderedEntry = null;
  let paragraphLines = [];

  const flushParagraph = () => {
    if (!paragraphLines.length) return;
    blocks.push(`<p>${formatInlineText(paragraphLines.join(" "))}</p>`);
    paragraphLines = [];
  };
  const flushUnordered = () => {
    if (!unorderedItems.length) return;
    blocks.push(`<ul>${unorderedItems.map((item) => `<li>${formatInlineText(item)}</li>`).join("")}</ul>`);
    unorderedItems = [];
  };
  const flushOrdered = () => {
    if (currentOrderedEntry) { orderedEntries.push(currentOrderedEntry); currentOrderedEntry = null; }
    if (!orderedEntries.length) return;
    blocks.push(`<ol>${orderedEntries.map((entry) => {
      const sub = entry.subItems.length
        ? `<ul>${entry.subItems.map((s) => `<li>${formatInlineText(s)}</li>`).join("")}</ul>`
        : "";
      return `<li>${formatInlineText(entry.text)}${sub}</li>`;
    }).join("")}</ol>`);
    orderedEntries = [];
  };
  const flushLists = () => { flushOrdered(); flushUnordered(); };

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      flushLists();
      flushParagraph();
      continue;
    }
    const indented = /^\s+/.test(line); // 行首缩进：标记为上一项的子内容
    if (trimmed.startsWith("### ")) {
      flushLists();
      flushParagraph();
      blocks.push(`<h3>${formatInlineText(trimmed.slice(4))}</h3>`);
      continue;
    }
    if (trimmed.startsWith("## ")) {
      flushLists();
      flushParagraph();
      blocks.push(`<h2>${formatInlineText(trimmed.slice(3))}</h2>`);
      continue;
    }
    const orderedMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);
    if (orderedMatch && !indented) {
      // 新的顶级有序项：归档上一个有序项，保持同一 <ol> 内编号连续
      flushParagraph();
      flushUnordered();
      if (currentOrderedEntry) orderedEntries.push(currentOrderedEntry);
      currentOrderedEntry = { text: orderedMatch[2], subItems: [] };
      continue;
    }
    const unorderedMatch = trimmed.match(/^[-*]\s+(.*)$/);
    if (unorderedMatch) {
      flushParagraph();
      if (indented && currentOrderedEntry) {
        // 缩进无序项：作为当前有序项的嵌套子项
        currentOrderedEntry.subItems.push(unorderedMatch[1]);
      } else {
        // 顶级无序项：先关闭有序列表，避免与独立无序列表混淆
        flushOrdered();
        unorderedItems.push(unorderedMatch[1]);
      }
      continue;
    }
    flushLists();
    paragraphLines.push(trimmed);
  }

  flushLists();
  flushParagraph();
  return `<div class="report-markdown">${blocks.join("")}</div>`;
}

function renderAnswerCard(answerCard, uiPolicy = {}) {
  if (!answerCard || typeof answerCard !== "object") return "";
  const mustShow = Array.isArray(answerCard.must_show) ? answerCard.must_show : [];
  const doNotDo = Array.isArray(answerCard.do_not_do) ? answerCard.do_not_do : [];
  const nextSteps = Array.isArray(answerCard.next_steps) ? answerCard.next_steps : [];
  const mustNotTruncate = Array.isArray(uiPolicy.must_not_truncate) ? uiPolicy.must_not_truncate : [];
  const sectionHtml = mustShow.map((section) => {
    const items = Array.isArray(section.items) ? section.items : [];
    return `<section class="answer-card-section" data-type="${escapeHtml(section.type || "info")}">
      <strong>${escapeHtml(section.label || "必看信息")}</strong>
      ${section.text ? `<p>${escapeHtml(section.text)}</p>` : ""}
      ${items.length ? `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : ""}
    </section>`;
  }).join("");
  const extras = [
    doNotDo.length ? `<section class="answer-card-section warning-card" data-type="do_not_do"><strong>不要做</strong><ul>${doNotDo.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></section>` : "",
    nextSteps.length ? `<section class="answer-card-section" data-type="next_steps"><strong>下一步</strong><ul>${nextSteps.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></section>` : "",
  ].filter(Boolean).join("");
  return `<article class="answer-card" data-answer-card-version="${escapeHtml(answerCard.version || "answer_card.v2")}" data-severity="${escapeHtml(answerCard.severity || "info")}" data-intent="${escapeHtml(answerCard.intent || "qa_card")}">
    <div class="answer-card-header answer-card-hero">
      <span>${escapeHtml(answerCard.intent || "qa_card")}</span>
      <strong>${escapeHtml(answerCard.title || "回答摘要")}</strong>
      <p>${escapeHtml(answerCard.one_line || "请查看下方必看信息。")}</p>
    </div>
    <small class="answer-card-policy">必看内容不截断：${escapeHtml(mustNotTruncate.join("、") || "answer_card")}</small>
    ${sectionHtml || `<section class="answer-card-section" data-type="summary"><strong>核心结论</strong><p>${escapeHtml(answerCard.one_line || "已生成回答。")}</p></section>`}
    ${extras}
  </article>`;
}

function renderFullReportDetails(response, uiPolicy = {}) {
  const markdown = String(response?.full_report?.markdown || response?.report || "").trim();
  if (!markdown) return "";
  const defaultCollapsed = Array.isArray(uiPolicy.default_collapsed) ? uiPolicy.default_collapsed : [];
  const openAttr = defaultCollapsed.includes("full_report.markdown") || defaultCollapsed.includes("full_report") ? "" : " open";
  return `<details class="full-report-details"${openAttr}>
    <summary>展开完整分析</summary>
    <div class="callout-card secondary">${renderReportMarkdown(markdown)}</div>
  </details>`;
}

function renderMedicalDisclaimer(response) {
  // 运动医学安全合规字段：后端返回 medical_disclaimer 即渲染为醒目提示，
  // 避免医疗免责声明被丢弃（伤病/康复类回答必须可见）。
  const disclaimer = String(response?.medical_disclaimer || "").trim();
  if (!disclaimer) return "";
  return `<aside class="callout-card warning-card medical-disclaimer" role="note" aria-label="医疗免责声明">
    <span>医疗免责声明</span>
    <p>${escapeHtml(disclaimer)}</p>
  </aside>`;
}

function renderReport(response) {
  const summary = summarizePlan(response);
  const generationStatus = String(response?.generation_status || "").trim();
  const isSkeleton = Boolean(generationStatus && generationStatus !== "complete");
  const requestedWeeks = state.lastPlanIntent?.requestedWeeks || "";
  const actualWeeks = String(summary.weeks || "");
  // workflow_pause：后端要求补齐画像字段才能继续生成计划。展示缺失字段清单，
  // 而非把后端占位符 final_report="__FILL_FIELDS__" 当普通 markdown 文本渲染。
  const workflowPause = response?.workflow_pause;
  if (generationStatus === "workflow_pause" && workflowPause && typeof workflowPause === "object") {
    const missingLabels = (Array.isArray(workflowPause.field_labels) && workflowPause.field_labels.length)
      ? workflowPause.field_labels
      : (Array.isArray(workflowPause.missing_fields) ? workflowPause.missing_fields : []);
    const pendingQuery = String(workflowPause.pending_query || "").trim();
    reportBox.className = "report-content";
    reportBox.innerHTML = `<div class="callout-card warning-card workflow-pause-notice">
      <span>需要补齐信息</span>
      <p>${escapeHtml(pendingQuery ? `针对「${pendingQuery}」生成训练计划` : "为生成安全、可执行的训练计划")}</p>
      ${missingLabels.length
        ? `<p>请补充以下关键字段后重新提交，工作流将从路由节点继续：</p><ul>${missingLabels.map((l) => `<li>${escapeHtml(l)}</li>`).join("")}</ul>`
        : "<p>请在画像面板补齐关键指标后重新提交。</p>"}
    </div>${renderMedicalDisclaimer(response)}`;
    resultBadge.textContent = "等待补齐";
    return;
  }
  // security_intercepted：安全护栏拦截，工作流已终止
  if (generationStatus === "security_intercepted") {
    reportBox.className = "report-content";
    reportBox.innerHTML = `<div class="callout-card warning-card"><span>请求已拦截</span><p>${escapeHtml(response?.message || "请求已被安全护栏拦截，工作流已终止。")}</p></div>`;
    resultBadge.textContent = "已拦截";
    return;
  }
  if (!summary.hasStructuredPlan) {
    const rawReport = String(response?.report || "").trim();
    const uiPolicy = response?.ui_policy || {};
    const answerCardHtml = response?.answer_card ? renderAnswerCard(response.answer_card, uiPolicy) : "";
    const hasAnswerCard = Boolean(answerCardHtml);
    // QA/纯文本响应：有 answer_card 时主区域展示卡片，完整报告折叠在 details；
    // 无 answer_card 时主区域直接渲染 report markdown，避免 escapeHtml 纯文本降级（##、** 原样显示）
    // 以及与 renderFullReportDetails 内的重复渲染。
    const mainContent = hasAnswerCard
      ? answerCardHtml
      : (rawReport ? renderReportMarkdown(rawReport) : "");
    const fullReportDetails = hasAnswerCard ? renderFullReportDetails(response, uiPolicy) : "";
    reportBox.className = mainContent ? "report-content" : "empty-state";
    reportBox.innerHTML = mainContent
      ? `${mainContent}${fullReportDetails}${renderMedicalDisclaimer(response)}`
      : "本次没有返回训练计划内容。请检查模型配置或重新生成。";
    resultBadge.textContent = mainContent ? "回答可查看" : "无结果";
    return;
  }
  const sections = [
    response?.answer_card ? renderAnswerCard(response.answer_card, response?.ui_policy || {}) : "",
    renderPhaseOverviewBar(response, summary),
    renderRacePrepOverview(response, summary),
    `<div class="report-summary">
      <div><span>目标</span><strong>${escapeHtml(runnerFacingText(summary.goal, "训练目标待确认"))}</strong></div>
      <div><span>周期</span><strong>${escapeHtml(summary.weeks)} 周</strong></div>
      <div><span>阶段</span><strong>${escapeHtml(runnerFacingText(summary.phase, "阶段待生成"))}</strong></div>
      <div><span>训练压力</span><strong>${escapeHtml(runnerFacingText(summary.load, "待生成"))}</strong></div>
    </div>`,
    `<div class="callout-card">
      <span>本周目标</span>
      <p>${escapeHtml(runnerFacingText(summary.weekGoal, "本周以稳定完成计划、观察恢复状态和及时反馈为主。"))}</p>
    </div>`,
  ];
  const performanceCard = renderPerformanceCalibration(summary.performanceCalibration);
  if (performanceCard) {
    sections.splice(1, 0, performanceCard);
  }

  if (requestedWeeks && actualWeeks && actualWeeks !== "-" && requestedWeeks !== actualWeeks) {
    sections.splice(1, 0, `<div class="callout-card warning-card">
      <span>建议周期</span>
      <p>页面根据比赛日期倒推出 ${escapeHtml(requestedWeeks)} 周，本次按画像生成了 ${escapeHtml(actualWeeks)} 周。若差异较大，请检查比赛日期是否正确后重新生成。</p>
    </div>`);
  } else if (requestedWeeks && actualWeeks && requestedWeeks === actualWeeks) {
    sections.splice(1, 0, `<div class="callout-card secondary">
      <span>建议周期</span>
      <p>已按比赛日期倒推的 ${escapeHtml(requestedWeeks)} 周生成训练日历。</p>
    </div>`);
  }

  if (summary.explanationSummary) {
    sections.push(`<div class="callout-card secondary"><span>关键解释</span><p>${escapeHtml(summary.explanationSummary)}</p></div>`);
  }
  if (response?.answer_card) {
    sections.push(renderFullReportDetails(response, response?.ui_policy || {}));
  }
  // 医疗免责声明始终展示（后端返回即渲染，运动医学应用的安全合规字段）
  sections.push(renderMedicalDisclaimer(response));

  reportBox.className = "report-content";
  reportBox.innerHTML = sections.join("");
  resultBadge.textContent = isSkeleton ? "计划可查看" : "已生成";
}

function dayKeyCandidates(day) {
  if (!day) return [];
  const week = day.week_index || "";
  const keys = [];
  if (week && day.day_index) keys.push(`${week}-${day.day_index}`);
  if (week && day.day_label) keys.push(`${week}-${day.day_label}`);
  if (week && day.day) keys.push(`${week}-${day.day}`);
  return keys;
}

function buildDayMap(days) {
  const map = new Map();
  days.forEach((day) => {
    dayKeyCandidates(day).forEach((key) => map.set(key, day));
  });
  return map;
}

function normalizeCalendarDays(response) {
  const calendar = getCalendar(response);
  const days = Array.isArray(calendar.days) ? calendar.days : [];
  const dailyCards = getDailyCards(response);
  const weekDays = getWeekPlanDays(response);
  if (!dailyCards.length && !weekDays.length) return days;

  const cardByKey = buildDayMap(dailyCards);
  const weekByKey = buildDayMap(weekDays);
  const baseDays = dailyCards.length ? dailyCards : days.length ? days : weekDays;
  return baseDays.map((day) => {
    const matchingWeekDay = dayKeyCandidates(day).map((key) => weekByKey.get(key)).find(Boolean);
    const matchingCard = dayKeyCandidates(day).map((key) => cardByKey.get(key)).find(Boolean);
    return { ...day, ...matchingWeekDay, ...matchingCard };
  });
}

function getDaySortValue(day, index) {
  const week = numberValue(day.week_index, 0);
  const dayIndex = numberValue(day.day_index, 0);
  if (week || dayIndex) return week * 7 + dayIndex;
  return index + 1;
}

function buildTrainingLoadSeries(days) {
  const loadDays = days
    .map((day, index) => ({
      label: text(day.date_str || day.date || day.day_label || day.day || `D${index + 1}`),
      originalIndex: index,
      sort: getDaySortValue(day, index),
      load: numberValue(day.training_load, 0),
    }))
    .sort((a, b) => a.sort - b.sort);

  return loadDays.map((item, index) => {
    const acuteStart = Math.max(0, index - 6);
    const chronicStart = Math.max(0, index - 41);
    const acuteSlice = loadDays.slice(acuteStart, index + 1);
    const chronicSlice = loadDays.slice(chronicStart, index + 1);
    const acute7 = acuteSlice.reduce((sum, day) => sum + day.load, 0);
    const chronic42 = chronicSlice.length
      ? (chronicSlice.reduce((sum, day) => sum + day.load, 0) / chronicSlice.length) * 7
      : 0;
    return {
      ...item,
      acute7,
      chronic42,
    };
  });
}

function buildTrainingLoadPointMap(days) {
  const map = new Map();
  buildTrainingLoadSeries(days).forEach((item) => {
    map.set(item.originalIndex, item);
  });
  return map;
}

function renderTrainingLoadChart(days) {
  const series = buildTrainingLoadSeries(days);
  const hasLoad = series.some((item) => item.load || item.acute7 || item.chronic42);
  if (!series.length || !hasLoad) {
    return `<div class="load-chart-empty">暂无可绘制的训练负荷曲线。</div>`;
  }

  const width = 820;
  const height = 260;
  const pad = { top: 20, right: 26, bottom: 42, left: 46 };
  const plotWidth = width - pad.left - pad.right;
  const plotHeight = height - pad.top - pad.bottom;
  const maxValue = Math.max(
    10,
    ...series.flatMap((item) => [item.load, item.acute7, item.chronic42])
  );
  const x = (index) => pad.left + (series.length === 1 ? plotWidth / 2 : (index / (series.length - 1)) * plotWidth);
  const y = (value) => pad.top + plotHeight - (value / maxValue) * plotHeight;
  const barWidth = Math.max(4, Math.min(18, plotWidth / Math.max(series.length, 1) * 0.48));
  const acutePoints = series.map((item, index) => `${x(index).toFixed(1)},${y(item.acute7).toFixed(1)}`).join(" ");
  const chronicPoints = series.map((item, index) => `${x(index).toFixed(1)},${y(item.chronic42).toFixed(1)}`).join(" ");
  const labelIndexes = new Set([0, Math.floor((series.length - 1) / 2), series.length - 1]);
  const gridValues = [0, Math.round(maxValue / 2), Math.round(maxValue)];

  return `
    <div class="load-chart-card">
      <div class="load-chart-heading">
        <div>
          <span class="section-kicker">训练压力</span>
          <h3>计划代理负荷趋势</h3>
        </div>
        <div class="load-chart-legend">
          <span><i class="legend-bar"></i>每日计划代理负荷</span>
          <span><i class="legend-acute"></i>7日累计代理负荷</span>
          <span><i class="legend-chronic"></i>42日折算代理周负荷</span>
        </div>
      </div>
      <svg class="load-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="训练负荷曲线">
        ${gridValues.map((value) => `
          <g>
            <line x1="${pad.left}" y1="${y(value).toFixed(1)}" x2="${width - pad.right}" y2="${y(value).toFixed(1)}" class="load-grid-line" />
            <text x="${pad.left - 10}" y="${(y(value) + 4).toFixed(1)}" class="load-axis-label" text-anchor="end">${escapeHtml(formatLoad(value))}</text>
          </g>
        `).join("")}
        ${series.map((item, index) => {
          const barHeight = Math.max(0, pad.top + plotHeight - y(item.load));
          return `<rect class="load-bar" x="${(x(index) - barWidth / 2).toFixed(1)}" y="${y(item.load).toFixed(1)}" width="${barWidth.toFixed(1)}" height="${barHeight.toFixed(1)}">
            <title>${escapeHtml(item.label)} 计划代理负荷 ${escapeHtml(formatLoad(item.load))}</title>
          </rect>`;
        }).join("")}
        <polyline class="load-line acute-line" points="${acutePoints}" />
        <polyline class="load-line chronic-line" points="${chronicPoints}" />
        ${series.map((item, index) => labelIndexes.has(index) ? `
          <text x="${x(index).toFixed(1)}" y="${height - 16}" class="load-axis-label" text-anchor="middle">${escapeHtml(item.label)}</text>
        ` : "").join("")}
      </svg>
    </div>
  `;
}

function renderTrainingLoadSummary(response, days) {
  const summary = getTrainingLoadSummary(response);
  const totalFromDays = days.reduce((sum, day) => sum + numberValue(day.training_load, 0), 0);
  const totalLoad = numberValue(summary.total_planned_load, totalFromDays);
  const loadImpact = numberValue(summary.load_impact_7d, 0);
  const baseFitness = numberValue(summary.base_fitness_42d_weekly_equivalent, 0);
  const weeklyLoadChanges = Array.isArray(summary.weekly_load_changes) && summary.weekly_load_changes.length
    ? summary.weekly_load_changes
    : (Array.isArray(summary.weekly_loads) ? summary.weekly_loads : []);
  const trend = text(summary.intensity_trend, "-");
  const trendZone = trendZoneLabel(summary.intensity_trend_zone);
  const loadMethod = loadMethodLabel(summary.method);
  const loadDisclaimer = loadDisclaimerText(summary.disclaimer);
  const chartHtml = renderTrainingLoadChart(days);

  if (!totalLoad && !loadImpact && !baseFitness) {
    loadSummaryBox.className = "load-summary-panel empty-state";
    loadSummaryBox.innerHTML = chartHtml;
    return;
  }

  loadSummaryBox.className = "load-summary-panel";
  loadSummaryBox.innerHTML = `
    <div class="load-summary-note">
      <strong>${escapeHtml(loadMethod)}</strong>
      <span>${escapeHtml(loadDisclaimer)}</span>
    </div>
    <div class="load-summary-card accent-load">
      <span>当前趋势判断</span>
      <strong>${escapeHtml(trendZone)}</strong>
      <small>近期负荷约为长期承载参考的 ${escapeHtml(trendRatioLabel(trend))}</small>
    </div>
    <div class="load-summary-card">
      <span>计划总负荷分</span>
      <strong>${escapeHtml(formatLoad(totalLoad))}</strong>
      <small>本次课表内所有训练日合计</small>
    </div>
    <div class="load-summary-card">
      <span>7日累计代理负荷</span>
      <strong>${escapeHtml(formatLoad(loadImpact))}</strong>
      <small>近期计划压力，不是疲劳诊断</small>
    </div>
    <div class="load-summary-card">
      <span>42日折算代理周负荷</span>
      <strong>${escapeHtml(formatLoad(baseFitness))}</strong>
      <small>长期承载能力参考，不是体能评分</small>
    </div>
    <div class="load-summary-card weekly-load-card">
      <span>周代理负荷变化</span>
      <strong>${escapeHtml(weeklyLoadChanges.length ? `${weeklyLoadChanges.length} 周可量化` : "暂无分周数据")}</strong>
      <small>较上周增减与负荷递进状态都已量化记录</small>
    </div>
    <div class="weekly-load-section">
      ${renderWeeklyLoadChanges(weeklyLoadChanges)}
    </div>
    <div class="load-summary-guidance">
      <span>阅读提示</span>
      <strong>先看趋势判断，再看单日高点。</strong>
      <small>高点需要结合睡眠、疼痛和连续训练日复核，不能只凭一个分数判断风险。</small>
    </div>
    ${chartHtml}
  `;
}

function isQualityTraining(day) {
  if (isRestDay(day)) return false;
  const haystack = [
    displayTrainingTitle(day),
    day.training_type,
    day.main_set,
    day.intensity_target,
    day.note,
  ].map((item) => String(item || "")).join(" ");
  return /间歇|阈值|节奏|专项|坡|渐进|HMP|长距离|tempo|interval|quality/i.test(haystack);
}

function updateCalendarStat(name, value) {
  const el = document.querySelector(`[data-calendar-stat="${name}"]`);
  if (el) {
    el.textContent = String(value);
  }
}

function renderCalendarStats(days) {
  const restDays = days.filter(isRestDay).length;
  const qualityDays = days.filter(isQualityTraining).length;
  const weeks = new Set(days.map((day, index) => numberValue(day.week_index, Math.ceil((index + 1) / 7)))).size;
  updateCalendarStat("total-days", days.length);
  updateCalendarStat("total-weeks", days.length ? weeks : 0);
  updateCalendarStat("rest-days", restDays);
  updateCalendarStat("key-sessions", qualityDays);
  calendarCount.textContent = days.length ? `${weeks} 周计划` : "待生成";
  $("calendar-section")?.classList.toggle("has-calendar-data", days.length > 0);
}

function parseTrainingDate(day) {
  const raw = String(day?.scheduled_date || day?.date || day?.date_str || "").trim();
  if (!raw) return null;
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return null;
  parsed.setHours(0, 0, 0, 0);
  return parsed;
}

function primaryTrainingDayIndex(days) {
  if (!days.length) return -1;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const datedFuture = days
    .map((day, index) => ({ day, index, date: parseTrainingDate(day) }))
    .filter((item) => item.date && item.date.getTime() >= today.getTime())
    .sort((a, b) => a.date.getTime() - b.date.getTime());
  const futureWorkout = datedFuture.find((item) => !isRestDay(item.day));
  if (futureWorkout) return futureWorkout.index;
  if (datedFuture.length) return datedFuture[0].index;
  const firstWorkout = days.findIndex((day) => !isRestDay(day));
  return firstWorkout >= 0 ? firstWorkout : 0;
}

function weekDaysForPrimary(days, primaryDay, primaryIndex) {
  const week = primaryDay?.week_index;
  if (week) {
    const sameWeek = days.filter((day) => String(day.week_index || "") === String(week));
    if (sameWeek.length) return sameWeek;
  }
  const start = Math.max(0, primaryIndex - (primaryIndex % 7));
  return days.slice(start, start + 7);
}

function planPressureLabel(day) {
  const load = numberValue(day?.training_load, 0);
  if (!load) return "计划压力待估算";
  return `计划压力${loadStatus(load).label}`;
}

function runnerTodayMeta(day) {
  const isRest = isRestDay(day);
  const duration = formatDuration(numberValue(day?.duration_min, 0));
  const intensity = runnerFacingText(day?.intensity_target || day?.pace_range || day?.heart_rate_zone || day?.rpe || day?.zone_range || day?.zone_label || day?.zone, isRest ? "恢复" : "按计划");
  const mainSet = trustedMainSetText(day, isRest ? "恢复日，无主课安排。" : "点开日卡查看完整主课。");
  return {
    type: displayTrainingTitle(day),
    duration: duration === "-" ? (isRest ? "恢复日" : "待确认") : duration,
    intensity,
    mainSet,
    risk: productStateLabel(dayProductStatus(day)),
  };
}

function feedbackCountLabel(days) {
  const feedbackDays = days.filter((day) => {
    return hasFeedbackRecord(day);
  }).length;
  return feedbackDays ? `${feedbackDays} 天已有反馈` : "训练后记录反馈";
}

function calendarSafetySummary(days) {
  const medicalFeedback = days.find((day) => {
    const riskGate = day?.latest_feedback?.risk_gate || day?.risk_gate || {};
    return riskGate.product_status === "medical_referral" || riskGate.status === "medical_referral";
  });
  if (medicalFeedback) {
    return {
      tone: "danger",
      title: "安全阻断",
      body: "已出现需要先停下的异常信号。停止训练，优先做专业评估。",
      action: "查看红旗日",
      dayIndex: days.indexOf(medicalFeedback),
    };
  }
  const recheckIndex = days.findIndex(requiresProtocolRecheck);
  if (recheckIndex >= 0) {
    const recheckCount = days.filter(requiresProtocolRecheck).length;
    return {
      tone: "warning",
      title: "先复核再执行",
      body: `${recheckCount} 天需要复核协议或训练依据，先点开日卡确认降级动作。`,
      action: "只看待复核",
      dayIndex: recheckIndex,
      filter: "recheck",
    };
  }
  const highLoadIndex = days.findIndex((day) => numberValue(day.training_load, 0) >= 120);
  if (highLoadIndex >= 0) {
    return {
      tone: "attention",
      title: "注意恢复窗口",
      body: "本计划含高压力训练日。执行前确认睡眠、疼痛和疲劳状态。",
      action: "查看高压力日",
      dayIndex: highLoadIndex,
    };
  }
  return {
    tone: "normal",
    title: "执行前自检",
    body: "当前未发现普通层安全阻断。每次训练前仍需完成疼痛和疲劳自检。",
    action: "查看训练安排",
    dayIndex: primaryTrainingDayIndex(days),
  };
}

function renderCalendarActionPanel(response, days) {
  if (!calendarActionPanel) return;
  if (!days.length) {
    calendarActionPanel.className = "calendar-action-panel empty-state runner-today-empty";
    calendarActionPanel.innerHTML = `
      <article class="calendar-action-card runner-today-card" data-runner-today-card>
        <span>下一次训练</span>
        <strong>先生成可执行训练日历</strong>
        <p>当前还没有训练日。按顺序完善画像、生成训练日历；如果之前保存过计划，可以恢复历史计划继续执行。</p>
        <div class="runner-today-meta" aria-label="下一步">
          <div><span>1</span><strong>完善画像</strong></div>
          <div><span>2</span><strong>生成训练日历</strong></div>
          <div><span>3</span><strong>恢复历史计划</strong></div>
        </div>
        <button type="button" class="primary-button compact-button" data-focus-plan-entry>回到生成入口</button>
      </article>
    `;
    return;
  }
  const primaryIndex = primaryTrainingDayIndex(days);
  const primaryDay = days[primaryIndex] || days[0];
  const weekDays = weekDaysForPrimary(days, primaryDay, primaryIndex);
  const weekKeySessions = weekDays.filter(isQualityTraining).slice(0, 2);
  const weekGoal = text(
    primaryDay.week_goal || primaryDay.training_objective || primaryDay.decision_summary,
    "本周以稳定完成计划、观察恢复状态和及时反馈为主。",
  );
  const safety = calendarSafetySummary(days);
  const todayMeta = runnerTodayMeta(primaryDay);
  const primaryEffect = feedbackEffectForDay(primaryDay);
  const keyText = weekKeySessions.length
    ? Array.from(new Set(weekKeySessions.map(displayTrainingTitle))).join("、")
    : "本周暂无高强度关键课，优先保证连续性。";
  const safetyAction = safety.filter ? "filter-recheck" : "open-day";
  calendarActionPanel.className = `calendar-action-panel safety-${safety.tone}`;
  calendarActionPanel.innerHTML = `
    <article class="calendar-action-card primary calendar-action-next runner-today-card" data-runner-today-card>
      <span>下一次训练</span>
      <strong>${escapeHtml(trainingDayLabel(primaryDay))} · ${escapeHtml(todayMeta.type)}</strong>
      <div class="runner-today-meta" aria-label="下一次训练要点">
        <div><span>训练类型</span><strong>${escapeHtml(todayMeta.type)}</strong></div>
        <div><span>时长</span><strong>${escapeHtml(todayMeta.duration)}</strong></div>
        <div><span>强度</span><strong>${escapeHtml(todayMeta.intensity)}</strong></div>
        <div><span>风险状态</span><strong>${escapeHtml(todayMeta.risk)}</strong></div>
      </div>
      <p><strong>主课</strong>：${escapeHtml(todayMeta.mainSet)}</p>
      ${primaryEffect ? `<p class="feedback-effect-inline" data-feedback-effect><strong>已按反馈调整</strong>：${escapeHtml(primaryEffect.adjusted_instruction || feedbackEffectStatusLabel(primaryEffect))}</p>` : ""}
      <div class="runner-today-actions">
        <button type="button" class="text-action" data-calendar-action="open-day" data-calendar-action-day-index="${primaryIndex}">打开日卡</button>
        <button type="button" class="text-action" data-calendar-action="open-feedback" data-calendar-action-day-index="${primaryIndex}">记录反馈</button>
      </div>
    </article>
    <div class="calendar-action-secondary" aria-label="本周摘要">
      <section class="calendar-action-mini">
        <span>本周重点</span>
        <strong>${escapeHtml(keyText)}</strong>
        <p>${escapeHtml(runnerFacingText(weekGoal, "本周以稳定完成计划、观察恢复状态和及时反馈为主。"))}</p>
      </section>
      <section class="calendar-action-mini safety">
        <span>安全提醒</span>
        <strong>${escapeHtml(safety.title)}</strong>
        <p>${escapeHtml(safety.body)}</p>
        <button type="button" class="text-action" data-calendar-action="${safetyAction}" data-calendar-action-day-index="${safety.dayIndex}">${escapeHtml(safety.action)}</button>
      </section>
      <section class="calendar-action-mini">
        <span>反馈入口</span>
        <strong>${escapeHtml(feedbackCountLabel(days))}</strong>
        <p>训练完成后记录完成度、疲劳、疼痛和睡眠。</p>
        <button type="button" class="text-action" data-calendar-action="open-feedback" data-calendar-action-day-index="${primaryIndex}">记录反馈</button>
      </section>
    </div>
  `;
}

function normalizeRiskLevel(value) {
  const raw = String(value || "").trim();
  if (raw === "medical_referral") return "medical_referral";
  if (raw === "risk_refused" || raw === "deescalate") return "deescalate";
  if (raw === "partial_generated" || raw === "attention") return "attention";
  if (raw === "generated" || raw === "normal" || raw === "low") return "normal";
  return raw || "unknown";
}

function hasFeedbackRecord(day) {
  const feedback = day?.latest_feedback || {};
  return Boolean(feedback.id || feedback.feedback_id || feedback.summary || feedback.completion_status || feedback.risk_gate);
}

function isFeedbackDue(day) {
  if (!day || isRestDay(day) || hasFeedbackRecord(day)) return false;
  const executionStatus = String(day.execution_status || day.sync_status || day.status || "").toLowerCase();
  if (["completed", "done", "partial", "missed", "skipped"].includes(executionStatus)) return true;
  const trainingDate = parseTrainingDate(day);
  if (!trainingDate) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return trainingDate.getTime() < today.getTime();
}

function frontendStatusFromDays(days) {
  const planned = days.filter((day) => !isRestDay(day));
  const summary = {
    completion_rate: 0,
    planned_count: planned.length,
    completed_count: 0,
    partial_count: 0,
    skipped_count: 0,
    missed_feedback_count: 0,
    risk_level: "unknown",
    risk_reasons: [],
    recovery_status: "unknown",
    next_training_recommendation: "等待训练反馈后给出下次训练建议。",
    generation_status: "not_evaluated",
    risk_rule_source: "frontend_feedback_summary",
  };
  planned.forEach((day) => {
    if (!hasFeedbackRecord(day)) {
      if (!isFeedbackDue(day)) return;
      summary.missed_feedback_count += 1;
      return;
    }
    const feedback = day.latest_feedback || {};
    const status = String(feedback.completion_status || "").toLowerCase();
    if (status === "completed") summary.completed_count += 1;
    else if (status === "partial") summary.partial_count += 1;
    else if (status === "missed" || status === "skipped") summary.skipped_count += 1;
    const riskGate = feedback.risk_gate || {};
    (feedback.reason_codes || riskGate.triggers || []).forEach((code) => {
      if (code && !summary.risk_reasons.includes(code)) summary.risk_reasons.push(code);
    });
    if (riskGate.product_status === "medical_referral" && !summary.risk_reasons.includes("medical_referral")) {
      summary.risk_reasons.push("medical_referral");
    }
  });
  summary.completion_rate = planned.length
    ? Math.round(((summary.completed_count + summary.partial_count * 0.5) / planned.length) * 100)
    : 0;
  if (summary.risk_reasons.includes("medical_referral")) {
    summary.risk_level = "medical_referral";
    summary.generation_status = "medical_referral";
    summary.next_training_recommendation = "停止训练并先做专业评估。";
  } else if (summary.risk_reasons.includes("pain_risk") || summary.risk_reasons.includes("high_fatigue")) {
    summary.risk_level = "deescalate";
    summary.generation_status = "partial_generated";
    summary.next_training_recommendation = "下次训练先降级，优先恢复。";
  } else if (summary.missed_feedback_count) {
    summary.risk_level = "attention";
    summary.generation_status = "partial_generated";
    summary.next_training_recommendation = "先补录遗漏反馈，再判断是否调整。";
  } else {
    summary.risk_level = "normal";
    summary.generation_status = "generated";
    summary.next_training_recommendation = "按计划执行下一次训练。";
  }
  summary.recovery_status = summary.risk_level;
  return summary;
}

function renderStatusPanel(response, days = normalizeCalendarDays(response)) {
  if (!statusPanel) return;
  const frontendSummary = frontendStatusFromDays(days);
  const hasFeedbackOnPage = days.some((day) => {
    const feedback = day?.latest_feedback || {};
    return Boolean(feedback.id || feedback.feedback_id || feedback.summary || feedback.risk_gate);
  });
  if (!days.length && !hasFeedbackOnPage) {
    statusPanel.hidden = true;
    return;
  }
  statusPanel.hidden = false;
  const summary = (hasFeedbackOnPage || frontendSummary.risk_level === "medical_referral")
    ? { ...(response?.execution_status_summary || {}), ...frontendSummary }
    : (response?.execution_status_summary || frontendSummary);
  const riskLevel = normalizeRiskLevel(summary.risk_level || summary.generation_status);
  statusPanel.className = `status-panel status-panel-${riskLevel}`;
  statusPanel.dataset.statusRiskLevel = riskLevel;
  const missed = numberValue(summary.missed_feedback_count, 0);
  const riskReasons = Array.isArray(summary.risk_reasons)
    ? summary.risk_reasons.map(statusLabel).join(" / ")
    : statusLabel(summary.risk_reasons);
  const missedHtml = missed
    ? `<button type="button" class="secondary-button compact-button" data-missed-feedback-reminder>补录 ${missed} 天反馈</button>`
    : `<span class="muted" data-missed-feedback-reminder>暂无漏反馈提醒</span>`;
  statusPanel.innerHTML = `
    <div class="status-panel-head">
      <div>
        <p class="section-kicker">训练状态</p>
        <h3>本周执行概览</h3>
      </div>
      <span>${escapeHtml(statusLabel(riskLevel))}</span>
    </div>
    <div class="status-panel-grid">
      <div><span>本周完成度</span><strong>${escapeHtml(text(summary.completion_rate, 0))}%</strong></div>
      <div><span>反馈记录</span><strong>${escapeHtml(text(summary.completed_count, 0))} 完成 / ${escapeHtml(text(summary.partial_count, 0))} 部分 / ${escapeHtml(text(summary.skipped_count, 0))} 跳过</strong></div>
      <div><span>风险提醒</span><strong>${escapeHtml(statusLabel(riskLevel))}${riskReasons && riskReasons !== "-" ? ` · ${escapeHtml(riskReasons)}` : ""}</strong></div>
      <div><span>下次训练建议</span><strong>${escapeHtml(runnerFacingText(summary.next_training_recommendation, "训练后记录反馈，再判断是否调整。"))}</strong></div>
    </div>
    <div class="status-panel-foot">${missedHtml}</div>
  `;
}

function adjustmentHistoryFromDays(days) {
  return days
    .filter((day) => day.latest_feedback)
    .map((day) => ({
      feedback_id: day.latest_feedback.feedback_id || day.latest_feedback.id || "",
      event_id: day.event_id || day.id || "",
      day_key: day.day_key || day.day_label || day.date || "",
      created_at: day.latest_feedback.created_at || "",
      reason_codes: day.latest_feedback.reason_codes || [],
      risk_gate: day.latest_feedback.risk_gate || {},
      protocol_recheck: day.latest_feedback.protocol_recheck || {},
      adaptive_adjustment: day.latest_feedback,
      affected_events: [],
    }));
}

function renderAdjustmentHistory(response, days = normalizeCalendarDays(response)) {
  if (!adjustmentHistory) return;
  const history = Array.isArray(response?.adjustment_history) && response.adjustment_history.length
    ? response.adjustment_history
    : adjustmentHistoryFromDays(days);
  adjustmentHistory.className = history.length ? "adjustment-history" : "adjustment-history empty-state";
  if (!history.length) {
    adjustmentHistory.hidden = true;
    adjustmentHistory.innerHTML = "";
    return;
  }
  adjustmentHistory.hidden = false;
  adjustmentHistory.innerHTML = `
    <div class="adjustment-history-head">
      <p class="section-kicker">反馈调整</p>
      <h3>调整历史</h3>
    </div>
    <div class="adjustment-history-list">
      ${history.slice(0, 5).map((item) => {
        const adjustment = item.adaptive_adjustment || {};
        const riskGate = item.risk_gate || {};
        const protocolRecheck = item.protocol_recheck || {};
        const affectedEvents = Array.isArray(item.affected_events) ? item.affected_events : [];
        const reasons = Array.isArray(item.reason_codes)
          ? item.reason_codes.map(statusLabel).join(" / ")
          : statusLabel(item.reason_codes);
        return `
          <article class="adjustment-history-item">
            <div>
              <strong>${escapeHtml(item.day_key || item.event_id || "训练反馈")}</strong>
              <span>${escapeHtml(item.created_at || "")}</span>
            </div>
            <p>${escapeHtml(adjustment.rationale || adjustment.next_day_adjustment || "已保存反馈调整。")}</p>
            <dl>
              <div><dt>调整原因</dt><dd>${escapeHtml(reasons || "-")}</dd></div>
              <div><dt>安全判断</dt><dd>${escapeHtml(statusLabel(riskGate.status || riskGate.product_status || "-"))}</dd></div>
              <div><dt>是否继续</dt><dd>${escapeHtml(protocolRecheck.allowed === false ? "不允许继续" : protocolRecheck.allowed === true ? "允许降级后继续" : "-")}</dd></div>
              <div><dt>影响训练</dt><dd>${escapeHtml(affectedEvents.length ? affectedEvents.map((event) => event.day_label || event.event_id).join(" / ") : "-")}</dd></div>
            </dl>
          </article>
        `;
      }).join("")}
    </div>
  `;
}

function calendarMonthLabel(day, index) {
  const dateText = String(day.date || day.date_str || "").trim();
  if (dateText) {
    const date = new Date(dateText);
    if (!Number.isNaN(date.getTime())) {
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
    }
  }
  const week = numberValue(day.week_index, Math.ceil((index + 1) / 7));
  return `第 ${Math.max(1, Math.ceil(week / 4))} 月`;
}

function groupCalendarDays(days, view) {
  const groups = new Map();
  days.forEach((day, index) => {
    const week = numberValue(day.week_index, Math.ceil((index + 1) / 7));
    const phase = text(day.phase || day.phase_label || day.block || day.load_level, "未分阶段");
    const key = view === "all"
      ? "完整计划"
      : view === "month"
        ? calendarMonthLabel(day, index)
        : view === "phase"
          ? phase
          : `第 ${week} 周`;
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        firstIndex: index,
        days: [],
      });
    }
    groups.get(key).days.push({ day, index });
  });
  return Array.from(groups.values()).sort((a, b) => a.firstIndex - b.firstIndex);
}

function calendarFilterMatches(day) {
  if (state.calendarFilter === "recheck") {
    return requiresProtocolRecheck(day);
  }
  if (state.calendarFilter === "key") {
    return hasActionLibraryMainSet(day) && !isRestDay(day);
  }
  return true;
}

function groupCalendarEntries(entries, view) {
  const groups = new Map();
  entries.forEach(({ day, index }) => {
    const week = numberValue(day.week_index, Math.ceil((index + 1) / 7));
    const phase = text(day.phase || day.phase_label || day.block || day.load_level, "未分阶段");
    const key = view === "all"
      ? "完整计划"
      : view === "month"
        ? calendarMonthLabel(day, index)
        : view === "phase"
          ? phase
          : `第 ${week} 周`;
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        firstIndex: index,
        days: [],
      });
    }
    groups.get(key).days.push({ day, index });
  });
  return Array.from(groups.values()).sort((a, b) => a.firstIndex - b.firstIndex);
}

function mainSetSource(day) {
  const trace = day?.trace || {};
  const fieldSources = day?.field_sources || trace.field_sources || {};
  return fieldSources.main_set || fieldSources.main || {};
}

function hasActionLibraryMainSet(day) {
  const source = mainSetSource(day);
  const actionMatch = day?.action_match || day?.trace?.action_match || {};
  return source.source_type === "action_library" || Boolean(actionMatch.action_id && actionMatch.main_set);
}

function requiresProtocolRecheck(day) {
  return day?.card_status === "needs_protocol_recheck" || day?.protocol_check?.allowed === false || day?.trace?.protocol_check?.allowed === false;
}

function trustedMainSetText(day, fallback = "等待详细安排") {
  if (isRestDay(day)) return "恢复日，无主课安排。";
  const actionMatch = day?.action_match || day?.trace?.action_match || {};
  if (hasActionLibraryMainSet(day)) {
    return cleanWorkoutText(day?.main_set || actionMatch.main_set || day?.intensity_target || day?.note, fallback);
  }
  return "动作库证据不足，暂不展示具体主课。";
}

// 训练类型 → 小红书封面视觉映射（配色复用 WeekTrainingCard.jsx TRAINING_BADGES 色系）
// label=封面大字 display；code=强度代号(E/M/T/I/R)；accent=封面渐变主色(CSS变量名)；icon=emoji(可换inline SVG)
const TRAINING_TYPE_VISUALS = {
  "间歇跑": { label: "摄氧量训练", code: "I · Z5", accent: "danger", icon: "⚡" },
  "节奏跑": { label: "阈值训练",   code: "T · Z4", accent: "warning", icon: "🔥" },
  "轻松跑": { label: "轻松跑",     code: "E · Z2", accent: "success", icon: "🍃" },
  "长距离": { label: "长距离",     code: "E · Z2", accent: "accent",  icon: "🛣️" },
  "恢复跑": { label: "恢复跑",     code: "E · Z1", accent: "success", icon: "💙" },
  "力量":   { label: "力量训练",   code: "",      accent: "purple",  icon: "🏋️" },
  "法特莱克":{ label: "法特莱克",   code: "M",     accent: "warning", icon: "💨" },
  "渐速跑": { label: "渐速跑",     code: "E→T",   accent: "teal",    icon: "📈" },
  "比赛模拟":{ label: "比赛模拟",   code: "M/R",   accent: "pink",    icon: "🏁" },
  "休息":   { label: "休息日",     code: "",      accent: "rest",    icon: "🌙" },
};

// 模糊匹配后端 training_type（可能含中英变体）到封面视觉；默认按轻松跑
function trainingTypeVisual(day) {
  const raw = String(day?.training_type || "").trim();
  if (/间歇|interv/i.test(raw)) return TRAINING_TYPE_VISUALS["间歇跑"];
  if (/节奏|阈值|tempo|threshold/i.test(raw)) return TRAINING_TYPE_VISUALS["节奏跑"];
  if (/长距|long/i.test(raw)) return TRAINING_TYPE_VISUALS["长距离"];
  if (/恢复|recovery/i.test(raw)) return TRAINING_TYPE_VISUALS["恢复跑"];
  if (/力量|strength/i.test(raw)) return TRAINING_TYPE_VISUALS["力量"];
  if (/法特|fartlek/i.test(raw)) return TRAINING_TYPE_VISUALS["法特莱克"];
  if (/渐速|progress/i.test(raw)) return TRAINING_TYPE_VISUALS["渐速跑"];
  if (/比赛|race/i.test(raw)) return TRAINING_TYPE_VISUALS["比赛模拟"];
  if (isRestDay(day) || /休息|rest/i.test(raw)) return TRAINING_TYPE_VISUALS["休息"];
  return TRAINING_TYPE_VISUALS["轻松跑"];
}

// 当日总公里数（热身+主课+放松），封面副信息用
function totalKm(day) {
  const sum = numberValue(day?.warmup_km, 0) + numberValue(day?.main_km, 0) + numberValue(day?.cooldown_km, 0);
  return sum > 0 ? Math.round(sum * 10) / 10 : 0;
}
// 判断当日是否今天，用于封面"今天"呼吸角标
function isToday(day) {
  const d = day?.date || day?.scheduled_date;
  if (!d) return false;
  const today = new Date(); const target = new Date(d);
  return today.toDateString() === target.toDateString();
}

function renderDayCard(day, index, loadPoint = null) {
  const isRest = isRestDay(day);
  const needsRecheck = requiresProtocolRecheck(day);
  const title = displayTrainingTitle(day);
  const label = trainingDayLabel(day, `第 ${day.day_index ?? index + 1} 天`);
  const schedule = [dayDateLabel(day), dayTimeLabel(day)].filter(Boolean).join(" · ");
  const zone = runnerFacingZoneLabel(day.zone_range || day.zone_label || day.zone, "轻松区间");
  const load = numberValue(day.training_load, 0);
  const duration = numberValue(day.duration_min, 0);
  const loadInfo = loadStatus(load);
  const loadPercent = Math.max(6, Math.min(100, load));
  const acute7 = numberValue(loadPoint?.acute7, 0);
  const chronic42 = numberValue(loadPoint?.chronic42, 0);
  const acuteRatio = acute7 > 0 ? (load / acute7) * 100 : 0;
  const chronicRatio = chronic42 > 0 ? (load / chronic42) * 100 : 0;
  const hoverTitle = `${label}：${title}，${formatDuration(duration)}，${loadInfo.label}。`;
  const productStatus = dayProductStatus(day);
  const effect = feedbackEffectForDay(day);
  const effectAction = String(effect?.action || effect?.product_status || effect?.status || "").trim();
  const needsEvidence = productStatus === "needs_evidence";
  const needsMedicalStop = ["stop_for_medical_referral", "medical_referral", "blocked_medical", "risk_refused"].includes(effectAction);
  const riskText = effect
    ? needsMedicalStop ? "先暂停" : "按调整执行"
    : needsRecheck ? "先确认"
      : needsEvidence ? "补依据"
        : isRest ? "恢复优先" : "可执行";
  const durationLabel = isRest ? "恢复日" : formatDuration(duration);
  const badgeLabel = effect ? "已调整" : needsRecheck ? "待复核" : needsEvidence ? "待补证据" : isRest ? "恢复" : isQualityTraining(day) ? "关键课" : "训练";
  const pressureText = isRest ? "低负荷" : loadInfo.label;
  const safetyText = effect ? needsMedicalStop ? "需评估" : "已调整" : needsRecheck ? "先复核" : needsEvidence ? "先查看" : isRest ? "按感觉" : "已自检";
  const loadTone = isRest ? "recovery" : (needsRecheck || needsEvidence) ? "warning" : loadInfo.className || "stable";
  const safetyTone = effect ? needsMedicalStop ? "warning" : "feedback" : (needsRecheck || needsEvidence) ? "warning" : "stable";
  // 证据等级 badge（A=教材/B=论文/C=教练实践），诚实展示每节训练课的依据强度
  const evidenceGrade = String(day.evidence_grade || "").trim().toUpperCase();
  const evidenceSource = String(day.evidence_source || "").trim();
  const evidenceBadge = evidenceGrade
    ? `<span class="day-evidence-badge grade-${evidenceGrade.toLowerCase()}" title="${escapeHtml(`证据等级 ${evidenceGrade}：${evidenceSource || "未标注"}（A=同行评审教材 / B=论文 / C=教练实践）`)}">依据${evidenceGrade}</span>`
    : "";
  // 小红书封面卡：训练类型大字 + 强度代号 + 副信息(km·配速) + 日期角标；功能信息(证据/复核/关键)降为封面微角标
  const visual = trainingTypeVisual(day);
  const code = visual.code || (isRest ? "" : zone);
  const km = totalKm(day);
  const subInfo = isRest ? durationLabel : `${durationLabel}${km ? ` · ${km}km` : ""}${day.pace_range ? ` · ${day.pace_range}` : ""}`;
  const dayOfWeek = dayDateLabel(day) || `第${day.day_index ?? index + 1}天`;
  const cornerBadges = [
    evidenceBadge,
    needsRecheck ? `<span class="cover-corner recheck" title="待复核">复核</span>` : "",
    isQualityTraining(day) ? `<span class="cover-corner key" title="关键课">关键</span>` : "",
  ].filter(Boolean).join("");
  return `
    <article class="xhs-card accent-${escapeHtml(visual.accent)} ${isRest ? "is-rest" : ""} ${isQualityTraining(day) ? "is-key" : ""} ${needsRecheck ? "needs-recheck" : ""} ${isToday(day) ? "is-today" : ""}"
             data-day-index="${index}" data-xhs-card data-accent="${escapeHtml(visual.accent)}"
             tabindex="0" role="button" aria-label="${escapeHtml(hoverTitle)}">
      <div class="xhs-cover" aria-hidden="true">
        <span class="xhs-cover-icon">${visual.icon}</span>
        <span class="xhs-cover-day">${escapeHtml(dayOfWeek)}</span>
        ${cornerBadges ? `<div class="xhs-cover-corners">${cornerBadges}</div>` : ""}
        <span class="xhs-cover-shine" aria-hidden="true"></span>
      </div>
      <div class="xhs-body">
        <h3 class="xhs-title">${escapeHtml(visual.label)}</h3>
        ${code ? `<span class="xhs-code">${escapeHtml(code)}</span>` : ""}
        <p class="xhs-sub">${escapeHtml(subInfo)}</p>
      </div>
      <span class="xhs-chev" aria-hidden="true">›</span>
    </article>
  `;
}

function weekGroupStateKey(group, view) {
  return `${view}:${group.firstIndex}:${group.key}`;
}

function isWeekGroupExpanded(group, view) {
  const stateKey = weekGroupStateKey(group, view);
  if (Object.prototype.hasOwnProperty.call(state.weekCollapseState, stateKey)) {
    return Boolean(state.weekCollapseState[stateKey]);
  }
  const days = normalizeCalendarDays(state.lastResponse || {});
  if (!days.length) {
    return group.firstIndex === 0;
  }
  const primaryIndex = primaryTrainingDayIndex(days);
  if (primaryIndex < 0) {
    return group.firstIndex === 0;
  }
  if (Array.isArray(group.days) && group.days.some((item) => item.index === primaryIndex)) {
    return true;
  }
  return group.firstIndex === 0;
}

function weekGroupPanelId(group, view) {
  return `week-card-panel-${view}-${group.firstIndex}`;
}

function normalizeWeekNavigationItems(groups, view) {
  return groups.map((group) => {
    const groupDays = group.days.map(({ day }) => day);
    const firstDay = groupDays[0] || {};
    const qualityCount = groupDays.filter(isQualityTraining).length;
    const recheckCount = groupDays.filter(requiresProtocolRecheck).length;
    return {
      key: weekGroupStateKey(group, view),
      label: group.key,
      phase: text(firstDay.phase || firstDay.phase_label || firstDay.block || firstDay.load_level, "阶段待确认"),
      qualityCount,
      recheckCount,
    };
  });
}

function renderWeekNavigator(groups, view) {
  const items = normalizeWeekNavigationItems(groups, view);
  if (!items.length || view === "all") return "";
  return `
    <nav class="week-navigator" data-week-navigator aria-label="周计划导航">
      <div class="week-navigator-head">
        <span class="section-kicker">周计划导航</span>
        <strong>周导航</strong>
      </div>
      <div class="week-nav-list">
        ${items.map((item, index) => `
          <button
            class="week-nav-button ${index === 0 ? "current" : ""}"
            type="button"
            data-week-nav-target="${escapeHtml(item.key)}"
            aria-current="${index === 0 ? "true" : "false"}"
          >
            <span>${escapeHtml(item.label)}</span>
            <small>${escapeHtml(item.phase)} · ${item.qualityCount} 关键${item.recheckCount ? ` · ${item.recheckCount} 复核` : ""}</small>
          </button>
        `).join("")}
      </div>
    </nav>
  `;
}

function syncWeekNavigatorActiveState(stateKey) {
  calendarBox.querySelectorAll("[data-week-nav-target]").forEach((button) => {
    const isCurrent = button.dataset.weekNavTarget === stateKey;
    button.classList.toggle("current", isCurrent);
    button.setAttribute("aria-current", isCurrent ? "true" : "false");
  });
}

function collectGroupSummaryValues(group, fieldNames, limit = 4) {
  const values = [];
  const seen = new Set();
  group.days.forEach(({ day }) => {
    fieldNames.forEach((fieldName) => {
      const rawValue = day?.[fieldName];
      const rawItems = Array.isArray(rawValue) ? rawValue : [rawValue];
      rawItems.forEach((item) => {
        const value = text(item, "").trim();
        if (!value || seen.has(value)) return;
        seen.add(value);
        values.push(value);
      });
    });
  });
  return values.slice(0, limit);
}

function weekExplanationCopyForView(view) {
  const copy = {
    week: {
      title: "本周安排逻辑",
      keySessionLabel: "本周关键课",
      emptyKeySession: "暂无关键课",
      defaultGoal: "本周以稳定完成计划和观察恢复状态为主。",
    },
    month: {
      title: "本月安排逻辑",
      keySessionLabel: "本组关键课",
      emptyKeySession: "本月暂无关键课",
      defaultGoal: "本月以连续性、负荷递进和恢复窗口平衡为主。",
    },
    phase: {
      title: "本阶段安排逻辑",
      keySessionLabel: "本阶段关键课",
      emptyKeySession: "本阶段暂无关键课",
      defaultGoal: "本阶段以训练目标、关键课分布和风险控制为主。",
    },
  };
  return copy[view] || copy.week;
}

function renderWeekExplanationSummary(group, view) {
  const copy = weekExplanationCopyForView(view);
  const groupDays = group.days.map(({ day }) => day);
  const explicitKeyWorkouts = collectGroupSummaryValues(group, ["key_workouts", "key_sessions"], 3);
  const keyWorkouts = explicitKeyWorkouts.length
    ? explicitKeyWorkouts
    : groupDays.filter(isQualityTraining).slice(0, 3).map((day) => displayTrainingTitle(day));
  const actions = collectGroupSummaryValues(group, ["action_suggestions", "execution_tips"], 2);
  const groupGoals = collectGroupSummaryValues(group, ["week_goal", "weekly_goal", "group_goal", "phase_goal", "training_objective", "decision_summary"], 1);
  const weekGoal = runnerFacingText(groupGoals[0] || copy.defaultGoal, copy.defaultGoal);
  const actionSummaries = actions.map((item) => runnerFacingText(item, "")).filter(Boolean);
  return `
    <section class="week-explanation-summary" aria-label="本组训练重点">
      <div>
        <span class="section-kicker">训练重点</span>
        <strong>${escapeHtml(copy.title)}</strong>
      </div>
      <p>${escapeHtml(weekGoal)}</p>
      <dl>
        <div>
          <dt>${escapeHtml(copy.keySessionLabel)}</dt>
          <dd>${escapeHtml(keyWorkouts.length ? keyWorkouts.join("、") : copy.emptyKeySession)}</dd>
        </div>
        <div>
          <dt>执行提醒</dt>
          <dd>${escapeHtml(actionSummaries.length ? actionSummaries.slice(0, 2).join("；") : "优先按日卡查看强度、证据和复核状态。")}</dd>
        </div>
      </dl>
    </section>
  `;
}

function renderLegacyWeekExplanationSummary(group) {
  const groupDays = group.days.map(({ day }) => day);
  const firstDay = groupDays[0] || {};
  const explicitKeyWorkouts = Array.isArray(firstDay.key_workouts) ? firstDay.key_workouts : [];
  const keyWorkouts = explicitKeyWorkouts.length
    ? explicitKeyWorkouts
    : groupDays.filter(isQualityTraining).slice(0, 3).map((day) => displayTrainingTitle(day));
  const actions = Array.isArray(firstDay.action_suggestions) ? firstDay.action_suggestions : [];
  const weekGoal = runnerFacingText(firstDay.week_goal || firstDay.training_objective || firstDay.decision_summary, "本周以稳定完成计划和观察恢复状态为主。");
  const actionSummaries = actions.map((item) => runnerFacingText(item, "")).filter(Boolean);
  return `
    <section class="week-explanation-summary" aria-label="本周训练重点">
      <div>
        <span class="section-kicker">训练重点</span>
        <strong>本周安排逻辑</strong>
      </div>
      <p>${escapeHtml(weekGoal)}</p>
      <dl>
        <div>
          <dt>本周关键课</dt>
          <dd>${escapeHtml(keyWorkouts.length ? keyWorkouts.join("、") : "暂无关键课")}</dd>
        </div>
        <div>
          <dt>执行提醒</dt>
          <dd>${escapeHtml(actionSummaries.length ? actionSummaries.slice(0, 2).join("；") : "优先按日卡查看强度、证据和复核状态。")}</dd>
        </div>
      </dl>
    </section>
  `;
}

function renderCalendarGroup(group, loadPointMap, view) {
  const stateKey = weekGroupStateKey(group, view);
  const panelId = weekGroupPanelId(group, view);
  const expanded = isWeekGroupExpanded(group, view);
  const groupDays = group.days.map(({ day }) => day);
  const restCount = groupDays.filter(isRestDay).length;
  const qualityCount = groupDays.filter(isQualityTraining).length;
  const recheckCount = groupDays.filter(requiresProtocolRecheck).length;
  const groupLoad = groupDays.reduce((total, day) => total + numberValue(day.training_load, 0), 0);
  const activeDayCount = groupDays.filter((day) => !isRestDay(day)).length;
  const firstDay = groupDays[0] || {};
  const phase = text(firstDay.phase || firstDay.phase_label || firstDay.block || firstDay.load_level, "阶段待确认");
  const loadLabel = groupLoad > 0 ? `本周训练压力 ${weeklyPressureLabel(groupLoad, activeDayCount)}` : "本周训练压力待估";
  const statusLabelText = recheckCount > 0 ? `${recheckCount} 天待复核` : "查看整周安排";

  return `
    <section class="calendar-group week-card ${expanded ? "is-expanded" : ""}" data-week-group="${escapeHtml(stateKey)}">
      <button
        class="week-card-toggle"
        data-week-toggle="${escapeHtml(stateKey)}"
        type="button"
        aria-expanded="${expanded ? "true" : "false"}"
        aria-controls="${escapeHtml(panelId)}"
      >
        <span class="week-card-main">
          <strong>${escapeHtml(group.key)}</strong>
          <em>${escapeHtml(phase)}</em>
        </span>
        <span class="week-card-metrics" aria-label="周摘要">
          <i>${group.days.length} 天</i>
          <i>${restCount} 休</i>
          <i>${qualityCount} 关键</i>
        </span>
        <span class="week-card-load">
          <strong>${escapeHtml(loadLabel)}</strong>
          <small>${escapeHtml(statusLabelText)}</small>
        </span>
        <span class="week-card-chevron" aria-hidden="true"></span>
      </button>
      <div id="${escapeHtml(panelId)}" class="week-card-body" ${expanded ? "" : "hidden"}>
        ${renderWeekExplanationSummary(group, view)}
        <div class="calendar-grid ${expanded ? "xhs-enter-play" : ""}">
          ${group.days.map(({ day, index }) => renderDayCard(day, index, loadPointMap.get(index))).join("")}
        </div>
      </div>
    </section>
  `;
}

function toggleWeekGroup(stateKey, { syncNavigator = true } = {}) {
  const group = Array.from(calendarBox.querySelectorAll("[data-week-group]"))
    .find((item) => item.dataset.weekGroup === stateKey);
  if (!group) return;
  const button = group.querySelector("[data-week-toggle]");
  const body = group.querySelector(".week-card-body");
  const expanded = button?.getAttribute("aria-expanded") !== "true";
  state.weekCollapseState[stateKey] = expanded;
  button?.setAttribute("aria-expanded", expanded ? "true" : "false");
  group.classList.toggle("is-expanded", expanded);
  if (body) {
    body.hidden = !expanded;
    if (expanded) {
      // 重播卡片 stagger 入场(每次展开都播, 因 toggle hidden 不重建 DOM)
      const grid = body.querySelector(".calendar-grid");
      if (grid) {
        grid.classList.remove("xhs-enter-play");
        void grid.offsetWidth;  // force reflow 重启动画
        grid.classList.add("xhs-enter-play");
      }
    }
  }
  if (syncNavigator) {
    syncWeekNavigatorActiveState(stateKey);
  }
}

function jumpToWeekGroup(stateKey) {
  const group = Array.from(calendarBox.querySelectorAll("[data-week-group]"))
    .find((item) => item.dataset.weekGroup === stateKey);
  if (!group) return;
  const button = group.querySelector("[data-week-toggle]");
  if (button?.getAttribute("aria-expanded") !== "true") {
    toggleWeekGroup(stateKey, { syncNavigator: false });
  }
  syncWeekNavigatorActiveState(stateKey);
  group.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderCalendar(response) {
  const days = normalizeCalendarDays(response);
  const hasStructuredPlan = summarizePlan(response).hasStructuredPlan;
  const monthGrid = document.getElementById("monthCalendarGrid");
  renderTrainingLoadSummary(response, days);
  renderCalendarStats(days);
  renderCalendarActionPanel(response, days);
  renderStatusPanel(response, days);
  renderAdjustmentHistory(response, days);
  if (!days.length) {
    if (monthGrid) {
      monthGrid.hidden = true;
      monthGrid.innerHTML = "";
    }
    setEmpty(calendarBox, hasStructuredPlan ? "本次返回里没有日历数据。可以尝试明确要求生成训练计划或月历。" : "智能对话不会改动训练日历；需要训练安排时请切换到“训练日历”。");
    calendarScopeHint.textContent = hasStructuredPlan ? "暂无可切换的日历视图" : "当前是智能对话结果，日历保持不变";
    updateWorkspaceSceneStatus();
    renderGlossaryTermsPanel(response);
    return;
  }

  const loadPointMap = buildTrainingLoadPointMap(days);
  const viewLabels = { week: "按周", month: "按月", phase: "按阶段", all: "全部" };
  const visibleEntries = days
    .map((day, index) => ({ day, index }))
    .filter(({ day }) => calendarFilterMatches(day));
  const groups = groupCalendarEntries(visibleEntries, state.calendarView);
  calendarScopeHint.textContent = `${viewLabels[state.calendarView] || "按周"}展示 ${groups.length} 组 / ${visibleEntries.length} 天，已展示完整计划`;
  if (!visibleEntries.length) {
    if (monthGrid) {
      monthGrid.hidden = true;
      monthGrid.innerHTML = "";
    }
    setEmpty(calendarBox, state.calendarFilter === "recheck" ? "当前没有待复核日。" : "当前筛选下没有关键课。");
    updateWorkspaceSceneStatus();
    renderGlossaryTermsPanel(response);
    return;
  }
  if (state.calendarView === "month") {
    if (monthGrid) {
      renderMonthCalendarGrid(visibleEntries.map(({ day }) => day));
    }
  } else if (monthGrid) {
    monthGrid.hidden = true;
    monthGrid.innerHTML = "";
  }
  calendarBox.className = state.calendarView === "all" ? "calendar-grid" : "calendar-groups";
  calendarBox.innerHTML = state.calendarView === "all"
    ? visibleEntries.map(({ day, index }) => renderDayCard(day, index, loadPointMap.get(index))).join("")
    : [
        renderWeekNavigator(groups, state.calendarView),
        groups.map((group) => renderCalendarGroup(group, loadPointMap, state.calendarView)).join(""),
      ].join("");
  calendarBox.querySelectorAll("[data-week-nav-target]").forEach((button) => {
    button.addEventListener("click", () => {
      jumpToWeekGroup(button.dataset.weekNavTarget || "");
    });
  });
  calendarBox.querySelectorAll("[data-week-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      toggleWeekGroup(button.dataset.weekToggle || "");
    });
  });
  calendarBox.querySelectorAll("[data-day-index]").forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.dataset.dayIndex);
      openDayModal(days[index], null, button);
    });
  });
  calendarActionPanel?.querySelectorAll("[data-calendar-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const action = button.dataset.calendarAction || "";
      const index = Number(button.dataset.calendarActionDayIndex);
      if (action === "filter-recheck") {
        state.calendarFilter = "recheck";
        calendarFilterButtons.forEach((item) => {
          const active = item.dataset.calendarFilter === "recheck";
          item.classList.toggle("active", active);
          item.setAttribute("aria-selected", active ? "true" : "false");
        });
        renderCalendar(state.lastResponse || response);
        calendarBox.scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }
      openDayModal(days[index], null, button);
      if (action === "open-feedback") {
        selectDayModalTab("feedback");
        resetDayModalScrollPosition();
      }
    });
  });
  updateWorkspaceSceneStatus();
  renderGlossaryTermsPanel(response);
}

function modalMetric(label, value) {
  return `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function buildDayModalSection(title, body, extraClass = "") {
  return `
    <section class="modal-section ${extraClass}">
      <span>${escapeHtml(title)}</span>
      <p>${escapeHtml(body)}</p>
    </section>
  `;
}

function buildWorkoutTimelineStep(title, body, extraClass = "") {
  return `
    <article class="timeline-step ${extraClass}">
      <div class="timeline-step-head">
        <span class="timeline-dot" aria-hidden="true"></span>
        <strong>${escapeHtml(title)}</strong>
      </div>
      <p>${escapeHtml(body)}</p>
    </article>
  `;
}

function buildWorkoutTimeline(warmup, mainSet, cooldown) {
  return `
    <section class="workout-timeline" aria-label="训练步骤时间轴，按顺序执行">
      ${buildWorkoutTimelineStep("1. 热身", warmup, "warmup")}
      ${buildWorkoutTimelineStep("2. 主课", mainSet, "primary-session")}
      ${buildWorkoutTimelineStep("3. 冷身", cooldown, "cooldown")}
    </section>
  `;
}

function buildLoadSourceSection(day, loadInfo) {
  const source = loadSourceParts(day);
  return `
    <section class="modal-section">
      <span>负荷口径</span>
      <ul class="load-source-list">
        <li><strong>来源</strong><em>${escapeHtml(source.method)}</em></li>
        <li><strong>计算</strong><em>${escapeHtml(source.calc)}</em></li>
        <li><strong>注意</strong><em>${escapeHtml(source.note)}</em></li>
        <li><strong>建议</strong><em>${escapeHtml(loadInfo.advice)}</em></li>
      </ul>
    </section>
  `;
}

function auditMetric(label, value) {
  return `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function resolveWorkflowTrace(day) {
  const dayTrace = day?.workflow_trace || day?.trace?.workflow_trace || {};
  if (dayTrace?.trace_version) return dayTrace;
  const responseTrace =
    state.lastResponse?.workflow_trace ||
    state.lastResponse?.structured_report?.workflow_trace ||
    state.lastResponse?.structured_training_plan?.workflow_trace ||
    {};
  if (responseTrace?.trace_version) return responseTrace;
  return {
    trace_version: "legacy_missing",
    status: "legacy_missing",
    evidence_state: {},
    protocol_state: {},
    risk_state: {},
    repair_state: {},
    feedback_state: {},
    audit_events: [],
  };
}

function buildAuditTraceHtml(day) {
  const workflowTrace = resolveWorkflowTrace(day);
  const evidenceState = workflowTrace.evidence_state || {};
  const protocolState = workflowTrace.protocol_state || {};
  const riskState = workflowTrace.risk_state || {};
  const repairState = workflowTrace.repair_state || {};
  const trace = day?.trace || {};
  const fieldSources = day?.field_sources || trace.field_sources || {};
  const mainSource = fieldSources.main_set || fieldSources.main || fieldSources.workout || {};
  const protocolCheck = day?.protocol_check || trace.protocol_check || {};
  const actionMatch = day?.action_match || trace.action_match || {};
  const kbFallback = day?.kb_fallback || trace.kb_fallback || {};
  const sourceType = mainSource.source_type || actionMatch.source_type || day?.evidence_tier || day?.explanation_source;
  const sourceId = mainSource.source_id || mainSource.source || actionMatch.source || actionMatch.source_id || "-";
  const page = mainSource.page || actionMatch.page || "";
  const protocolAllowed = protocolCheck.allowed === false ? "否" : protocolCheck.allowed === true ? "是" : "-";
  const violations = listText(protocolCheck.violations || protocolCheck.errors || protocolCheck.issues, "无");
  const alternatives = listText(actionMatch.alternatives, "-");
  const needsEvidence = listText(day?.needs_evidence || trace.needs_evidence || kbFallback.needs_evidence, "-");
  const blockedCore = listText(kbFallback.blocked_core_candidates, "-");
  const volumeBasisLabel = protocolCheck.volume_basis === "recent_four_week_mileage"
    ? "近4周跑量"
    : protocolCheck.volume_basis
      ? "计划周跑量"
      : "-";
  const effectiveVolume = protocolCheck.effective_weekly_volume_km
    ? `${protocolCheck.effective_weekly_volume_km} km`
    : "-";
  const recentVolume = protocolCheck.recent_four_week_mileage_km
    ? `${protocolCheck.recent_four_week_mileage_km} km`
    : "-";
  const traceKeys = compactJson({
    status: workflowTrace.status,
    evidence_state: {
      status: evidenceState.status,
      evidence_count: evidenceState.evidence_count,
    },
    protocol_state: {
      status: protocolState.status,
      selected_archetype: protocolState.selected_archetype,
    },
    risk_state: {
      fail_closed: Boolean(riskState.fail_closed),
      status: riskState.status,
    },
    repair_state: {
      repair_applied: Boolean(repairState.repair_applied),
      repair_attempts: repairState.repair_attempts || 0,
    },
  });
  return `
    <details class="audit-panel" data-audit-trace hidden data-expert-only>
      <summary>
        <span>审计链路</span>
        <strong>${escapeHtml(sourceTypeLabel(sourceType))}</strong>
      </summary>
      <div class="audit-grid">
        ${auditMetric("主课字段来源", `${sourceTypeLabel(sourceType)} / ${sourceId}${page ? ` / p.${page}` : ""}`)}
        ${auditMetric("字段置信度", confidenceLabel(mainSource.confidence || actionMatch.confidence))}
        ${auditMetric("协议允许", protocolAllowed)}
        ${auditMetric("质量课上限", text(protocolCheck.quality_session_cap || protocolCheck.quality_sessions_cap || protocolCheck.quality_sessions_this_week, "-"))}
        ${auditMetric("长跑上限", protocolCheck.long_run_cap_km ? `${protocolCheck.long_run_cap_km} km` : "-")}
        ${auditMetric("容量依据", volumeBasisLabel)}
        ${auditMetric("有效预算跑量", effectiveVolume)}
        ${auditMetric("近4周跑量", recentVolume)}
        ${auditMetric("协议违规", violations)}
        ${auditMetric("动作命中", text(actionMatch.action_id || actionMatch.workout_type, "-"))}
        ${auditMetric("动作备选", alternatives)}
        ${auditMetric("缺失证据", needsEvidence)}
        ${auditMetric("KB 阻断主课候选", blockedCore)}
        ${auditMetric("卡片状态", statusLabel(day?.card_status || day?.generation_status))}
        ${auditMetric("追踪版本", workflowTrace.trace_version || "legacy_missing")}
        ${auditMetric("证据状态", `${evidenceState.status || "legacy_missing"} / ${text(evidenceState.evidence_count, 0)} 条`)}
        ${auditMetric("协议状态", `${protocolState.status || "legacy_missing"} / ${protocolState.selected_archetype || "-"}`)}
        ${auditMetric("修复状态", repairState.repair_applied ? `已修复 ${text(repairState.repair_attempts, 0)} 项` : "未修复")}
        ${auditMetric("Fail-closed", riskState.fail_closed ? "是" : "否")}
        ${auditMetric("审计节点", traceKeys)}
      </div>
    </details>
  `;
}

function getHmpGlossaryTerms(response = state.lastResponse) {
  const report = getStructuredReport(response || {});
  const plan = getStructuredPlan(response || {});
  const panel =
    report.half_marathon_protocol_panel ||
    response?.half_marathon_protocol_panel ||
    plan.half_marathon_protocol_panel ||
    {};
  return Array.isArray(panel.glossary_terms) ? panel.glossary_terms : [];
}

function renderGlossaryTerms(terms = getHmpGlossaryTerms()) {
  if (!terms.length) return "";
  return `
    <section class="modal-section glossary-section">
      <span>术语解释</span>
      <div class="glossary-term-list">
        ${terms.slice(0, 6).map((item) => `
          <article>
            <strong>${escapeHtml(item.term || item.name || item.id || "HMP 术语")}</strong>
            <p>${escapeHtml(item.short_definition || item.definition || item.description || "暂无定义。")}</p>
            <em>${escapeHtml(item.training_effect || item.training_impact || item.impact || "用于统一训练解释口径。")}</em>
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

function buildTrainingReasonGrid(day, objective, adjustment) {
  const protocolCheck = day?.protocol_check || day?.trace?.protocol_check || {};
  const numericDoseSignals = [
    protocolCheck.effective_weekly_volume_km ? `有效预算跑量 ${protocolCheck.effective_weekly_volume_km} 公里` : "",
    protocolCheck.long_run_cap_km ? `长跑上限 ${protocolCheck.long_run_cap_km} 公里` : "",
    protocolCheck.quality_session_cap ? `质量课上限 ${protocolCheck.quality_session_cap} 次` : "",
    day?.distance_km ? `当日距离 ${day.distance_km} 公里` : "",
    day?.duration_min ? `预计 ${day.duration_min} 分钟` : "",
  ].filter(Boolean);
  const capacity = numericDoseSignals.length
    ? numericDoseSignals.join("；")
    : "剂量依据待补：缺少有效预算跑量、当日距离/时长或质量课上限，暂不把模板解释当作专业剂量依据。";
  const recovery = runnerFacingText(day?.recovery_window || day?.recovery_hint, "关键课后保留恢复窗口；疲劳或疼痛时优先降级。");
  const nextStep = runnerFacingText(day?.next_session_link || day?.progression_hint, "完成后结合反馈决定后续训练是否维持、降级或重排。");
  return `
    <div class="modal-explain-grid training-reason-grid">
      ${buildDayModalSection("练什么能力", objective)}
      ${buildDayModalSection("为什么是这个剂量", capacity)}
      ${buildDayModalSection("如何恢复或降级", adjustment || recovery)}
      ${buildDayModalSection("后续承接", nextStep)}
    </div>
  `;
}

function buildDayEvidenceActionHtml(day) {
  const status = dayProductStatus(day);
  const note = status === "needs_evidence"
    ? "当前没有可绑定的动作库或本地证据；可以查看模型知识说明，但不能作为核心处方依据。"
    : "打开依据详情，查看来源、页码、摘录、证据类型和依据影响。";
  return `
    <section class="modal-section evidence-action-section">
      <span>为什么这样练</span>
      <p>${escapeHtml(note)}</p>
      <button class="evidence-badge-button" type="button" data-evidence-open data-evidence-scope="day">查看依据</button>
    </section>
  `;
}

function buildTrustStatusHtml(day) {
  const actionMatch = day?.action_match || day?.trace?.action_match || {};
  const source = mainSetSource(day);
  const protocolCheck = day?.protocol_check || day?.trace?.protocol_check || {};
  const riskGate = day?.risk_gate || day?.trace?.risk_gate || {};
  const actionLabel = hasActionLibraryMainSet(day)
    ? `${actionMatch.source || source.source_id || "已验证"}${actionMatch.page || source.page ? ` / p.${actionMatch.page || source.page}` : ""}`
    : "待补充";
  const protocolLabel = protocolCheck.allowed === false
    ? "待协议复核"
    : protocolCheck.allowed === true
      ? "协议已校验"
      : "未校验";
  const riskHasGate = Boolean(riskGate.product_status || riskGate.status || riskGate.risk_level || riskGate.triggers);
  const riskLabel = riskHasGate
    ? statusLabel(riskGate.product_status || riskGate.status || riskGate.risk_level)
    : "未完成风险自检";
  return `
    <section class="trust-status-strip" aria-label="可信状态">
      <div>
        <span>可信状态</span>
        <strong>${escapeHtml(requiresProtocolRecheck(day) ? "待复核" : hasActionLibraryMainSet(day) ? "可追踪" : "待补证据")}</strong>
      </div>
      <div>
        <span>安排来源</span>
        <strong>${escapeHtml(actionLabel)}</strong>
      </div>
      <div>
        <span>安全检查</span>
        <strong>${escapeHtml(protocolLabel)}</strong>
      </div>
      <div>
        <span>风险状态</span>
        <strong>${escapeHtml(riskLabel)}</strong>
      </div>
    </section>
  `;
}

function buildDayModalHtml(day) {
  const isRest = isRestDay(day);
  const needsRecheck = requiresProtocolRecheck(day);
  const title = displayTrainingTitle(day);
  const dayLabel = trainingDayLabel(day, "训练日");
  const schedule = formatScheduleTime(day);
  const week = numberValue(day.week_index, 0);
  const phase = runnerFacingText(day.phase || day.phase_label || day.block || day.load_level, "阶段待确认");
  const warmup = runnerFacingText(day.warmup || day.warmup_text, isRest ? "无需热身，保持轻松活动即可。" : "按计划轻松热身。");
  const mainSet = trustedMainSetText(day, isRest ? "休息恢复，避免额外加练。" : "等待主课安排。");
  const cooldown = runnerFacingText(day.cooldown || day.cooldown_text, isRest ? "可做轻柔拉伸或散步。" : "慢跑或拉伸放松。");
  const venue = runnerFacingText(day.venue, isRest ? "家中或轻松环境" : "按实际路况选择");
  const notes = runnerFacingText(day.notes || day.risk_alert || day.note, isRest ? "把睡眠、补水和轻松活动作为今天的重点。" : "若出现疼痛或异常疲劳，优先降级。");
  const objective = runnerFacingText(
    day.training_objective || day.why_scheduled || day.decision_summary || day.week_goal,
    isRest ? "通过恢复吸收前序训练刺激，为下一次训练保留状态。" : "服务于本周期的能力建设，保持强度与恢复的平衡。",
  );
  const adjustment = runnerFacingText(
    feedbackEffectForDay(day)?.adjusted_instruction || day.alternative_workout || day.adjustment_hint || day.risk_adjustment || day.risk_alert,
    isRest ? "如果状态很好，也不要补高强度；最多增加轻松散步。" : "疲劳明显时降为轻松跑或缩短主课；疼痛时停止跑步并改为恢复活动。",
  );
  const basis = describeDayBasis(day);
  const recheckAction = protocolRecheckActionText(day);
  const load = numberValue(day.training_load, 0);
  const loadInfo = loadStatus(load);
  const duration = numberValue(day.duration_min, 0);
  const distance = numberValue(day.distance_km || day.km || day.planned_km, 0);
  const zone = runnerFacingText(day.zone_range || day.zone_label || day.zone || day.intensity_zone, isRest ? "恢复" : "按计划");
  const intensity = runnerFacingText(day.intensity_target || day.pace_range || day.heart_rate_zone || day.rpe, zone);
  return `
    <header class="modal-day-hero ${isRest ? "rest" : ""} ${needsRecheck ? "needs-recheck" : ""}">
      <div>
        <p class="section-kicker">当天训练</p>
        <h2 id="dayModalTitle">${escapeHtml(dayLabel)} · ${escapeHtml(title)}</h2>
        <span>${escapeHtml(week ? `第 ${week} 周` : "当前计划")} / ${escapeHtml(phase)}</span>
        ${schedule ? `<small class="modal-schedule-line">训练时间 ${escapeHtml(schedule)}</small>` : ""}
      </div>
      <strong>${escapeHtml(isRest ? "恢复日" : needsRecheck ? "待协议复核" : "执行日")}</strong>
    </header>
    <nav class="day-modal-tab-nav" role="tablist" aria-label="训练日详情分区">
      <button id="dayModalTabPlan" type="button" class="active" role="tab" aria-selected="true" aria-controls="dayModalPanelPlan" tabindex="0" data-day-modal-tab="plan">训练安排</button>
      <button id="dayModalTabAudit" type="button" role="tab" aria-selected="false" aria-controls="dayModalPanelAudit" tabindex="-1" data-day-modal-tab="audit">训练依据</button>
      <button id="dayModalTabFeedback" type="button" role="tab" aria-selected="false" aria-controls="dayModalPanelFeedback" tabindex="-1" data-day-modal-tab="feedback">反馈调整</button>
    </nav>
    <div id="dayModalPanelPlan" class="day-modal-panel" role="tabpanel" aria-labelledby="dayModalTabPlan" data-day-modal-panel="plan">
      <div class="modal-primary-summary" aria-label="今日训练摘要">
        <div><span>时长</span><strong>${escapeHtml(formatDuration(duration))}</strong></div>
        <div><span>强度</span><strong>${escapeHtml(intensity)}</strong></div>
        <div><span>安全</span><strong>${escapeHtml(needsRecheck ? "先复核" : "可执行")}</strong></div>
      </div>
      ${buildWorkoutTimeline(warmup, mainSet, cooldown)}
      ${buildFeedbackEffectHtml(day)}
      <details class="coach-insights">
        <summary>
          <span>可选查看</span>
          <strong>训练解释与依据</strong>
        </summary>
        <div class="coach-insights-body">
          ${buildTrainingReasonGrid(day, objective, adjustment)}
        </div>
      </details>
    </div>
    <div id="dayModalPanelAudit" class="day-modal-panel" role="tabpanel" aria-labelledby="dayModalTabAudit" data-day-modal-panel="audit" hidden>
      ${buildTrustStatusHtml(day)}
      ${buildProductStateHtml(day)}
      <div class="modal-metric-grid">
        ${modalMetric("距离", distance ? `${distance.toFixed(1)} 公里` : "-")}
        ${modalMetric("训练时间", schedule || "-")}
        ${modalMetric("时长", formatDuration(duration))}
        ${modalMetric("强度", intensity)}
        ${modalMetric("计划代理负荷", `${formatLoad(load)} · ${loadInfo.label}`)}
      </div>
      <div class="modal-explain-grid">
        ${buildDayModalSection("复核动作", recheckAction, "action-guidance")}
        ${buildDayModalSection("风险与调整", adjustment)}
        ${buildDayModalSection("场地与备注", `${venue}；${notes}`)}
        ${buildDayModalSection("为什么今天这么练", objective)}
        ${buildDayModalSection("基石依据", basis.sourceText || "当前训练来自结构化计划。")}
        ${buildDayEvidenceActionHtml(day)}
        ${buildDayModalSection("依据影响", basis.effectText)}
        ${buildDayModalSection("安全校验", basis.validationText)}
        ${buildLoadSourceSection(day, loadInfo)}
        ${renderGlossaryTerms()}
      </div>
      ${buildAuditTraceHtml(day)}
    </div>
    <div id="dayModalPanelFeedback" class="day-modal-panel" role="tabpanel" aria-labelledby="dayModalTabFeedback" data-day-modal-panel="feedback" hidden>
      ${buildLatestFeedbackHtml(day)}
      ${buildFeedbackEffectHtml(day)}
      <div class="modal-actions">
        <button type="button" class="secondary-button" aria-pressed="false" data-modal-feedback="feedback_done">已完成</button>
        <button type="button" class="secondary-button" aria-pressed="false" data-modal-feedback="feedback_partial">部分完成</button>
        <button type="button" class="secondary-button" aria-pressed="false" data-modal-feedback="feedback_skipped">不适/未完成</button>
      </div>
      <p class="feedback-selected-summary" data-feedback-selected>已选择：已完成 · 疲劳轻微 · 没有疼痛 · 睡眠良好</p>
      <section class="modal-feedback-panel" data-modal-feedback-form data-feedback-quick-first>
        <div class="modal-actions compact-feedback-actions">
          <button type="button" class="primary-button" data-modal-feedback-action="submit">记录反馈并计算调整</button>
          <button type="button" class="secondary-button" data-modal-feedback-action="compose">生成调整说明</button>
        </div>
        <details class="modal-feedback-detail" data-feedback-detail>
          <summary>
            <span>补充细节</span>
            <strong>疲劳、睡眠、疼痛和安全信号</strong>
          </summary>
          <div class="modal-feedback-heading">
          <div>
            <p class="section-kicker">训练反馈</p>
            <h3>当天反馈</h3>
          </div>
          <span>直接基于这一天调整后续计划</span>
          </div>
          <div class="feedback-form modal-feedback-form">
            <label>
              <span>完成状态</span>
              <select data-feedback-field="completion">
                <option value="已完成">已完成</option>
                <option value="部分完成">部分完成</option>
                <option value="未完成">未完成</option>
              </select>
            </label>
            <label>
              <span>主观疲劳</span>
              <select data-feedback-field="fatigue">
                <option value="轻微">轻微</option>
                <option value="中等">中等</option>
                <option value="明显">明显</option>
                <option value="高疲劳">高疲劳</option>
              </select>
            </label>
            <label>
              <span>疼痛/不适</span>
              <select data-feedback-field="pain">
                <option value="没有疼痛">没有疼痛</option>
                <option value="轻微不适">轻微不适</option>
                <option value="疼痛风险">疼痛风险</option>
              </select>
            </label>
            <label>
              <span>睡眠恢复</span>
              <select data-feedback-field="sleep">
                <option value="良好">良好</option>
                <option value="一般">一般</option>
                <option value="较差">较差</option>
              </select>
            </label>
            <fieldset class="wide medical-red-flag-checklist" data-medical-red-flag-checklist>
              <legend>需要先停下的异常信号</legend>
              <p>如果出现以下任一情况，系统会优先建议停止训练并做专业评估。</p>
              <div>
                ${MEDICAL_RED_FLAGS.map((item) => `
                  <label>
                    <input type="checkbox" value="${escapeHtml(item.value)}" data-medical-red-flag />
                    <span>${escapeHtml(item.label)}</span>
                  </label>
                `).join("")}
              </div>
            </fieldset>
            <label class="wide">
              <span>本周有没有别的安排</span>
              <textarea name="scheduleConstraints" data-feedback-field="scheduleConstraints" placeholder="例如：周二周四上课跑不了，需要避开这些日子。"></textarea>
            </label>
            <label class="wide">
              <span>补充说明</span>
              <textarea data-feedback-field="notes" placeholder="例如：后半程心率偏高，第二天小腿紧张。"></textarea>
            </label>
          </div>
          <div class="modal-actions">
            <button type="button" class="secondary-button" data-modal-feedback-action="clear">清空说明</button>
          </div>
        </details>
        <div class="modal-feedback-result empty-state" data-feedback-result>提交反馈后，这里会显示明日调整、本周微调和可能影响的后续训练。</div>
      </section>
    </div>
    <footer class="day-modal-sticky-actions">
      <button type="button" class="secondary-button" data-day-modal-tab="audit">查看依据</button>
      <button type="button" class="primary-button" data-day-modal-tab="feedback">记录完成情况</button>
    </footer>
  `;
}

function closeDayModal() {
  dayModal.classList.remove("open");
  dayModal.setAttribute("aria-hidden", "true");
  dayModal.hidden = true;
  deactivateFocusTrap(dayModal);
  state.lastDayModalTrigger?.focus();
  state.lastDayModalTrigger = null;
}

function resetDayModalScrollPosition() {
  const card = dayModal.querySelector(".day-modal-card");
  if (card) {
    card.scrollTop = 0;
  }
}

function getDayDetailRoot(element = null) {
  return element?.closest?.("#calendarDetailContent, #dayModalContent") || dayModalContent;
}

function selectDayModalTab(target = "plan", { focus = false, root = dayModalContent } = {}) {
  const tabButtons = Array.from(root.querySelectorAll('[role="tab"][data-day-modal-tab]'));
  const matchedTarget = tabButtons.some((button) => button.dataset.dayModalTab === target) ? target : "plan";
  tabButtons.forEach((item) => {
    const active = item.dataset.dayModalTab === matchedTarget;
    item.classList.toggle("active", active);
    item.setAttribute("aria-selected", active ? "true" : "false");
    item.setAttribute("tabindex", active ? "0" : "-1");
    if (active && focus) item.focus();
  });
  root.querySelectorAll("[data-day-modal-panel]").forEach((panel) => {
    panel.hidden = panel.dataset.dayModalPanel !== matchedTarget;
  });
}

function handleDayModalTabKeydown(event) {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
  const root = getDayDetailRoot(event.currentTarget);
  const tabs = Array.from(root.querySelectorAll('[role="tab"][data-day-modal-tab]'));
  const currentIndex = Math.max(0, tabs.indexOf(event.currentTarget));
  const lastIndex = tabs.length - 1;
  const nextIndex = event.key === "Home"
    ? 0
    : event.key === "End"
      ? lastIndex
      : event.key === "ArrowLeft"
        ? (currentIndex - 1 + tabs.length) % tabs.length
        : (currentIndex + 1) % tabs.length;
  event.preventDefault();
  selectDayModalTab(tabs[nextIndex]?.dataset.dayModalTab || "plan", { focus: true, root });
}

function handleSegmentedControlKeydown(event, buttons) {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
  const enabled = buttons.filter((button) => !button.disabled && !button.hidden);
  const currentIndex = Math.max(0, enabled.indexOf(event.currentTarget));
  const lastIndex = enabled.length - 1;
  if (lastIndex < 0) return;
  const nextIndex = event.key === "Home"
    ? 0
    : event.key === "End"
      ? lastIndex
      : event.key === "ArrowLeft"
        ? (currentIndex - 1 + enabled.length) % enabled.length
        : (currentIndex + 1) % enabled.length;
  event.preventDefault();
  enabled[nextIndex]?.focus();
  enabled[nextIndex]?.click();
}

function applyFeedbackPreset(root, preset = {}) {
  const completion = getFeedbackField(root, "completion");
  const fatigue = getFeedbackField(root, "fatigue");
  const pain = getFeedbackField(root, "pain");
  const sleep = getFeedbackField(root, "sleep");
  const notes = getFeedbackField(root, "notes");
  if (completion && preset.completion) completion.value = preset.completion;
  if (fatigue && preset.fatigue) fatigue.value = preset.fatigue;
  if (pain && preset.pain) pain.value = preset.pain;
  if (sleep && preset.sleep) sleep.value = preset.sleep;
  if (notes && preset.notes) notes.value = preset.notes;
  root?.querySelectorAll?.("[data-medical-red-flag]").forEach((input) => {
    input.checked = false;
  });
  syncFeedbackQuickChoiceUi(root, preset);
  syncMedicalRedFlagUi(root);
}

function syncFeedbackQuickChoiceUi(root = dayModalContent, preset = collectFeedbackPayload(root)) {
  const completion = preset.completion || getFeedbackField(root, "completion")?.value || "已完成";
  const fatigue = preset.fatigue || getFeedbackField(root, "fatigue")?.value || "轻微";
  const pain = preset.pain || getFeedbackField(root, "pain")?.value || "没有疼痛";
  const sleep = preset.sleep || getFeedbackField(root, "sleep")?.value || "良好";
  const selected = root?.querySelector?.("[data-feedback-selected]");
  if (selected) {
    selected.textContent = `已选择：${completion} · 疲劳${fatigue} · ${pain} · 睡眠${sleep}`;
  }
  root?.querySelectorAll?.("[data-modal-feedback]").forEach((button) => {
    const key = button.dataset.modalFeedback || "";
    const quickPreset = FEEDBACK_QUICK_PRESETS[key] || {};
    const active = quickPreset.completion === completion && quickPreset.fatigue === fatigue && quickPreset.pain === pain;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
  });
}

function syncMedicalRedFlagUi(root = dayModalContent) {
  const flags = selectedMedicalRedFlags(root);
  const result = root?.querySelector?.("[data-feedback-result]");
  const composeButton = root?.querySelector?.('[data-modal-feedback-action="compose"]');
  if (composeButton) {
    composeButton.textContent = flags.length ? "提交安全反馈" : "生成调整建议";
  }
  if (flags.length && result) {
    result.className = "modal-feedback-result";
    result.innerHTML = buildFeedbackResultHtml(
      buildLocalMedicalReferralPayload(collectFeedbackPayload(root), `医疗红旗：${medicalRedFlagLabels(flags).join("、")}`),
      [],
    );
  } else if (result?.querySelector?.("[data-feedback-medical-referral]")) {
    result.className = "modal-feedback-result empty-state";
    result.textContent = "提交反馈后，这里会显示明日调整、本周微调和可能影响的后续训练。";
  }
}

function bindDayModalInteractions(root) {
  if (!root) return;
  root.querySelectorAll("[data-modal-feedback]").forEach((button) => {
    button.addEventListener("click", () => {
      const presetKey = button.dataset.modalFeedback || "feedback_done";
      applyFeedbackPreset(root, FEEDBACK_QUICK_PRESETS[presetKey]);
    });
  });
  root.querySelector('[data-modal-feedback-action="compose"]')?.addEventListener("click", () => composeFeedbackPrompt(root));
  root.querySelector('[data-modal-feedback-action="submit"]')?.addEventListener("click", () => submitFeedbackApi(root));
  root.querySelector('[data-modal-feedback-action="clear"]')?.addEventListener("click", () => {
    const notes = getFeedbackField(root, "notes");
    if (notes) notes.value = "";
    const result = root.querySelector("[data-feedback-result]");
    if (result) {
      result.className = "modal-feedback-result empty-state";
      result.textContent = "提交反馈后，这里会显示明日调整、本周微调和可能影响的后续训练。";
    }
  });
  root.querySelectorAll("[data-evidence-open]").forEach((button) => {
    button.addEventListener("click", () => {
      openEvidenceDrawer({ day: state.selectedDay }, button);
    });
  });
  root.querySelectorAll("[data-medical-red-flag]").forEach((input) => {
    input.addEventListener("change", () => syncMedicalRedFlagUi(root));
  });
  root.querySelectorAll("[data-feedback-field]").forEach((input) => {
    input.addEventListener("change", () => syncFeedbackQuickChoiceUi(root));
  });
  root.querySelectorAll("[data-day-modal-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      selectDayModalTab(button.dataset.dayModalTab || "plan", { focus: button.getAttribute("role") === "tab", root });
    });
  });
  root.querySelectorAll('[role="tab"][data-day-modal-tab]').forEach((button) => {
    button.addEventListener("keydown", handleDayModalTabKeydown);
  });
}

function openDayModal(day, feedbackPreset = null, opener = null) {
  if (!day) return;
  state.selectedDay = day;
  state.lastDayModalTrigger = opener instanceof HTMLElement ? opener : document.activeElement;
  // FLIP First: 记录触发卡片(opener)位置尺寸，用于封面卡→modal 共享元素过渡
  const flipEnabled = opener instanceof HTMLElement && !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const firstRect = flipEnabled ? opener.getBoundingClientRect() : null;
  dayModalContent.innerHTML = buildDayModalHtml(day);
  dayModal.classList.add("open");
  dayModal.hidden = false;
  dayModal.setAttribute("aria-hidden", "false");
  // FLIP Last+Invert+Play: 封面卡→modal-card 平滑展开(仿小红书点笔记进详情)
  if (firstRect) {
    const card = dayModal.querySelector(".day-modal-card");
    if (card) {
      const lastRect = card.getBoundingClientRect();
      const dx = firstRect.left - lastRect.left;
      const dy = firstRect.top - lastRect.top;
      const sx = lastRect.width ? firstRect.width / lastRect.width : 1;
      const sy = lastRect.height ? firstRect.height / lastRect.height : 1;
      card.style.transformOrigin = "top left";
      card.style.transform = `translate(${dx}px, ${dy}px) scale(${sx}, ${sy})`;
      card.style.transition = "none";
      // 双 rAF: 先应用 invert，下一帧再 play 过渡到原位
      requestAnimationFrame(() => requestAnimationFrame(() => {
        card.style.transition = "transform .35s cubic-bezier(.2,.8,.2,1)";
        card.style.transform = "";
      }));
      const cleanup = () => {
        card.style.transition = "";
        card.style.transform = "";
        card.style.transformOrigin = "";
        card.removeEventListener("transitionend", cleanup);
      };
      card.addEventListener("transitionend", cleanup);
    }
  }
  activateFocusTrap(dayModal, closeDayModal);
  dayModalClose.focus();
  resetDayModalScrollPosition();
  if (feedbackPreset) {
    applyFeedbackPreset(dayModalContent, feedbackPreset);
  } else {
    syncFeedbackQuickChoiceUi(dayModalContent, FEEDBACK_QUICK_PRESETS.feedback_done);
  }
  bindDayModalInteractions(dayModalContent);
}

function renderReferences(target, payload, valueKey, detailKey, emptyMessage) {
  const values = payload?.[valueKey] || {};
  const details = payload?.[detailKey] || {};
  const keys = Object.keys(values);
  if (!keys.length) {
    setEmpty(target, emptyMessage);
    return;
  }

  target.className = "chip-grid";
  target.innerHTML = keys
    .map((key) => {
      const label = values[key];
      const detail = details[key] || "";
      return `
        <div class="info-chip">
          <strong>${escapeHtml(key)} ${escapeHtml(label)}</strong>
          ${detail ? `<small>${escapeHtml(detail)}</small>` : ""}
        </div>
      `;
    })
    .join("");
}

function getApiBaseCandidates() {
  return Array.from(new Set([
    getApiBase(),
    ...API_BASE_CANDIDATES,
  ].filter(Boolean)));
}

async function ping({ autoDetect = false } = {}) {
  try {
    const data = await window.__apiClient.apiFetch("/health", { timeoutMs: 2500 });
    // 传入完整 health 数据以支持 LLM 状态提示条
    renderHealth(data.status, data.model, data.provider, null, data);
  } catch (error) {
    if (autoDetect && await window.__apiClient.detectApiBase()) {
      return;
    }
    renderHealth("", "", "", error.message);
  }
}

async function loadMeta() {
  try {
    const [zones, tiers] = await Promise.all([
      window.__apiClient.apiFetch("/zone-reference"),
      window.__apiClient.apiFetch("/evidence-tier-reference"),
    ]);
    renderReferences(zonesBox, zones, "zones", "zones_detail", "没有强度区间数据");
    renderReferences(tiersBox, tiers, "evidence_tiers", "descriptions", "没有训练依据数据");
  } catch (error) {
    setEmpty(zonesBox, `区间加载失败：${error.message}`);
    setEmpty(tiersBox, "请确认本地服务已启动。");
  }
}

function yesNoLabel(value) {
  return value ? "是" : "否";
}

function renderKbGovernanceMetric(label, value) {
  return `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function renderKbGovernanceList(items = [], emptyText = "暂无待处理项") {
  if (!items.length) return `<div class="empty-state">${escapeHtml(emptyText)}</div>`;
  return `
    <div class="kb-governance-list">
      ${items.slice(0, 8).map((item) => `
        <article>
          <strong>${escapeHtml(text(item.domain_pack || item.subdomain, "未命名 domain"))}</strong>
          <span>${escapeHtml(text(item.next_action || item.release_gate_impact || item.gap_status, "待补治理动作"))}</span>
          <em>sources ${escapeHtml(text(item.needed_source_count, 0))} / rules ${escapeHtml(text(item.needed_rule_count, 0))} / tier ${escapeHtml(text(item.required_quality_tier || item.minimum_quality_tier, "-"))}</em>
        </article>
      `).join("")}
    </div>
  `;
}

function renderKbGovernance(data) {
  const runtime = data?.runtime || {};
  const releaseGate = data?.release_gate || {};
  const domainGapSummary = data?.domain_gap_summary || {};
  const actionableGaps = Array.isArray(data?.top_actionable_domain_gaps) ? data.top_actionable_domain_gaps : [];
  const workQueue = Array.isArray(data?.release_work_queue) ? data.release_work_queue : [];
  const blockers = releaseGate.readiness_blockers || runtime.replacement_blockers || [];
  kbGovernanceStatus.className = data?.status === "ready" ? "status-note ok" : "status-note error";
  kbGovernanceStatus.textContent = data?.status === "ready"
    ? "KB 治理门禁已通过，可继续评估生产替换。"
    : `KB 治理仍阻塞：${listText(blockers, data?.status || "blocked")}`;
  kbGovernanceContent.className = "kb-governance-content";
  kbGovernanceContent.innerHTML = `
    <div class="kb-governance-grid">
      ${renderKbGovernanceMetric("can_replace_runtime", yesNoLabel(runtime.can_replace_runtime))}
      ${renderKbGovernanceMetric("commercial_release_ready", yesNoLabel(releaseGate.commercial_release_ready))}
      ${renderKbGovernanceMetric("first_batch_release_ready", yesNoLabel(releaseGate.first_batch_release_ready || runtime.first_batch_release_ready))}
      ${renderKbGovernanceMetric("source deficits", text(domainGapSummary.domain_packs_with_source_deficits, 0))}
    </div>
    <section>
      <h3>Top domain gaps</h3>
      ${renderKbGovernanceList(actionableGaps, "暂无 domain gap")}
    </section>
    <section>
      <h3>Release work queue</h3>
      ${renderKbGovernanceList(workQueue, "暂无 release work queue")}
    </section>
  `;
}

async function loadKbGovernance() {
  if (!kbGovernanceStatus || !kbGovernanceContent) return;
  const token = String(state.apiToken || apiTokenInput?.value || "").trim();
  if (!token) {
    kbGovernanceStatus.className = "status-note error";
    kbGovernanceStatus.textContent = "请先填写访问令牌，再读取 KB 治理门禁。";
    return;
  }
  kbGovernanceStatus.className = "status-note";
  kbGovernanceStatus.textContent = "正在读取 KB 治理门禁...";
  kbGovernanceContent.className = "empty-state";
  kbGovernanceContent.textContent = "加载中";
  try {
    const data = await window.__apiClient.apiFetch("/admin/kb-governance", {
      headers: getExpertBearerHeaders(),
      timeoutMs: 5000,
    });
    renderKbGovernance(data);
  } catch (error) {
    kbGovernanceStatus.className = "status-note error";
    kbGovernanceStatus.textContent = `KB 治理门禁加载失败：${error.message}`;
    kbGovernanceContent.className = "empty-state";
    kbGovernanceContent.textContent = "请确认专家令牌和后端服务状态。";
  }
}

function isPlanLikeQuery(query) {
  return /训练计划|周计划|月历|日历|课表|生成计划|制定|安排|备赛|半马|全马|马拉松/.test(query);
}

function renderEvidenceSourceIndicator(response) {
  const el = $("evidenceSourceIndicator");
  if (!el) return;
  const answerSourceMode = String(response?.answer_source_mode || "").trim();
  const chainItems = response?.evidence_chain?.items;
  // 后端 evidence_chain 是对象契约；只用 items 判定，避免把对象误当数组导致来源状态隐藏。
  const hasEvidenceChain = Array.isArray(chainItems) && chainItems.length > 0;
  if (!answerSourceMode && !hasEvidenceChain) {
    el.hidden = true;
    return;
  }
  el.hidden = false;
  let statusClass = "source-none";
  let icon = "-";
  let label = "未绑定外部证据";

  switch (answerSourceMode) {
    case "verified_source":
      statusClass = "source-verified";
      icon = "✓"; // checkmark
      label = "有科学证据支持";
      break;
    case "model_general_knowledge":
      statusClass = "source-model-knowledge";
      icon = "i";
      label = "基于模型通用知识";
      break;
    case "blocked_needs_evidence":
      statusClass = "source-blocked";
      icon = "!";
      label = "证据不足，建议仅供参考";
      break;
    default:
      if (hasEvidenceChain) {
        statusClass = "source-verified";
        icon = "✓";
        label = "有科学证据支持";
      } else if (String(response?.report || "").length > 50) {
        statusClass = "source-none";
        icon = "-";
        label = "未绑定外部证据";
      }
      break;
  }

  el.className = `evidence-source-indicator ${statusClass}`;
  el.innerHTML = `<span class="evidence-source-indicator-icon">${icon}</span><span>${label}</span>`;
}

function renderQueryPayload(payload) {
  state.lastResponse = payload;
  renderReport(payload);
  renderCalendar(payload);
  renderEvidencePreview(payload);
  renderEvidenceSourceIndicator(payload);
  const hasStructuredPlan = summarizePlan(payload).hasStructuredPlan;
  updateWorkspaceFlow(hasStructuredPlan ? "calendar" : "answer", hasStructuredPlan ? "训练日历已生成。优先查看周重点，再点开单日卡片反馈调整。" : "这是智能对话结果，可在下方查看回答与依据。");
  if (hasStructuredPlan) {
    setActiveDrawerSection("calendar");
  } else {
    updateWorkspaceFlow("answer", "这是智能对话结果，可在下方查看回答与依据。");
    setActiveDrawerSection("basis");
  }
  syncPlanProgressFromPayload(payload);
  tokenUsageBox.textContent = formatTokenUsage(payload.token_usage);
  auditScoresBox.textContent = formatAuditScores(payload.audit_scores);
  guidedQuestionsBox.textContent = renderQuestions(payload.guided_questions);
  if (payload.message) {
    queryHint.textContent = payload.message;
  }
  if (payload.training_plan_id) {
    renderPlanHistory();
  }
}

async function runQuery(textValue) {
  let query = (textValue || queryInput.value || "").trim();
  const qaMode = currentQueryMode === "qa";
  if (!query) {
    if (qaMode) {
      setEmpty(reportBox, "请输入你想问 AI 教练的问题，例如训练安排、伤病预防、补给或恢复。");
      resultBadge.textContent = "等待提问";
      queryHint.textContent = "智能对话需要先输入一个具体问题。";
      renderPlanProgress({
        percent: 0,
        activeStep: "connect",
        status: "idle",
        phase: "等待问题",
        signal: "输入问题后即可向 AI 教练提问",
      });
      queryInput.focus();
      return;
    }
    const draft = getProfileDraft();
    const missingFields = actionableProfileMissingFields(draft);
    if (!missingFields.length) {
      query = profileDraftToPrompt(draft);
      queryInput.value = query;
      localStorage.setItem("marathon-profile-draft", JSON.stringify(draft));
      profileStatus.textContent = "已用于本次计划";
    } else {
      setEmpty(reportBox, `请先补齐关键画像：${missingFields.join("、")}。这些信息会直接影响训练安排和安全降级。`);
      resultBadge.textContent = "缺少画像";
      renderPlanProgress({
        percent: 0,
        activeStep: "profile",
        status: "error",
        phase: "缺少我的情况",
        signal: `还缺：${missingFields.join("、")}`,
      });
      setActiveDrawerSection("profile");
      return;
    }
  }

  const planLike = qaMode ? false : isPlanLikeQuery(query);
  capturePlanIntent(query);
  if (!planLike && llmProviderInput.value === "openai" && llmProviderInput.dataset.activeProviderConfigured === "false") {
    setEmpty(reportBox, "OpenAI 需要服务端配置 OPENAI_API_KEY。请配置后刷新模型选项，或切换到 Ollama。");
    resultBadge.textContent = "模型未配置";
    renderPlanProgress({
      percent: 0,
      activeStep: "connect",
      status: "error",
      phase: "模型未配置",
      signal: "OpenAI provider 需要服务端 API Key",
    });
    return;
  }
  if (
    !planLike
    && llmProviderInput.value === "ds"
    && llmProviderInput.dataset.activeProviderConfigured === "false"
    && !dsApiKeyInput.value.trim()
  ) {
    setEmpty(reportBox, "使用 DeepSeek 前，请先填写 API Key；该密钥只在当前会话中使用。");
    resultBadge.textContent = "缺少 API Key";
    dsApiKeyStatus.textContent = "请填写 DeepSeek API Key 后再生成。";
    renderPlanProgress({
      percent: 0,
      activeStep: "connect",
      status: "error",
      phase: "缺少 API Key",
      signal: "DeepSeek 请求需要当前会话中的 API Key",
    });
    return;
  }

  setBusy(qaMode ? "正在询问 AI 教练..." : "正在生成训练日历...");
  resetPlanProgress();
  updateWorkspaceFlow(
    "generating",
    qaMode ? "正在处理智能对话，回答会显示在下方结果区。" : "正在生成训练日历，完成后会自动打开日历。",
  );
  if (planLike) {
    calendarBox.innerHTML = '<div class="loading-state">正在等待结构化日历</div>';
  }
  if (planLike) {
    startPlanProgressDrift();
  } else {
    renderPlanProgress({
      percent: 22,
      activeStep: "connect",
      status: "running",
      phase: "普通问答处理中",
      signal: "当前请求不是训练计划，日历轨迹会在计划类问题中启用",
    });
  }

  if (state.queryController) {
    state.queryController.abort();
  }
  const controller = new AbortController();
  const runId = state.queryRunId + 1;
  state.queryRunId = runId;
  state.queryController = controller;
  cancelQueryButton.disabled = false;
  queryHint.textContent = qaMode ? "正在向 AI 教练提问。" : "正在生成结构化训练日历。";

  try {
    let payload;
    try {
      if (planLike) {
        // 流式优先：真实节点进度驱动；失败降级非流式（保留多 base + 重试）
        payload = await window.__apiClient.streamQueryPayload(query, {
          responseMode: "full", controller,
          onNode: (evt) => updateProgressFromNode(evt.node, evt.stepId),
        });
      } else {
        payload = await window.__apiClient.requestQueryPayload(query, { responseMode: "full", controller });
      }
    } catch (error) {
      if (controller.signal.aborted || !planLike) {
        throw error;
      }
      // 流式或首次请求未完成：降级非流式重试（更长窗口）
      stopPlanProgressDrift();
      renderPlanProgress({
        percent: 74,
        activeStep: "calendar",
        status: "running",
        phase: "计划请求重试中",
        signal: "流式或首次请求未完成，正在用更长窗口重试结构化日历",
      });
      queryHint.textContent = "首次请求未完成，正在自动重试一次。";
      payload = await window.__apiClient.requestQueryPayload(query, { responseMode: "full", controller, retry: true });
    }
    if (runId !== state.queryRunId || controller.signal.aborted) {
      return;
    }
    renderQueryPayload(payload);
    state.queryController = null;
    cancelQueryButton.disabled = true;
  } catch (error) {
    if (runId !== state.queryRunId || controller.signal.aborted) {
      setEmpty(reportBox, "请求已取消。");
      resultBadge.textContent = "已取消";
      queryHint.textContent = "已停止等待本地训练服务响应。";
      renderPlanProgress({
        percent: currentPlanProgressPercent(),
        activeStep: "skeleton",
        status: "cancelled",
        phase: "请求已取消",
        signal: "已停止等待本地训练服务响应",
      });
      cancelQueryButton.disabled = true;
      state.queryController = null;
      return;
    }
    const friendlyError = window.__apiClient.explainApiError(error, state.lastQueryBase || getApiBase());
    setEmpty(reportBox, `请求失败：${friendlyError}`);
    setEmpty(calendarBox, "无法刷新日历。");
    resultBadge.textContent = "失败";
    queryHint.textContent = friendlyError;
    stopPlanProgressDrift();
    renderPlanProgress({
      percent: currentPlanProgressPercent(),
      activeStep: "skeleton",
      status: "error",
      phase: "请求失败",
      signal: friendlyError,
    });
    cancelQueryButton.disabled = true;
    state.queryController = null;
  }
}

function clearResult() {
  if (state.queryController) {
    state.queryController.abort();
  }
  state.queryController = null;
  cancelQueryButton.disabled = true;
  setEmpty(loadSummaryBox, "训练负荷会在生成计划后显示。");
  state.lastResponse = null;
  setEmpty(reportBox, "还没有结果。填写我的情况或补充说明后，可以生成训练日历。");
  setEmpty(calendarBox, "计划生成后会在这里展示日历卡片。");
  renderCalendarActionPanel({}, []);
  updateWorkspaceFlow("profile");
  calendarScopeHint.textContent = "生成后可按周、按月或按阶段浏览完整计划";
  setEmpty(evidencePreview, "生成计划后，会从返回结果中提取证据编号、证据层级和来源摘要。");
  resultBadge.textContent = "待生成";
  renderCalendarStats([]);
  evidenceCount.textContent = "0 条";
  statusPanel.hidden = true;
  adjustmentHistory.hidden = true;
  adjustmentHistory.innerHTML = "";
  tokenUsageBox.textContent = "-";
  auditScoresBox.textContent = "-";
  guidedQuestionsBox.textContent = "-";
  queryHint.textContent = "提交后会优先返回可执行计划。";
  $("calendar-section")?.classList.remove("has-calendar-data");
  resetPlanProgress();
}

function moveWorkspaceSectionsToDrawer() {
  const drawerSections = $("drawerWorkspaceSections");
  if (!drawerSections) return;
  drawerSections.innerHTML = "";
}

function setTopNavCurrent(sectionId) {
  const targetBySection = {
    plan: "plan",
    templates: "plan",
    history: "calendar-section",
    settings: "plan",
    calendar: "calendar-section",
    profile: "profile",
    basis: "evidence",
  };
  const targetId = targetBySection[sectionId] || sectionId;
  document.querySelectorAll(".top-nav nav a, .mobile-quick-nav a").forEach((link) => {
    const hrefId = (link.getAttribute("href") || "").replace(/^#/, "");
    const navId = link.dataset.navSection || hrefId;
    if (navId === targetId) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
}

function setActiveDrawerSection(sectionId, opener = null) {
  const drawerSectionNodes = Array.from(document.querySelectorAll("[data-drawer-section]"));
  const targetSection = drawerSectionNodes.find((section) => section.dataset.drawerSection === sectionId);
  if (targetSection?.hasAttribute("data-expert-only")) return;
  setTopNavCurrent(sectionId);
  if (sectionId === "profile") {
    const profileSection = drawerSectionNodes.find((section) => section.dataset.drawerSection === "profile");
    if (profileSection) profileSection.hidden = true;
    const profileSummary = drawerSectionNodes.find((section) => section.dataset.drawerSection === "profile-summary");
    if (profileSummary) profileSummary.hidden = false;
    drawerActionButtons.forEach((button) => {
      const isActive = button.dataset.drawerAction === sectionId;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-current", isActive ? "true" : "false");
    });
    if (isMobileDrawerMode()) closeSideDrawer();
    openProfilePanel();
    return;
  }
  const targetInDrawer = Boolean(targetSection?.closest?.("#drawerWorkspaceSections, .side-drawer-content"));
  const drawer = document.querySelector("[data-side-drawer]");
  if (drawer && targetInDrawer) {
    drawer.open = true;
    activateSideDrawerModal(drawer, opener);
  } else if (drawer && isMobileDrawerMode()) {
    closeSideDrawer();
  }
  drawerSectionNodes.forEach((section) => {
    const isActive = section.dataset.drawerSection === sectionId;
    const isPersistent = section.hasAttribute("data-persistent-section");
    section.hidden = isPersistent ? false : !isActive;
    section.classList.toggle("is-active", isActive);
  });
  drawerActionButtons.forEach((button) => {
    const isActive = button.dataset.drawerAction === sectionId;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-current", isActive ? "true" : "false");
  });
  if (targetSection && !targetInDrawer) {
    window.requestAnimationFrame(() => targetSection.scrollIntoView({ behavior: "smooth", block: "start" }));
  }
}

function filterDrawerActions(query) {
  const normalizedQuery = String(query || "").trim().toLowerCase();
  const directMatches = new Set();
  if (normalizedQuery.includes("profile") || normalizedQuery.includes("画像") || normalizedQuery.includes("资料")) directMatches.add("profile");
  if (normalizedQuery.includes("calendar") || normalizedQuery.includes("日历") || normalizedQuery.includes("训练")) directMatches.add("calendar");
  if (normalizedQuery.includes("basis") || normalizedQuery.includes("evidence") || normalizedQuery.includes("依据") || normalizedQuery.includes("证据") || normalizedQuery.includes("解释")) directMatches.add("basis");
  if (normalizedQuery.includes("history") || normalizedQuery.includes("历史")) directMatches.add("history");
  if (normalizedQuery.includes("settings") || normalizedQuery.includes("api") || normalizedQuery.includes("设置") || normalizedQuery.includes("模型") || normalizedQuery.includes("接口")) directMatches.add("settings");
  if (normalizedQuery.includes("template") || normalizedQuery.includes("prompt") || normalizedQuery.includes("模板") || normalizedQuery.includes("快捷")) directMatches.add("templates");
  let visibleActions = 0;
  drawerActionButtons.forEach((button) => {
    if (button.hasAttribute("data-expert-only")) {
      button.hidden = true;
      return;
    }
    const haystack = `${button.textContent || ""} ${button.dataset.drawerQuery || ""}`.toLowerCase();
    const directMatch = directMatches.has(button.dataset.drawerAction || "");
    button.hidden = Boolean(normalizedQuery) && !directMatch && !haystack.includes(normalizedQuery);
    if (!button.hidden) visibleActions += 1;
  });
  if (drawerEmptyState) {
    drawerEmptyState.hidden = !normalizedQuery || visibleActions > 0;
  }
}

function showSamplePlan() {
  queryInput.value = "请给一个半马新手示例训练日历，我会之后再补充自己的画像。";
  setActiveDrawerSection("profile");
  queryHint.textContent = "已填入示例请求；你可以先完善我的情况，服务连接后再生成训练日历。";
}

document.addEventListener("click", (event) => {
  const retry = event.target.closest?.("[data-health-retry]");
  if (retry) {
    event.preventDefault();
    ping({ autoDetect: true });
    loadLlmOptions();
    return;
  }
  const samplePlan = event.target.closest?.("[data-sample-plan]");
  if (samplePlan) {
    event.preventDefault();
    showSamplePlan();
    return;
  }
  const focusPlanEntry = event.target.closest?.("[data-focus-plan-entry]");
  if (focusPlanEntry) {
    event.preventDefault();
    setTopNavCurrent("plan");
    $("plan")?.scrollIntoView({ behavior: "smooth", block: "start" });
    queryInput?.focus({ preventScroll: true });
  }
});

apiBaseInput.addEventListener("change", () => {
  state.apiBase = getApiBase();
  localStorage.setItem("marathon-api-base", state.apiBase);
  ping({ autoDetect: true });
  loadLlmOptions();
  loadMeta();
});

apiTokenInput?.addEventListener("input", () => {
  state.apiToken = apiTokenInput.value.trim();
});

apiTokenInput?.addEventListener("change", () => {
  state.apiToken = apiTokenInput.value.trim();
  ping({ autoDetect: true });
  loadLlmOptions();
  loadMeta();
});

loadKbGovernanceButton?.addEventListener("click", loadKbGovernance);

llmProviderInput.addEventListener("change", () => {
  renderModelOptions();
  localStorage.setItem("marathon_llm_provider", llmProviderInput.value);
  localStorage.setItem("marathon_llm_model", llmModelInput.value.trim());
});

providerButtons.forEach((button) => {
  button.addEventListener("click", () => {
    llmProviderInput.value = button.dataset.providerChoice || "ds";
    renderModelOptions();
    localStorage.setItem("marathon_llm_provider", llmProviderInput.value);
    localStorage.setItem("marathon_llm_model", llmModelInput.value.trim());
  });
});

llmModelInput.addEventListener("change", () => {
  localStorage.setItem("marathon_llm_model", llmModelInput.value.trim());
});

saveDsApiKeyButton.addEventListener("click", () => {
  const value = dsApiKeyInput.value.trim();
  if (!value) {
    dsApiKeyStatus.textContent = "请先填写 API Key。";
    return;
  }
  localStorage.removeItem("marathon_ds_api_key");
  dsApiKeyStatus.textContent = "API Key 仅在当前会话内使用，刷新后不会保留。";
});

clearDsApiKeyButton.addEventListener("click", () => {
  dsApiKeyInput.value = "";
  localStorage.removeItem("marathon_ds_api_key");
  dsApiKeyStatus.textContent = "API Key 已清除。";
});

document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    queryInput.value = button.getAttribute("data-prompt") || "";
    queryInput.focus();
  });
});

drawerActionButtons.forEach((button) => {
  button.addEventListener("click", () => {
    setActiveDrawerSection(button.dataset.drawerAction || "", button);
  });
});

drawerSearchInput?.addEventListener("input", () => {
  filterDrawerActions(drawerSearchInput.value);
});

topNavSearchInput?.addEventListener("focus", () => {
  const drawer = document.querySelector("[data-side-drawer]");
  if (drawer && !isMobileDrawerMode()) {
    drawer.open = true;
    setDrawerContentAvailability(drawer, true);
  }
});

topNavSearchInput?.addEventListener("input", () => {
  if (drawerSearchInput) drawerSearchInput.value = topNavSearchInput.value;
  filterDrawerActions(topNavSearchInput.value);
});

topNavSearchInput?.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") return;
  const firstVisibleAction = drawerActionButtons.find((button) => !button.hidden);
  if (firstVisibleAction) {
    event.preventDefault();
    firstVisibleAction.click();
  }
});

drawerSearchInput?.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") return;
  const firstVisibleAction = drawerActionButtons.find((button) => !button.hidden);
  if (firstVisibleAction) {
    event.preventDefault();
    firstVisibleAction.click();
  }
});

document.querySelectorAll("[data-open-drawer-section]").forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    setActiveDrawerSection(link.dataset.openDrawerSection || "", link);
  });
});

document.querySelectorAll('.top-nav nav a[href="#plan"]:not([data-query-nav]), .mobile-quick-nav a[href="#plan"]:not([data-query-nav])').forEach((link) => {
  link.addEventListener("click", () => {
    setQueryMode("plan");
    setTopNavCurrent("plan");
  });
});

document.querySelectorAll("[data-side-drawer-close]").forEach((button) => {
  button.addEventListener("click", () => closeSideDrawer());
});

document.querySelector("[data-side-drawer]")?.addEventListener("toggle", (event) => {
  const drawer = event.currentTarget;
  if (drawer.open) {
    setDrawerContentAvailability(drawer, true);
    activateSideDrawerModal(drawer, document.activeElement);
  } else {
    setDrawerContentAvailability(drawer, false);
    document.body.classList.remove("side-drawer-modal-open");
    setSideDrawerModalInert(false, drawer);
    deactivateFocusTrap(drawer);
  }
});

window.addEventListener("resize", syncSideDrawerViewportState);

document.querySelectorAll("[data-workspace-generate]").forEach((button) => {
  button.addEventListener("click", () => runQuery());
});

calendarViewButtons.forEach((button) => {
  button.addEventListener("click", () => {
    state.calendarView = button.dataset.calendarView || "week";
    calendarViewButtons.forEach((item) => {
      const active = item === button;
      item.classList.toggle("active", active);
      item.setAttribute("aria-selected", active ? "true" : "false");
    });
    if (state.lastResponse) {
      renderCalendar(state.lastResponse);
    }
  });
  button.addEventListener("keydown", (event) => handleSegmentedControlKeydown(event, calendarViewButtons));
});

calendarFilterButtons.forEach((button) => {
  button.addEventListener("click", () => {
    state.calendarFilter = button.dataset.calendarFilter || "all";
    calendarFilterButtons.forEach((item) => {
      const active = item === button;
      item.classList.toggle("active", active);
      item.setAttribute("aria-selected", active ? "true" : "false");
    });
    if (state.lastResponse) {
      renderCalendar(state.lastResponse);
    }
  });
  button.addEventListener("keydown", (event) => handleSegmentedControlKeydown(event, calendarFilterButtons));
});

$("runQuery").addEventListener("click", () => runQuery());
cancelQueryButton.addEventListener("click", () => {
  if (state.queryController) {
    state.queryController.abort();
  }
  state.queryController = null;
  cancelQueryButton.disabled = true;
  resultBadge.textContent = "已取消";
  queryHint.textContent = "已取消当前请求。";
  stopPlanProgressDrift();
  renderPlanProgress({
    percent: currentPlanProgressPercent(),
    activeStep: "skeleton",
    status: "cancelled",
    phase: "请求已取消",
    signal: "当前计划生成已停止",
  });
});
dayModalClose.addEventListener("click", closeDayModal);
dayModalBackdrop.addEventListener("click", closeDayModal);
evidenceDrawerClose.addEventListener("click", closeEvidenceDrawer);
evidenceDrawerBackdrop.addEventListener("click", closeEvidenceDrawer);
document.addEventListener("click", (event) => {
  const opener = event.target instanceof HTMLElement ? event.target.closest("[data-evidence-open]") : null;
  if (!opener || dayModalContent.contains(opener)) return;
  openEvidenceDrawer({
    id: opener.dataset.evidenceId,
    all: opener.dataset.evidenceScope === "all",
  }, opener);
});
closeProfilePanelButton.addEventListener("click", closeProfilePanel);
cancelProfilePanelButton.addEventListener("click", closeProfilePanel);
saveProfilePanelButton.addEventListener("click", saveProfilePanel);
profileEditorDialog.addEventListener("click", (event) => {
  if (event.target === profileEditorDialog) {
    closeProfilePanel();
  }
});
document.addEventListener("keydown", (event) => {
  if (handleFocusTrapKeydown(event)) return;
  if (event.key === "Escape" && evidenceDrawer.classList.contains("open")) {
    closeEvidenceDrawer();
    return;
  }
  if (event.key === "Escape" && dayModal.classList.contains("open")) {
    closeDayModal();
  }
});
$("loadMeta").addEventListener("click", () => loadMeta());
$("clearResult").addEventListener("click", clearResult);
// ── P2-1: Mode toggle (训练日历 / 自由问答) ──
const queryModeButtons = Array.from(document.querySelectorAll("[data-query-mode]"));
let currentQueryMode = "plan";
const suggestedQuestionsEl = $("suggestedQuestions");

function syncWorkspaceIntentCards(mode) {
  document.querySelectorAll("[data-workspace-intent]").forEach((button) => {
    const isActive = button.dataset.workspaceIntent === mode;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", isActive ? "true" : "false");
  });
}

function setQueryMode(mode = "plan") {
  currentQueryMode = mode === "qa" ? "qa" : "plan";
  queryModeButtons.forEach((item) => {
    const active = item.dataset.queryMode === currentQueryMode;
    item.classList.toggle("active", active);
    item.setAttribute("aria-selected", active ? "true" : "false");
  });
  setTopNavCurrent(currentQueryMode === "qa" ? "dialog" : "plan");
  updateQueryModeUi();
  syncWorkspaceIntentCards(currentQueryMode);
}

queryModeButtons.forEach((button) => {
  button.addEventListener("click", () => setQueryMode(button.dataset.queryMode || "plan"));
});

document.querySelectorAll("[data-workspace-intent]").forEach((button) => {
  button.addEventListener("click", () => {
    const intent = button.dataset.workspaceIntent === "qa" ? "qa" : "plan";
    setQueryMode(intent);
    if (intent === "qa") {
      queryInput.placeholder = "例如：膝盖疼还能跑吗？跑前吃什么？跑后怎么恢复？";
      queryHint.textContent = "智能对话只回答问题，不会改动当前训练日历。";
    } else {
      queryInput.placeholder = "可留空使用我的情况，或补充目标赛事、可训练日、近期伤病/疲劳。";
      queryHint.textContent = "训练日历会根据我的情况生成可点击日历。";
    }
    queryInput.focus({ preventScroll: true });
  });
});

document.querySelectorAll("[data-query-nav]").forEach((link) => {
  link.addEventListener("click", () => {
    setQueryMode(link.dataset.queryNav || "qa");
    setTopNavCurrent("dialog");
  });
});

function updateQueryModeUi() {
  const isQa = currentQueryMode === "qa";
  const composerTitle = $("composerTitle");
  if (composerTitle) {
    composerTitle.textContent = isQa ? "智能对话" : "生成日历";
  }
  if (suggestedQuestionsEl) {
    suggestedQuestionsEl.hidden = !isQa;
  }
  if (queryInput) {
    queryInput.placeholder = isQa
      ? "向 AI 教练提问，例如：如何预防膝盖疼？跑前应该吃什么？"
      : "补充说明，例如：我想生成 12 周半马计划，周末适合长跑，近期小腿容易紧。也可以留空，直接使用侧栏画像生成。";
  }
  const runQueryBtn = $("runQuery");
  if (runQueryBtn) {
    runQueryBtn.textContent = isQa ? "向教练提问" : "生成训练日历";
    runQueryBtn.title = isQa ? "提交问题给 AI 教练" : "根据画像生成训练日历";
  }
  const queryHintEl = $("queryHint");
  if (queryHintEl) {
    queryHintEl.textContent = isQa ? "准备向 AI 教练提问" : "准备好后生成训练日历";
  }
}

// ── P2-1: Suggested question click ──
if (suggestedQuestionsEl) {
  suggestedQuestionsEl.addEventListener("click", (event) => {
    const chip = event.target.closest("[data-question]");
    if (chip && queryInput) {
      queryInput.value = chip.dataset.question || "";
      queryInput.focus();
    }
  });
}

// ── P2-1: Quick action template switching ──
document.addEventListener("click", (event) => {
  const quickBtn = event.target.closest("[data-prompt]");
  if (quickBtn && queryInput) {
    const prompt = quickBtn.dataset.prompt || "";
    if (prompt.includes("自由问答") || prompt.includes("跑步训练相关问题")) {
      // Switch to Q&A mode
      if (currentQueryMode !== "qa") {
        const qaModeBtn = document.querySelector("[data-query-mode=\"qa\"]");
        if (qaModeBtn) qaModeBtn.click();
      } else {
        updateQueryModeUi();
      }
    } else if (prompt.includes("训练日历") || prompt.includes("训练计划")) {
      if (currentQueryMode !== "plan") {
        const planModeBtn = document.querySelector("[data-query-mode=\"plan\"]");
        if (planModeBtn) planModeBtn.click();
      } else {
        updateQueryModeUi();
      }
    }
  }
});

// ── P2-2: "我是新手" button ──
const beginnerButton = $("beginnerQuickFill");
const BEGINNER_DEFAULTS = {
  goal: "健康跑 / 完成第一个 5K 或半马",
  experience: "新手",
  lastMonthMileage: "50 km",
  raceDate: "",
  availableDays: "周一、周三、周五、周六",
  longRun: "40 分钟",
  limitations: "暂无严重伤病",
};

function applyBeginnerDefaults() {
  Object.entries(BEGINNER_DEFAULTS).forEach(([key, value]) => {
    const input = document.querySelector(`[data-profile-field="${key}"]`);
    if (input) input.value = value;
  });
  // Hide advanced fields for beginners
  document.querySelectorAll(".profile-field-advanced").forEach((el) => {
    el.classList.add("hidden-by-experience");
  });
  // Update derived metrics
  if (typeof updateProfileDerivedMetrics === "function") {
    updateProfileDerivedMetrics();
  }
  // Save draft
  if (typeof saveProfileDraft === "function") {
    saveProfileDraft();
  }
  const profileStatusEl = $("profileStatus");
  if (profileStatusEl) {
    profileStatusEl.textContent = "新手画像已填充";
    profileStatusEl.className = "pill muted-pill";
  }
}

if (beginnerButton) {
  beginnerButton.addEventListener("click", applyBeginnerDefaults);
}

// ── P2-2: Profile experience-level changes ──
function syncAdvancedFieldVisibility() {
  const experienceInput = document.querySelector("[data-profile-field=\"experience\"]");
  if (!experienceInput) return;
  const value = String(experienceInput.value || "").trim().toLowerCase();
  const isBeginner = value === "新手" || value === "beginner" || value.includes("新手");
  document.querySelectorAll(".profile-field-advanced").forEach((el) => {
    if (isBeginner) {
      el.classList.add("hidden-by-experience");
    } else {
      el.classList.remove("hidden-by-experience");
    }
  });
}

document.querySelectorAll("[data-profile-field=\"experience\"]").forEach((input) => {
  input.addEventListener("input", syncAdvancedFieldVisibility);
  input.addEventListener("change", syncAdvancedFieldVisibility);
});

$("saveProfileDraft").addEventListener("click", saveProfileDraft);
$("buildProfilePrompt").addEventListener("click", buildProfilePrompt);
$("runProfilePlan").addEventListener("click", async () => {
  setQueryMode("plan");
  if (!queryInput.value.trim()) {
    await saveProfileDraft();
  }
  await runQuery();
});
document.querySelectorAll("[data-profile-field]").forEach((input) => {
  input.addEventListener("input", () => updateProfileDerivedMetrics());
});
$("savePlanDraft").addEventListener("click", saveCurrentPlanSnapshot);
$("loadPlanDrafts").addEventListener("click", renderPlanHistory);
toggleHistoryListButton?.addEventListener("click", () => {
  state.historyExpanded = !state.historyExpanded;
  renderPlanHistory();
});
queryInput.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
    runQuery();
  }
});

const savedBase = localStorage.getItem("marathon-api-base");
if (savedBase) {
  apiBaseInput.value = savedBase;
  state.apiBase = savedBase;
}
localStorage.removeItem("marathon_ds_api_key");
dsApiKeyStatus.textContent = "API Key 仅在当前会话内使用；更推荐在服务端配置 DEEPSEEK_API_KEY / DS_API_KEY。";

// ── Integration: Month Calendar View [product-calendar][P1] ──

function renderMonthCalendarGrid(days) {
  const grid = document.getElementById("monthCalendarGrid");
  if (!grid) return;
  if (!days || !days.length) {
    grid.hidden = true;
    return;
  }
  // Only show month grid in month view
  if (state.calendarView !== "month") {
    grid.hidden = true;
    return;
  }
  grid.hidden = false;

  // Group days by month
  const monthMap = new Map();
  days.forEach((day, index) => {
    const date = parseTrainingDate(day);
    if (!date) return;
    const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
    if (!monthMap.has(monthKey)) {
      monthMap.set(monthKey, { key: monthKey, year: date.getFullYear(), month: date.getMonth(), days: [] });
    }
    monthMap.get(monthKey).days.push({ day, index, date });
  });

  if (!monthMap.size) {
    grid.hidden = true;
    return;
  }

  const monthEntries = Array.from(monthMap.values()).sort((a, b) => a.key.localeCompare(b.key));
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const todayStr = today.toISOString().slice(0, 10);
  const dayNames = ["日", "一", "二", "三", "四", "五", "六"];

  let html = "";

  monthEntries.forEach((monthData) => {
    const firstDay = new Date(monthData.year, monthData.month, 1);
    const lastDay = new Date(monthData.year, monthData.month + 1, 0);
    const startDayOfWeek = firstDay.getDay();
    const totalDays = lastDay.getDate();
    const dayMap = new Map();
    monthData.days.forEach(({ day, index, date }) => {
      const dayNum = date.getDate();
      if (!dayMap.has(dayNum)) dayMap.set(dayNum, []);
      dayMap.get(dayNum).push({ day, index });
    });

    const monthNames = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"];
    html += `<div class="calendar-month-nav">
      <button type="button" data-month-prev disabled>←</button>
      <strong>${monthData.year}年${monthNames[monthData.month]}</strong>
      <button type="button" data-month-next disabled>→</button>
    </div>`;
    html += `<div class="calendar-month-header">${dayNames.map((d) => `<span>${d}</span>`).join("")}</div>`;
    html += `<div class="calendar-month-grid">`;

    // Empty cells before the first day
    for (let i = 0; i < startDayOfWeek; i++) {
      html += `<div class="calendar-month-cell empty" aria-hidden="true"></div>`;
    }

    for (let d = 1; d <= totalDays; d++) {
      const dateStr = `${monthData.year}-${String(monthData.month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      const isToday = dateStr === todayStr;
      const entries = dayMap.get(d) || [];
      const mainEntry = entries[0];
      const day = mainEntry ? mainEntry.day : null;
      const index = mainEntry ? mainEntry.index : -1;
      const isRest = day ? isRestDay(day) : true;
      const isQuality = day ? isQualityTraining(day) : false;
      const needsRecheck = day ? requiresProtocolRecheck(day) : false;
      const hasRace = day ? /race|比赛|赛事/i.test(String(day.training_title || day.main_set || "")) : false;
      const trainingLabel = day ? displayTrainingTitle(day) : "";
      const indicatorClass = hasRace ? "race" : needsRecheck ? "recheck" : isQuality ? "quality" : isRest ? "rest" : "default";

      html += `<button class="calendar-month-cell${isToday ? " today" : ""}${entries.length ? "" : " empty"}"
        type="button"
        data-month-day-index="${index}"
        ${!entries.length ? "disabled" : ""}
        aria-label="${dateStr}${trainingLabel ? "：" + trainingLabel : ""}">
        <span class="month-day-number">${d}</span>
        ${trainingLabel ? `<span class="month-day-label">${escapeHtml(trainingLabel.substring(0, 12))}</span>` : ""}
        <span class="month-day-indicator ${indicatorClass}" aria-hidden="true"></span>
      </button>`;
    }
    html += `</div>`;
  });

  grid.innerHTML = html;

  // Wire up month day click → open day modal or detail drawer
  grid.querySelectorAll("[data-month-day-index]").forEach((button) => {
    button.addEventListener("click", () => {
      const dayIndex = parseInt(button.dataset.monthDayIndex, 10);
      if (isNaN(dayIndex)) return;
      const response = state.lastResponse;
      if (!response) return;
      const days = normalizeCalendarDays(response);
      const day = days[dayIndex];
      if (!day) return;
      if (window.innerWidth <= 768) {
        openCalendarDetailDrawer(day, dayIndex);
      } else {
        openDayModal(day, null, button);
      }
    });
  });
}

// ── Integration: Calendar Detail Drawer (mobile) [product-calendar][P1] ──

const calendarDetailDrawer = document.getElementById("calendarDetailDrawer");
const calendarDetailBackdrop = document.getElementById("calendarDetailDrawerBackdrop");
const calendarDetailContent = document.getElementById("calendarDetailContent");

function openCalendarDetailDrawer(day, index) {
  if (!calendarDetailDrawer || !calendarDetailContent) return;
  state.selectedDay = day;
  calendarDetailContent.innerHTML = buildDayModalHtml(day);
  calendarDetailDrawer.classList.add("open");
  calendarDetailDrawer.hidden = false;
  calendarDetailDrawer.setAttribute("aria-hidden", "false");
  if (calendarDetailBackdrop) {
    calendarDetailBackdrop.hidden = false;
    calendarDetailBackdrop.classList.add("open");
  }
  bindDayModalInteractions(calendarDetailContent);
}

function closeCalendarDetailDrawer() {
  if (!calendarDetailDrawer) return;
  calendarDetailDrawer.classList.remove("open");
  calendarDetailDrawer.setAttribute("aria-hidden", "true");
  calendarDetailDrawer.hidden = true;
  if (calendarDetailBackdrop) {
    calendarDetailBackdrop.classList.remove("open");
    calendarDetailBackdrop.hidden = true;
  }
}

if (calendarDetailBackdrop) {
  calendarDetailBackdrop.addEventListener("click", closeCalendarDetailDrawer);
}
document.querySelector("[data-calendar-detail-close]")?.addEventListener("click", closeCalendarDetailDrawer);

// ── Integration: Workspace Scene Status [product-workspace][P1] ──

function updateWorkspaceSceneStatus() {
  const container = document.getElementById("workspaceSceneStatus");
  if (!container) return;

  const hasPlan = Boolean(state.lastResponse && normalizeCalendarDays(state.lastResponse).length);
  const hasProfile = Boolean(state.latestProfile && Object.keys(state.latestProfile).length > 1);
  const hasRecentAdjustment = Boolean(state.lastFeedbackResult);

  let scene = "first_time";
  if (hasRecentAdjustment) scene = "post_feedback";
  else if (hasPlan) scene = "in_cycle";
  else if (hasProfile) scene = "free_explore";

  let statusHtml = "";
  if (hasPlan) {
    const days = normalizeCalendarDays(state.lastResponse);
    const primaryIndex = primaryTrainingDayIndex(days);
    const primaryDay = days[primaryIndex];
    const statusSummary = frontendStatusFromDays(days);
    const todayLabel = primaryDay ? trainingDayLabel(primaryDay) : "查看日历";
    const todayType = primaryDay ? (isRestDay(primaryDay) ? "恢复日" : "训练日") : "";
    statusHtml = `
      <div class="workspace-scene-status" data-workspace-scene="${scene}" aria-label="工作台状态">
        <div class="workspace-scene-head">
          <p class="section-kicker">当前状态</p>
          <h3>${escapeHtml(todayLabel)}${todayType ? " · " + escapeHtml(todayType) : ""}</h3>
          <span>风险等级：${escapeHtml(statusLabel(statusSummary.risk_level))} · 完成度：${escapeHtml(statusSummary.completion_rate)}%</span>
        </div>
        <div class="workspace-scene-items">
          <div><span>风险状态</span><strong>${escapeHtml(statusLabel(statusSummary.risk_level))}</strong></div>
          <div><span>本周完成</span><strong>${escapeHtml(statusSummary.completion_rate)}%</strong></div>
          <div><span>漏反馈</span><strong>${escapeHtml(statusSummary.missed_feedback_count)} 天</strong></div>
          <div><span>建议</span><strong>${escapeHtml(statusSummary.next_training_recommendation || "按计划执行")}</strong></div>
        </div>
      </div>
    `;
  }
  container.innerHTML = statusHtml;
}

// ── Integration: Glossary Terms [product-evidence][P1] ──

function renderGlossaryTermsPanel(response) {
  const glossarySection = document.getElementById("glossaryTerms");
  const glossaryContent = document.getElementById("glossaryTermsContent");
  if (!glossarySection || !glossaryContent) return;

  const terms = getHmpGlossaryTerms(response);
  if (!terms.length) {
    glossarySection.hidden = true;
    return;
  }
  glossarySection.hidden = false;
  glossaryContent.innerHTML = terms.slice(0, 9).map((item) => `
    <article>
      <strong>${escapeHtml(item.term || item.name || item.id || "HMP 术语")}</strong>
      <p>${escapeHtml(item.short_definition || item.definition || item.description || "暂无定义。")}</p>
      <em>${escapeHtml(item.training_effect || item.training_impact || item.impact || "用于统一训练解释口径。")}</em>
    </article>
  `).join("");
}

// ── Integration: Adaptive Explanation after Feedback [product-explanation][P1] ──

function renderAdaptiveExplanationAfterFeedback(feedbackResult) {
  const container = document.getElementById("adaptiveExplanation");
  if (!container) return;

  if (!feedbackResult) {
    container.hidden = true;
    return;
  }

  container.hidden = false;
  const fb = feedbackResult.feedback || feedbackResult;
  const riskLevel = fb.risk_gate?.product_status || fb.risk_gate?.status || "normal";
  const riskClass = `adaptive-risk-${riskLevel}`;
  const adjustmentText = fb.rationale || fb.next_day_adjustment || fb.adaptive_adjustment?.rationale || "";
  const affectedCount = Array.isArray(feedbackResult.affected_events) ? feedbackResult.affected_events.length : 0;

  container.className = `adaptive-explanation-card ${riskClass}`;
  container.innerHTML = `
    <div class="adaptive-explanation-head">
      <div>
        <p class="section-kicker">计划调整</p>
        <h3>${riskLevel === "medical_referral" ? "需要专业评估" : riskLevel === "deescalate" ? "计划已调整" : "反馈已记录"}</h3>
      </div>
      <span class="adaptive-risk-badge">${escapeHtml(statusLabel(riskLevel))}</span>
    </div>
    <div class="adaptive-risk-banner">
      <p>${escapeHtml(adjustmentText || "系统已根据你的反馈评估当前状态。查看日历确认调整后的安排。")}</p>
    </div>
    ${affectedCount ? `
      <div class="adaptive-detail-list">
        <div><dt>影响范围</dt><dd>${escapeHtml(affectedCount)} 个后续训练日</dd></div>
        <div><dt>下次训练</dt><dd>${escapeHtml(fb.next_day_adjustment || "查看日历确认")}</dd></div>
      </div>
    ` : ""}
    <div class="adaptive-next-actions">
      <strong>建议下一步</strong>
      <ul>
        <li>查看更新后的训练日历确认调整内容。</li>
        <li>下次训练后及时记录反馈，持续评估恢复状态。</li>
        ${riskLevel === "deescalate" ? "<li>如连续两次降级，考虑减少本周训练次数。</li>" : ""}
      </ul>
    </div>
  `;
}

// ── Integration: NLP Profile Confirmation [product-profile][P1] ──

function showNlpProfileConfirmation(changes = []) {
  const container = document.getElementById("profileNlpConfirmation");
  if (!container || !changes.length) {
    if (container) container.hidden = true;
    return;
  }
  container.hidden = false;
  container.innerHTML = `
    <h4>检测到画像变更</h4>
    <p>系统从你的输入中提取到以下画像信息。请确认是否更新：</p>
    <ul class="nlp-field-changes">
      ${changes.map((change) => `
        <li>
          <span class="nlp-field-name">${escapeHtml(change.label || change.field)}</span>
          ${change.oldValue ? `<span class="nlp-old-value">${escapeHtml(change.oldValue)}</span>` : ""}
          <span class="nlp-new-value">${escapeHtml(change.newValue)}</span>
        </li>
      `).join("")}
    </ul>
    <div class="nlp-confirmation-actions">
      <button class="primary-button compact-button" data-nlp-confirm>确认更新</button>
      <button class="secondary-button compact-button" data-nlp-dismiss>忽略</button>
    </div>
  `;

  container.querySelector("[data-nlp-confirm]")?.addEventListener("click", () => {
    changes.forEach((change) => {
      const input = document.querySelector(`[data-profile-field="${change.draftKey}"]`) ||
                    document.querySelector(`[data-profile-editor-field="${change.field}"]`);
      if (input) input.value = change.newValue;
    });
    saveProfileDraft();
    container.hidden = true;
  });

  container.querySelector("[data-nlp-dismiss]")?.addEventListener("click", () => {
    container.hidden = true;
  });
}

// ── Integration: Feedback Detail Form Binding [product-feedback][P1] ──

function initFeedbackDetailForm(container) {
  if (!container) return;
  // Progressive step navigation
  container.querySelectorAll("[data-feedback-next]").forEach((button) => {
    button.addEventListener("click", () => {
      const currentStep = button.closest("[data-feedback-step]");
      const allSteps = Array.from(container.querySelectorAll("[data-feedback-step]"));
      const currentIndex = allSteps.indexOf(currentStep);
      if (currentIndex >= 0 && currentIndex < allSteps.length - 1) {
        currentStep.hidden = true;
        allSteps[currentIndex + 1].hidden = false;
        const progressLabel = container.querySelector("[data-feedback-progress]");
        if (progressLabel) progressLabel.textContent = `${currentIndex + 2}/${allSteps.length} 完成`;
        allSteps[currentIndex + 1].querySelector("input, select, textarea")?.focus();
      }
    });
  });

  container.querySelectorAll("[data-feedback-prev]").forEach((button) => {
    button.addEventListener("click", () => {
      const currentStep = button.closest("[data-feedback-step]");
      const allSteps = Array.from(container.querySelectorAll("[data-feedback-step]"));
      const currentIndex = allSteps.indexOf(currentStep);
      if (currentIndex > 0) {
        currentStep.hidden = true;
        allSteps[currentIndex - 1].hidden = false;
        const progressLabel = container.querySelector("[data-feedback-progress]");
        if (progressLabel) progressLabel.textContent = `${currentIndex}/${allSteps.length} 完成`;
      }
    });
  });

  // Quick preset buttons
  container.querySelectorAll("[data-feedback-quick]").forEach((radio) => {
    radio.addEventListener("change", () => {
      const presetKey = radio.value === "已完成" ? "feedback_done" : radio.value === "部分完成" ? "feedback_partial" : "feedback_skipped";
      const preset = FEEDBACK_QUICK_PRESETS[presetKey];
      if (preset && container.closest(".day-modal")) {
        applyFeedbackPreset(container.closest(".day-modal"), preset);
      }
    });
  });
}

// ── Integration: Feedback Result Hook ──

const _originalBuildFeedbackResultHtml = buildFeedbackResultHtml;
buildFeedbackResultHtml = function(payload, affectedDays) {
  const html = _originalBuildFeedbackResultHtml(payload, affectedDays);
  renderAdaptiveExplanationAfterFeedback(payload);
  return html;
};

async function bootstrap() {
  moveWorkspaceSectionsToDrawer();
  syncSideDrawerViewportState();
  resetPlanProgress();
  renderRunnerIdentityCard(profileDraftToApi(getProfileDraft()));
  updateQueryModeUi();
  await ping({ autoDetect: true });
  await Promise.allSettled([
    loadLlmOptions(),
    loadMeta(),
    loadProfileDraft(),
  ]);
  renderPlanHistory();
  updateWorkspaceSceneStatus();
}

bootstrap();
