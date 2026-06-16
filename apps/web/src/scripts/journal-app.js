const STORAGE_KEY = "journal-ink-state-v2";
const CURRENT_WEEK_IDX = 0;

const DEFAULT_PROFILE = {
  goal: "",
  raceDate: "",
  pb5k: "", pb10k: "", pbHalf: "", pbFull: "",
  trainingDays: [],
  longestRun: "",
  recentPace: "",
  kneeStatus: "",
  note: "",
};

const DEFAULT_WEEK_SETUP = {
  goal: "",
  availableDays: [],
  note: "",
};

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function mapLlmPlanToDynamicContent(weekPlan, weekKey) {
  const ZONE_BADGES = {
    "轻松跑": ["心率区间 2"],
    "恢复跑": ["心率区间 1", "轻松节奏"],
    "间歇跑": ["心率区间 4-5", "高强度间歇"],
    "摄氧量训练": ["心率区间 5", "摄氧量"],
    "长距离": ["心率区间 2-3", "耐力训练"],
    "节奏跑": ["心率区间 3-4", "乳酸阈值"],
    "无氧阈跑": ["心率区间 3-4", "无氧阈"],
    "有氧阈值训练": ["心率区间 3", "有氧阈值"],
    "马拉松配速跑": ["心率区间 3", "马拉松配速"],
    "渐进跑": ["心率区间 2-4", "渐进跑"],
    "法特莱克": ["心率区间 2-4", "速度游戏"],
    "坡道训练": ["心率区间 3-5", "坡道"],
    "短冲": ["心率区间 5", "短冲"],
    "休息": ["休息日"],
  };
  const result = {};
  for (const day of (weekPlan.days || [])) {
    if (!day.day) continue;
    const key = `${weekKey}-${day.day}`;
    const trainingType = day.training_type || "训练";
    const durationMatch = (day.main_set || "").match(/约?(\d+)\s*分钟/);
    const duration = durationMatch ? durationMatch[1] : "";
    const title = trainingType === "休息" ? "休息日"
      : duration ? `${trainingType} ${duration} 分钟` : trainingType;
    const paceMatch = (day.main_set || "").match(/配速\s*([\d:]+(?:[-–][\d:]+)?)\s*\/km/);
    const zoneBadges = ZONE_BADGES[trainingType] || ["训练"];
    const badges = paceMatch
      ? [zoneBadges[0], `配速 ${paceMatch[1]}/km`]
      : zoneBadges;
    const structure = [];
    if (day.warmup && day.warmup !== "无") structure.push({ label: "热身", caption: day.warmup });
    if (day.main_set) structure.push({ label: "主课", caption: day.main_set, isMain: true });
    if (day.cooldown && day.cooldown !== "无") structure.push({ label: "放松", caption: day.cooldown });
    result[key] = {
      title,
      badges,
      reason: day.notes || `${trainingType}，按计划执行。`,
      explanation: day.main_set || "按计划执行本次训练。",
      structure,
    };
  }
  return result;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = String(str ?? "");
  return div.innerHTML;
}

function nowText() {
  const date = new Date();
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function todayText() {
  return new Date().toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "numeric",
    day: "numeric",
  });
}

function weekdayText(dateValue) {
  if (!dateValue) return "";
  const days = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
  const date = new Date(dateValue);
  if (Number.isNaN(date.getTime())) return "";
  return days[date.getDay()];
}

// ── 自由周数计划：日期 + week-key 辅助函数 ──────────────────────────────
const WEEKDAY_TO_OFFSET = { 周一: 0, 周二: 1, 周三: 2, 周四: 3, 周五: 4, 周六: 5, 周日: 6 };

// 取 date 所在周的周一（getDay() 0=周日..6=周六）。
function startOfWeekMonday(date) {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  const dow = d.getDay(); // 0=Sun
  const diffToMonday = dow === 0 ? -6 : 1 - dow;
  d.setDate(d.getDate() + diffToMonday);
  return d;
}

function formatCnDate(date) {
  return `${date.getMonth() + 1} 月 ${date.getDate()} 日`;
}

// planStartMonday 偏移 weekOffset 周后的周一。
function weekMondayFor(planStartMonday, weekOffset) {
  const d = new Date(planStartMonday);
  d.setDate(d.getDate() + weekOffset * 7);
  return d;
}

// "M 月 D 日 - M 月 D 日"（周一..周日）。
function formatWeekRange(planStartMonday, weekOffset) {
  const monday = weekMondayFor(planStartMonday, weekOffset);
  const sunday = new Date(monday);
  sunday.setDate(sunday.getDate() + 6);
  return `${formatCnDate(monday)} - ${formatCnDate(sunday)}`;
}

// 某周某个工作日（如"周二"）对应的 "M 月 D 日"。
function formatDayDate(planStartMonday, weekOffset, weekdayName) {
  const monday = weekMondayFor(planStartMonday, weekOffset);
  const offset = WEEKDAY_TO_OFFSET[weekdayName] ?? 0;
  const d = new Date(monday);
  d.setDate(d.getDate() + offset);
  return formatCnDate(d);
}

// week-key 单一来源：保证 renderHome/initDay 的 `${week.key}-${day}` 查找
// 与 mapLlmPlanToDynamicContent 写入的 key 一致。
function weekKeyForIndex(idx) {
  return `week-${idx}`;
}

// 从比赛日推算计划周数，镜像后端 derive_plan_duration_weeks：
// max(1, ceil((race - today) / 7))，clamp [1, 26]，无法解析返回 null。
function derivePlanWeeksFromRaceDate(raceDate) {
  if (!raceDate) return null;
  const race = new Date(raceDate);
  if (Number.isNaN(race.getTime())) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  race.setHours(0, 0, 0, 0);
  const days = Math.round((race - today) / 86400000);
  if (days <= 0) return null;
  const weeks = Math.ceil(days / 7);
  return Math.max(1, Math.min(26, weeks));
}

function createBaseState() {
  return {
    profile: clone(DEFAULT_PROFILE),
    weekSetup: clone(DEFAULT_WEEK_SETUP),
    events: [],
    feedbacks: [],
    versions: [],
    currentVersionId: null,
    selectedWeekIndex: 0,
    dynamicContent: {},
    lastWeekPlans: [],
  };
}

