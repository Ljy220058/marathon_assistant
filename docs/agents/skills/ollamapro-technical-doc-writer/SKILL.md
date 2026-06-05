---
name: ollamapro-technical-doc-writer
description: Use this project-local skill whenever upgrading OllamaPro KnowledgeHub Markdown docs, especially index-driven batch documentation, API/process docs, architecture notes, Runbooks, test docs, and traceable technical requirements. It preserves Obsidian links, frontmatter, confidence labels, current-state boundaries, and source-backed claims.
---

# OllamaPro Technical Doc Writer

This skill is for upgrading the OllamaPro KnowledgeHub documentation in place. The goal is not to make the text longer for its own sake. The goal is to make each document useful for a future engineer who must understand the current project, verify claims, and safely continue implementation.

## Core Rules

- Preserve existing frontmatter, headings, Obsidian links, current conclusions, confidence language, and known limitations.
- Prefer current repository facts over generic product language.
- Separate evidence levels clearly:
  - `源码确认`: confirmed by a repository path or code symbol.
  - `测试确认`: confirmed by a test file or test command.
  - `文档确认`: confirmed by an existing project doc.
  - `待实测`: plausible but not run in this pass.
- Do not claim medical, sports-science, safety, production, or API behavior has been validated unless the current pass actually verified it.
- When a claim is derived from a filename, heading, or existing document instead of fresh runtime verification, say so.
- Keep Chinese as the primary prose language. Preserve API fields, commands, paths, library names, and error names in their original form.
- Keep Obsidian wiki links as `[[...]]`; do not rewrite them to normal Markdown links.

## Reference Models

Use these public documentation practices as method, not content:

- Diátaxis (`https://diataxis.fr/`): distinguish explanation, reference, how-to, and tutorial needs.
- Google Developer Style (`https://developers.google.com/style`): keep structure predictable and terms consistent.
- Microsoft Writing Style Guide (`https://learn.microsoft.com/en-us/style-guide/welcome/`): write directly, clearly, and actionably.
- Kubernetes content guide (`https://kubernetes.io/docs/contribute/style/content-guide/`): link to canonical sources and avoid copying brittle content.
- OpenAPI documentation practice (`https://learn.openapis.org/specification/docs.html`): explain fields, examples, status codes, auth, and interaction effects.
- Atlassian PRD practice (`https://www.atlassian.com/agile/product-management/requirements`): include goals, assumptions, user stories, non-goals, and success criteria for requirement docs.

## Document Type Mapping

Classify the document before expanding it:

| Type | Typical path or title | Add emphasis |
|---|---|---|
| Project state | `00_项目中枢` | current truth, confidence, migration boundary, risks |
| Requirement/process | `01_需求与范围`, `流程`, `用户角色` | goals, users, scenarios, states, non-goals, success criteria |
| Frontend module | `02_页面与交互`, `前端`, `模块`, `工作台` | component responsibility, state, API consumption, empty/error/loading cases |
| Data asset | `04_数据与资产`, `数据`, `KB`, `Chunks`, `SQLite` | owner, lifecycle, schema, persistence, privacy, governance |
| Architecture layer | `05_技术栈与架构`, `层`, `系统结构` | entrypoints, dependencies, data flow, failure modes, fallback |
| LangGraph node | title contains `节点` | node input/output, state mutation, routing, safety, tests |
| API | `06_API与流程`, title contains `API` | method/path, request/response, auth, errors, rate limits, frontend consumers |
| Runbook | `07_运行与维护`, `Runbook`, `本地运行`, `发布`, `回滚` | commands, checks, diagnostics, rollback, operational cautions |
| Test doc | `08_限制与验证`, `测试`, `验证` | test scope, fixtures, commands, expected contract, gaps |

## Upgrade Template

Append or replace a marked upgrade block:

```markdown
<!-- OLLAMAPRO_DOC_UPGRADE_START -->
## 详细技术文档升级

### 读者与用途
...

### 事实依据与证据等级
...

### 核心职责与边界
...

### 关键链路或数据流
...

### 接口、状态与失败模式
...

### 测试与验收
...

### 后续任务顺序
...

### 注意事项
...

<!-- OLLAMAPRO_DOC_UPGRADE_END -->
```

For API docs, include request/response/auth/error/frontend/test subsections. For Runbooks, include concrete commands and diagnostic order. For requirement docs, include user scenarios, success criteria, and non-goals.

## Quality Bar

Before finishing an upgraded document, check:

- It still has frontmatter and exactly one primary title.
- It names what is confirmed, what is inferred, and what is not verified.
- It gives the next engineer a task order, not just background.
- It references canonical local files or tests when available.
- It avoids turning training advice into medical certainty.
- It does not mix the historical Marathon_Assistant Flask/Jinja/SQLite project into current OllamaPro facts.
