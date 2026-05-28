// profileState.js — Unified profile state contract [product-profile][P0]
// 侧边栏、向导和计划链路读写同一状态契约
//
// Sources of truth:
// 1. state.latestProfile      — last known profile snapshot from API/draft
// 2. localStorage draft       — user-managed offline draft (marathon-profile-draft)
// 3. DOM inputs               — profile fields and profile editor dialog
//
// All readers/writers MUST go through these helpers to ensure consistency.

const LOCAL_STORAGE_KEY = "marathon-profile-draft";

const PROFILE_FIELD_MAP = {
  goal: { key: "goal", draftKey: "goal", label: "目标", type: "text" },
  experience: { key: "experience_level", draftKey: "experience", label: "经验", type: "text" },
  lastMonthMileage: { key: "recent_four_week_mileage", draftKey: "lastMonthMileage", label: "上个月月跑量", type: "text" },
  currentHalfTime: { key: "current_half_time", draftKey: "currentHalfTime", label: "当前半马 PB", type: "text" },
  raceDate: { key: "target_race_date", draftKey: "raceDate", label: "比赛日期", type: "text" },
  availableDays: { key: "available_days", draftKey: "availableDays", label: "可训练日", type: "text" },
  longRun: { key: "max_session_minutes", draftKey: "longRun", label: "最长训练", type: "text" },
  targetPace: { key: "t_pace", draftKey: "targetPace", label: "目标配速", type: "text" },
  limitations: { key: "notes", draftKey: "limitations", label: "伤病/疲劳限制", type: "text" },
  lthr: { key: "lthr", label: "LTHR", type: "number" },
  vo2max: { key: "vo2max", label: "VO₂max", type: "number" },
  terrain_preference: { key: "terrain_preference", label: "场地偏好", type: "text" },
  training_types: { key: "training_types", label: "训练类型偏好", type: "text" },
  // P1-8: 新增营养与体质相关字段
  weight: { key: "weight_kg", draftKey: "weight", label: "体重", type: "text" },
  sex: { key: "sex", draftKey: "sex", label: "性别", type: "text" },
  dietType: { key: "diet_type", draftKey: "dietType", label: "饮食类型", type: "text" },
  sweatRate: { key: "sweat_rate", draftKey: "sweatRate", label: "出汗率", type: "text" },
  giSensitivity: { key: "gi_sensitivity", draftKey: "giSensitivity", label: "胃肠敏感度", type: "text" },
};

/**
 * Read the canonical profile draft from localStorage.
 * Returns a plain object with draftKey values.
 */
export function getProfileDraft() {
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

/**
 * Persist a profile draft to localStorage by merging into the existing draft.
 */
export function saveProfileDraft(partial = {}) {
  try {
    const current = getProfileDraft();
    const merged = { ...current, ...partial };
    // Remove null/undefined entries
    Object.keys(merged).forEach((key) => {
      if (merged[key] === null || merged[key] === undefined) delete merged[key];
    });
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(merged));
    return merged;
  } catch {
    return partial;
  }
}

/**
 * Delete the entire profile draft from localStorage.
 */
export function clearProfileDraft() {
  try {
    localStorage.removeItem(LOCAL_STORAGE_KEY);
  } catch {
    // best effort
  }
}

/**
 * Read a single draft value by draftKey.
 */
export function getProfileDraftValue(draftKey) {
  return getProfileDraft()[draftKey] || "";
}

/**
 * Build a profile object from the current DOM inputs (data-profile-field).
 * Used by the inline profile grid and the editor dialog.
 */
export function collectProfileFromDom(doc = document) {
  const profile = {};
  const inputs = Array.from(doc.querySelectorAll("[data-profile-field], [data-profile-editor-field]"));
  inputs.forEach((input) => {
    const rawKey = input.dataset.profileField || input.dataset.profileEditorField || "";
    const value = input.type === "checkbox"
      ? input.checked
      : String(input.value || "").trim();
    if (!rawKey) return;
    const mapping = Object.values(PROFILE_FIELD_MAP).find((m) => m.key === rawKey);
    const outputKey = mapping ? mapping.key : rawKey;
    if (value) profile[outputKey] = value;
  });
  return profile;
}

