# 首页双入口信息架构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把首页从“训练日历、智能对话、画像、依据混在一起”的复杂工作台，调整为两个明确入口：`生成训练日历` 与 `问 AI 教练`，并确保两个入口各自有清晰状态、结果区域和下一步。

**Architecture:** 保留现有 Astro 页面、`app.js` 状态机、`/query` API 与日历渲染链路；本次只做前端信息架构和交互入口收敛，不重写后端、不新增依赖。新增一个轻量“任务入口层”，通过现有 `data-query-mode`、`runQuery()`、`setQueryMode()` 驱动原有功能，避免破坏训练日历和智能对话已修复的链路。

**Tech Stack:** Astro、Vanilla JavaScript、CSS、pytest contract tests、Astro build、Playwright DOM smoke check via local `playwright-core`。

---

## File Structure

- Modify: `apps/web/src/pages/index.astro`
  - 在 `#plan` 主 composer 前增加双入口任务选择区。
  - 保留原有 `#queryModeSwitch`，但弱化为当前任务状态，不作为主要入口。
  - 增加明确说明文案：训练日历会生成可点击日历；智能对话只回答问题，不改动日历。

- Modify: `apps/web/src/scripts/app.js`
  - 增加入口卡点击处理：`[data-workspace-intent]`。
  - 复用 `setQueryMode("plan" | "qa")`。
  - 根据入口设置 placeholder、按钮文字、hint，并聚焦输入框。
  - 确保智能对话返回后不强行跳日历。

- Modify: `apps/web/src/styles/workspace-scenes.css` 或 `apps/web/src/styles/components.css`
  - 增加 `.intent-entry-grid`、`.intent-entry-card` 等样式。
  - 使用现有浅色 token：`var(--panel)`、`var(--border)`、`var(--accent)`、`var(--muted)`。
  - 保持响应式：桌面两列，移动端单列。

- Modify: `tests/test_astro_frontend_contract.py`
  - 增加合同测试，保证双入口 DOM、文案、data attributes、JS handler 存在。

---

### Task 1: 添加双入口 DOM 契约测试

**Files:**
- Modify: `tests/test_astro_frontend_contract.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_astro_frontend_contract.py` 追加测试：

```python
def test_homepage_has_clear_plan_and_qa_entry_points():
    page = _read_stripped(ASTRO_PAGE)
    script = _read_stripped(APP_SCRIPT)
    styles = _read_stripped(root / "apps" / "web" / "src" / "styles" / "workspace-scenes.css")

    assert "data-workspace-intent=\"plan\"" in page
    assert "data-workspace-intent=\"qa\"" in page
    assert "生成训练日历" in page
    assert "问 AI 教练" in page
    assert "智能对话不会改动训练日历" in page
    assert "document.querySelectorAll(\"[data-workspace-intent]\")" in script
    assert "setQueryMode(intent)" in script
    assert ".intent-entry-grid" in styles
    assert ".intent-entry-card" in styles
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
PYTHONIOENCODING=utf-8 python -m pytest ../../tests/test_astro_frontend_contract.py::test_homepage_has_clear_plan_and_qa_entry_points -q
```

Expected: FAIL，因为页面、脚本和样式尚未包含双入口契约。

---

### Task 2: 在首页添加两个主入口卡片

**Files:**
- Modify: `apps/web/src/pages/index.astro`

- [ ] **Step 1: 修改 `#plan` 中 composer heading 后的结构**

在 `#workspaceSceneStatus` 后、`.question-composer` 前插入：

```astro
<div class="intent-entry-grid" aria-label="选择你现在要做的事">
  <button class="intent-entry-card is-active" type="button" data-workspace-intent="plan">
    <span class="intent-entry-kicker">训练日历</span>
    <strong>生成训练日历</strong>
    <small>根据我的情况生成可点击日历，查看每天怎么练、为什么这样练。</small>
  </button>
  <button class="intent-entry-card" type="button" data-workspace-intent="qa">
    <span class="intent-entry-kicker">智能对话</span>
    <strong>问 AI 教练</strong>
    <small>回答伤病、补给、恢复和训练问题；智能对话不会改动训练日历。</small>
  </button>
</div>
```

- [ ] **Step 2: 调整默认提示文案**

保持 `textarea#queryInput`，但 placeholder 改为更清晰：

```astro
placeholder="训练日历：可留空使用我的情况；智能对话：输入你想问的问题。"
```

`#queryHint` 默认文案改为：

```astro
<span id="queryHint" class="muted">选择“生成训练日历”或“问 AI 教练”，系统会按任务显示结果。</span>
```

---

### Task 3: 为双入口添加交互逻辑

**Files:**
- Modify: `apps/web/src/scripts/app.js`

- [ ] **Step 1: 在 query mode 初始化附近添加入口同步函数**

在已有 `setQueryMode(mode)` 定义附近加入：

```js
function syncWorkspaceIntentCards(mode) {
  document.querySelectorAll("[data-workspace-intent]").forEach((button) => {
    const isActive = button.dataset.workspaceIntent === mode;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", isActive ? "true" : "false");
  });
}
```

- [ ] **Step 2: 在 `setQueryMode(mode)` 内调用同步**

在 `setQueryMode(mode)` 末尾加入：

```js
syncWorkspaceIntentCards(currentQueryMode);
```

- [ ] **Step 3: 添加入口卡 click handler**

