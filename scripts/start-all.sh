#!/usr/bin/env bash
# House-DIY 一键启动：ComfyUI + FastAPI + Vue dev
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${HOME}/House-DIY-env"
COMFYUI_DIR="${HOME}/ComfyUI"
PID_DIR="${ROOT}/.run"
mkdir -p "$PID_DIR"

cleanup() {
  echo ""
  echo "正在停止 House-DIY 服务..."
  for pidfile in "$PID_DIR"/*.pid; do
    [[ -f "$pidfile" ]] || continue
    pid="$(cat "$pidfile")"
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
    fi
    rm -f "$pidfile"
  done
}
trap cleanup EXIT INT TERM

port_in_use() {
  lsof -i ":$1" -sTCP:LISTEN -t >/dev/null 2>&1
}

start_if_free() {
  local name="$1" port="$2" cmd="$3" pidfile="$4"
  if port_in_use "$port"; then
    echo "[$name] 端口 $port 已在监听，跳过启动"
    return
  fi
  echo "[$name] 启动中 (port $port)..."
  bash -lc "$cmd" &
  echo $! > "$pidfile"
  sleep 2
}

echo "House-DIY start-all — $ROOT"
echo "----------------------------------------"

# oMLX 提示（App 版需手动启动）
if curl -s -o /dev/null -w '' --connect-timeout 2 "http://127.0.0.1:8000/health" 2>/dev/null; then
  echo "[oMLX] 已在 8000 运行"
else
  echo "[oMLX] 未检测到 8000 — 请先启动 oMLX App 或 brew services start omlx"
fi

# ComfyUI
if [[ -d "$COMFYUI_DIR" ]]; then
  start_if_free "ComfyUI" 8188 \
    "cd '$COMFYUI_DIR' && source '$VENV/bin/activate' && python main.py --listen 127.0.0.1 --port 8188" \
    "$PID_DIR/comfyui.pid"
else
  echo "[ComfyUI] 目录不存在: $COMFYUI_DIR"
fi

# FastAPI
if [[ ! -x "$VENV/bin/uvicorn" ]]; then
  echo "[FastAPI] 安装依赖..."
  "$VENV/bin/pip" install -q -r "$ROOT/server/requirements.txt"
fi
start_if_free "FastAPI" 8080 \
  "cd '$ROOT/server' && source '$VENV/bin/activate' && uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload" \
  "$PID_DIR/api.pid"

# Vue
if [[ ! -d "$ROOT/web/node_modules" ]]; then
  echo "[Vue] npm install..."
  (cd "$ROOT/web" && npm install)
fi
start_if_free "Vue" 5173 \
  "cd '$ROOT/web' && npm run dev -- --host 127.0.0.1 --port 5173" \
  "$PID_DIR/web.pid"

echo "----------------------------------------"
echo "服务地址:"
echo "  前端   http://127.0.0.1:5173"
echo "  API    http://127.0.0.1:8080/api/v1/health"
echo "  ComfyUI http://127.0.0.1:8188"
echo "  oMLX   http://127.0.0.1:8000"
echo ""
echo "按 Ctrl+C 停止由本脚本启动的服务"
echo "----------------------------------------"

# 保持前台
wait