function normalizeState(partial) {
  const base = createBaseState();
  const mergedProfile = { ...base.profile, ...(partial?.profile || {}) };
  // migration: old saves had `level`, new uses pb fields
  if (mergedProfile.level) delete mergedProfile.level;
  if (mergedProfile.pb !== undefined) {
    if (!mergedProfile.pb5k && !mergedProfile.pb10k && !mergedProfile.pbHalf) {
      mergedProfile.pb5k = ""; mergedProfile.pb10k = ""; mergedProfile.pbHalf = ""; mergedProfile.pbFull = "";
    }
    delete mergedProfile.pb;
  }
  const state = {
    ...base,
    ...partial,
    profile: mergedProfile,
    weekSetup: { ...base.weekSetup, ...(partial?.weekSetup || {}) },
    events: Array.isArray(partial?.events) ? partial.events : base.events,
    feedbacks: Array.isArray(partial?.feedbacks) ? partial.feedbacks : base.feedbacks,
    versions: Array.isArray(partial?.versions) ? partial.versions : base.versions,
    currentVersionId: partial?.currentVersionId || base.currentVersionId,
    selectedWeekIndex: typeof partial?.selectedWeekIndex === "number"
      ? partial.selectedWeekIndex
      : 0,
  };
  if (state.versions.length && !state.versions.some((v) => v.id === state.currentVersionId)) {
    state.currentVersionId = state.versions[0].id;
  }
  // clamp selectedWeekIndex to current version's actual week count
  const _curVer = state.versions.find((v) => v.id === state.currentVersionId) || state.versions[0];
  const _maxIdx = (_curVer?.weeks?.length || 1) - 1;
  if (state.selectedWeekIndex > _maxIdx) state.selectedWeekIndex = Math.max(0, _maxIdx);
  // carry lastWeekPlans across sessions
  state.lastWeekPlans = Array.isArray(partial?.lastWeekPlans) ? partial.lastWeekPlans : base.lastWeekPlans;
  return state;
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return createBaseState();
    return normalizeState(JSON.parse(raw));
  } catch {
    return createBaseState();
  }
}

function saveState(state) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  return state;
}

function currentVersion(state) {
  if (!state.versions || !state.versions.length) return null;
  return state.versions.find((version) => version.id === state.currentVersionId) || state.versions[0];
}

// 对单个课程 card 应用当前周装饰（不可训练日 mute、临时事件注入、降级）。
// ctx = { availableDays: Set, eventByDay: Map, shouldDowngrade: bool }
function applyCurrentWeekDecorations(session, ctx) {
  const { availableDays, eventByDay, shouldDowngrade } = ctx;
  const next = { ...session };
  if (!availableDays.has(next.day)) {
    next.title = "机动休息";
    next.meta = "本周不排课";
    next.muted = true;
  }
  const event = eventByDay.get(next.day);
  if (event) {
    next.title = event.title ? `${event.type} · ${event.title}` : `${event.type}`;
    next.meta = event.replace ? `替换 ${event.replace}` : (event.note || `原${next.title}顺延`);
    next.event = true;
    next.href = "/event";
  }
  if (shouldDowngrade && !next.completed && !next.event && !next.muted) {
    const downgradeMap = {
      "间歇跑": "恢复跑 30 分钟",
      "长跑": "轻松跑 35 分钟",
      "节奏跑": "轻松跑 30 分钟",
    };
    for (const [keyword, replacement] of Object.entries(downgradeMap)) {
      if (next.title.includes(keyword)) {
        next.meta = `降级 ← ${next.title}`;
        next.title = replacement;
        break;
      }
    }
  }
  return next;
}

function buildWeeks(profile, weekSetup, events, options) {
  return [];
}

// 根据 LLM 生成的 weekPlans 构建 N 个生成周（week-0 起始）。
function buildDynamicWeeks(profile, weekSetup, events, weekPlans, options) {
  const planStartMonday = startOfWeekMonday(new Date());
  const availableDays = new Set((weekSetup.availableDays || profile.trainingDays || []).map((day) => String(day).trim()));
  const eventByDay = new Map();
  events.forEach((event) => {
    if (event?.day) eventByDay.set(String(event.day).trim(), event);
  });
  const ctx = { availableDays, eventByDay, shouldDowngrade: options?.downgrade === true };

  return weekPlans.map((wp, gi) => {
    const key = weekKeyForIndex(gi);
    const isCurrentWeek = gi === 0;

    const dynMap = mapLlmPlanToDynamicContent(wp, key);

    const days = (wp.days || []).filter((d) => d?.day && d.session_type && d.session_type !== "rest");
    const sessions = days.map((d) => {
      const dcKey = `${key}-${d.day}`;
      const dc = dynMap[dcKey] || {};
      const card = {
        day: d.day,
        title: dc.title || d.session_type || "训练",
        meta: dc.badges ? dc.badges.join(" · ") : "",
        date: formatDayDate(planStartMonday, gi, d.day),
      };
      return isCurrentWeek ? applyCurrentWeekDecorations(card, ctx) : card;
    });

    const week = {
      key,
      label: isCurrentWeek ? "本周" : `第 ${gi + 1} 周`,
      phase: wp.phase || "",
      range: formatWeekRange(planStartMonday, gi),
      goal: isCurrentWeek ? (weekSetup.goal || wp.week_goal || "") : (wp.week_goal || ""),
      sessions,
    };
    if (isCurrentWeek && events.length) {
      week.eventSummary = `${events.length} 个临时事件`;
    }
    return week;
  });
}

function buildPlanVersion(state, note, options) {
  const weekPlans = options?.weekPlans;
  const weeks = weekPlans?.length
    ? buildDynamicWeeks(state.profile, state.weekSetup, state.events, weekPlans, options)
    : buildWeeks(state.profile, state.weekSetup, state.events, options);
  const version = {
    id: `v-${Date.now()}`,
    name: `第 ${state.versions.length + 1} 版`,
    createdAt: nowText(),
    note,
    weeks,
    dynamic: Boolean(weekPlans?.length),
  };
  state.versions = [version, ...state.versions.filter((item) => item.id !== version.id)].slice(0, 8);
  state.currentVersionId = version.id;
  return version;
}

function setCheckedValues(container, name, values) {
  const normalized = new Set((values || []).map((value) => String(value).trim()));
  container.querySelectorAll(`input[name="${name}"]`).forEach((input) => {
    input.checked = normalized.has(String(input.value).trim());
  });
}

function readCheckedValues(container, name) {
  return Array.from(container.querySelectorAll(`input[name="${name}"]:checked`)).map((input) => input.value);
}

