# 前端 UI 统一为智能文档三栏工作台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `apps/web` 整个前端站点统一为与 `intelligent-docs` 页面一致的三栏工作台风格，并交付一个可运行的首页样板。

**Architecture:** 先抽出全站共享的 Design Tokens 和工作台布局基元，再把首页与智能文档页映射到同一套三栏结构。业务逻辑继续由现有脚本驱动，只调整 DOM 契约、布局容器和样式层级，避免功能回归。

**Tech Stack:** Astro, 原生 HTML/CSS/JS, Playwright smoke, Python contract tests, Vite/Astro build

---

## 文件地图

### 主要修改文件
- `apps/web/src/styles/base.css`：全站 Design Tokens、基础可访问性、页面底色与聚焦样式。
- `apps/web/src/styles/layout.css`：三栏工作台 Grid、左栏/主栏/依据栏布局、响应式断点。
- `apps/web/src/styles/intelligent-docs.css`：智能文档页的视觉基准样式，统一使用 tokens。
- `apps/web/src/styles/commercial-light.css`：若仍有局部浅色组件需要共享，统一收敛到 tokens。
- `apps/web/src/pages/index.astro`：首页重构为三栏工作台样板，保留现有 `id` / `data-*` 契约。
- `apps/web/src/pages/intelligent-docs.astro`：将智能文档页改为共享工作台结构，作为视觉基准页。
- `apps/web/src/scripts/app.js`：修正任何依赖旧层级的选择器，补齐稳定的行为契约。
- `apps/web/src/scripts/intelligentDocs.js`：对齐智能文档页的事件绑定与空状态表现。
- `apps/web/src/scripts/apiClient.js`：仅在需要时补充对新 DOM 容器的兼容读取，不改 API 协议。
- `apps/web/src/scripts/evidenceDrawer.js`：如右侧依据区 DOM 调整，保持抽屉开关兼容。
- `tests/test_astro_frontend_contract.py`：补充页面结构、token、风险提示和数据属性契约测试。
- `apps/web/scripts/smoke-workspace.mjs`：补充桌面/移动端三栏布局、风险提示优先级和隐藏面板检查。

### 新增或可选新增文件
- 如首页重构后需要把公共工作台片段拆出来，可新增 `apps/web/src/scripts/workbenchLayout.js` 作为纯 DOM 助手，但只有在现有 `app.js` 明显过长时才拆。

---

### Task 1: 提取全站 Design Tokens 与基础可访问性

**Files:**
- Modify: `apps/web/src/styles/base.css`
- Modify: `apps/web/src/styles/intelligent-docs.css`
- Modify: `apps/web/src/styles/commercial-light.css`
- Test: `tests/test_astro_frontend_contract.py`

- [ ] **Step 1: 写一个会失败的 token 契约测试**

```python
def test_shared_workbench_tokens_exist_in_base_css():
    base = _read_stripped(root / "apps" / "web" / "src" / "styles" / "base.css")
    for token in [
        "--app-bg",
        "--app-shell-bg",
        "--app-border",
        "--app-text",
        "--radius-shell",
        "--radius-container",
        "--radius-component",
    ]:
        assert token in base
```

- [ ] **Step 2: 运行测试确认它先失败**

Run: `python -m pytest tests/test_astro_frontend_contract.py -k shared_workbench_tokens -v`
Expected: FAIL，因为 `base.css` 里还没有这些 Design Tokens。

- [ ] **Step 3: 写最小实现**

在 `apps/web/src/styles/base.css` 顶部加入共享 token：

```css
:root {
  --app-bg: #eef5ef;
  --app-shell-bg: #fdfefc;
  --app-border: #173321;
  --app-border-soft: #d9e3dc;
  --app-text: #173321;
  --app-muted: #63746b;
  --app-accent: #35a762;
  --app-nav-height: 64px;
  --app-shell-padding: 24px;
  --radius-shell: 24px;
  --radius-container: 16px;
  --radius-component: 8px;
}
```

