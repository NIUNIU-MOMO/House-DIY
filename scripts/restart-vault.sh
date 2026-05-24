#!/usr/bin/env bash
# House-DIY 初始化 / 修复 Vault 目录结构
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${HOME}/House-DIY-env"

echo "House-DIY restart-vault — $ROOT"
echo "----------------------------------------"

if [[ ! -x "$VENV/bin/python" ]]; then
  echo "[Vault] Python 虚拟环境未找到: $VENV" >&2
  exit 1
fi

cd "$ROOT/server"
# shellcheck disable=SC1091
source "$VENV/bin/activate"

python - <<'PY'
from app.core.config import settings
from app.services.knowledge.vault_io import bootstrap_vault

vault_root = settings.vault_path()
templates = settings.vault_templates_path()
result = bootstrap_vault(vault_root, templates)
print(f"[Vault] 目录: {result['directories']}")
print(f"[Vault] 模板: {result['templates']}")
if not vault_root.is_dir():
    raise SystemExit("[Vault] 初始化失败")
print(f"[Vault] 路径: {vault_root}")
PY

echo "----------------------------------------"
echo "[Vault] 已就绪"
