# 贡献与维护指南

> 本仓库采用 monorepo 管理产品代码、前端、研究材料、数据入口和产物索引。提交前先判断改动类型，再运行对应检查。

## 开发环境

- 后端包路径：`apps/backend/src`
- 前端工作区：`apps/web`
- 研究脚本：`tools/research/`
- 知识库工具：`tools/kb/`
- 仓库治理脚本：`tools/dev/check_repo.py`

推荐后端启动：

```powershell
$env:PYTHONPATH="apps/backend/src"
python -m uvicorn marathon_qa_assistant.apps.api_app:app --host 127.0.0.1 --port 8000
```

推荐前端启动：

```powershell
cd apps/web
npm run dev
```

## 改动分流

| 改动类型 | 主要目录 | 必跑检查 |
|---|---|---|
| 后端 API / 计划生成 | `apps/backend/src` | `pytest tests/test_api_app.py tests/test_plan_workflow_expectations.py -q` |
| 日程与课表生成 | `apps/backend/src/marathon_qa_assistant/services` | `pytest tests/test_daily_schedule_generator.py -q` |
| 前端页面和样式 | `apps/web/src` | `cd apps/web; npm run build; npm run smoke:workspace` |
| 研究脚本与 benchmark | `research/`、`tools/research/` | 对应项目 smoke + manifest 路径检查 |
| 数据、上传资料、产物 | `data/`、`artifacts/` | `python tools/dev/check_repo.py --scope hygiene` |
| 文档和治理规则 | `docs/`、`TODO.md`、`.github/` | `python tools/dev/check_repo.py --scope docs` |

## 提交前最小检查

```powershell
python tools/dev/check_repo.py
git diff --check
git status --short --branch
```

如果改动涉及产品运行路径，再追加对应 targeted tests。不要用“全量测试太慢”替代 targeted tests；先跑最相关的一组。

## 代码管理规则

- 不在根目录新增产品源码、数据缓存或构建产物。
- 新代码和工具路径使用 ASCII + `snake_case`。
- 新文档路径使用 ASCII slug，中文写在 Markdown 标题中。
- 大文件、PDF、zip、FAISS index 和 release 包必须有 manifest 或发布说明。
- 前后端重构必须保留 public facade 一轮，例如 `api_app.app`、`build_structured_training_plan_skeleton()`、`generate_daily_schedule()`。
- 不在一个 PR 中同时做目录迁移、产品逻辑修改和研究产物整理。

## PR 要求

每个 PR 至少说明：

- 改了什么。
- 如何验证。
- 是否影响 API、数据、artifacts、research outputs。
- 是否保留兼容入口。

使用 `.github/PULL_REQUEST_TEMPLATE.md` 填写即可。
