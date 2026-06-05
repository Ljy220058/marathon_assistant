# Codex-native TODO Automation Design

## 背景

当前项目的 `TODO.md` 已经同时承载产品模块、论文任务、待确认问题、来源文档和验收线索。用户希望把 TODO 工作流做成可被 Codex 使用的模块化、系统化、自动化能力，而不是建设独立 Web 看板或长期项目管理服务。

本设计面向全局 Codex 使用，依托已创建的 `codex-work-team` plugin/MCP。第一版目标是让 Codex 能在任意项目中扫描 TODO、结构化任务、生成执行计划、进入受控自动执行、运行验证并回写 Markdown 状态。

## 目标

1. 提供跨项目通用的 TODO 自动化能力。
2. 保留 Markdown 作为人类可读入口和回写界面。
3. 使用结构化存储作为自动化状态真源。
4. 接入 `codex-work-team` 的角色分工和 subagent 调度规则。
5. 支持受控自动权限：低风险任务可自动执行，高风险操作必须请求用户确认。
6. 每次扫描、计划、执行、验证、回写都留下审计记录。

## 非目标

1. 第一版不做 Web 看板。
2. 第一版不做长期运行的本地服务。
3. 第一版不自动进行 Git commit、push 或 PR。
4. 第一版不跨项目批量修改文件，除非用户明确批准。
5. 第一版不尝试替代现有项目管理工具，只为 Codex 提供可调用的自动化底座。

## 总体架构

```text
C:\Users\26318\plugins\codex-work-team
  |
  |-- .mcp.json
  |
  |-- scripts\
  |     |-- codex_work_team_mcp.py
  |     |-- todo_automation\
  |           |-- scanner.py
  |           |-- normalizer.py
  |           |-- store.py
  |           |-- writer.py
  |           |-- audit.py
  |
  |-- skills\
        |-- codex-work-team
        |-- codex-todo-automation
```

全局数据目录：

```text
C:\Users\26318\.codex\todo-automation\
  todo.sqlite
  audit.jsonl
```

数据流：

```text
TODO.md / docs / README / AGENTS.md
  -> todo_scan_project
  -> todo_normalize
  -> todo.sqlite
  -> todo_plan
  -> 用户批准 ready 任务
  -> Codex/codex-work-team 执行
  -> test-runner 验证
  -> todo_update_status
  -> todo_writeback
  -> audit.jsonl
```

## 模块设计

### scanner.py

负责发现项目中的待办来源。

扫描对象：

- `TODO.md`
- `README.md`
- `AGENTS.md`
- `docs/**/*.md`
- 可配置的项目文档路径

第一版只识别 Markdown 任务项和明确的待确认条目：

```text
- [ ] 任务标题
- [x] 已完成任务
- [ ] 待确认：...
```

输出为任务候选，不直接改变任务状态。

### normalizer.py

负责把任务候选转成结构化任务。

核心字段：

```text
task_id
project_root
source_file
source_line
title
module
priority
status
risk_level
source_refs
acceptance_hint
verification_hint
created_at
updated_at
```

模块推断优先来自 Markdown 标题层级。例如 `## 用户画像模块` 下的任务自动归入 `用户画像模块`。

风险等级第一版采用保守规则：

- `low`：文档更新、单文件小修、明确验收标准。
- `medium`：涉及代码修改、测试补充、UI 行为变更。
- `high`：架构/API/数据模型/依赖/Git/跨项目/删除文件。

### store.py

负责 SQLite 读写。

第一版表：

```text
projects
tasks
task_events
task_plans
task_verifications
```

SQLite 是自动化状态真源。Markdown 只作为导入来源和回写界面。

### writer.py

负责把完成状态和验证摘要回写到 Markdown。

第一版只允许安全回写：

- 将原任务行从 `[ ]` 改为 `[x]`。
- 在任务行后追加简短完成备注。
- 不重排整份 `TODO.md`。
- 不删除原文。

示例：

```text
- [x] 落地 RunnerIdentityCard。完成：2026-05-11；验证：pytest tests/test_profile_identity_card.py
```

### audit.py

负责写入追加式 JSONL 审计日志。

事件类型：

```text
scan
normalize
plan
approve
execute_start
execute_finish
verify_start
verify_finish
writeback
blocked
failed
```

每条事件记录：

```text
timestamp
project_root
task_id
event_type
actor
summary
details
```

## MCP 工具设计

新增一个或多个 MCP server，注册在 `codex-work-team` plugin 的 `.mcp.json` 中。

第一版工具：

