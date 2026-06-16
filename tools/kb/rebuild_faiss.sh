#!/bin/bash
# 从 chunks.jsonl 重建 v2_sharded 各分片 FAISS 索引
#
# 用法:
#   bash tools/kb/rebuild_faiss.sh                          # 重建全部分片
#   bash tools/kb/rebuild_faiss.sh nutrition medical_safety # 只重建指定分片
#
# 前置条件:
#   Ollama 正在运行且 bge-m3:latest 已拉取 → ollama pull bge-m3:latest
#
# 频率: KB chunks.jsonl 发生变更后手动执行

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

CONDA_ENV="torch2.5.1"

# ── 激活 conda 环境 ───────────────────────────────────────────────────────────
# 兼容 conda init 未写入 .bashrc 的情况（Windows Git Bash / WSL 均适用）
CONDA_BASE="$(conda info --base 2>/dev/null || true)"
if [ -n "$CONDA_BASE" ]; then
    # shellcheck source=/dev/null
    source "$CONDA_BASE/etc/profile.d/conda.sh"
    conda activate "$CONDA_ENV"
    echo "✓ conda 环境已激活: $CONDA_ENV"
else
    echo "⚠ 未找到 conda，跳过环境激活（假设当前 Python 已正确）"
fi

cd "$PROJECT_ROOT"

echo ""
echo "=== v2_sharded FAISS 重建 ==="
echo "项目根目录: $PROJECT_ROOT"
echo "Python:      $(python --version 2>&1)"
echo ""

# 委托给 Python 脚本（支持参数透传）
if [ $# -gt 0 ]; then
    python tools/kb/rebuild_sharded_faiss.py --shards "$@"
else
    python tools/kb/rebuild_sharded_faiss.py
fi
