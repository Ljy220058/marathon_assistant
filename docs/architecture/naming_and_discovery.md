# 命名与检索治理

> 版本：V1
>
> 范围：仓库路径命名、检索边界、manifest 入口和当前命名例外。本轮不批量重命名既有文件。

## 目标

- 让开发者和 agent 能稳定找到代码、文档、研究材料和产物。
- 让长题名 PDF、中文文档和历史产物有短入口，不靠直接猜文件名。
- 让默认 `rg` 检索排除缓存和本地依赖，但不误排除正式 `archive/`、`artifacts/`、`research/` 证据。
- 让后续重命名有规则、有验收命令、有回滚边界。

## 命名规则

| 范围 | 新增命名规则 | 例外处理 |
|---|---|---|
| 代码、工具、配置路径 | 全 ASCII，使用 `snake_case`。示例：`tools/research/stai/check_text_integrity.py`。 | 既有公开 import 和已记录兼容 wrapper 不在本轮改名。 |
| Python 包路径 | 包名保持 `marathon_qa_assistant.*`，路径使用 ASCII 目录。 | 不因目录治理改变公开 import。 |
| 产品/架构文档 | 路径使用 ASCII slug，中文写在 Markdown 标题里。示例：`docs/product/backlog.md`。 | 既有中文文件名保留，后续逐步迁入 ASCII slug。 |
| 研究分析草稿 | 新文件使用 `NN_topic_slug.md`，标题可中文。示例：`03_claim_boundary.md`。 | 旧中文编号文件暂不重命名，先由项目 TODO 或 manifest 串起来。 |
| 论文、文献、PDF 原始文件 | 可保留长题名或原始文件名，但必须有 manifest 提供短名、主题、来源、用途和路径。 | 不直接批量改 PDF 文件名，避免破坏引用链。 |
| `data/` | 原始资料、curated 资料、上传种子和 quarantine 分层管理。 | 隔离资料使用 `_quarantine_*` 前缀并在 manifest 写明状态。 |
| `artifacts/` | 按项目、日期、用途分层，例如 `artifacts/research_runs/stai2026/<run_id>/`。 | 旧 UI audit 目录先保留，由 `artifacts/MANIFEST.md` 标注迁移目标。 |
| `archive/` | 按项目、日期、来源批次分层，不靠零散目录名表达含义。 | `archive/local_caches/` 仅用于本地缓存归档并默认忽略。 |

## 默认检索流程

1. 搜索代码和文档时默认用 `rg`：

```powershell
rg "<keyword>" apps docs research tools tests
rg --files | rg "<path-or-topic>"
```

2. 搜索长题名资料时先看 manifest，再打开原始文件：

```powershell
Get-Content research/mexrxbench/analysis/exercise_health_cross_research_2026/manifest.md
Get-Content data/uploads/seed/manifest.md
Get-Content artifacts/MANIFEST.md
```

3. 如果要全仓库查缓存噪声，使用：

```powershell
rg --files | rg "node_modules|\.npm-cache|\.pytest_cache|__pycache__|archive/local_caches|apps/web/dist"
```

期望无输出。该检查依赖根目录 `.rgignore`。

## `.rgignore` 边界

默认排除：

- `apps/web/node_modules/`
- `apps/web/.npm-cache/`
- `apps/web/dist/`
- `.pytest_cache/`
- `**/__pycache__/`
- `archive/local_caches/`

默认不排除：

- `archive/`
- `artifacts/`
- `research/`
- `data/uploads/seed/`

原因：这些目录可能包含历史证据、实验产物、发布包或原始资料，不能因为噪声高就从检索里消失。

## Manifest 契约

高噪声入口至少维护以下字段：

| 字段 | 含义 |
|---|---|
| `short_id` | 人和 agent 使用的短名，优先 ASCII。 |
| `path` | 仓库内相对路径。 |
| `topic` | 主题或项目归属。 |
| `source` | 来源、生成脚本、上传批次或已知出处。未知时写 `unknown`，不要猜。 |
| `purpose` | 当前用途：默认检索、curation 候选、隔离、release、审计等。 |
| `quality_state` | `active`、`curated`、`quarantined`、`legacy`、`generated` 等。 |
| `next_action` | 需要补元数据、迁移、退役或验证时写清下一步。 |

当前 manifest 入口：

- [M-EXRxBench 运动健康交叉研究 manifest](../../research/mexrxbench/analysis/exercise_health_cross_research_2026/manifest.md)
- [上传种子资料 manifest](../../data/uploads/seed/manifest.md)
- [Artifacts manifest](../../artifacts/MANIFEST.md)

## 当前例外

统计命令：

```powershell
git -c core.quotePath=false ls-files
```

当前快照日期：2026-05-21。

| 指标 | 数量 | 处理策略 |
|---|---:|---|
| 已跟踪文件 | 1146 | 作为本轮统计基线。 |
| 非 ASCII 路径 | 30 | 不批量重命名；新文件优先 ASCII slug，旧文件后续逐项迁移。 |
| 带空格路径 | 1 | 通过 manifest 标注；后续迁移时改为 `snake_case`。 |
| 路径长度超过 120 字符 | 143 | 主要集中在研究论文 notes/PDF；先依赖 manifest 和编号索引。 |

代表性例外：

- `archive/2026-04-30_security_reports/软件安全测试汇总_2026-04-29.md`
- `data/uploads/seed/Level2꞉Chapter4꞉BasicTrainingMethodology_English.pdf`
- `data/uploads/seed/动作库.pdf`
- `docs/architecture/LangGraph_实验记录.md`
- `docs/product/plans/周期化训练课分配改造计划.md`
- `docs/ui_redesign/00_UI改进路线总纲.md`
- `data/uploads/seed/_quarantine_low_quality_20260512_knowledge_cleanup/Periodization for Massive Strength Gains.pdf`
- `research/mexrxbench/analysis/exercise_health_cross_research_2026/papers/004_effects-of-different-doses-of-exercise-and-diet-induced-weight-loss-on-beta-cell-funct.md`

## 后续迁移原则

- 先改索引和引用，再改文件名。
- 每次只迁移一个项目或一个目录族。
- 重命名前先运行 `git grep` 找引用，迁移后运行链接检查。
- 对论文和实验产物，保留旧名到新名的 manifest 映射至少一个维护周期。
