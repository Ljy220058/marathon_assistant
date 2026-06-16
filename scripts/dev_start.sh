#!/usr/bin/env bash
# 后端开发启动脚本。
# 默认 8001 端口（避开 8000 冲突）；可用第一个参数覆盖，如 bash scripts/dev_start.sh 8002
# 用法：bash scripts/dev_start.sh [端口号]
set -e
cd "$(dirname "$0")/.."  # 从 scripts/ 回到项目根
export MARATHON_PORT="${1:-8000}"
export PYTHONPATH="apps/backend/src"
export MARATHON_DEV_PERMISSIVE_CORS=1  # 开发模式：允许前端 (4321) 跨域访问后端（_env_flag 只认 "1"，不认 true/yes）
export DEEPSEEK_MODEL=deepseek-chat  # 官方标准模型（比 v4-pro 快 3-5×），避免计划生成 504 超时
export MARATHON_RERANK_ENABLED=1  # 开启 reranker（装 GPU torch 后自动用 cuda，速度+质量兼顾；CPU torch 时会慢）
export MARATHON_DEV_FORCE_DEEPSEEK=1  # dev 强制 DeepSeek：忽略前端 localStorage 残留的 ollama（本地推理慢，导致计划生成 504），统一走云端 DeepSeek（快 3-5×）
echo "→ 启动后端 http://127.0.0.1:${MARATHON_PORT} (PYTHONPATH=${PYTHONPATH})"
exec python -m marathon_qa_assistant.apps.api_app
