#!/usr/bin/env bash
# House-DIY 依赖验收脚本 — 对齐 docs/04 §6 验收清单
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS=0
FAIL=0
WARN=0

green() { printf '\033[32m✓ %s\033[0m\n' "$1"; PASS=$((PASS + 1)); }
red()   { printf '\033[31m✗ %s\033[0m\n' "$1"; FAIL=$((FAIL + 1)); }
yellow(){ printf '\033[33m! %s\033[0m\n' "$1"; WARN=$((WARN + 1)); }

load_omlx_key() {
  if [[ -n "${HOUSE_DIY_OMLX_API_KEY:-}" ]]; then
    return
  fi
  if [[ -f "$ROOT/server/.env" ]]; then
    # shellcheck disable=SC1091
    set -a
    source "$ROOT/server/.env" 2>/dev/null || true
    set +a
  fi
}

check_http() {
  local name="$1" url="$2" expected="${3:-200}"
  local code
  code="$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 "$url" 2>/dev/null || echo "000")"
  if [[ "$code" == "$expected" ]]; then
    green "$name ($url) HTTP $code"
  else
    red "$name ($url) HTTP $code (期望 $expected)"
  fi
}

echo "House-DIY 环境检查 — $ROOT"
echo "----------------------------------------"

# Python venv
if [[ -x "${HOME}/House-DIY-env/bin/python" ]]; then
  ver="$("${HOME}/House-DIY-env/bin/python" --version 2>&1)"
  green "Python venv: $ver"
else
  red "Python venv 未找到: ~/House-DIY-env"
fi

# Node
if command -v node >/dev/null 2>&1; then
  green "Node $(node --version)"
else
  red "Node 未安装"
fi

# oMLX
load_omlx_key
if [[ -n "${HOUSE_DIY_OMLX_API_KEY:-}" ]]; then
  models_code="$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 \
    -H "Authorization: Bearer ${HOUSE_DIY_OMLX_API_KEY}" \
    "http://127.0.0.1:8000/v1/models" 2>/dev/null || echo "000")"
  if [[ "$models_code" == "200" ]]; then
    green "oMLX /v1/models (已认证)"
  else
    red "oMLX /v1/models HTTP $models_code"
  fi
else
  check_http "oMLX 端口" "http://127.0.0.1:8000/health"
  yellow "未配置 HOUSE_DIY_OMLX_API_KEY，跳过模型列表认证检查"
fi

# ComfyUI
check_http "ComfyUI" "http://127.0.0.1:8188/"

# Redis
if docker ps --filter name=house-diy-redis --format '{{.Names}}' 2>/dev/null | grep -q house-diy-redis; then
  if docker exec house-diy-redis redis-cli ping 2>/dev/null | grep -q PONG; then
    green "Redis house-diy-redis PONG"
  else
    red "Redis 容器运行中但 ping 失败"
  fi
else
  red "Redis 容器 house-diy-redis 未运行"
fi

# Vault
VAULT="${HOUSE_DIY_VAULT_PATH:-$HOME/House-DIY-Vault}"
if [[ -d "$VAULT/Cases" && -d "$VAULT/.house-diy/chroma" ]]; then
  green "Obsidian Vault: $VAULT"
else
  red "Vault 目录不完整: $VAULT"
fi

# vault-templates
if [[ -f "$ROOT/vault-templates/case-template.md" ]]; then
  green "vault-templates 已就绪"
else
  red "vault-templates 缺失"
fi

# FastAPI
health_body="$(curl -s --connect-timeout 3 "http://127.0.0.1:8080/api/v1/health" 2>/dev/null || true)"
if echo "$health_body" | grep -q '"status"'; then
  green "FastAPI /api/v1/health 返回 ok"
else
  yellow "FastAPI 未运行 (http://127.0.0.1:8080) — 执行 ./scripts/start-all.sh 启动"
fi

# Vue dev server (optional)
vite_code="$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 2 "http://127.0.0.1:5173/" 2>/dev/null || echo "000")"
if [[ "$vite_code" == "200" ]]; then
  green "Vue dev server (5173)"
else
  yellow "Vue dev server 未运行 (5173)"
fi

# ComfyUI FLUX models
flux_count="$(find "${HOME}/ComfyUI/models" -name '*.safetensors' 2>/dev/null | wc -l | tr -d ' ')"
if [[ "${flux_count:-0}" -gt 0 ]]; then
  green "ComfyUI 模型文件: ${flux_count} 个 safetensors"
else
  yellow "ComfyUI models 目录未找到 safetensors"
fi

echo "----------------------------------------"
echo "通过: $PASS  失败: $FAIL  警告: $WARN"
if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
exit 0
