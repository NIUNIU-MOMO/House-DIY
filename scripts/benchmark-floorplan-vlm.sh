#!/usr/bin/env bash
# 户型 VLM 基准测试：对 6 个黄金样本输出对比表
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${HOME}/House-DIY-env"
PYTHON="${VENV}/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  echo "[benchmark] 未找到虚拟环境: $VENV" >&2
  echo "请先创建 venv 并安装 server/requirements.txt" >&2
  exit 1
fi

cd "$ROOT/server"
export PYTHONPATH="."

exec "$PYTHON" "$ROOT/scripts/benchmark_floorplan_vlm.py" "$@"