```text
todo_scan_project(root)
  扫描项目 TODO 来源并入库任务候选。

todo_normalize(root)
  将候选任务结构化，补全模块、状态、风险和验收提示。

todo_list(root?, status?, module?, risk_level?)
  查询任务库。

todo_plan(task_id)
  生成执行计划、建议角色分工和验证命令。

todo_approve(task_id)
  将任务标记为 ready，允许 Codex 受控自动执行。

todo_update_status(task_id, status, note?)
  更新任务状态并写审计日志。

todo_writeback(task_id)
  将已完成任务回写到来源 Markdown。

todo_audit(task_id)
  查看任务的审计事件链。
```

## 状态机

```text
discovered
  从 Markdown 扫描到，但尚未结构化。

normalized
  已归一化入库。

planned
  已生成执行计划。

ready
  用户已批准进入受控自动执行。

in_progress
  Codex 正在处理。

blocked
  缺信息、风险过高或需要用户决策。

verification
  实现完成，等待或正在验证。

done
  验证通过，已回写。

failed
  执行或验证失败。

deferred
  用户或系统主动延后。
```

允许的常规流转：

```text
discovered -> normalized -> planned -> ready -> in_progress -> verification -> done
planned -> blocked
in_progress -> blocked
verification -> failed
failed -> planned
ready -> deferred
```

## Codex 工作流

用户触发：

```text
使用 codex-work-team，扫描本项目 TODO 并列出可自动执行任务
```

执行流程：

1. `coordinator` 调用 `todo_scan_project` 和 `todo_normalize`。
2. 调用 `todo_list` 展示任务清单、风险等级和推荐顺序。
3. 用户批准一批任务进入 `ready`。
4. `coordinator` 调用 `todo_plan`。
5. 根据任务类型使用 `codex-work-team` 分配角色。
6. 低风险实现由主 Codex 或 worker subagent 执行。
7. 使用 `test-runner` 或项目现有命令验证。
8. 调用 `todo_update_status` 记录结果。
9. 验证通过后调用 `todo_writeback`。
10. `reviewer` 对中高风险结果做最终审查。

## 受控自动权限

自动允许：

- 扫描 Markdown 和项目文档。
- 结构化任务入库。
- 生成执行计划。
- 派发只读 explorer 分析。
- 执行低风险代码或文档修改。
- 运行项目已有测试、lint、build 命令。
- 更新任务状态。
- 回写已完成任务状态。
- 写审计日志。

必须请求用户确认：

- 安装依赖。
- 修改全局配置。
- 删除文件。
- 跨项目批量修改。
- 修改架构、API、数据库 schema 或持久化格式。
- 执行 Git commit、push、PR。
- 执行破坏性命令。
- 验收标准不明确但任务影响用户可见行为。

## 验证策略

第一版验证分三层：

1. 工具级验证：MCP initialize、tools/list、tools/call smoke test。
2. 数据级验证：扫描当前项目 `TODO.md`，确认任务数量、模块、来源行和状态正确。
3. 回写级验证：使用临时 Markdown fixture 验证 `[ ] -> [x]` 和完成备注，不直接在真实 `TODO.md` 上做破坏性试验。

项目任务执行时，优先使用已有验证命令：

- Python 项目：`python -m pytest` 或具体测试文件。
- 前端项目：`npm test`、`npm run lint`、`npm run build`。
- 无测试时：执行语法检查或导入检查，并在任务审计中标记验证限制。

## 第一版交付物

1. `codex-todo-automation` skill。
2. `todo_automation` Python 模块。
3. SQLite schema 初始化逻辑。
4. TODO MCP 工具注册。
5. 扫描、归一化、查询、审批、状态更新、回写、审计工具。
6. 当前项目 `TODO.md` 的只读扫描验证。
7. 临时 fixture 的回写验证。

## 风险与约束

1. Markdown 格式不统一会导致扫描漏项。第一版只支持明确 checkbox 待办。
2. 自动回写必须保持最小改动，避免重排文档造成大 diff。
3. Codex 执行任务时仍需遵守项目 AGENTS.md 和用户全局习惯。
4. 结构化任务库和 Markdown 可能短暂不一致，回写前必须重新检查来源行内容是否仍匹配。
5. 高风险任务必须进入 `blocked`，不能为了自动化强行执行。

## 成功标准

1. Codex 能在当前项目扫描 `TODO.md` 并生成结构化任务列表。
2. 用户能批准某个任务进入 `ready`。
3. Codex 能基于 `task_id` 生成执行计划。
4. 低风险任务完成后能记录验证结果。
5. 已完成任务能安全回写来源 Markdown。
6. `audit.jsonl` 能追踪每个任务从扫描到回写的关键事件。