function renderProfileSummary(state) {
  const map = {
    goal: state.profile.goal,
    raceDate: state.profile.raceDate,
    pb5k: state.profile.pb5k || "—",
    pb10k: state.profile.pb10k || "—",
    pbHalf: state.profile.pbHalf || "—",
    pbFull: state.profile.pbFull || "—",
    trainingDays: state.profile.trainingDays.join(" / "),
    longestRun: state.profile.longestRun,
    recentPace: `${state.profile.recentPace}`,
    kneeStatus: state.profile.kneeStatus,
  };
  document.querySelectorAll("[data-profile-value]").forEach((node) => {
    const key = node.getAttribute("data-profile-value");
    if (!key || !(key in map)) return;
    node.textContent = map[key];
  });
  const note = document.querySelector("[data-profile-note]");
  if (note) note.textContent = state.profile.note || "临时比赛优先顺延。";
}

function renderHome(state) {
  const version = currentVersion(state);
  const hasplan = version != null && Array.isArray(version.weeks) && version.weeks.some((w) => w.sessions.length > 0);
  const currentWeek = hasplan ? version.weeks[CURRENT_WEEK_IDX] : null;

  const label = document.querySelector("[data-home-version]");
  if (label) label.textContent = version ? `${version.name} · ${version.note}` : "";
  const goal = document.querySelector("[data-home-goal]");
  if (goal) goal.textContent = currentWeek?.goal || "";

  const todayCard = document.querySelector("[data-home-today]");
  const progressCard = document.querySelector("[data-home-progress]");
  const emptyCard = document.querySelector("[data-home-empty]");
  if (todayCard) todayCard.hidden = !hasplan;
  if (progressCard) progressCard.hidden = !hasplan;
  if (emptyCard) emptyCard.hidden = hasplan;

  if (!currentWeek || !hasplan) return;

  const sessions = currentWeek.sessions || [];
  const todaySession = sessions.find((s) => s.current) || sessions.find((s) => !s.completed && !s.muted) || sessions[0];

  if (todaySession) {
    const kicker = document.querySelector("[data-today-kicker]");
    if (kicker) kicker.textContent = `${todaySession.day} · ${todaySession.date}`;
    const title = document.querySelector("[data-today-title]");
    if (title) title.textContent = todaySession.title;

    const metaKey = `${currentWeek.key}-${todaySession.day}`;
    const dynSession = state.dynamicContent?.[metaKey];

    const badges = document.querySelector("[data-today-badges]");
    if (badges) {
      const badgeMap = {
        "轻松跑": ["心率区间 2", `配速 ${state.profile.recentPace || "6'48\"/km"}`],
        "恢复跑": ["心率区间 1", "轻松节奏"],
        "间歇跑": ["心率区间 4-5", "高强度"],
        "长跑": ["心率区间 2-3", "耐力训练"],
        "节奏跑": ["心率区间 3-4", "乳酸阈值"],
      };
      const labels = dynSession?.badges
        || Object.entries(badgeMap).find(([k]) => todaySession.title.includes(k))?.[1]
        || ["训练"];
      badges.innerHTML = labels.map((l) => `<span class="journal-badge">${escapeHtml(l)}</span>`).join("");
    }

    const reason = document.querySelector("[data-today-reason]");
    if (reason) {
      reason.textContent = dynSession?.reason || "按计划执行本次训练。";
    }

    const todayIdx = sessions.indexOf(todaySession);
    const dayHref = `/day?w=${CURRENT_WEEK_IDX}&i=${todayIdx >= 0 ? todayIdx : 0}`;
    document.querySelectorAll("[data-today-day-link]").forEach((el) => { el.href = dayHref; });

    const risk = document.querySelector("[data-today-risk]");
    if (risk) {
      const knee = state.profile.kneeStatus;
      if (knee && knee !== "无不适" && knee !== "正常" && knee !== "无") {
        risk.hidden = false;
        risk.textContent = `膝部${knee}，强度已下调。`;
      } else {
        risk.hidden = true;
      }
    }
  }

  const completed = sessions.filter((s) => s.completed).length;
  const total = sessions.filter((s) => !s.muted).length;
  const remaining = total - completed;

  const progressText = document.querySelector("[data-progress-text]");
  if (progressText) {
    if (remaining <= 0) progressText.textContent = "本周目标完成！";
    else if (remaining === 1) progressText.textContent = "再练一次就满了";
    else progressText.textContent = `还有 ${remaining} 次训练`;
  }

  const dots = document.querySelector("[data-progress-dots]");
  if (dots) {
    dots.innerHTML = sessions
      .filter((s) => !s.muted)
      .map((s) => {
        if (s.completed) return `<span class="journal-progress-dot is-done"></span>`;
        if (s.current) return `<span class="journal-progress-dot is-current"></span>`;
        return `<span class="journal-progress-dot"></span>`;
      })
      .join("");
  }

  const badge = document.querySelector("[data-progress-badge]");
  if (badge) badge.textContent = `${completed} / ${total} 次训练`;

  const homeSessionList = document.querySelector("[data-home-session-list]");
  if (homeSessionList) {
    homeSessionList.innerHTML = sessions.map((s, i) => {
      const href = `/day?w=${CURRENT_WEEK_IDX}&i=${i}`;
      const cls = [
        "journal-session-card",
        s.completed && "is-complete",
        s.current && "is-current",
        s.event && "is-event",
        s.muted && "is-muted",
      ].filter(Boolean).join(" ");
      return `<a class="${cls}" href="${href}">` +
        `<span>${escapeHtml(s.date)} ${escapeHtml(s.day)}</span>` +
        `<strong>${escapeHtml(s.title)}</strong>` +
        `<div class="journal-meta">${escapeHtml(s.meta || "")}</div>` +
        `</a>`;
    }).join("");
  }
}

function estimateSessionLoad(title) {
  const minMatch = title.match(/(\d+)\s*分钟/);
  let duration;
  if (minMatch) {
    duration = parseInt(minMatch[1]);
  } else {
    const intervalMatch = title.match(/(\d+)\s*[xX×]\s*\d+/);
    duration = intervalMatch ? Math.min(parseInt(intervalMatch[1]) * 4, 60) : 30;
  }
  const factors = { "间歇跑": 1.2, "节奏跑": 0.9, "长跑": 0.7, "轻松跑": 0.55, "恢复跑": 0.4 };
  const matched = Object.entries(factors).find(([k]) => title.includes(k));
  return Math.round(duration * (matched ? matched[1] : 0.6));
}