同时把 `body`、`html`、`:focus-visible`、`grid-background`、链接/按钮基础色改成 token 驱动，保证智能文档页和首页共享相同底层视觉。

- [ ] **Step 4: 再跑测试确认通过**

Run: `python -m pytest tests/test_astro_frontend_contract.py -k shared_workbench_tokens -v`
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add apps/web/src/styles/base.css apps/web/src/styles/intelligent-docs.css apps/web/src/styles/commercial-light.css tests/test_astro_frontend_contract.py
git commit -m "feat(ui): add shared workbench tokens"
```

---

### Task 2: 把首页重构成智能文档同款三栏工作台

**Files:**
- Modify: `apps/web/src/pages/index.astro`
- Modify: `apps/web/src/styles/layout.css`
- Modify: `apps/web/src/scripts/app.js`
- Test: `tests/test_astro_frontend_contract.py`
- Test: `apps/web/scripts/smoke-workspace.mjs`

- [ ] **Step 1: 写会失败的首页结构测试**

```python
def test_index_page_uses_three_column_workbench_structure():
    content = _read_stripped(root / "apps" / "web" / "src" / "pages" / "index.astro")
    for marker in ["app-shell", "app-side", "app-main", "app-evidence"]:
        assert marker in content
```

- [ ] **Step 2: 运行测试确认它先失败**

Run: `python -m pytest tests/test_astro_frontend_contract.py -k three_column_workbench_structure -v`
Expected: FAIL，因为首页还没改成 `app-shell` 结构。

- [ ] **Step 3: 写首页最小结构改造**

把首页的主内容从现有卡片堆叠改为三栏工作台：

```astro
<main id="workspace" class="app-container">
  <header class="top-nav">...</header>
  <nav class="mobile-quick-nav">...</nav>
  <section class="app-shell" aria-label="训练工作台">
    <aside class="app-side" aria-label="Workspace">
      <!-- 训练导航、准备、画像摘要、历史与设置 -->
    </aside>
    <section class="app-main" aria-label="Main">
      <!-- 生成训练日历、今日训练、日历主体、反馈入口 -->
    </section>
    <aside class="app-evidence" aria-label="Evidence">
      <!-- 风险提示、依据、快捷操作 -->
    </aside>
  </section>
</main>
```

关键要求：

- 保留现有 `id` 与 `data-*`，例如 `runQuery`、`calendar`、`dayModal`、`evidenceDrawer`、`statusPanel`、`adjustmentHistory`。
- 保留 `data-plan-generation-entry`、`data-calendar-view`、`data-drawer-action`、`data-open-drawer-section` 等行为契约。
- `app.js` 里所有点击、折叠、日历切换、历史计划、反馈入口都只能继续依赖这些稳定契约，不再新增对视觉 class 层级的依赖。
- 把原来只在移动端才有的风险提示，前置到主任务区顶部或紧贴今日训练卡。

在 `layout.css` 中把 `.app-layout`、`.main-stack`、`.side-rail` 改造成首页三栏 Grid 的基础布局，并把旧的 `dashboard-grid`、`workspace-flow`、`hero-panel` 逐步收敛进统一工作台结构。

- [ ] **Step 4: 运行首页结构测试确认通过**

Run: `python -m pytest tests/test_astro_frontend_contract.py -k three_column_workbench_structure -v`
Expected: PASS。

- [ ] **Step 5: 运行工作台 smoke 验证桌面与移动端**

Run: `cd apps/web && npm run smoke:workspace`
Expected: PASS，且桌面端 `app-shell` 可见、移动端无横向溢出、风险提示不被压到不可见位置。

- [ ] **Step 6: 提交**

```bash
git add apps/web/src/pages/index.astro apps/web/src/styles/layout.css apps/web/src/scripts/app.js tests/test_astro_frontend_contract.py apps/web/scripts/smoke-workspace.mjs
git commit -m "feat(ui): rebuild home as workbench layout"
```

---

### Task 3: 让智能文档页成为共享视觉基准页

**Files:**
- Modify: `apps/web/src/pages/intelligent-docs.astro`
- Modify: `apps/web/src/styles/intelligent-docs.css`
- Modify: `apps/web/src/scripts/intelligentDocs.js`
- Test: `tests/test_astro_frontend_contract.py`

- [ ] **Step 1: 写会失败的智能文档共享样式测试**

```python
def test_intelligent_docs_page_uses_shared_workbench_classes():
    content = _read_stripped(root / "apps" / "web" / "src" / "pages" / "intelligent-docs.astro")
    assert "docs-top" in content
    assert "docs-shell" in content
    assert "docs-side" in content
    assert "docs-main-column" in content
    assert "docs-evidence" in content