/**
 * Merge a profile object back into DOM inputs.
 */
export function populateProfileToDom(profile = {}, doc = document) {
  Object.entries(PROFILE_FIELD_MAP).forEach(([draftKey, mapping]) => {
    const value = profile[mapping.key] ?? profile[draftKey] ?? "";
    // Populate data-profile-field inputs
    const profileInput = doc.querySelector(`[data-profile-field="${draftKey}"]`);
    if (profileInput && profileInput.type !== "checkbox") {
      profileInput.value = String(value);
    }
    // Populate profile editor inputs
    const editorInput = doc.querySelector(`[data-profile-editor-field="${mapping.key}"]`);
    if (editorInput && editorInput.type !== "checkbox") {
      editorInput.value = String(value);
    }
  });
}

/**
 * Build a full canonical profile object used by plan generation.
 * Priority: DOM inputs > state.latestProfile > localStorage draft.
 */
export function buildCanonicalProfile(options = {}) {
  const { latestProfile = {}, doc = document } = options;
  const draft = getProfileDraft();
  const domProfile = collectProfileFromDom(doc);

  const merged = {
    goal: "",
    experience_level: "",
    recent_four_week_mileage: "",
    current_half_time: "",
    target_race_date: "",
    available_days: "",
    max_session_minutes: "",
    t_pace: "",
    lthr: "",
    vo2max: "",
    terrain_preference: "",
    training_types: "",
    notes: "",
    // P1-8: 新增营养与体质字段
    weight_kg: "",
    sex: "",
    diet_type: "",
    sweat_rate: "",
    gi_sensitivity: "",
  };

  // Merge order: draft (lowest) → latestProfile → DOM (highest for active editing)
  Object.assign(merged, draftToCanonicalFields(draft));
  Object.assign(merged, pickCanonicalFields(latestProfile));
  Object.assign(merged, pickCanonicalFields(domProfile));

  return merged;
}

function draftToCanonicalFields(draft = {}) {
  const result = {};
  Object.entries(PROFILE_FIELD_MAP).forEach(([draftKey, mapping]) => {
    if (draft[draftKey] !== undefined && draft[draftKey] !== null && draft[draftKey] !== "") {
      result[mapping.key] = draft[draftKey];
    }
  });
  return result;
}

function pickCanonicalFields(source = {}) {
  const result = {};
  const keys = Object.values(PROFILE_FIELD_MAP).map((m) => m.key);
  keys.forEach((key) => {
    if (source[key] !== undefined && source[key] !== null && source[key] !== "") {
      result[key] = source[key];
    }
  });
  return result;
}

/**
 * Profile change notification contract.
 * Returns { hasChanges, changes: [{ field, oldValue, newValue }], confirmationRequired }
 */
export function detectProfileChanges(previousProfile = {}, currentProfile = {}) {
  const changes = [];
  const fields = new Set([
    ...Object.keys(previousProfile),
    ...Object.keys(currentProfile),
  ]);
  fields.forEach((field) => {
    const oldValue = String(previousProfile[field] || "").trim();
    const newValue = String(currentProfile[field] || "").trim();
    if (oldValue !== newValue) {
      changes.push({ field, oldValue, newValue });
    }
  });
  const impactfulFields = ["goal", "target_race_date", "available_days", "recent_four_week_mileage", "current_half_time"];
  const hasImpactfulChange = changes.some((c) => impactfulFields.includes(c.field));
  return {
    hasChanges: changes.length > 0,
    changes,
    confirmationRequired: hasImpactfulChange,
    impactfulChanges: changes.filter((c) => impactfulFields.includes(c.field)),
  };
}

// Expose globally for non-module usage
if (typeof window !== "undefined") {
  Object.assign(window, {
    getProfileDraft,
    saveProfileDraft,
    clearProfileDraft,
    getProfileDraftValue,
    collectProfileFromDom,
    populateProfileToDom,
    buildCanonicalProfile,
    detectProfileChanges,
    PROFILE_FIELD_MAP,
  });
}