function renderCalendar(state) {
  const root = document.querySelector("[data-calendar-root]");
  if (!root) return;
  const version = currentVersion(state);
  const weeks = version?.weeks || [];

  const versionLabel = root.querySelector("[data-calendar-version]");
  if (versionLabel) versionLabel.textContent = version ? `${version.name} · ${version.note}` : "还没有计划";

  const eventCount = root.querySelector("[data-calendar-event-count]");
  if (eventCount) {
    if (!state.events.length) {
      eventCount.hidden = true;
    } else {
      const names = state.events.map((e) => `${e.title || e.type}（${e.day || ""}）`).join("、");
      eventCount.textContent = `临时事件：${names}`;
      eventCount.hidden = false;
    }
  }

  const prevBtn = root.querySelector("[data-week-prev]");
  const nextBtn = root.querySelector("[data-week-next]");
  const phaseLabel = root.querySelector("[data-week-phase]");
  const weekLabel = root.querySelector("[data-week-label]");
  const weekRange = root.querySelector("[data-week-range]");
  const goalNode = root.querySelector("[data-week-goal]");
  const sessionList = root.querySelector("[data-session-list]");
  const summaryNode = root.querySelector("[data-week-summary]");
  const loadNode = root.querySelector("[data-week-load]");

  function showWeek(idx) {
    const clamped = Math.max(0, Math.min(weeks.length - 1, idx));
    state.selectedWeekIndex = clamped;
    saveState(state);

    const week = weeks[clamped];
    if (!week) return;

    if (phaseLabel) phaseLabel.textContent = week.phase;
    if (weekLabel) weekLabel.textContent = week.label;
    if (weekRange) weekRange.textContent = week.range;
    if (goalNode) goalNode.textContent = week.goal;

    if (prevBtn) prevBtn.disabled = clamped <= 0;
    if (nextBtn) nextBtn.disabled = clamped >= weeks.length - 1;

    if (sessionList) {
      sessionList.innerHTML = week.sessions
        .map((s, i) => {
          const href = s.event ? "/event" : `/day?w=${clamped}&i=${i}`;
          const cls = [
            "journal-session-card",
            s.completed && "is-complete",
            s.current && "is-current",
            s.event && "is-event",
            s.muted && "is-muted",
          ].filter(Boolean).join(" ");
          return `<a class="${cls}" href="${href}">` +
            `<span>${escapeHtml(s.date)} ${escapeHtml(s.day)}</span>` +
            `<strong>${escapeHtml(s.title)}</strong>` +
            `<div class="journal-meta">${escapeHtml(s.meta || "")}</div>` +
            `</a>`;
        })
        .join("");
    }

    if (summaryNode) summaryNode.textContent = `${week.sessions.filter((s) => !s.muted).length} 个安排`;

    if (loadNode) {
      const active = week.sessions.filter((s) => !s.muted);
      const totalLoad = active.reduce((sum, s) => sum + estimateSessionLoad(s.title), 0);
      if (active.length > 0) {
        loadNode.textContent = `预期负荷：约 ${totalLoad} AU`;
        loadNode.hidden = false;
      } else {
        loadNode.hidden = true;
      }
    }
  }

  if (prevBtn) prevBtn.addEventListener("click", () => showWeek(state.selectedWeekIndex - 1));
  if (nextBtn) nextBtn.addEventListener("click", () => showWeek(state.selectedWeekIndex + 1));

  const initialIdx = typeof state.selectedWeekIndex === "number" ? state.selectedWeekIndex : CURRENT_WEEK_IDX;
  showWeek(initialIdx);
}

function renderHistory(state) {
  const list = document.querySelector("[data-version-list]");
  if (!list) return;
  const currentId = state.currentVersionId;
  list.innerHTML = state.versions
    .map((version) => {
      const active = version.id === currentId ? " is-active" : "";
      return `
        <article class="journal-tile journal-version-card${active}">
          <span>${escapeHtml(version.createdAt)}</span>
          <strong>${escapeHtml(version.name)}</strong>
          <div class="journal-footnote">${escapeHtml(version.note)}</div>
          <div class="journal-action-row" style="margin-top: 10px;">
            <button class="journal-btn" type="button" data-restore-version="${escapeHtml(version.id)}">恢复这个版本</button>
          </div>
        </article>
      `;
    })
    .join("");
  list.querySelectorAll("[data-restore-version]").forEach((button) => {
    button.addEventListener("click", () => {
      const versionId = button.getAttribute("data-restore-version");
      const next = loadState();
      const version = next.versions.find((item) => item.id === versionId);
      if (!version) return;
      next.currentVersionId = version.id;
      next.selectedWeekIndex = CURRENT_WEEK_IDX;
      saveState(next);
      window.location.href = "/calendar";
    });
  });
}

function renderEventList(state) {
  const list = document.querySelector("[data-event-list]");
  if (!list) return;
  if (!state.events.length) {
    list.innerHTML = `<div class="journal-empty"><strong>还没有临时事件</strong><span>临时比赛、出差、请假都从这里插入。</span></div>`;
    return;
  }
  list.innerHTML = state.events
    .map((event) => `
      <article class="journal-tile journal-event-card">
        <span>${escapeHtml(event.type)}</span>
        <strong>${escapeHtml(event.title)}</strong>
        <div class="journal-footnote">${escapeHtml(event.date || "")} ${escapeHtml(event.day || "")}</div>
        <div class="journal-footnote">${escapeHtml(event.note || "")}</div>
      </article>
    `)
    .join("");
}

function initProfileEdit(state) {
  const form = document.querySelector("#profileEditorForm");
  if (!form) return;
  form.goal.value = state.profile.goal;
  form.raceDate.value = state.profile.raceDate;
  form.pb5k.value = state.profile.pb5k || "";
  form.pb10k.value = state.profile.pb10k || "";
  form.pbHalf.value = state.profile.pbHalf || "";
  form.pbFull.value = state.profile.pbFull || "";
  form.longestRun.value = state.profile.longestRun;
  form.recentPace.value = state.profile.recentPace;
  form.kneeStatus.value = state.profile.kneeStatus;
  form.note.value = state.profile.note;
  setCheckedValues(form, "trainingDays", state.profile.trainingDays);

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const next = loadState();
    next.profile = {
      goal: form.goal.value.trim(),
      raceDate: form.raceDate.value,
      pb5k: form.pb5k.value.trim(),
      pb10k: form.pb10k.value.trim(),
      pbHalf: form.pbHalf.value.trim(),
      pbFull: form.pbFull.value.trim(),
      trainingDays: readCheckedValues(form, "trainingDays"),
      longestRun: form.longestRun.value.trim(),
      recentPace: form.recentPace.value.trim(),
      kneeStatus: form.kneeStatus.value.trim(),
      note: form.note.value.trim(),
    };
    next.weekSetup.availableDays = next.profile.trainingDays;
    buildPlanVersion(next, "基础画像已更新");
    saveState(next);
    window.location.href = "/profile";
  });
}

