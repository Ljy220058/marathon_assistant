import test from "node:test";
import assert from "node:assert/strict";

import { createBrowserHarness, loadBrowserScript } from "./browser-script-harness.mjs";


test("feedback modal escapes dynamic HTML fields", () => {
  const harness = createBrowserHarness();
  loadBrowserScript("src/scripts/feedbackModal.js", harness);

  const html = harness.window.__feedbackModal.buildFeedbackResultHtml({
    generation_status: "suggested",
    next_day_adjustment: '<img src=x onerror=alert(1)>',
    weekly_adjustment: '<script>alert("xss")</script>',
    affected_events: [{ day_label: "<b>周二</b>" }],
    feedback_replan: {
      patches: [
        {
          original: { main_set: 'javascript:alert(1)' },
          suggested: { main_set: '<a href="javascript:alert(2)">bad</a>' },
        },
      ],
    },
  });

  assert.equal(html.includes("<script>"), false);
  assert.equal(html.includes("<img"), false);
  assert.equal(html.includes("javascript:alert"), false);
  assert.equal(html.includes("&lt;img src=x onerror=alert(1)&gt;"), true);
  assert.equal(html.includes("&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;"), true);
});


test("calendar renderer escapes fallback day labels and workout type", () => {
  const harness = createBrowserHarness();
  const calendarElement = { innerHTML: "" };
  harness.document.__setElement("calendar", calendarElement);
  loadBrowserScript("src/scripts/calendarRenderer.js", harness);

  harness.window.__calendarRenderer.renderCalendar({
    daily_schedule_cards: [
      {
        day_label: '<img src=x onerror=alert(1)>',
        training_type: '<script>alert(1)</script>',
      },
    ],
  });

  assert.equal(calendarElement.innerHTML.includes("<script>"), false);
  assert.equal(calendarElement.innerHTML.includes("<img"), false);
  assert.equal(calendarElement.innerHTML.includes("&lt;img src=x onerror=alert(1)&gt;"), true);
  assert.equal(calendarElement.innerHTML.includes("&lt;script&gt;alert(1)&lt;/script&gt;"), true);
});


test("api client preserves timeout error instead of switching ports", async () => {
  const harness = createBrowserHarness({
    state: { apiBase: "http://127.0.0.1:8000", lastQueryBase: "", apiToken: "", lastRequestId: "" },
    fetch: async () => {
      throw new Error("请求超时，已停止等待本地训练服务响应。");
    },
  });
  harness.document.__setElement("apiBase", { value: "http://127.0.0.1:8000" });
  harness.document.__setElement("llmProvider", { value: "ds" });
  harness.document.__setElement("llmModel", { value: "" });
  loadBrowserScript("src/scripts/apiClient.js", harness);

  await assert.rejects(
    harness.window.__apiClient.requestQueryPayload("今天适合怎么练？", {
      planLike: false,
      controller: new AbortController(),
    }),
    /请求超时，已停止等待本地训练服务响应。/,
  );
});


test("api client routes knowledge source endpoints through public summary and expert detail APIs", async () => {
  const requests = [];
  const harness = createBrowserHarness({
    state: { apiBase: "http://127.0.0.1:8000", lastQueryBase: "", apiToken: "", lastRequestId: "" },
    fetch: async (url) => {
      requests.push(String(url));
      return {
        ok: true,
        status: 200,
        statusText: "OK",
        headers: { get: () => "" },
        json: async () => ({}),
      };
    },
  });
  harness.document.__setElement("apiBase", { value: "http://127.0.0.1:8000" });
  loadBrowserScript("src/scripts/apiClient.js", harness);

  await harness.window.__apiClient.loadKnowledgeSourceSummary();
  await harness.window.__apiClient.loadKnowledgeSources();

  assert.deepEqual(requests, [
    "http://127.0.0.1:8000/knowledge/sources/summary",
    "http://127.0.0.1:8000/knowledge/sources",
  ]);
});


test("api client uses qa_fast mode for non-plan coach questions", async () => {
  const requests = [];
  const harness = createBrowserHarness({
    state: { apiBase: "http://127.0.0.1:8000", lastQueryBase: "", apiToken: "", lastRequestId: "" },
    fetch: async (_url, options) => {
      requests.push(JSON.parse(options.body));
      return {
        ok: true,
        status: 200,
        statusText: "OK",
        headers: { get: () => "" },
        json: async () => ({}),
      };
    },
  });
  harness.document.__setElement("apiBase", { value: "http://127.0.0.1:8000" });
  harness.document.__setElement("llmProvider", { value: "ds" });
  harness.document.__setElement("llmModel", { value: "" });
  loadBrowserScript("src/scripts/apiClient.js", harness);

  await harness.window.__apiClient.requestQueryPayload("今天适合怎么练？", {
    planLike: false,
    controller: new AbortController(),
  });

  assert.equal(requests[0].response_mode, "qa_fast");
  assert.equal(requests[0].timeout_sec, 45);
});
