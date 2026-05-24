#!/usr/bin/env bash
# House-DIY 重启 ComfyUI（8188）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=_service-common.sh
source "$ROOT/scripts/_service-common.sh"

echo "House-DIY restart-comfyui — $ROOT"
echo "----------------------------------------"

stop_service "ComfyUI" 8188 "$PID_DIR/comfyui.pid" || true
start_comfyui
sleep 2

if port_in_use 8188; then
  echo "----------------------------------------"
  echo "[ComfyUI] 重启完成 http://127.0.0.1:8188"
  exit 0
fi

echo "[ComfyUI] 重启失败" >&2
exit 1
