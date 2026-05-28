// Calendar Renderer — 日历分组、周/月/阶段/全部视图切换、日卡 HTML 与弹窗打开逻辑。
// 使用 IIFE 隔离，通过 window.__calendarRenderer 暴露 API。

(function () {

  function normalizeCalendarDays(response) {
    // 从 plan state 中提取并归一化所有训练日
    const plan = (response?.structured_training_plan || response?.structured_report?.structured_training_plan || {});
    const cards = response?.daily_schedule_cards || response?.structured_report?.daily_schedule_cards || [];
    const calendar = response?.monthly_training_calendar || response?.structured_report?.monthly_training_calendar || {};
    const calendarDays = Array.isArray(calendar.days) ? calendar.days : [];
    const weekDays = [];
    (plan.week_plans || []).forEach((week) => {
      (week.days || []).forEach((day, index) => {
        weekDays.push({ ...day, week_index: week.week_index, day_index: index + 1, phase: week.phase });
      });
    });

    const baseDays = cards.length ? cards : calendarDays.length ? calendarDays : weekDays;
    return baseDays.map((day, idx) => {
      const matchingWeekDay = weekDays.find(
        (wd) => (wd.day_index !== undefined && wd.day_index === day.day_index && wd.week_index === day.week_index) ||
          (wd.day_label && wd.day_label === day.day_label)
      ) || {};
      const matchingCard = cards.find(
        (c) => (c.day_index !== undefined && c.day_index === day.day_index && c.week_index === day.week_index) ||
          (c.day_label && c.day_label === day.day_label)
      ) || {};
      return {
        week_index: day.week_index ?? matchingWeekDay.week_index,
        day_index: day.day_index ?? matchingWeekDay.day_index ?? idx + 1,
        day_label: day.day_label || matchingWeekDay.day_label || matchingWeekDay.day,
        phase: day.phase || matchingWeekDay.phase,
        ...matchingWeekDay,
        ...day,
        ...matchingCard,
      };
    });
  }

  function renderCalendar(response) {
    // 委托给 app.js 中的同名全局函数
    if (typeof window.renderCalendar === "function" && window.renderCalendar !== renderCalendar) {
      return window.renderCalendar(response);
    }
    // 后备：若 app.js 未加载，设置一个基本展示
    const days = normalizeCalendarDays(response);
    const el = document.getElementById("calendar");
    if (!el) return;
    if (!days.length) {
      el.innerHTML = '<div class="empty-state">计划生成后会在这里展示日历卡片。</div>';
      return;
    }
    el.innerHTML = days.map((day, index) => {
      const label = day.day_label || `第${index + 1}天`;
      const type = day.training_type || day.workout_type || "训练";
      return `<article class="day-card" data-day-index="${index}"><strong>${label}</strong><span>${type}</span></article>`;
    }).join("");
  }

  function openDayModal(day, response, trigger) {
    // 委托给 app.js 中的 openDayModal
    if (typeof window.openDayModal === "function" && window.openDayModal !== openDayModal) {
      return window.openDayModal(day, response, trigger);
    }
    console.warn("openDayModal: app.js 尚未加载完整实现");
  }

  // 挂载到 window
  window.__calendarRenderer = { renderCalendar, openDayModal, normalizeCalendarDays };
})();
