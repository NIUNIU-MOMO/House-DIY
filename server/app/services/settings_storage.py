from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

SETTINGS_FILENAME = "settings.local.json"


class StorageSettings(BaseModel):
    output_root: str = Field(default="./data/projects", min_length=1)


def get_settings_path() -> Path:
    """
    本地运行时配置文件路径

    @return settings.local.json 绝对路径
    """
    server_root = Path(__file__).resolve().parents[2]
    return server_root / SETTINGS_FILENAME


def load_storage_settings() -> StorageSettings:
    """
    读取本地存储配置

    @return 存储配置，文件不存在时返回默认值
    """
    path = get_settings_path()
    if not path.is_file():
        return StorageSettings()
    data = json.loads(path.read_text(encoding="utf-8"))
    return StorageSettings.model_validate(data)


def save_storage_settings(settings: StorageSettings) -> StorageSettings:
    """
    写入本地存储配置

    @param settings 存储配置
    @return 写入后的配置
    """
    path = get_settings_path()
    path.write_text(
        settings.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return settings


def resolve_output_root(env_fallback: str | None = None) -> Path:
    """
    解析有效输出根目录：UI 配置 > 环境变量 > 默认值

    @param env_fallback 环境变量 HOUSE_DIY_OUTPUT_ROOT 或 projects_dir
    @return 输出根目录绝对路径
    """
    path = get_settings_path()
    if path.is_file():
        file_settings = load_storage_settings()
        if file_settings.output_root:
            return Path(file_settings.output_root).expanduser().resolve()
    if env_fallback:
        return Path(env_fallback).expanduser().resolve()
    return Path("./data/projects").resolve()


def check_output_root_writable(output_root: Path | None = None) -> tuple[bool, str | None]:
    """
    检测输出根目录是否可写

    @param output_root 待检测目录，默认使用当前生效路径
    @return (是否可写, 错误信息)
    """
    root = output_root or resolve_output_root()
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True, None
    except OSError as exc:
        return False, str(exc)