function initWeekSetup(state) {
  const form = document.querySelector("#weekSetupForm");
  if (!form) return;
  form.weekGoal.value = state.weekSetup.goal;
  form.note.value = state.weekSetup.note;
  setCheckedValues(form, "availableDays", state.weekSetup.availableDays);

  const api = window.__apiClient;
  let backendOnline = false;
  if (api) api.detectApiBase().then((ok) => { backendOnline = ok; }).catch(() => {});

  const nodeProgress = document.querySelector("[data-plan-node-progress]");
  const nodeTrack = document.querySelector("[data-plan-node-track]");

  function pushNode(label, isRetry) {
    if (!nodeTrack) return;
    const active = nodeTrack.querySelector(".is-active");
    if (active) active.className = "journal-node is-done";
    const chip = document.createElement("span");
    chip.className = isRetry ? "journal-node is-active is-retry" : "journal-node is-active";
    chip.textContent = label;
    nodeTrack.appendChild(chip);
    window.scrollTo(0, document.body.scrollHeight);
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const next = loadState();
    next.weekSetup = {
      goal: form.weekGoal.value.trim(),
      availableDays: readCheckedValues(form, "availableDays"),
      note: form.note.value.trim(),
    };

    let llmResult = null;
    if (backendOnline && api) {
      const submitBtn = form.querySelector("[type=submit]");
      if (submitBtn) submitBtn.disabled = true;
      // 清空旧内容，避免重复
      if (nodeTrack) nodeTrack.innerHTML = "";
      if (nodeProgress) nodeProgress.hidden = false;
      pushNode("规划中");

      const days = (next.weekSetup.availableDays || []).join("、") || "未指定";
      const goal = next.weekSetup.goal || "完成本周训练";
      const pbHalf = next.profile?.pbHalf ? `\n半马PB：${next.profile.pbHalf}` : "";
      const raceDate = next.profile?.raceDate || "";
      const planWeeks = derivePlanWeeksFromRaceDate(raceDate);
      const weeksLine = planWeeks ? `\n计划周期 ${planWeeks} 周` : "";
      const raceLine = raceDate ? `\n目标比赛日期：${raceDate}` : "";
      const query = `生成${goal}，可训练日：${days}${pbHalf}${weeksLine}${raceLine}`;

      try {
        llmResult = await api.streamQueryPayload(query, {
          responseMode: "full",
          mode: "subagent",
          onNode: (evt) => {
            const label = NODE_LABELS[evt.node] || evt.node;
            pushNode(label, evt.node === "supervisor");
          },
        });
      } catch (_) { /* 后端失败也继续本地生成 */ }

      // 最后一个激活节点标为完成
      if (nodeTrack) {
        const active = nodeTrack.querySelector(".is-active");
        if (active) active.className = "journal-node is-done";
      }
    }

    // 全量映射 LLM 所有周到 dynamicContent，构建 N 周计划版本
    // DEBUG: log structured_training_plan for E2E diagnosis
    console.log("[week-setup] llmResult keys:", llmResult ? Object.keys(llmResult) : "null");
    console.log("[week-setup] structured_training_plan:", JSON.stringify(llmResult?.structured_training_plan)?.slice(0, 500));
    if (llmResult?.structured_training_plan) {
      const weekPlans = llmResult.structured_training_plan.week_plans || [];
      console.log("[week-setup] week_plans length:", weekPlans.length, "first wp keys:", weekPlans[0] ? Object.keys(weekPlans[0]) : "empty");
      if (weekPlans.length) {
        let dyn = { ...(next.dynamicContent || {}) };
        weekPlans.forEach((wp, gi) => {
          const key = weekKeyForIndex(gi);
          dyn = { ...dyn, ...mapLlmPlanToDynamicContent(wp, key) };
        });
        next.dynamicContent = dyn;
        next.lastWeekPlans = weekPlans;
        buildPlanVersion(next, "本周设置已更新", { weekPlans });
      } else {
        buildPlanVersion(next, "本周设置已更新");
      }
    } else {
      buildPlanVersion(next, "本周设置已更新");
    }
    next.selectedWeekIndex = CURRENT_WEEK_IDX;
    saveState(next);
    window.location.href = "/calendar";
  });
}

function initEventForm(state) {
  const form = document.querySelector("#eventForm");
  if (!form) return;
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const next = loadState();
    const payload = {
      id: `evt-${Date.now()}`,
      type: form.eventType.value,
      title: form.eventTitle.value.trim(),
      day: weekdayText(form.eventDate.value),
      date: form.eventDate.value,
      replace: form.eventReplace.value.trim(),
      note: form.eventNote.value.trim(),
      createdAt: nowText(),
    };
    next.events = [payload, ...next.events];
    buildPlanVersion(next, "插入临时事件后重排", { weekPlans: next.lastWeekPlans });
    saveState(next);
    window.location.href = "/calendar";
  });
  const list = document.querySelector("[data-event-list]");
  if (list) renderEventList(state);
}

function initFeedbackForm() {
  const form = document.querySelector("#feedbackForm");
  if (!form) return;
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const submitter = event.submitter;
    const action = submitter?.value || "save";

    const next = loadState();
    const completion = form.querySelector('input[name="completion"]:checked')?.value || "未开始";
    const bodyParts = readCheckedValues(form, "bodyParts");
    const bodyText = bodyParts.length ? bodyParts.join("、") : "无不适";
    const fatigue = Number(form.fatigue.value);
    const actualVolume = (form.actualVolume?.value || "").trim();
    const avgHr = (form.avgHr?.value || "").trim();
    const temperature = (form.temperature?.value || "").trim();

    const feedback = {
      id: `fb-${Date.now()}`,
      date: todayText(),
      completion,
      fatigue: String(fatigue),
      body: bodyText,
      actualVolume,
      avgHr,
      temperature,
      note: form.notes.value.trim(),
    };
    next.feedbacks = [feedback, ...next.feedbacks].slice(0, 8);
    const needsRebuild = completion !== "已完成" || fatigue >= 4 || bodyParts.length > 0;
    if (needsRebuild) {
      const shouldDowngrade = fatigue >= 4 || completion === "未完成";
      const reason = shouldDowngrade ? "疲劳/未完成，已降级下次训练" : "依据今日反馈微调";
      buildPlanVersion(next, reason, { downgrade: shouldDowngrade, weekPlans: next.lastWeekPlans });
    }
    saveState(next);

    if (action === "analyze") {
      // 构建自然语言负荷分析查询，发给 adaptive_coach
      const version = currentVersion(next);
      const currentWeek = version?.weeks?.[CURRENT_WEEK_IDX];
      const todaySession = (currentWeek?.sessions || []).find((s) => s.current) || (currentWeek?.sessions || [])[0];
      const sessionName = todaySession?.title || "今日训练";

      const parts = [`今日反馈：${sessionName}`];
      parts.push(`完成情况：${completion}`);
      if (actualVolume) parts.push(`实际完成量：${actualVolume}`);
      if (avgHr) parts.push(`平均心率：${avgHr} bpm`);
      parts.push(`疲劳度：${fatigue}/5`);
      if (bodyParts.length) parts.push(`不适部位：${bodyText}`);
      if (feedback.note) parts.push(`备注：${feedback.note}`);
      parts.push("请帮我估算今日实际训练负荷，并给出下次训练是否需要调整的建议。");

      const query = parts.join("，");
      window.location.href = `/dialog?q=${encodeURIComponent(query)}`;
    } else {
      window.location.href = "/";
    }
  });
}

