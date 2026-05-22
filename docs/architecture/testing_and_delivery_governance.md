# 测试配置与共享交付治理

> 目的：补充仓库治理规则，明确 `pytest.ini`、多 agent 共享契约和最终验收命令的版本管理边界。

## 根目录测试配置

- 根目录允许保留 `pytest.ini`。
- `pytest.ini` 的职责是把默认 pytest 收集范围限制到项目 `tests/`。
- 这样可以避免 `python -m pytest` 误收集 `archive/local_caches/` 中的第三方包测试。
- 不允许把业务临时配置、个人路径或环境密钥写入 `pytest.ini`。

## 多 Agent 共享契约

- 后端、前端、QA/reviewer 和版本管理 agent 必须定期复查 [共享交付契约](../quality/shared_delivery_contract.md)。
- 任一 agent 修改跨端 API、DOM/data attribute、migration、状态枚举、观测指标、验证命令或版本范围时，必须同步更新共享契约。
- 如果发现其他 agent 的改动与共享契约冲突，不允许静默覆盖；先记录冲突，再做最小兼容修复。

## 共同验收

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest -q

cd apps/web
npm run build
$env:WORKSPACE_URL='http://127.0.0.1:4322/#workspace'
npm run smoke:workspace

cd ../..
python tools/dev/check_repo.py --scope hygiene
git diff --check
```

## 版本边界

- 不使用 `git add .`。
- 不提交缓存、构建产物、个人画像、本地数据或无关 agent 改动。
- 每个版本单元都要有清楚的文件范围、验收命令和剩余风险说明。
