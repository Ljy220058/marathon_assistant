const STORAGE_KEY = "journal-ink-state-v1";
const WEEK_KEY_ORDER = ["previous", "current", "next"];

const WEEK_BLUEPRINTS = [
  {
    key: "previous",
    label: "上一周",
    range: "6 月 9 日 - 6 月 15 日",
    goal: "把恢复和节奏重新接上。",
    sessions: [
      { day: "周三", date: "6 月 10 日", title: "节奏跑 25 分钟", meta: "✓ 已完成", href: "./ink-day.html", completed: true },
      { day: "周五", date: "6 月 12 日", title: "恢复跑 30 分钟", meta: "✓ 已完成", href: "./ink-day.html", completed: true },
      { day: "周一", date: "6 月 15 日", title: "恢复跑 30 分钟", meta: "✓ 已完成", href: "./ink-day.html", completed: true },
    ],
  },
  {
    key: "current",
    label: "本周",
    range: "6 月 16 日 - 6 月 22 日",
    goal: "稳定完成 3 次训练，保留恢复余量。",
    sessions: [
      { day: "周二", date: "6 月 16 日", title: "轻松跑 40 分钟", meta: "今天 · 06:30", href: "./ink-day.html", current: true },
      { day: "周四", date: "6 月 19 日", title: "间歇跑 6 x 400m", meta: "19:30", href: "./ink-day.html" },
      { day: "周六", date: "6 月 21 日", title: "长跑 55 分钟", meta: "07:00", href: "./ink-day.html" },
    ],
  },
  {
    key: "next",
    label: "下一周",
    range: "6 月 23 日 - 6 月 28 日",
    goal: "在保持周频率的前提下抬一点负荷。",
    sessions: [
      { day: "周二", date: "6 月 24 日", title: "轻松跑 40 分钟", meta: "06:30", href: "./ink-day.html" },
      { day: "周四", date: "6 月 26 日", title: "间歇跑 8 x 400m", meta: "19:30", href: "./ink-day.html" },
      { day: "周六", date: "6 月 28 日", title: "长跑 60 分钟", meta: "07:00", href: "./ink-day.html" },
    ],
  },
];

const DEFAULT_PROFILE = {
  goal: "半马完赛",
  raceDate: "2026-09-21",
  level: "新手",
  trainingDays: ["周一", "周三", "周六"],
  longestRun: "12 km",
  recentPace: `6'48"/km`,
  kneeStatus: "轻度紧张",
  note: "临时比赛优先顺延。",
};

const DEFAULT_WEEK_SETUP = {
  goal: "稳定完成本周三次训练",
  availableDays: ["周一", "周三", "周六"],
  sessionCount: "3",
  intensity: "中等",
  note: "周四晚间可训练，周末如有比赛先让位。",
};