const NODE_LABELS = {
  security_gate: "安全检查",
  router: "路由分析",
  profiler: "画像同步",
  entity_extraction: "实体提取",
  wiki_search: "知识检索",
  context_fanout: "文档分发",
  evidence_retriever: "证据检索",
  crag_corrector: "检索纠错",
  conditioning_constraints: "约束校验",
  coach: "教练分析",
  therapist: "康复建议",
  nutritionist: "营养建议",
  supervisor: "审核打回·重排",
  auditor: "质量审核",
  formatter: "整理回复",
  guided_questions: "生成追问",
  planner: "制定计划",
  executor: "执行计划",
  research_analyst: "深度研究",
  adaptive_coach: "动态调整",
  missing_info_handler: "补充信息",
};

function initDialog(state) {
  const thread = document.querySelector("#dialogThread");
  const input = document.querySelector("#dialogInput");
  const send = document.querySelector("#dialogSend");
  if (!thread || !input || !send) return;

  const api = window.__apiClient;
  let backendOnline = false;
  let busy = false;

  if (api) {
    api.detectApiBase().then((ok) => { backendOnline = ok; }).catch(() => {});
  }

  // 聊天历史持久化：存 {role, text} 数组，AI 存原始 markdown 文本
  const CHAT_KEY = "journal-dialog-history-v1";
  const MAX_HISTORY = 40;

  function loadHistory() {
    try { return JSON.parse(localStorage.getItem(CHAT_KEY) || "[]"); } catch { return []; }
  }

  function saveHistory(history) {
    try { localStorage.setItem(CHAT_KEY, JSON.stringify(history.slice(-MAX_HISTORY))); } catch {}
  }

  // 将历史列表渲染到 thread（清空后重建）
  function restoreThread(history) {
    thread.innerHTML = "";
    history.forEach(({ role, text }) => {
      if (role === "user") {
        const row = document.createElement("div");
        row.className = "journal-chat-row user";
        row.innerHTML = `<div class="journal-chat-bubble">${escapeHtml(text)}</div>`;
        thread.appendChild(row);
      } else {
        const row = document.createElement("div");
        row.className = "journal-chat-row ai";
        row.innerHTML = `<div class="journal-chat-bubble">${renderMarkdown(text)}</div>`;
        thread.appendChild(row);
      }
    });
    // 推迟到下一帧再滚动，否则 innerHTML 未完成布局时 scrollHeight 为 0
    requestAnimationFrame(() => {
      const saved = parseInt(localStorage.getItem("journal-dialog-scroll-v1") || "-1", 10);
      if (saved >= 0) window.scrollTo(0, saved);
      else window.scrollTo(0, document.body.scrollHeight);
    });
  }

  // 滚动时持久化位置（页面级 window scroll）
  window.addEventListener("scroll", () => {
    try { localStorage.setItem("journal-dialog-scroll-v1", String(window.scrollY)); } catch {}
  }, { passive: true });

  let chatHistory = loadHistory();
  restoreThread(chatHistory);

  const localReply = (text) => {
    if (/比赛|出差|请假|没空|周四/.test(text)) {
      return { text: "先插入临时事件，再重新生成本周计划。", action: { label: "去插入事件", href: "/event" } };
    }
    if (/重排|重新生成|本周/.test(text)) {
      return { text: "先打开本周设置，确认训练日和强度，再生成新版本。", action: { label: "去本周设置", href: "/week-setup" } };
    }
    if (/画像|我的情况|目标|比赛日期/.test(text)) {
      return { text: "先补基础画像，再回到计划页生成。", action: { label: "编辑画像", href: "/profile-edit" } };
    }
    if (/反馈|疲劳|疼|膝/.test(text)) {
      return { text: "先记录今日反馈，再决定下一版是否降量。", action: { label: "去今日反馈", href: "/feedback" } };
    }
    return { text: "可以问本周怎么排、临时比赛怎么插、反馈后怎么改。", action: { label: "看版本历史", href: "/history" } };
  };

  function appendUser(text) {
    chatHistory.push({ role: "user", text });
    saveHistory(chatHistory);
    const row = document.createElement("div");
    row.className = "journal-chat-row user";
    row.innerHTML = `<div class="journal-chat-bubble">${escapeHtml(text)}</div>`;
    thread.appendChild(row);
    window.scrollTo(0, document.body.scrollHeight);
    try { localStorage.removeItem("journal-dialog-scroll-v1"); } catch {}
  }

  // appendAi 渲染 html，saveMarkdown 存持久化（原始 markdown 文本）
  function appendAi(html, saveMarkdown) {
    if (saveMarkdown !== undefined) {
      chatHistory.push({ role: "ai", text: saveMarkdown });
      saveHistory(chatHistory);
    }
    const row = document.createElement("div");
    row.className = "journal-chat-row ai";
    row.innerHTML = `<div class="journal-chat-bubble">${html}</div>`;
    thread.appendChild(row);
    window.scrollTo(0, document.body.scrollHeight);
    return row;
  }

  function appendLoading() {
    const row = document.createElement("div");
    row.className = "journal-chat-row ai";
    row.innerHTML = `<div class="journal-chat-bubble"><div class="journal-node-track" data-node-track></div></div>`;
    thread.appendChild(row);
    // 初始激活节点
    const track = row.querySelector("[data-node-track]");
    const initial = document.createElement("span");
    initial.className = "journal-node is-active";
    initial.textContent = "分析中";
    track.appendChild(initial);
    window.scrollTo(0, document.body.scrollHeight);
    return row;
  }

  // 轻量 markdown → HTML：仅支持标题/加粗/列表/表格/引用标记，所有文本先转义防 XSS。
  function renderInline(text) {
    let s = escapeHtml(text);
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/\[(\d+)\]/g, '<sup class="journal-cite">[$1]</sup>');
    return s;
  }

  function renderMarkdown(src) {
    const lines = String(src || "").split("\n");
    const out = [];
    let listOpen = false;
    let tableRows = [];

    const flushList = () => { if (listOpen) { out.push("</ul>"); listOpen = false; } };
    const flushTable = () => {
      if (!tableRows.length) return;
      const cells = tableRows.map((r) =>
        r.replace(/^\||\|$/g, "").split("|").map((c) => c.trim())
      );
      const isSep = (row) => row.every((c) => /^:?-{2,}:?$/.test(c));
      let html = '<div class="journal-md-table-wrap"><table class="journal-md-table">';
      cells.forEach((row, i) => {
        if (isSep(row)) return;
        const tag = i === 0 ? "th" : "td";
        html += "<tr>" + row.map((c) => `<${tag}>${renderInline(c)}</${tag}>`).join("") + "</tr>";
      });
      html += "</table></div>";
      out.push(html);
      tableRows = [];
    };

    for (const raw of lines) {
      const line = raw.trimEnd();
      if (/^\s*\|.*\|\s*$/.test(line)) { flushList(); tableRows.push(line.trim()); continue; }
      flushTable();
      const h = line.match(/^(#{1,4})\s+(.*)$/);
      if (h) { flushList(); out.push(`<div class="journal-md-h${h[1].length}">${renderInline(h[2])}</div>`); continue; }
      const li = line.match(/^\s*[-*]\s+(.*)$/);
      if (li) { if (!listOpen) { out.push('<ul class="journal-md-list">'); listOpen = true; } out.push(`<li>${renderInline(li[1])}</li>`); continue; }
      if (/^\s*---+\s*$/.test(line)) { flushList(); out.push('<div class="journal-md-hr"></div>'); continue; }
      if (!line.trim()) { flushList(); continue; }
      flushList();
      out.push(`<p class="journal-md-p">${renderInline(line)}</p>`);
    }
    flushList();
    flushTable();
    return out.join("");
  }

  function renderApiResponse(payload) {
    const questions = payload.guided_questions || [];
    let html = renderMarkdown(payload.report || "暂无回复");
    if (questions.length) {
      html += `<div class="journal-chip-row" style="margin-top:12px;">`;
      questions.forEach((q) => {
        html += `<button type="button" class="journal-badge is-action" data-suggest>${escapeHtml(q)}</button>`;
      });
      html += `</div>`;
    }
    return html;
  }

  function renderLocalResponse(r) {
    let html = escapeHtml(r.text);
    html += `<div class="journal-chat-link"><a href="${escapeHtml(r.action.href)}">${escapeHtml(r.action.label)}</a></div>`;
    html += `<div class="journal-footnote" style="margin-top:8px;opacity:0.5;">离线模式</div>`;
    return html;
  }

  function bindSuggestButtons() {
    document.querySelectorAll("[data-suggest]").forEach((btn) => {
      if (btn._bound) return;
      btn._bound = true;
      btn.addEventListener("click", () => {
        input.value = btn.textContent.trim();
        handleSend();
      });
    });
  }

  async function handleSend() {
    const value = input.value.trim();
    if (!value || busy) return;
    input.value = "";
    appendUser(value);

    if (backendOnline && api) {
      busy = true;
      send.disabled = true;
      const loadingRow = appendLoading();
      const controller = new AbortController();
      try {
        const payload = await api.streamQueryPayload(value, {
          responseMode: "full",
          controller,
          onNode: (evt) => {
            const label = NODE_LABELS[evt.node] || evt.node;
            const track = loadingRow.querySelector("[data-node-track]");
            if (!track) return;
            // 当前激活节点 → 已完成
            const active = track.querySelector(".is-active");
            if (active) active.className = "journal-node is-done";
            // 追加新激活节点
            const chip = document.createElement("span");
            chip.className = "journal-node is-active" + (evt.node === "supervisor" ? " is-retry" : "");
            chip.textContent = label;
            track.appendChild(chip);
            window.scrollTo(0, document.body.scrollHeight);
          },
        });
        loadingRow.remove();
        appendAi(renderApiResponse(payload), payload.report || "");
      } catch (err) {
        loadingRow.remove();
        const controller2 = new AbortController();
        try {
          const payload = await api.requestQueryPayload(value, { responseMode: "full", controller: controller2 });
          appendAi(renderApiResponse(payload), payload.report || "");
        } catch (err2) {
          const fallback = localReply(value);
          let html = renderLocalResponse(fallback);
          html += `<div class="journal-footnote" style="color:var(--warn);">${escapeHtml(api.explainApiError(err2))}</div>`;
          appendAi(html, fallback.text);
        }
      } finally {
        busy = false;
        send.disabled = false;
        bindSuggestButtons();
      }
    } else {
      const fallback = localReply(value);
      appendAi(renderLocalResponse(fallback), fallback.text);
    }
  }

  send.addEventListener("click", handleSend);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.isComposing) handleSend();
  });
  bindSuggestButtons();

  const prefill = new URLSearchParams(window.location.search).get("q");
  if (prefill) {
    input.value = prefill;
    setTimeout(() => handleSend(), 300);
  }
}

