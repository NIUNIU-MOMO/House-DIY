#!/usr/bin/env bash
# House-DIY 公共变量与函数（供 restart-*.sh 复用）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${HOME}/House-DIY-env"
COMFYUI_DIR="${HOME}/ComfyUI"
COMFYUI_VENV="${COMFYUI_DIR}/venv"
REDIS_CONTAINER="house-diy-redis"
PID_DIR="${ROOT}/.run"

mkdir -p "$PID_DIR"

port_in_use() {
  lsof -i ":$1" -sTCP:LISTEN -t >/dev/null 2>&1
}

redis_ready() {
  docker exec "$REDIS_CONTAINER" redis-cli ping 2>/dev/null | grep -q PONG
}

ensure_docker() {
  if docker info >/dev/null 2>&1; then
    return 0
  fi
  if command -v colima >/dev/null 2>&1; then
    echo "[Redis] Docker 未就绪，尝试启动 Colima..."
    colima start
    sleep 2
  fi
  docker info >/dev/null 2>&1
}

ensure_redis() {
  if redis_ready; then
    return 0
  fi

  if ! ensure_docker; then
    echo "[Redis] Docker 不可用 — 请启动 Colima 或手动运行 $REDIS_CONTAINER" >&2
    return 1
  fi

  if docker container inspect "$REDIS_CONTAINER" >/dev/null 2>&1; then
    echo "[Redis] 启动容器 $REDIS_CONTAINER..."
    docker start "$REDIS_CONTAINER" >/dev/null
  else
    echo "[Redis] 创建并启动 $REDIS_CONTAINER (redis:7)..."
    docker pull redis:7
    docker run -d \
      --name "$REDIS_CONTAINER" \
      --restart unless-stopped \
      -p 6379:6379 \
      redis:7 >/dev/null
  fi

  sleep 1
  if redis_ready; then
    echo "[Redis] PONG"
    return 0
  fi

  echo "[Redis] 启动后 ping 失败 — 请检查: docker logs $REDIS_CONTAINER" >&2
  return 1
}

stop_redis_container() {
  if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
    echo "[Redis] Docker 不可用，跳过停止"
    return 0
  fi

  if ! docker container inspect "$REDIS_CONTAINER" >/dev/null 2>&1; then
    echo "[Redis] 容器不存在，跳过停止"
    return 0
  fi

  if docker ps --filter "name=^/${REDIS_CONTAINER}$" --format '{{.Names}}' 2>/dev/null | grep -qx "$REDIS_CONTAINER"; then
    echo "[Redis] 停止容器 $REDIS_CONTAINER..."
    docker stop "$REDIS_CONTAINER" >/dev/null
  fi
}

stop_service() {
  local name="$1" port="$2" pidfile="$3"

  echo "[$name] 停止中..."

  if [[ -f "$pidfile" ]]; then
    local pid
    pid="$(cat "$pidfile")"
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
    rm -f "$pidfile"
  fi

  if port_in_use "$port"; then
    local pids
    pids="$(lsof -i ":$port" -sTCP:LISTEN -t 2>/dev/null | sort -u | tr '\n' ' ' || true)"
    if [[ -n "${pids// /}" ]]; then
      echo "[$name] 清理端口 $port 残留: ${pids// /, }"
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

  if port_in_use "$port"; then
    echo "[$name] 警告: 端口 $port 仍在监听" >&2
    return 1
  fi

  echo "[$name] 已停止"
  return 0
}

start_comfyui() {
  if [[ ! -d "$COMFYUI_DIR" ]]; then
    echo "[ComfyUI] 目录不存在: $COMFYUI_DIR" >&2
    return 1
  fi
  if [[ ! -x "${COMFYUI_VENV}/bin/python" ]]; then
    echo "[ComfyUI] 虚拟环境未找到: ${COMFYUI_VENV}" >&2
    return 1
  fi
  if port_in_use 8188; then
    echo "[ComfyUI] 端口 8188 已在监听"
    return 0
  fi

  echo "[ComfyUI] 启动中 (port 8188)..."
  bash -lc "cd '$COMFYUI_DIR' && source '${COMFYUI_VENV}/bin/activate' && python main.py --listen 127.0.0.1 --port 8188" &
  echo $! > "$PID_DIR/comfyui.pid"
  sleep 2

  if port_in_use 8188; then
    echo "[ComfyUI] 已就绪"
    return 0
  fi

  echo "[ComfyUI] 启动失败" >&2
  return 1
}