function clone(value) {
  return JSON.parse(JSON.stringify(value));
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

function createBaseState() {
  const profile = clone(DEFAULT_PROFILE);
  const weekSetup = clone(DEFAULT_WEEK_SETUP);
  const events = [
    {
      id: "evt-1",
      type: "比赛",
      title: "城市 10K",
      day: "周六",
      date: "2026-06-21",
      replace: "长跑 55 分钟",
      note: "原长跑顺延到周日。",
      createdAt: "2026-06-16 08:30",
    },
  ];
  const weeks = buildWeeks(profile, weekSetup, events);
  const firstVersion = {
    id: "v-1",
    name: "第 1 版",
    createdAt: "2026-06-16 08:00",
    note: "基础生成",
    weeks,
  };
  return {
    profile,
    weekSetup,
    events,
    feedbacks: [
      {
        id: "fb-1",
        date: "2026-06-15",
        completion: "已完成",
        fatigue: "2",
        body: "无不适",
        note: "今天控制得住。",
      },
    ],
    versions: [firstVersion],
    currentVersionId: firstVersion.id,
    selectedWeekKey: "current",
  };
}

function normalizeState(partial) {
  const base = createBaseState();
  const state = {
    ...base,
    ...partial,
    profile: { ...base.profile, ...(partial?.profile || {}) },
    weekSetup: { ...base.weekSetup, ...(partial?.weekSetup || {}) },
    events: Array.isArray(partial?.events) ? partial.events : base.events,
    feedbacks: Array.isArray(partial?.feedbacks) ? partial.feedbacks : base.feedbacks,
    versions: Array.isArray(partial?.versions) && partial.versions.length ? partial.versions : base.versions,
    currentVersionId: partial?.currentVersionId || base.currentVersionId,
    selectedWeekKey: partial?.selectedWeekKey || base.selectedWeekKey,
  };
  if (!state.versions.some((version) => version.id === state.currentVersionId)) {
    state.currentVersionId = state.versions[0].id;
  }
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
  return state.versions.find((version) => version.id === state.currentVersionId) || state.versions[0];
}

function buildWeeks(profile, weekSetup, events, options) {
  const weeks = clone(WEEK_BLUEPRINTS);
  const currentWeek = weeks.find((week) => week.key === "current");
  if (!currentWeek) return weeks;

  const availableDays = new Set((weekSetup.availableDays || profile.trainingDays || []).map((day) => String(day).trim()));
  const eventByDay = new Map();
  events.forEach((event) => {
    if (event?.day) eventByDay.set(String(event.day).trim(), event);
  });

  const shouldDowngrade = options?.downgrade === true;

  currentWeek.sessions = currentWeek.sessions.map((session, index) => {
    const next = { ...session };
    if (weekSetup.sessionCount && Number(weekSetup.sessionCount) < currentWeek.sessions.length && index >= Number(weekSetup.sessionCount)) {
      next.title = "机动恢复 25 分钟";
      next.meta = "本周减量";
      next.current = false;
      next.muted = true;
      return next;
    }
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
      next.href = "./ink-event.html";
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
  });

  if (events.length) {
    currentWeek.eventSummary = `${events.length} 个临时事件`;
  }
  currentWeek.goal = `${weekSetup.goal || currentWeek.goal} · ${weekSetup.intensity || "中等"}强度`;

  const nextWeek = weeks.find((week) => week.key === "next");
  if (nextWeek && Number(weekSetup.sessionCount) <= 2) {
    nextWeek.goal = "先保住恢复，再谈加量。";
  }
  return weeks;
}

function buildPlanVersion(state, note, options) {
  const version = {
    id: `v-${Date.now()}`,
    name: `第 ${state.versions.length + 1} 版`,
    createdAt: nowText(),
    note,
    weeks: buildWeeks(state.profile, state.weekSetup, state.events, options),
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
    level: state.profile.level,
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
  const hasplan = version.weeks.some((w) => w.sessions.length > 0);
  const label = document.querySelector("[data-home-version]");
  if (label) label.textContent = `${version.name} · ${version.note}`;
  const goal = document.querySelector("[data-home-goal]");
  if (goal) goal.textContent = version.weeks.find((week) => week.key === "current")?.goal || "稳定完成本周三次训练";
  const todayCard = document.querySelector("[data-home-today]");
  const progressCard = document.querySelector("[data-home-progress]");
  const emptyCard = document.querySelector("[data-home-empty]");
  if (todayCard) todayCard.hidden = !hasplan;
  if (progressCard) progressCard.hidden = !hasplan;
  if (emptyCard) emptyCard.hidden = hasplan;
}

function renderCalendar(state) {
  const root = document.querySelector("[data-calendar-root]");
  if (!root) return;
  const version = currentVersion(state);
  const weeks = version.weeks;

  const versionLabel = root.querySelector("[data-calendar-version]");
  if (versionLabel) versionLabel.textContent = `${version.name} · ${version.note}`;
  const eventCount = root.querySelector("[data-calendar-event-count]");
  if (eventCount) eventCount.textContent = `${state.events.length} 个临时事件`;

  const panels = Array.from(root.querySelectorAll("[data-week-panel]"));
  const buttons = Array.from(root.querySelectorAll("[data-week-nav]"));
  const selected = WEEK_KEY_ORDER.includes(state.selectedWeekKey) ? state.selectedWeekKey : "current";

  const showWeek = (weekKey) => {
    state.selectedWeekKey = weekKey;
    saveState(state);
    panels.forEach((panel) => {
      panel.hidden = panel.getAttribute("data-week-panel") !== weekKey;
    });
    buttons.forEach((button) => {
      button.classList.toggle("is-active", button.getAttribute("data-week-nav") === weekKey);
    });
  };

  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      const weekKey = button.getAttribute("data-week-nav");
      if (weekKey) showWeek(weekKey);
    });
  });

  panels.forEach((panel) => {
    const weekKey = panel.getAttribute("data-week-panel");
    const week = weeks.find((item) => item.key === weekKey);
    if (!week) return;
    const headStrong = panel.querySelector(".journal-week-head strong");
    const headSpan = panel.querySelector(".journal-week-head span");
    const goalNode = panel.querySelector("[data-week-goal]");
    if (headStrong) headStrong.textContent = week.label;
    if (headSpan) headSpan.textContent = week.range;
    if (goalNode) goalNode.textContent = week.goal;
    const sessionCards = Array.from(panel.querySelectorAll(".journal-session-card"));
    week.sessions.forEach((session, index) => {
      const card = sessionCards[index];
      if (!card) return;
      const [dateNode, titleNode, metaNode] = [card.querySelector("span"), card.querySelector("strong"), card.querySelector(".journal-meta")];
      if (dateNode) dateNode.textContent = `${session.date} ${session.day}`;
      if (titleNode) titleNode.textContent = session.title;
      if (metaNode) metaNode.textContent = session.meta;
      card.href = session.href || "./ink-day.html";
      card.classList.toggle("is-complete", Boolean(session.completed));
      card.classList.toggle("is-current", Boolean(session.current));
      card.classList.toggle("is-event", Boolean(session.event));
      card.classList.toggle("is-muted", Boolean(session.muted));
    });
    const summary = panel.querySelector("[data-week-summary]");
    if (summary) summary.textContent = week.eventSummary || `${week.sessions.length} 个安排`;
  });

  showWeek(selected);
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
      next.selectedWeekKey = "current";
      saveState(next);
      window.location.href = "./ink-calendar.html";
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
  form.level.value = state.profile.level;
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
      level: form.level.value.trim(),
      trainingDays: readCheckedValues(form, "trainingDays"),
      longestRun: form.longestRun.value.trim(),
      recentPace: form.recentPace.value.trim(),
      kneeStatus: form.kneeStatus.value.trim(),
      note: form.note.value.trim(),
    };
    buildPlanVersion(next, "基础画像已更新");
    saveState(next);
    window.location.href = "./ink-profile.html";
  });
}

