import json
import shutil
from pathlib import Path

VAULT_SUBDIRS = (
    "Cases",
    "References",
    "Templates",
    "Assets",
    "Specs",
    ".house-diy/chroma",
)

INDEX_STATE_VERSION = 1


def ensure_vault_dirs(vault_root: Path) -> list[Path]:
    """
    创建 Vault 标准目录结构

    @param vault_root Vault 根路径
    @return 已确保存在的目录列表
    """
    created: list[Path] = []
    for relative in VAULT_SUBDIRS:
        directory = vault_root / relative
        directory.mkdir(parents=True, exist_ok=True)
        created.append(directory)

    index_state = vault_root / ".house-diy" / "index_state.json"
    if not index_state.exists():
        index_state.write_text(
            json.dumps({"version": INDEX_STATE_VERSION, "documents": {}}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return created


def sync_templates(vault_root: Path, templates_source: Path) -> list[Path]:
    """
    将项目 vault-templates 复制到 Vault/Templates

    @param vault_root Vault 根路径
    @param templates_source 项目内模板目录
    @return 已复制的目标文件列表
    """
    ensure_vault_dirs(vault_root)
    destination = vault_root / "Templates"
    copied: list[Path] = []

    if not templates_source.is_dir():
        return copied

    for source_file in sorted(templates_source.glob("*.md")):
        target_file = destination / source_file.name
        shutil.copy2(source_file, target_file)
        copied.append(target_file)

    return copied


def bootstrap_vault(vault_root: Path, templates_source: Path) -> dict[str, list[str]]:
    """
    初始化 Vault 目录并同步模板

    @param vault_root Vault 根路径
    @param templates_source 项目内模板目录
    @return 创建的目录与复制的模板路径（字符串形式）
    """
    directories = ensure_vault_dirs(vault_root)
    templates = sync_templates(vault_root, templates_source)
    return {
        "directories": [str(path.relative_to(vault_root)) for path in directories],
        "templates": [path.name for path in templates],
    }
