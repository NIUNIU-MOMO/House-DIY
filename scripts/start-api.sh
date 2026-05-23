#!/usr/bin/env bash
# House-DIY 仅启动 / 重启 FastAPI 后端（8080）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${HOME}/House-DIY-env"
PID_DIR="${ROOT}/.run"
API_PORT=8080
API_PIDFILE="${PID_DIR}/api.pid"

mkdir -p "$PID_DIR"

port_in_use() {
  lsof -i ":$1" -sTCP:LISTEN -t >/dev/null 2>&1
}

stop_api() {
  echo "[FastAPI] 停止中..."

  if [[ -f "$API_PIDFILE" ]]; then
    local pid
    pid="$(cat "$API_PIDFILE")"
    if kill -0 "$pid" 2>/dev/null; then
      pkill -TERM -P "$pid" 2>/dev/null || true
      kill -TERM "$pid" 2>/dev/null || true
      local i
      for i in $(seq 1 10); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 1
      done
      if kill -0 "$pid" 2>/dev/null; then
        pkill -KILL -P "$pid" 2>/dev/null || true
        kill -KILL "$pid" 2>/dev/null || true
      fi
    fi
    rm -f "$API_PIDFILE"
  fi

  if port_in_use "$API_PORT"; then
    local pids
    pids="$(lsof -i ":$API_PORT" -sTCP:LISTEN -t 2>/dev/null | sort -u | tr '\n' ' ' || true)"
    if [[ -n "${pids// /}" ]]; then
      echo "[FastAPI] 清理端口 $API_PORT 残留: ${pids// /, }"
      local pid
      for pid in $pids; do
        kill -TERM "$pid" 2>/dev/null || true
      done
      sleep 2
      for pid in $pids; do
        kill -0 "$pid" 2>/dev/null && kill -KILL "$pid" 2>/dev/null || true
      done
    fi
  fi

  if port_in_use "$API_PORT"; then
    echo "[FastAPI] 错误: 端口 $API_PORT 仍被占用" >&2
    exit 1
  fi
  echo "[FastAPI] 已停止"
}

cleanup() {
  echo ""
  echo "正在停止 FastAPI..."
  stop_api
}
trap cleanup EXIT INT TERM

echo "House-DIY start-api — $ROOT"
echo "----------------------------------------"

if [[ -f "$API_PIDFILE" ]] || port_in_use "$API_PORT"; then
  echo "[FastAPI] 检测到运行中，执行重启..."
  stop_api
else
  echo "[FastAPI] 未在运行，直接启动..."
fi

if [[ ! -x "$VENV/bin/uvicorn" ]]; then
  echo "[FastAPI] 安装依赖..."
  "$VENV/bin/pip" install -q -r "$ROOT/server/requirements.txt"
fi

echo "[FastAPI] 启动中 (port $API_PORT)..."
bash -lc "cd '$ROOT/server' && source '$VENV/bin/activate' && uvicorn app.main:app --host 127.0.0.1 --port $API_PORT --reload" &
echo $! > "$API_PIDFILE"
sleep 2

if ! port_in_use "$API_PORT"; then
  echo "[FastAPI] 启动失败，请检查上方日志" >&2
  rm -f "$API_PIDFILE"
  exit 1
fi

echo "----------------------------------------"
echo "  API  http://127.0.0.1:${API_PORT}/api/v1/health"
echo "  文档 http://127.0.0.1:${API_PORT}/docs"
echo ""
echo "按 Ctrl+C 停止 FastAPI"
echo "----------------------------------------"

wait
