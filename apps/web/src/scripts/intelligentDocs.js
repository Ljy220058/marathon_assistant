// 智能文档页：复用 /query，把知识库回答与引用依据拆成用户可核对的视图。
(function () {
  window.state = window.state || { apiBase: "http://127.0.0.1:8000", apiToken: "", lastRequestId: "" };
  const form = document.querySelector("[data-docs-form]");
  const questionInput = document.querySelector("[data-docs-question]");
  const submitButton = document.querySelector("[data-docs-submit]");
  const answerPanel = document.querySelector("[data-docs-answer]");
  const answerTitle = document.querySelector("[data-docs-answer-title]");
  const answerBody = document.querySelector("[data-docs-answer-body]");
  const alertBox = document.querySelector("[data-docs-alert]");
  const evidenceList = document.querySelector("[data-docs-evidence-list]");
  const expandAllButton = document.querySelector("[data-docs-expand-all]");
  const requestId = document.querySelector("[data-docs-request-id]");
  const sourceSummary = document.querySelector("[data-source-summary]");
  const totalSourceCount = document.querySelector("[data-total-source-count]");
  const readySourceCount = document.querySelector("[data-ready-source-count]");
  const registryOnlySourceCount = document.querySelector("[data-registry-only-source-count]");
  const sourceSummaryText = document.querySelector("[data-source-summary-text]");
  const health = document.getElementById("docsHealth");

  const DEFAULT_QUESTION = "膝盖疼还能继续跑吗？";
  const LOW_RELEVANCE_THRESHOLD = 50;

  const DISPLAY_MODE_LABELS = {
    verified_source: "可定位来源",
    legacy_explanation: "解释性线索",
    graph_hint: "图谱关联线索",
    model_general_knowledge: "模型常识说明",
    needs_evidence: "待补证据",
    rejected_source: "已阻断来源",
  };

  if (!form || !questionInput || !answerPanel || !answerBody || !evidenceList) return;

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function renderPlainText(text) {
    const clean = String(text || "").trim();
    if (!clean) return "<p>知识库暂时没有生成回答，请换个问法再试。</p>";
    return clean
      .split(/\n{2,}/)
      .map((paragraph) => `<p>${escapeHtml(paragraph).replace(/\n/g, "<br />")}</p>`)
      .join("");
  }

  function setHealth(status, message) {
    if (!health) return;
    health.hidden = false;
    health.classList.toggle("ok", status === "ok");
    health.classList.toggle("error", status === "error");
    health.textContent = message;
  }

  async function refreshHealth() {
    if (!window.__apiClient?.detectApiBase) return;
    try {
      const ok = await window.__apiClient.detectApiBase();
      setHealth(ok ? "ok" : "error", ok ? "已连接" : "未连接");
    } catch {
      setHealth("error", "未连接");
    }
  }

  function setLoading(isLoading) {
    answerPanel.classList.toggle("is-loading", isLoading);
    if (submitButton) {
      submitButton.disabled = isLoading;
      submitButton.textContent = isLoading ? "生成中" : "发送";
    }
  }

  function setAlert(kind, html) {
    answerPanel.classList.toggle("is-error", kind === "error");
    if (alertBox) alertBox.innerHTML = `<span class="docs-alert-icon" aria-hidden="true">!</span><div>${html}</div>`;
  }

  function renderSourceSummary(payload) {
    if (!sourceSummary || !payload) return;
    sourceSummary.hidden = false;
    const total = payload.total_sources ?? "-";
    const ready = payload.ready_sources ?? "-";
    const registryOnly = payload.registry_only_sources ?? "-";
    if (totalSourceCount) totalSourceCount.textContent = String(total);
    if (readySourceCount) readySourceCount.textContent = String(ready);
    if (registryOnlySourceCount) registryOnlySourceCount.textContent = String(registryOnly);
    if (sourceSummaryText) {
      sourceSummaryText.textContent = `当前有 ${ready} 个可回答来源，${registryOnly} 个仅作线索。`;
    }
  }

  async function loadSourceSummary() {
    if (!window.__apiClient?.loadKnowledgeSourceSummary) return;
    try {
      renderSourceSummary(await window.__apiClient.loadKnowledgeSourceSummary());
    } catch {
      renderSourceSummary({ total_sources: "-", ready_sources: "-", registry_only_sources: "-" });
      if (sourceSummaryText) sourceSummaryText.textContent = "知识源概览暂不可用，仍可继续提问。";
    }
  }

  function collectEvidenceItems(payload) {
    const chain = payload?.evidence_chain || {};
    const candidates = [
      chain.items,
      chain.evidence,
      chain.sources,
      chain.citations,
      payload?.ranked_evidence,
      payload?.structured_report?.evidence,
    ];
    for (const candidate of candidates) {
      if (Array.isArray(candidate) && candidate.length) return candidate;
    }
    return [];
  }

  function displayModeLabel(mode) {
    return DISPLAY_MODE_LABELS[String(mode || "").trim()] || "来源状态待核对";
  }

  function parseRelevancePercent(value) {
    if (typeof value === "number" && Number.isFinite(value)) {
      return Math.max(0, Math.min(100, Math.round(value * 100 <= 100 ? value : value)));
    }
    const text = String(value ?? "").trim();
    if (!text) return null;
    const match = text.match(/(\d+(?:\.\d+)?)/);
    if (!match) return null;
    const num = Number.parseFloat(match[1]);
    if (!Number.isFinite(num)) return null;
    return num <= 1 ? Math.round(num * 100) : Math.round(num);
  }

  function formatRelevancePercent(value) {
    const parsed = parseRelevancePercent(value);
    if (parsed === null) return "相关度待核对";
    return `相关度 ${parsed}%`;
  }

  function isInjuryQuery(query) {
    return /疼|痛|伤|拉伤|扭伤|不适|肿|步态|跛|抽筋|膝|踝|足底|跟腱|胫骨|髂胫束/.test(String(query || ""));
  }

  function buildEvidenceCoverageAlert(payload, query) {
    const chain = payload?.evidence_chain || {};
    const mode = String(chain.answer_source_mode || payload?.answer_source_mode || "").trim();
    const items = collectEvidenceItems(payload);
    if (isInjuryQuery(query)) {
      return "<strong>伤病提示：</strong>如疼痛加重、肿胀或影响跑姿，请停止训练并寻求专业评估。";
    }
    if (!items.length || mode === "needs_evidence") {
      return "<strong>来源提示：</strong>当前问题需要更多可定位来源支撑（当前问题缺少可定位来源），请谨慎参考。";
    }
    return "<strong>来源提示：</strong>回答已附来源，可在右侧核对。";
  }

  function normalizeEvidenceItem(item, index) {
    const raw = item && typeof item === "object" ? item : { text: item };
    const breakdown = raw.score_breakdown && typeof raw.score_breakdown === "object" ? raw.score_breakdown : {};
    const relevancePercent = parseRelevancePercent(
      raw.relevance_percent
        ?? raw.relevance_score
        ?? raw.hybrid_score
        ?? raw.score
        ?? breakdown.relevance
        ?? breakdown.hybrid_score
        ?? breakdown.vector_score
        ?? breakdown.vector
    );
    const title = raw.topic || raw.title || raw.label || raw.citation_label || `引用依据 ${index + 1}`;
    const file = raw.source_label || raw.source_file || raw.file || raw.source || raw.document || "来源待补充";
    const locator = raw.locator_hint || raw.page_hint || raw.page || raw.page_number || raw.pages || "定位待补充";
    const sourceStatus = String(raw.source_status || "unknown");
    const hasFullText = Boolean(raw.has_full_text || sourceStatus === "ready");
    const evidenceKind = String(raw.evidence_kind || "unknown");
    const sourceStatusLabel = hasFullText || evidenceKind === "body_chunk" ? "正文证据" : "仅登记线索";
    const displayStatus = displayModeLabel(raw.display_mode) || raw.relevance || raw.relevance_label || raw.score_label || raw.kind;
    const sourceMeta = `${file} · ${formatRelevancePercent(relevancePercent)}`;
    const locatorMeta = `${locator} · ${displayStatus}`;
    const quote = raw.text_span || raw.user_facing_summary || raw.quote || raw.excerpt || raw.snippet || raw.text || raw.content || raw.summary || "当前来源只有命中线索，暂无可直接核验摘录。";
    return { title, file, page: locator, score: locatorMeta, quote, relevancePercent, sourceStatusLabel, sourceStatus, hasFullText, evidenceKind, sourceMeta, locatorMeta };
  }

  function updateExpandAllVisibility() {
    if (!expandAllButton) return;
    const rows = Array.from(evidenceList.querySelectorAll("[data-docs-evidence-row]"));
    expandAllButton.hidden = rows.length <= 1;
  }

  function renderEvidence(payload) {
    const items = collectEvidenceItems(payload).map(normalizeEvidenceItem);
    if (!items.length) {
      items.push(
        {
          title: "暂无来源",
          file: "等待提问",
          page: "",
          score: "待生成",
          quote: "回答生成后会显示可核对来源。",
          relevancePercent: null,
          sourceStatusLabel: "等待来源",
          sourceMeta: "等待提问",
          locatorMeta: "回答生成后显示摘录",
        }
      );
    }

    evidenceList.innerHTML = items.map((item, index) => {
      const expanded = item.relevancePercent === null || item.relevancePercent >= LOW_RELEVANCE_THRESHOLD;
      const lowRelevanceHint = item.relevancePercent !== null && item.relevancePercent < LOW_RELEVANCE_THRESHOLD
        ? "可能不相关，已折叠"
        : "";
      return `<section class="docs-row" data-docs-evidence-row data-relevance-percent="${escapeHtml(item.relevancePercent ?? "unknown")}">
        <button class="docs-toggle" type="button" aria-expanded="${expanded ? "true" : "false"}">
          <span class="docs-source-dot" aria-hidden="true"></span>
          <span class="docs-row-title">${escapeHtml(item.title)}</span>
          <span class="docs-chevron" aria-hidden="true">${expanded ? "⌃" : "⌄"}</span>
        </button>
        <div class="docs-source" ${expanded ? "" : "hidden"}>
          <div class="source-header">
            <div class="docs-file">${escapeHtml(item.file)}</div>
            <div class="source-status">${escapeHtml(item.sourceStatusLabel)}</div>
          </div>
          <div class="source-meta">${escapeHtml(item.sourceMeta)} · ${escapeHtml(item.locatorMeta)}${lowRelevanceHint ? ` · ${escapeHtml(lowRelevanceHint)}` : ""}</div>
          <div class="source-excerpt">${escapeHtml(item.quote)}</div>
        </div>
      </section>`;
    }).join("");
    updateExpandAllVisibility();
  }

  function updateAnswer(payload) {
    if (answerTitle) answerTitle.textContent = "AI 回答";
    if (requestId && payload?.__request_id) {
      requestId.hidden = false;
      requestId.textContent = `请求 ${payload.__request_id}`;
    }
    setAlert("info", buildEvidenceCoverageAlert(payload, questionInput.value || DEFAULT_QUESTION));
    answerBody.innerHTML = renderPlainText(payload?.report || payload?.message || "");
    renderEvidence(payload);
  }

  async function submitQuestion(event) {
    event?.preventDefault();
    const query = String(questionInput.value || "").trim() || DEFAULT_QUESTION;
    questionInput.value = query;
    setLoading(true);
    setAlert("info", "<strong>生成中：</strong>正在查找来源并生成回答。");
    answerBody.innerHTML = "<p>生成中，请稍候。</p>";
    try {
      const controller = new AbortController();
      const payload = await window.__apiClient.requestQueryPayload(query, { planLike: false, controller });
      updateAnswer(payload);
      setHealth("ok", "已连接");
    } catch (error) {
      const message = window.__apiClient?.explainApiError
        ? window.__apiClient.explainApiError(error)
        : String(error?.message || error || "请求失败");
      setAlert("error", `<strong>生成失败：</strong>${escapeHtml(message)}`);
      answerBody.innerHTML = "<p>可以检查本地 API 服务是否启动，或稍后重新生成。</p>";
      setHealth("error", "请求失败");
    } finally {
      setLoading(false);
    }
  }

  evidenceList.addEventListener("click", (event) => {
    const toggle = event.target.closest(".docs-toggle");
    if (!toggle) return;
    const row = toggle.closest("[data-docs-evidence-row]");
    const source = row?.querySelector(".docs-source");
    const nextExpanded = toggle.getAttribute("aria-expanded") !== "true";
    toggle.setAttribute("aria-expanded", String(nextExpanded));
    const chevron = toggle.querySelector(".docs-chevron");
    if (chevron) chevron.textContent = nextExpanded ? "⌃" : "⌄";
    if (source) source.hidden = !nextExpanded;
  });

  expandAllButton?.addEventListener("click", () => {
    const rows = Array.from(evidenceList.querySelectorAll("[data-docs-evidence-row]"));
    const shouldExpand = rows.some((row) => row.querySelector(".docs-toggle")?.getAttribute("aria-expanded") !== "true");
    rows.forEach((row) => {
      const toggle = row.querySelector(".docs-toggle");
      const source = row.querySelector(".docs-source");
      const chevron = row.querySelector(".docs-chevron");
      toggle?.setAttribute("aria-expanded", String(shouldExpand));
      if (source) source.hidden = !shouldExpand;
      if (chevron) chevron.textContent = shouldExpand ? "⌃" : "⌄";
    });
    expandAllButton.textContent = shouldExpand ? "全部收起" : "全部展开";
  });

  document.querySelector('[data-docs-action="retry"]')?.addEventListener("click", submitQuestion);
  document.querySelector('[data-docs-action="profile"]')?.addEventListener("click", () => {
    window.location.href = "/#profile";
  });
  document.querySelector('[data-docs-action="risk"]')?.addEventListener("click", () => {
    evidenceList.querySelector(".docs-toggle")?.focus();
  });

  form.addEventListener("submit", submitQuestion);
  refreshHealth();
  loadSourceSummary();
  updateExpandAllVisibility();
})();