```

- [ ] **Step 2: 运行测试确认它先失败**

Run: `python -m pytest tests/test_astro_frontend_contract.py -k intelligent_docs_page_uses_shared_workbench_classes -v`
Expected: FAIL 或部分 FAIL，直到智能文档页结构对齐完成。

- [ ] **Step 3: 写最小实现**

把智能文档页继续作为视觉基准，但把可复用布局明确化：

```astro
<main class="docs-shell" id="docs-main">
  <aside class="docs-side">...</aside>
  <section class="docs-main-column">...</section>
  <aside class="docs-evidence">...</aside>
</main>
```

在 `intelligent-docs.css` 中把页面颜色、边框、圆角、输入框、按钮、折叠依据、风险提示全部切回 `base.css` 的共享 token，不再写死一套孤立颜色。确保 `docs-alert`、`docs-answer`、`docs-row` 使用 `--radius-container` / `--radius-component` 的层级，而不是全部使用大圆角。

- [ ] **Step 4: 重新跑契约测试**

Run: `python -m pytest tests/test_astro_frontend_contract.py -k intelligent_docs_page_uses_shared_workbench_classes -v`
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add apps/web/src/pages/intelligent-docs.astro apps/web/src/styles/intelligent-docs.css apps/web/src/scripts/intelligentDocs.js tests/test_astro_frontend_contract.py
git commit -m "feat(ui): align intelligent docs with shared workbench"
```

---

### Task 4: 把响应式降级和风险提示层级修正到安全可见

**Files:**
- Modify: `apps/web/src/styles/layout.css`
- Modify: `apps/web/src/styles/intelligent-docs.css`
- Modify: `apps/web/src/scripts/app.js`
- Modify: `apps/web/src/scripts/intelligentDocs.js`
- Test: `apps/web/scripts/smoke-workspace.mjs`
- Test: `tests/test_astro_frontend_contract.py`

- [ ] **Step 1: 写会失败的移动端风险提示测试**

```python
def test_mobile_risk_hint_is_promoted_near_main_action():
    content = _read_stripped(root / "apps" / "web" / "src" / "pages" / "index.astro")
    assert "risk" in content.lower()
    assert "今日训练" in content or "训练风险" in content
```

- [ ] **Step 2: 运行测试确认它先失败或不完整**

Run: `python -m pytest tests/test_astro_frontend_contract.py -k mobile_risk_hint_is_promoted_near_main_action -v`
Expected: FAIL，直到风险提示从右栏下沉变成主任务区附近的显式区块。

- [ ] **Step 3: 写最小实现**

在 `layout.css` 与 `intelligent-docs.css` 中完成响应式规则：

```css
@media (max-width: 1200px) {
  .app-shell {
    grid-template-columns: 200px 1fr 280px;
    gap: 16px;
  }
}

@media (max-width: 900px) {
  .app-shell {
    grid-template-columns: 1fr 280px;
  }

  .app-side {
    display: none; /* 或转为抽屉入口，但不得阻塞主任务与风险提示 */
  }
}

@media (max-width: 768px) {
  .app-shell {
    grid-template-columns: 1fr;
    margin: 0;
    border: 0;
    border-radius: 0;
  }

  .risk-hint,
  .docs-alert {
    order: -1;
  }
}
```

