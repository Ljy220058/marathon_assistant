// Evidence Drawer — 证据抽屉数据归一化和打开/关闭逻辑。
// 使用 IIFE 隔离，通过 window.__evidenceDrawer 暴露 API。

(function () {

  function normalizeEvidencePages(items) {
    if (!Array.isArray(items)) return [];
    return items.map((item, idx) => ({
      index: idx + 1,
      source_id: item.source_id || item.id || `evidence-${idx}`,
      title: item.title || item.source_title || item.label || "训练依据",
      source_type: item.source_type || item.evidence_tier || "reference",
      excerpt: item.excerpt || item.snippet || item.content || "",
      page: item.page || item.page_number || "",
      confidence: item.confidence || item.score || "",
      llm_general_knowledge: item.llm_general_knowledge || item.model_knowledge || "",
      is_model_knowledge: !!(item.llm_general_knowledge || item.model_knowledge),
    }));
  }

  // ── P2-6: Parse answer source mode for display ──
  function getAnswerSourceModeInfo(response) {
    const mode = String(response?.answer_source_mode || "").trim();
    const configs = {
      verified_source: { className: "source-verified", label: "有科学证据支持", icon: "✓" },
      model_general_knowledge: { className: "source-model-knowledge", label: "基于模型通用知识", icon: "i" },
      blocked_needs_evidence: { className: "source-blocked", label: "证据不足，建议仅供参考", icon: "!" },
    };
    return configs[mode] || { className: "source-none", label: "未绑定外部证据", icon: "-" };
  }

  function resolveEvidenceItemsForDrawer(day, response) {
    // 收集某个训练日关联的所有证据条目
    const items = [];
    const evidenceList = response?.evidence_items || response?.structured_report?.evidence_items || [];
    const dayEvidenceIds = Array.isArray(day?.evidence_ids)
      ? day.evidence_ids
      : Array.isArray(day?.evidence_id) ? day.evidence_id : (day?.evidence_id ? [day.evidence_id] : []);

    if (dayEvidenceIds.length > 0) {
      dayEvidenceIds.forEach((id) => {
        const match = evidenceList.find((e) => (e.id || e.source_id) === id);
        if (match) items.push(match);
      });
    }

    // 若有 llm_general_knowledge 但无外部证据，添加说明卡片
    const hasNoEvidence = items.length === 0;
    const hasModelKnowledge = day?.llm_general_knowledge || day?.explanation_source === "llm_general_knowledge";
    if (hasNoEvidence && hasModelKnowledge) {
      items.push({
        source_type: "llm_general_knowledge",
        title: "模型知识说明（未绑定外部证据）",
        excerpt: typeof day.llm_general_knowledge === "string"
          ? day.llm_general_knowledge
          : "该训练安排基于模型对训练原则的一般理解生成，未绑定具体来源文档。不能作为核心处方依据，不生成伪引用。",
        llm_general_knowledge: true,
        is_model_knowledge: true,
      });
    }

    return normalizeEvidencePages(items);
  }

  function openEvidenceDrawer(items) {
    if (typeof window.openEvidenceDrawer === "function" && window.openEvidenceDrawer !== openEvidenceDrawer) {
      return window.openEvidenceDrawer(items);
    }
    const drawer = document.getElementById("evidenceDrawer");
    const content = document.getElementById("evidenceDrawerContent");
    const count = document.getElementById("evidenceDrawerCount");
    if (!drawer || !content) return;
    const pages = normalizeEvidencePages(items);
    if (count) count.textContent = `${pages.length} 条`;
    content.innerHTML = pages.map((item) => `
      <article class="evidence-drawer-item">
        <strong>[${item.index}] ${item.title}</strong>
        ${item.page ? `<small>页码：${item.page}</small>` : ""}
        <p>${item.excerpt}</p>
        ${item.is_model_knowledge ? '<em class="model-knowledge-note">模型知识说明，非外部检索证据</em>' : ""}
      </article>
    `).join("") || '<div class="empty-state">暂无相关依据。</div>';
    drawer.classList.add("open");
    drawer.setAttribute("aria-hidden", "false");
  }

  function closeEvidenceDrawer() {
    if (typeof window.closeEvidenceDrawer === "function" && window.closeEvidenceDrawer !== closeEvidenceDrawer) {
      return window.closeEvidenceDrawer();
    }
    const drawer = document.getElementById("evidenceDrawer");
    if (drawer) {
      drawer.classList.remove("open");
      drawer.setAttribute("aria-hidden", "true");
    }
  }

  window.__evidenceDrawer = {
    openEvidenceDrawer,
    closeEvidenceDrawer,
    resolveEvidenceItemsForDrawer,
    normalizeEvidencePages,
    getAnswerSourceModeInfo,
  };
})();
