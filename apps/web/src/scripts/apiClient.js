// API Client — 统一管理后端通信、地址探测、查询和反馈请求。
// 所有 API 错误均转为用户可读提示。
// 使用 IIFE 隔离命名空间，避免与 app.js 全局函数冲突。

(function () {
  const LOCAL_API_BASE = "http://127.0.0.1:8000";
  const FULL_QUERY_TIMEOUT_SEC = 120;
  const FULL_QUERY_TIMEOUT_MS = 120000;
  const CONFIGURED_API_BASE = String(
    window.MARATHON_API_BASE || document.body?.dataset?.apiBase || ""
  ).trim().replace(/\/$/, "");
  const DEFAULT_API_BASE = CONFIGURED_API_BASE || LOCAL_API_BASE;
  const API_BASE_CANDIDATES = [DEFAULT_API_BASE, LOCAL_API_BASE, "http://127.0.0.1:8001", "http://127.0.0.1:8010", "http://127.0.0.1:8011"];

  function _getApiBase() {
    const input = document.getElementById("apiBase");
    const fallback = (typeof state !== "undefined" && state.apiBase) || DEFAULT_API_BASE;
    return (input?.value || fallback).replace(/\/$/, "");
  }

  function _getApiAuthHeaders() {
    const tokenInput = document.getElementById("apiToken");
    const token = String(
      (typeof state !== "undefined" && state.apiToken) || tokenInput?.value || ""
    ).trim();
    return token ? { "X-Marathon-API-Key": token } : {};
  }

  async function apiFetch(path, options = {}) {
    const { base, timeoutMs = 30000, signal, headers = {}, ...fetchOptions } = options;
    const apiBase = (base || _getApiBase()).replace(/\/$/, "");
    const controller = new AbortController();
    let timedOut = false;
    const timeoutId = timeoutMs
      ? window.setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs)
      : null;
    if (signal) {
      signal.addEventListener("abort", () => controller.abort(), { once: true });
    }
    try {
      const response = await fetch(`${apiBase}${path}`, {
        headers: { "Content-Type": "application/json", ..._getApiAuthHeaders(), ...headers },
        signal: controller.signal,
        ...fetchOptions,
      });
      if (typeof state !== "undefined") {
        state.lastRequestId = response.headers.get("X-Request-ID") || state.lastRequestId || "";
      }
      if (!response.ok) {
        let detail = `${response.status} ${response.statusText}`;
        try { const errPayload = await response.json(); detail = errPayload.detail || detail; } catch {}
        throw new Error(detail);
      }
      const payload = await response.json();
      if (payload && typeof payload === "object" && typeof state !== "undefined" && state.lastRequestId) {
        payload.__request_id = state.lastRequestId;
      }
      return payload;
    } catch (error) {
      if (error?.name === "AbortError") {
        throw new Error(timedOut ? "请求超时，已停止等待本地训练服务响应。" : "请求已取消。");
      }
      throw error;
    } finally {
      if (timeoutId) window.clearTimeout(timeoutId);
    }
  }

  function explainApiError(error, base) {
    const apiBase = base || _getApiBase();
    const message = String(error?.message || error || "").trim();
    if (message.includes("请求超时")) {
      return `${apiBase} 已连接，但 AI 生成超过等待时间。当前可能是 DeepSeek/RAG 检索或报告生成较慢，请稍后重试。`;
    }
    if (message.includes("Failed to fetch") || message.includes("NetworkError") ||
        message.includes("Load failed") || message.includes("Network request failed")) {
      return `本地训练服务不可用：无法连接 ${apiBase}。请确认本地服务正在该端口运行，当前推荐端口是 8000。`;
    }
    return `${apiBase} 返回错误：${message || "未知错误"}`;
  }

  function getApiBaseCandidates() {
    return Array.from(new Set([_getApiBase(), ...API_BASE_CANDIDATES].filter(Boolean)));
  }

  async function detectApiBase() {
    const candidates = getApiBaseCandidates();
    const input = document.getElementById("apiBase");
    for (const base of candidates) {
      try {
        const data = await apiFetch("/health", { base, timeoutMs: 2500 });
        if (input) input.value = base;
        if (typeof state !== "undefined") {
          state.apiBase = base;
          state.lastQueryBase = base;
        }
        localStorage.setItem("marathon-api-base", base);
        if (typeof renderHealth === "function") {
          renderHealth(data.status, data.model, data.provider);
        }
        return true;
      } catch {}
    }
    return false;
  }

  function buildQueryPayload(query, responseMode, timeoutSec) {
    const llmProviderInput = document.getElementById("llmProvider");
    const llmModelInput = document.getElementById("llmModel");
    return {
      query, mode: "team", user_id: "default_user", stream: false,
      llm_provider: llmProviderInput?.value || "ds",
      llm_model: (llmModelInput?.value || "").trim(),
      response_mode: responseMode, timeout_sec: timeoutSec,
    };
  }

  function resolveQueryTimeout(responseMode, retry = false) {
    const mode = String(responseMode || "full").trim().toLowerCase();
    if (mode === "skeleton" || mode === "skeleton_first") {
      return retry ? 90 : 60;
    }
    if (mode === "qa_fast" || mode === "quick_qa") {
      return 45;
    }
    return FULL_QUERY_TIMEOUT_SEC;
  }

  function resolveQueryTimeoutMs(responseMode, retry = false) {
    const mode = String(responseMode || "full").trim().toLowerCase();
    if (mode === "skeleton" || mode === "skeleton_first") {
      return retry ? 100000 : 70000;
    }
    if (mode === "qa_fast" || mode === "quick_qa") {
      return 52000;
    }
    return FULL_QUERY_TIMEOUT_MS;
  }

  function isQueryTimeoutError(error) {
    return String(error?.message || error || "").includes("请求超时");
  }

  async function requestQueryPayloadFromBase(query, base, { responseMode = "full", controller, retry = false } = {}) {
    const normalizedMode = String(responseMode || "full").trim().toLowerCase();
    const timeoutSec = resolveQueryTimeout(normalizedMode, retry);
    const timeoutMs = resolveQueryTimeoutMs(normalizedMode, retry);
    return apiFetch("/query", {
      base, method: "POST",
      body: JSON.stringify(buildQueryPayload(query, normalizedMode, timeoutSec)),
      signal: controller.signal, timeoutMs,
    });
  }

  async function requestQueryPayload(query, { responseMode = "full", controller, retry = false } = {}) {
    const bases = Array.from(new Set([
      _getApiBase(),
      (typeof state !== "undefined" && state.lastQueryBase) || DEFAULT_API_BASE,
      ...API_BASE_CANDIDATES,
    ].filter(Boolean)));
    let lastError = null;
    const input = document.getElementById("apiBase");
    for (const base of bases) {
      if (controller.signal.aborted) throw new Error("请求已取消。");
      try {
        const payload = await requestQueryPayloadFromBase(query, base, { responseMode, controller, retry });
        if (typeof state !== "undefined") state.lastQueryBase = base;
        if (input && input.value !== base) {
          input.value = base;
          if (typeof state !== "undefined") state.apiBase = base;
          localStorage.setItem("marathon-api-base", base);
        }
        return payload;
      } catch (error) {
        // /query 已经连上后端但生成超时，不再切换到其它端口，避免把慢响应误报成本地服务不可用。
        if (isQueryTimeoutError(error)) {
          throw error;
        }
        lastError = error;
      }
    }
    throw lastError || new Error("请求失败。");
  }

  async function submitFeedback(root) {
    if (typeof submitFeedbackApi === "function") return submitFeedbackApi(root);
    const el = root || document.getElementById("dayModalContent");
    const ctx = typeof buildFeedbackContext === "function" ? buildFeedbackContext(el) : {};
    const payload = typeof collectFeedbackPayload === "function" ? collectFeedbackPayload(el) : {};
    if (!ctx.plan_id || !ctx.event_id) {
      throw new Error("反馈需要绑定到具体训练日，请先生成并保存训练日历。");
    }
    return apiFetch(`/plans/${ctx.plan_id}/feedback`, {
      method: "POST", body: JSON.stringify(payload), timeoutMs: 45000,
    });
  }

  async function loadPlanDetail(planId) {
    if (typeof loadSavedPlan === "function") return loadSavedPlan(planId);
    try {
      const payload = await apiFetch(`/plans/${planId}`, { timeoutMs: 15000 });
      if (typeof restorePlanResponse === "function") {
        restorePlanResponse(payload, "已加载计划");
      }
      return payload;
    } catch (error) {
      throw new Error(`加载计划失败：${error.message}`);
    }
  }

  async function loadKnowledgeSourceSummary() {
    return apiFetch("/knowledge/sources/summary", { timeoutMs: 15000 });
  }

  async function loadKnowledgeSources() {
    return apiFetch("/knowledge/sources", { timeoutMs: 30000 });
  }

  // 挂载到 window 供外部引用
  window.__apiClient = {
    apiFetch, detectApiBase, requestQueryPayload, submitFeedback, loadPlanDetail,
    explainApiError, requestQueryPayloadFromBase,
    loadKnowledgeSourceSummary, loadKnowledgeSources,
  };
})();
