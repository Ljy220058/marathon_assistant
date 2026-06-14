#!/usr/bin/env bash
# 后端开发启动脚本。
# 默认 8001 端口（避开 8000 冲突）；可用第一个参数覆盖，如 bash scripts/dev_start.sh 8002
# 用法：bash scripts/dev_start.sh [端口号]
set -e
cd "$(dirname "$0")/.."  # 从 scripts/ 回到项目根
export MARATHON_PORT="${1:-8001}"
export PYTHONPATH="apps/backend/src"
export MARATHON_DEV_PERMISSIVE_CORS=true  # 开发模式：允许前端 (4321) 跨域访问后端
echo "→ 启动后端 http://127.0.0.1:${MARATHON_PORT} (PYTHONPATH=${PYTHONPATH})"
exec python -m marathon_qa_assistant.apps.api_app