function initDay(state) {
  const root = document.querySelector("[data-day-root]");
  if (!root) return;

  const params = new URLSearchParams(window.location.search);
  const weekIdx = parseInt(params.get("w") ?? String(CURRENT_WEEK_IDX), 10);
  const safeIdx = Number.isFinite(weekIdx) ? weekIdx : CURRENT_WEEK_IDX;
  const idx = parseInt(params.get("i") || "0", 10);

  const version = currentVersion(state);
  if (!version) return;
  const week = version.weeks[safeIdx] || version.weeks[CURRENT_WEEK_IDX];
  if (!week) return;
  const session = week.sessions[idx] || week.sessions[0];
  if (!session) return;

  const kicker = root.querySelector("[data-day-kicker]");
  if (kicker) kicker.textContent = `${session.day} · ${session.date}`;

  const title = root.querySelector("[data-day-title]");
  if (title) title.textContent = session.title;

  document.title = `${session.day}训练 - 马拉松助手`;

  const sessionKey = `${week.key}-${session.day}`;
  const dynSession = state.dynamicContent?.[sessionKey];

  const badgeMap = {
    "轻松跑": ["心率区间 2", `配速 ${state.profile.recentPace || "6'48\"/km"}`],
    "恢复跑": ["心率区间 1", "轻松节奏"],
    "间歇跑": ["心率区间 4-5", "高强度间歇"],
    "长跑": ["心率区间 2-3", "耐力训练"],
    "节奏跑": ["心率区间 3-4", "乳酸阈值"],
  };
  const badges = root.querySelector("[data-day-badges]");
  if (badges) {
    const labels = dynSession?.badges
      || Object.entries(badgeMap).find(([k]) => session.title.includes(k))?.[1]
      || [session.meta || "训练"];
    badges.innerHTML = labels.map((l) => `<span class="journal-badge">${escapeHtml(l)}</span>`).join("");
  }

  const durationMatch = session.title.match(/(\d+)\s*分钟/);
  const duration = durationMatch ? durationMatch[1] : "30";

  const mainCaption = root.querySelector("[data-day-main-caption]");
  if (mainCaption) mainCaption.textContent = `${duration} 分钟`;

  // "问 AI 教练" 按钮预填当前训练问题
  const mainLink = root.querySelector("[data-day-main-link]");
  if (mainLink) mainLink.href = `/dialog?q=${encodeURIComponent(session.title + " 怎么练")}`;

  const meta = root.querySelector("[data-day-meta]");
  if (meta) {
    const parts = [];
    if (session.completed) parts.push("✓ 已完成");
    if (session.meta) parts.push(session.meta);
    meta.textContent = parts.join(" · ");
  }

  const explanation = root.querySelector("[data-day-explanation]");
  if (explanation) {
    explanation.textContent = dynSession?.explanation || "今日训练按计划执行。";
  }

  // 主课训练结构（优先 dynamicContent）
  const structure = root.querySelector("[data-day-structure]");
  if (structure) {
    const steps = dynSession?.structure || [];
    if (steps.length) {
      structure.innerHTML = steps.map((step) =>
        `<div class="journal-flow-step${step.isMain ? " is-main" : ""}">` +
        `<strong>${escapeHtml(step.label)}</strong>` +
        `<div class="journal-caption">${escapeHtml(step.caption)}</div>` +
        `</div>`
      ).join("");
    }
  }
}

