#!/usr/bin/env bash
# House-DIY 一键停止：Vue + FastAPI + ComfyUI + Redis（与 start-all.sh 对应）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="${ROOT}/.run"
REDIS_CONTAINER="house-diy-redis"
KEEP_REDIS=false

usage() {
  cat <<EOF
用法: $(basename "$0") [选项]

停止由 start-all.sh 拉起的组件（逆序：Vue → FastAPI → ComfyUI → Redis）。

选项:
  --keep-redis    停止进程服务但保留 Redis 容器运行
  -h, --help      显示此帮助

说明:
  oMLX (:8000) 不由本仓库脚本启动，此处不会停止。
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --keep-redis)
      KEEP_REDIS=true
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "未知选项: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

port_in_use() {
  lsof -i ":$1" -sTCP:LISTEN -t >/dev/null 2>&1
}

# 先 TERM 进程树，超时再 KILL；最后按端口兜底清理残留监听
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
        if kill -0 "$pid" 2>/dev/null; then
          kill -KILL "$pid" 2>/dev/null || true
        fi
      done
    fi
  fi

  if port_in_use "$port"; then
    echo "[$name] 警告: 端口 $port 仍在监听"
    return 1
  fi
  echo "[$name] 已停止"
  return 0
}

stop_redis() {
  if [[ "$KEEP_REDIS" == true ]]; then
    echo "[Redis] 保留运行 (--keep-redis)"
    return 0
  fi

  if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
    echo "[Redis] Docker 不可用，跳过"
    return 0
  fi

  if ! docker container inspect "$REDIS_CONTAINER" >/dev/null 2>&1; then
    echo "[Redis] 容器不存在，跳过"
    return 0
  fi

  if docker ps --filter "name=^/${REDIS_CONTAINER}$" --format '{{.Names}}' 2>/dev/null | grep -qx "$REDIS_CONTAINER"; then
    echo "[Redis] 停止容器 $REDIS_CONTAINER..."
    docker stop "$REDIS_CONTAINER" >/dev/null
    echo "[Redis] 已停止"
  else
    echo "[Redis] 容器未运行，跳过"
  fi
}

echo "House-DIY stop-all — $ROOT"
echo "----------------------------------------"

fail=0
stop_service "Vue" 5173 "$PID_DIR/web.pid" || fail=1
stop_service "FastAPI" 8080 "$PID_DIR/api.pid" || fail=1
stop_service "ComfyUI" 8188 "$PID_DIR/comfyui.pid" || fail=1
stop_redis || fail=1

echo "----------------------------------------"
if curl -s -o /dev/null -w '' --connect-timeout 2 "http://127.0.0.1:8000/health" 2>/dev/null; then
  echo "[oMLX] 仍在 8000 运行（未由本脚本管理，需手动关闭）"
else
  echo "[oMLX] 未检测到 8000"
fi
echo "----------------------------------------"

if [[ "$fail" -eq 0 ]]; then
  echo "House-DIY 组件已全部停止。"
else
  echo "部分组件停止失败，请检查上方警告。" >&2
  exit 1
fi
