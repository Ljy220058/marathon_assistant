// Evidence Drawer — 证据抽屉数据归一化和打开/关闭逻辑。
// 使用 IIFE 隔离，通过 window.__evidenceDrawer 暴露 API。

(function () {
  const DISPLAY_MODE_LABELS = {
    verified_source: "可定位来源",
    legacy_explanation: "旧知识库解释性来源",
    graph_hint: "图谱关联线索",
    model_general_knowledge: "模型常识说明",
    needs_evidence: "待补证据",
    rejected_source: "已阻断来源",
  };

  function text(value, fallback = "") {
    const raw = String(value || "").trim();
    return raw || fallback;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function displayModeLabel(mode) {
    const key = String(mode || "").trim();
    return DISPLAY_MODE_LABELS[key] || "训练依据";
  }

  // ── 证据层级标签（Task 4: evidence tier）──
  const EVIDENCE_TIER_CONFIG = {
    scientific_evidence: { label: "📚 科学文献", cssClass: "tier-scientific" },
    exercise_reference: { label: "🏃 训练动作参考", cssClass: "tier-exercise" },
    protocol_rule: { label: "⚙ 系统规则层", cssClass: "tier-protocol" },
  };

  function tierLabel(tier) {
    const key = String(tier || "").trim();
    const config = EVIDENCE_TIER_CONFIG[key];
    return config ? config.label : "";
  }

  function tierClass(tier) {
    const key = String(tier || "").trim();
    const config = EVIDENCE_TIER_CONFIG[key];
    return config ? config.cssClass : "tier-exercise";
  }

  /** 前端 fallback：无 evidence_tier 的旧数据自动从 source_file/display_mode 推断。 */
  function inferEvidenceTier(item) {
    const sourceFile = String(item?.source_file || item?.document || "").toLowerCase();
    const displayMode = String(item?.display_mode || item?.source_type || "").toLowerCase();
    const domainPack = String(item?.domain_pack || "").toLowerCase();
    // 科学文献特征
    if (["doi", "pmid", "10.", "pubmed"].some(kw => sourceFile.includes(kw))) return "scientific_evidence";
    if (["sports_science", "literature", "research_paper"].includes(domainPack)) return "scientific_evidence";
    // 系统规则特征
    if (["protocol_rule", "system_rule"].includes(domainPack)) return "protocol_rule";
    if (displayMode === "protocol_rule" || item?.evidence_domain === "protocol_rule") return "protocol_rule";
    // 动作库特征
    if (sourceFile.includes("动作库") || domainPack === "action_library") return "exercise_reference";
    // 默认 fallback：动作库参考（最保守分类）
    return "exercise_reference";
  }

  function normalizeLocator(item) {
    const pageHint = item?.page_hint || item?.page || item?.page_number || "";
    const section = item?.section || item?.section_title || "";
    const locatorHint = item?.locator_hint || section || (pageHint ? `页码提示：${pageHint}` : "");
    return { pageHint: text(pageHint), section: text(section), locatorHint: text(locatorHint) };
  }

  function canShowCitationBadge(item) {
    const sourceUrl = text(item?.source_url);
    const hasLocator = Boolean(text(item?.page) || text(item?.section));
    return Boolean(sourceUrl && hasLocator);
  }

  function normalizeEvidencePages(items) {
    if (!Array.isArray(items)) return [];
    return items.map((item, idx) => {
      const locator = normalizeLocator(item || {});
      const displayMode = item?.display_mode || item?.source_type || item?.evidence_tier || "legacy_explanation";
      const sourceStatus = String(item?.source_status || "unknown");
      const hasFullText = Boolean(item?.has_full_text || sourceStatus === "ready");
      const evidenceKind = String(item?.evidence_kind || "unknown");
      const sourceStatusLabel = hasFullText || evidenceKind === "body_chunk" ? "正文证据" : "仅登记线索";
      const excerpt = item?.text_span || item?.user_facing_summary || item?.excerpt || item?.snippet || item?.content || item?.summary || "";
      // 完整原文：后端 evidence_bundle.text 未截断，前端仅 excerpt 被截为 300 字
      const fullText = item?.text || item?.full_text || "";
      const hasExpandableText = fullText.length > excerpt.length + 20;
      // 证据层级标注：优先使用后端 evidence_tier，fallback 推断
      const evidenceTier = item?.evidence_tier || inferEvidenceTier(item || {});
      return {
        index: idx + 1,
        source_id: item?.source_id || item?.id || item?.evidence_id || item?.chunk_id || `evidence-${idx}`,
        title: text(item?.source_label || item?.title || item?.source_title || item?.label || item?.source_name || item?.document, "训练依据"),
        source_type: item?.source_type || item?.evidence_tier || "reference",
        display_mode: displayMode,
        display_mode_label: displayModeLabel(displayMode),
        source_status: sourceStatus,
        has_full_text: hasFullText,
        evidence_kind: evidenceKind,
        source_status_label: sourceStatusLabel,
        excerpt: text(excerpt, item?.display_mode === "needs_evidence" ? "当前结论仍待补充可核验证据。" : "后端暂未返回用户可见摘录。"),
        full_text: text(fullText, excerpt),
        has_expandable_text: hasExpandableText,
        summary: text(item?.user_facing_summary),
        page: locator.pageHint,
        page_hint: locator.pageHint,
        section: locator.section,
        locator_hint: locator.locatorHint,
        source_url: text(item?.source_url),
        can_show_citation: canShowCitationBadge(item || {}),
        source_authority: item?.source_authority || item?.kb_metadata?.source_authority || "",
        confidence: item?.confidence || item?.score || "",
        is_model_knowledge: displayMode === "model_general_knowledge" || !!(item?.llm_general_knowledge || item?.model_knowledge),
        evidence_tier: evidenceTier,
        tier_label: tierLabel(evidenceTier),
        tier_class: tierClass(evidenceTier),
      };
    });
  }

  // ── P2-6: Parse answer source mode for display ──
  function getAnswerSourceModeInfo(response) {
    const mode = String(response?.answer_source_mode || "").trim();
    const configs = {
      verified_source: { className: "source-verified", label: "有科学证据支持", icon: "✓" },
      model_general_knowledge: { className: "source-model-knowledge", label: "基于模型通用知识", icon: "i" },
      needs_evidence: { className: "source-blocked", label: "证据不足，建议仅供参考", icon: "!" },
      blocked_needs_evidence: { className: "source-blocked", label: "证据不足，建议仅供参考", icon: "!" },
    };
    return configs[mode] || { className: "source-none", label: "未绑定外部证据", icon: "-" };
  }

  function evidenceChainItems(response) {
    const chain = response?.evidence_chain;
    if (Array.isArray(chain?.items)) return chain.items;
    if (Array.isArray(chain)) return chain;
    return response?.evidence_items || response?.structured_report?.evidence_items || [];
  }

  function collectDayEvidenceRefs(day) {
    const refs = [];
    const push = (value) => {
      if (Array.isArray(value)) value.forEach(push);
      else if (value && typeof value === "object") push(value.id || value.evidence_id || value.source_id || value.chunk_id);
      else if (value) refs.push(String(value));
    };
    push(day?.evidence_ids);
    push(day?.evidence_id);
    push(day?.evidence_refs);
    if (day?.field_sources && typeof day.field_sources === "object") {
      Object.values(day.field_sources).forEach(push);
    }
    return Array.from(new Set(refs));
  }

  function evidenceMatchesRef(item, ref) {
    return [item?.id, item?.evidence_id, item?.source_id, item?.chunk_id, item?.citation_label]
      .filter(Boolean)
      .some((value) => String(value) === String(ref));
  }

  function resolveEvidenceItemsForDrawer(day, response) {
    // 优先使用 canonical evidence_chain.items，并尽量按训练日证据引用关联。
    const evidenceList = evidenceChainItems(response);
    const refs = collectDayEvidenceRefs(day);
    let items = evidenceList;
    if (refs.length > 0) {
      const matched = evidenceList.filter((item) => refs.some((ref) => evidenceMatchesRef(item, ref)));
      if (matched.length) items = matched;
    }

    const hasNoEvidence = !items.length;
    const hasModelKnowledge = day?.llm_general_knowledge || day?.explanation_source === "llm_general_knowledge";
    if (hasNoEvidence && hasModelKnowledge) {
      items = [{
        display_mode: "model_general_knowledge",
        source_label: "模型常识说明（未绑定外部证据）",
        text_span: typeof day.llm_general_knowledge === "string"
          ? day.llm_general_knowledge
          : "该训练安排基于模型对训练原则的一般理解生成，未绑定具体来源文档。不能作为核心处方依据，不生成伪引用。",
        user_facing_summary: "模型常识说明，非外部检索证据。",
      }];
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
      <article class="evidence-drawer-item evidence-status-card">
        ${item.tier_label ? `<span class="evidence-tier-tag ${item.tier_class}">${item.tier_label}</span>` : ""}
        <strong>[${item.index}] ${item.title}</strong>
        ${item.source_authority ? `<span class="evidence-authority-badge authority-${item.source_authority.toLowerCase()}">${item.source_authority}级来源</span>` : ""}
        <small>${item.display_mode_label} · ${item.source_status_label}</small>
        ${item.can_show_citation ? `<a class="evidence-citation-link" href="${item.source_url}" target="_blank" rel="noreferrer">查看原文定位</a>` : ""}
        ${item.evidence_tier === "scientific_evidence" && item.source_url ? `<a class="evidence-doi-link" href="${item.source_url}" target="_blank" rel="noreferrer">📄 查看文献（DOI/PMID）</a>` : ""}
        ${item.locator_hint ? `<small class="evidence-locator-hint">${item.locator_hint}</small>` : ""}
        <p>${item.excerpt}</p>
        ${item.has_expandable_text ? `
          <button class="evidence-expand-toggle" onclick="var t=this;var d=t.nextElementSibling;var open=d.style.display==='block';d.style.display=open?'none':'block';t.textContent=open?'▸ 展开全文':'▾ 收起全文';">▸ 展开全文</button>
          <div class="evidence-full-text" style="display:none;">${escapeHtml(item.full_text)}</div>
        ` : ""}
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
    displayModeLabel,
    canShowCitationBadge,
    tierLabel,
    tierClass,
    inferEvidenceTier,
  };
})();