function initBasis(state) {
  const contentEl = document.querySelector("[data-basis-content]");
  const emptyEl = document.querySelector("[data-basis-empty]");
  if (!contentEl) return;

  const feedbacks = state.feedbacks || [];
  if (feedbacks.length === 0) {
    contentEl.hidden = true;
    if (emptyEl) emptyEl.hidden = false;
    return;
  }

  contentEl.hidden = false;
  if (emptyEl) emptyEl.hidden = true;

  // 最多取最近 7 条，按时间从旧到新排列
  const recent = feedbacks.slice(0, 7).reverse();
  const count = recent.length;

  // 日期区间
  const dateEl = document.querySelector("[data-basis-date]");
  if (dateEl) {
    dateEl.textContent = count === 1
      ? recent[0].date
      : `${recent[0].date} - ${recent[count - 1].date}`;
  }

  // 徽章：条目数
  const badgeEl = document.querySelector("[data-basis-badge]");
  if (badgeEl) badgeEl.textContent = `${count} 条反馈`;

  // 疲劳趋势 SVG 折线图
  const svgEl = document.querySelector("[data-basis-svg]");
  if (svgEl) {
    const X0 = 40, Y0 = 42, W = 350, H = 140;
    const vals = recent.map((f) => Math.min(5, Math.max(1, Number(f.fatigue) || 3)));
    const pts = vals.map((v, i) => {
      const x = Math.round(X0 + W * (count === 1 ? 0.5 : i / (count - 1)));
      const y = Math.round((Y0 + H) - ((v - 1) / 4) * H);
      return { x, y };
    });
    const pointsStr = pts.map((p) => `${p.x},${p.y}`).join(" ");
    svgEl.innerHTML =
      `<line x1="40" y1="182" x2="390" y2="182" stroke="#bfc2c5" stroke-width="1"/>` +
      `<line x1="40" y1="42" x2="40" y2="182" stroke="#bfc2c5" stroke-width="1"/>` +
      (count > 1 ? `<polyline fill="none" stroke="#334a5d" stroke-width="3" points="${pointsStr}"/>` : "") +
      `<g fill="#334a5d">${pts.map((p) => `<circle cx="${p.x}" cy="${p.y}" r="4"/>`).join("")}</g>`;
  }

  // 统计徽章
  const statsEl = document.querySelector("[data-basis-stats]");
  if (statsEl) {
    const completed = recent.filter((f) => f.completion === "已完成").length;
    const hrVals = recent.map((f) => Number(f.avgHr)).filter((v) => v > 0);
    const avgHr = hrVals.length
      ? Math.round(hrVals.reduce((a, b) => a + b, 0) / hrVals.length)
      : null;
    let html = `<span class="journal-badge">完成 ${completed} / ${count} 次</span>`;
    if (avgHr) html += ` <span class="journal-badge">平均心率 ${avgHr} bpm</span>`;
    statsEl.innerHTML = html;
  }

  // 标注列表：异常心率 / 高疲劳 / 身体不适 + 下次训练
  const notesEl = document.querySelector("[data-basis-notes]");
  if (notesEl) {
    const notable = [];
    for (const fb of recent) {
      const hr = Number(fb.avgHr);
      const fatigue = Number(fb.fatigue);
      if (hr > 155) notable.push({ date: fb.date, text: `心率 ${hr} bpm` });
      else if (fatigue >= 4) notable.push({ date: fb.date, text: `疲劳度 ${fatigue}/5` });
      else if (fb.body && fb.body !== "无不适") notable.push({ date: fb.date, text: fb.body });
    }
    // 补充：下一个未完成课表
    const version = currentVersion(state);
    const upcoming = (version?.weeks?.[CURRENT_WEEK_IDX]?.sessions || []).find(
      (s) => !s.completed && !s.muted
    );
    if (upcoming) notable.push({ date: upcoming.day, text: upcoming.title });

    notesEl.innerHTML = notable.length
      ? notable.slice(0, 4).map(
          (n) => `<a class="journal-note-card" href="/feedback"><span>${n.date}</span><strong>${n.text}</strong></a>`
        ).join("")
      : `<p style="color:var(--muted);font-size:13px;padding:8px 0;">本周暂无特殊标注</p>`;
  }
}

function initPage() {
  const state = loadState();
  saveState(state);
  renderProfileSummary(state);
  renderHome(state);
  renderCalendar(state);
  renderHistory(state);
  renderEventList(state);
  initProfileEdit(state);
  initWeekSetup(state);
  initEventForm(state);
  initFeedbackForm(state);
  initDialog(state);
  initDay(state);
  initBasis(state);
}

window.JournalInk = {
  loadState,
  saveState,
  buildPlanVersion,
  buildWeeks,
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initPage, { once: true });
} else {
  initPage();
}