function initWeekSetup(state) {
  const form = document.querySelector("#weekSetupForm");
  if (!form) return;
  form.weekGoal.value = state.weekSetup.goal;
  form.sessionCount.value = state.weekSetup.sessionCount;
  form.intensity.value = state.weekSetup.intensity;
  form.note.value = state.weekSetup.note;
  setCheckedValues(form, "availableDays", state.weekSetup.availableDays);

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const next = loadState();
    next.weekSetup = {
      goal: form.weekGoal.value.trim(),
      availableDays: readCheckedValues(form, "availableDays"),
      sessionCount: form.sessionCount.value,
      intensity: form.intensity.value,
      note: form.note.value.trim(),
    };
    buildPlanVersion(next, "本周设置已更新");
    saveState(next);
    window.location.href = "./ink-calendar.html";
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
    buildPlanVersion(next, "插入临时事件后重排");
    saveState(next);
    window.location.href = "./ink-calendar.html";
  });
  const list = document.querySelector("[data-event-list]");
  if (list) renderEventList(state);
}

function initFeedbackForm() {
  const form = document.querySelector("#feedbackForm");
  if (!form) return;
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const next = loadState();
    const completion = form.querySelector('input[name="completion"]:checked')?.value || "未开始";
    const bodyParts = readCheckedValues(form, "bodyParts");
    const bodyText = bodyParts.length ? bodyParts.join("、") : "无不适";
    const fatigue = Number(form.fatigue.value);
    const feedback = {
      id: `fb-${Date.now()}`,
      date: todayText(),
      completion,
      fatigue: String(fatigue),
      body: bodyText,
      note: form.notes.value.trim(),
    };
    next.feedbacks = [feedback, ...next.feedbacks].slice(0, 8);
    const needsRebuild = completion !== "已完成" || fatigue >= 4 || bodyParts.length > 0;
    if (needsRebuild) {
      const shouldDowngrade = fatigue >= 4 || completion === "未完成";
      const reason = shouldDowngrade ? "疲劳/未完成，已降级下次训练" : "依据今日反馈微调";
      buildPlanVersion(next, reason, { downgrade: shouldDowngrade });
    }
    saveState(next);
    window.location.href = "./ink-home.html";
  });
}

function initDialog(state) {
  const thread = document.querySelector("#dialogThread");
  const input = document.querySelector("#dialogInput");
  const send = document.querySelector("#dialogSend");
  if (!thread || !input || !send) return;

  const reply = (text) => {
    const lower = text.toLowerCase();
    if (/比赛|出差|请假|没空|周四/.test(text)) {
      return {
        text: "先插入临时事件，再重新生成本周计划。",
        action: { label: "去插入事件", href: "./ink-event.html" },
      };
    }
    if (/重排|重新生成|本周/.test(text)) {
      return {
        text: "先打开本周设置，确认训练日和强度，再生成新版本。",
        action: { label: "去本周设置", href: "./ink-week-setup.html" },
      };
    }
    if (/画像|我的情况|目标|比赛日期/.test(text)) {
      return {
        text: "先补基础画像，再回到计划页生成。",
        action: { label: "编辑画像", href: "./ink-profile-edit.html" },
      };
    }
    if (/反馈|疲劳|疼|膝/.test(lower)) {
      return {
        text: "先记录今日反馈，再决定下一版是否降量。",
        action: { label: "去今日反馈", href: "./ink-feedback.html" },
      };
    }
    return {
      text: "可以问本周怎么排、临时比赛怎么插、反馈后怎么改。",
      action: { label: "看版本历史", href: "./ink-history.html" },
    };
  };

  send.addEventListener("click", () => {
    const value = input.value.trim();
    if (!value) return;
    const userRow = document.createElement("div");
    userRow.className = "journal-chat-row user";
    userRow.innerHTML = `<div class="journal-chat-bubble">${escapeHtml(value)}</div>`;
    thread.appendChild(userRow);

    const nextReply = reply(value);
    const aiRow = document.createElement("div");
    aiRow.className = "journal-chat-row ai";
    aiRow.innerHTML = `
      <div class="journal-chat-bubble">
        ${escapeHtml(nextReply.text)}
        <div class="journal-chat-link"><a href="${escapeHtml(nextReply.action.href)}">${escapeHtml(nextReply.action.label)}</a></div>
      </div>
    `;
    thread.appendChild(aiRow);
    input.value = "";
    thread.scrollTop = thread.scrollHeight;
  });

  document.querySelectorAll("[data-suggest]").forEach((btn) => {
    btn.addEventListener("click", () => {
      input.value = btn.textContent.trim();
      send.click();
    });
  });
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