在全局事件绑定区加入：

```js
document.querySelectorAll("[data-workspace-intent]").forEach((button) => {
  button.addEventListener("click", () => {
    const intent = button.dataset.workspaceIntent === "qa" ? "qa" : "plan";
    setQueryMode(intent);
    if (intent === "qa") {
      queryInput.placeholder = "例如：膝盖疼还能跑吗？跑前吃什么？跑后怎么恢复？";
      queryHint.textContent = "智能对话只回答问题，不会改动当前训练日历。";
    } else {
      queryInput.placeholder = "可留空使用我的情况，或补充目标赛事、可训练日、近期伤病/疲劳。";
      queryHint.textContent = "训练日历会根据我的情况生成可点击日历。";
    }
    queryInput.focus({ preventScroll: true });
  });
});
```

---

### Task 4: 添加双入口样式

**Files:**
- Modify: `apps/web/src/styles/workspace-scenes.css`

- [ ] **Step 1: 添加桌面样式**

追加：

```css
.intent-entry-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 12px 0 16px;
}

.intent-entry-card {
  display: grid;
  gap: 6px;
  border: 1px solid var(--border);
  border-radius: 16px;
  background: var(--panel);
  color: var(--text);
  padding: 16px;
  text-align: left;
  box-shadow: var(--shadow-soft);
  cursor: pointer;
}

.intent-entry-card:hover,
.intent-entry-card:focus-visible {
  border-color: var(--border-strong);
  outline: 3px solid rgba(37, 99, 235, 0.16);
  outline-offset: 2px;
}

.intent-entry-card.is-active {
  border-color: var(--accent);
  background: var(--tech-accent);
}

.intent-entry-kicker {
  color: var(--muted);
  font-size: 12px;
  font-weight: 850;
  letter-spacing: 0.08em;
}

.intent-entry-card strong {
  font-size: 20px;
  font-weight: 900;
}

.intent-entry-card small {
  color: var(--muted);
  line-height: 1.55;
}
```

- [ ] **Step 2: 添加移动端样式**

追加：

```css
@media (max-width: 720px) {
  .intent-entry-grid {
    grid-template-columns: 1fr;
  }

  .intent-entry-card {
    padding: 14px;
  }
}
```

---

### Task 5: 运行验证

**Files:**
- Test only

- [ ] **Step 1: 运行合同测试**

Run:

```bash
PYTHONIOENCODING=utf-8 python -m pytest ../../tests/test_astro_frontend_contract.py -q
```

Expected: `44 passed` 或更多，允许已有 `langchain-community` warning。

- [ ] **Step 2: 构建前端**

Run:

```bash
npm run build
```

Expected: `Complete!`，生成 2 pages。

- [ ] **Step 3: 浏览器 smoke 验收双入口**

Run:

```bash
node --input-type=module - <<'NODE'
import playwrightCore from './node_modules/playwright-core/index.js';
const { chromium } = playwrightCore;
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
await page.goto('http://127.0.0.1:4321/', { waitUntil: 'networkidle' });
const before = await page.evaluate(() => ({
  cards: Array.from(document.querySelectorAll('[data-workspace-intent]')).map((el) => ({
    intent: el.dataset.workspaceIntent,
    active: el.classList.contains('is-active'),
    text: el.innerText,
  })),
  button: document.getElementById('runQuery')?.innerText,
  hint: document.getElementById('queryHint')?.innerText,
}));
await page.click('[data-workspace-intent="qa"]');
const afterQa = await page.evaluate(() => ({
  activeIntent: document.querySelector('[data-workspace-intent].is-active')?.dataset.workspaceIntent,
  button: document.getElementById('runQuery')?.innerText,
  hint: document.getElementById('queryHint')?.innerText,
  placeholder: document.getElementById('queryInput')?.placeholder,
}));
await page.click('[data-workspace-intent="plan"]');
const afterPlan = await page.evaluate(() => ({
  activeIntent: document.querySelector('[data-workspace-intent].is-active')?.dataset.workspaceIntent,
  button: document.getElementById('runQuery')?.innerText,
  hint: document.getElementById('queryHint')?.innerText,
  placeholder: document.getElementById('queryInput')?.placeholder,
  overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
}));
console.log(JSON.stringify({ before, afterQa, afterPlan }, null, 2));
await browser.close();
NODE
```

Expected:
- `before.cards.length === 2`
- `afterQa.activeIntent === "qa"`
- `afterQa.button === "向教练提问"`
- `afterPlan.activeIntent === "plan"`
- `afterPlan.button === "生成训练日历"`
- `overflow === false`

---

## Self-Review

Spec coverage:
- 双入口：首页 DOM task 覆盖。
- 训练日历入口：复用现有 plan mode，明确生成可点击日历。
- 智能对话入口：复用 qa mode，明确不改日历。
- 不改后端：计划只触及 Astro、CSS、app.js、contract test。
- 验证：pytest、build、Playwright smoke 覆盖。

Placeholder scan:
- 无 TBD / TODO / “类似 Task N”。

Type consistency:
- DOM attribute 使用统一：`data-workspace-intent="plan|qa"`。
- JS 使用 `button.dataset.workspaceIntent`，与 DOM dataset 映射一致。
- 样式类使用统一：`.intent-entry-grid`、`.intent-entry-card`、`.intent-entry-kicker`。