移动端的原则：

- 风险提示必须在主操作区附近出现，不允许只放在折叠底部。
- 引用依据和规则来源可以折叠或下移。
- 左栏可以折叠成抽屉或快捷导航，但不能影响生成、查看和反馈入口。

- [ ] **Step 4: 跑 smoke 检查桌面与移动端**

Run: `cd apps/web && npm run smoke:workspace`
Expected: PASS，且移动端没有可见横向滚动条或被裁切的风险提示。

- [ ] **Step 5: 提交**

```bash
git add apps/web/src/styles/layout.css apps/web/src/styles/intelligent-docs.css apps/web/src/scripts/app.js apps/web/src/scripts/intelligentDocs.js apps/web/scripts/smoke-workspace.mjs tests/test_astro_frontend_contract.py
git commit -m "fix(ui): promote risk hints on responsive layout"
```

---

### Task 5: 做全量验证并修正选择器回归

**Files:**
- Modify: `apps/web/src/scripts/app.js`
- Modify: `apps/web/src/scripts/intelligentDocs.js`
- Modify: `apps/web/src/scripts/apiClient.js`
- Modify: `apps/web/src/scripts/evidenceDrawer.js`
- Modify: `tests/test_astro_frontend_contract.py`
- Modify: `apps/web/scripts/smoke-workspace.mjs`

- [ ] **Step 1: 补一个回归测试，防止再写回视觉 class 依赖**

```python
def test_frontend_scripts_use_stable_behavior_contracts():
    content = _read_stripped(APP_SCRIPT)
    assert "data-action=\"generate-plan\"" in content or "data-plan-generation-entry" in content
    assert ".calendar-card .btn-submit" not in content
    assert "parentNode.querySelector" not in content
```

- [ ] **Step 2: 运行针对性测试**

Run: `python -m pytest tests/test_astro_frontend_contract.py -q`
Expected: PASS。

- [ ] **Step 3: 运行前端构建**

Run: `cd apps/web && npm run build`
Expected: PASS，Astro 产物能正常生成。

- [ ] **Step 4: 运行 smoke**

Run: `cd apps/web && npm run smoke:workspace`
Expected: PASS，桌面/移动端都能通过基础可视检查。

- [ ] **Step 5: 修复所有失败项并重复验证**

如果 build 或 smoke 失败，只修复失败点对应的 DOM 契约或样式，不做无关重构；修复后重新执行同一条命令直到通过。

- [ ] **Step 6: 最终提交**

```bash
git add apps/web/src/scripts/app.js apps/web/src/scripts/intelligentDocs.js apps/web/src/scripts/apiClient.js apps/web/src/scripts/evidenceDrawer.js tests/test_astro_frontend_contract.py apps/web/scripts/smoke-workspace.mjs
git commit -m "fix(ui): harden workbench contract and smoke"
```

---

## 计划自查

### 1. Spec 覆盖检查

- 全站统一成智能文档三栏工作台：Task 1、2、3。
- Design Tokens 与圆角层级：Task 1。
- 首页样板：Task 2。
- 智能文档页作为共享视觉基准：Task 3。
- 响应式降级与风险提示优先级：Task 4。
- DOM 契约防回归与验证：Task 2、5。

### 2. 占位符扫描

已检查本计划，不包含 `TBD`、`TODO`、`implement later`、`fill in details` 等占位表达。

### 3. 类型与命名一致性

计划中统一使用：

- 工作台容器：`app-container`、`app-shell`、`app-side`、`app-main`、`app-evidence`
- 智能文档容器：`docs-top`、`docs-shell`、`docs-side`、`docs-main-column`、`docs-evidence`
- 稳定行为契约：`id`、`data-action`、`data-state`、`data-*`

这些命名在各任务中保持一致，没有引入前后不一致的新函数名或新接口名。
