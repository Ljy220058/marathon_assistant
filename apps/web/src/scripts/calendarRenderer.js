// Calendar renderer fallback used before app.js overrides it.
(function () {
  function sanitizeText(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;")
      .replace(/javascript:/gi, "javascript&#058;");
  }

  function normalizeCalendarDays(response) {
    const plan = response?.structured_training_plan || response?.structured_report?.structured_training_plan || {};
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
      const matchingWeekDay =
        weekDays.find(
          (weekDay) =>
            (weekDay.day_index !== undefined &&
              weekDay.day_index === day.day_index &&
              weekDay.week_index === day.week_index) ||
            (weekDay.day_label && weekDay.day_label === day.day_label),
        ) || {};
      const matchingCard =
        cards.find(
          (card) =>
            (card.day_index !== undefined &&
              card.day_index === day.day_index &&
              card.week_index === day.week_index) ||
            (card.day_label && card.day_label === day.day_label),
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
    if (typeof window.renderCalendar === "function" && window.renderCalendar !== renderCalendar) {
      return window.renderCalendar(response);
    }

    const days = normalizeCalendarDays(response);
    const el = document.getElementById("calendar");
    if (!el) return;

    if (!days.length) {
      el.innerHTML = '<div class="empty-state">计划生成后会在这里展示日历卡片。</div>';
      return;
    }

    el.innerHTML = days
      .map((day, index) => {
        const label = sanitizeText(day.day_label || `第${index + 1}天`);
        const type = sanitizeText(day.training_type || day.workout_type || "训练");
        return `<article class="day-card" data-day-index="${index}"><strong>${label}</strong><span>${type}</span></article>`;
      })
      .join("");
  }

  function openDayModal(day, response, trigger) {
    if (typeof window.openDayModal === "function" && window.openDayModal !== openDayModal) {
      return window.openDayModal(day, response, trigger);
    }
    console.warn("openDayModal: app.js 尚未加载完整实现");
  }

  window.__calendarRenderer = { renderCalendar, openDayModal, normalizeCalendarDays };
})();
