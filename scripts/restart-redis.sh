#!/usr/bin/env bash
# House-DIY 重启 Redis Docker 容器（6379）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=_service-common.sh
source "$ROOT/scripts/_service-common.sh"

echo "House-DIY restart-redis — $ROOT"
echo "----------------------------------------"

stop_redis_container || true
ensure_redis

if redis_ready; then
  echo "----------------------------------------"
  echo "[Redis] 重启完成 redis://127.0.0.1:6379/0"
  exit 0
fi

echo "[Redis] 重启失败" >&2
exit 1
