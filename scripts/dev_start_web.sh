#!/usr/bin/env bash
# 前端 astro dev 启动脚本（端口 4321）。
cd "$(dirname "$0")/../apps/web" || exit 1  # scripts/ → apps/web
echo "→ 启动前端 astro dev http://localhost:4321"
exec npm run dev
