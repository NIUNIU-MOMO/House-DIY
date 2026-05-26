from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

from app.services.floorplan.storage import ensure_project_dir, get_project_dir

SCHEME_MAX_COUNT = 10
DEFAULT_SCHEME_ID = "a"
DEFAULT_SCHEME_NAME = "方案 A"
DESIGN_SPEC_FILENAME = "design_spec.json"
SCHEME_META_FILENAME = "meta.json"
SCHEMES_DIRNAME = "schemes"


class SchemeMeta(BaseModel):
    id: str
    name: str
    status: str = "empty"
    stale: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SchemeCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class SchemeUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    status: str | None = None


def get_schemes_root(project_id: int) -> Path:
    """
    方案根目录

    @param project_id 项目 ID
    @return schemes 目录路径
    """
    return get_project_dir(project_id) / SCHEMES_DIRNAME


def get_scheme_dir(project_id: int, scheme_id: str) -> Path:
    """
    单个方案目录

    @param project_id 项目 ID
    @param scheme_id 方案 ID
    @return 方案目录路径
    """
    return get_schemes_root(project_id) / scheme_id


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_scheme_meta(project_id: int, meta: SchemeMeta) -> Path:
    scheme_dir = get_scheme_dir(project_id, meta.id)
    scheme_dir.mkdir(parents=True, exist_ok=True)
    meta_path = scheme_dir / SCHEME_META_FILENAME
    meta_path.write_text(meta.model_dump_json(indent=2), encoding="utf-8")
    return meta_path


def load_scheme_meta(project_id: int, scheme_id: str) -> dict | None:
    """
    读取方案 meta.json

    @param project_id 项目 ID
    @param scheme_id 方案 ID
    @return meta 字典，不存在时 None
    """
    meta_path = get_scheme_dir(project_id, scheme_id) / SCHEME_META_FILENAME
    if not meta_path.is_file():
        return None
    return json.loads(meta_path.read_text(encoding="utf-8"))


def save_scheme_meta(project_id: int, meta: SchemeMeta) -> Path:
    """
    写入方案 meta

    @param project_id 项目 ID
    @param meta 方案元数据
    @return meta.json 路径
    """
    meta.updated_at = _now_iso()
    return _write_scheme_meta(project_id, meta)


def list_schemes(project_id: int) -> list[SchemeMeta]:
    """
    列出项目全部方案

    @param project_id 项目 ID
    @return 方案列表
    """
    schemes_root = get_schemes_root(project_id)
    if not schemes_root.is_dir():
        return []

    schemes: list[SchemeMeta] = []
    for child in sorted(schemes_root.iterdir()):
        if not child.is_dir():
            continue
        meta_path = child / SCHEME_META_FILENAME
        if not meta_path.is_file():
            continue
        schemes.append(SchemeMeta.model_validate(json.loads(meta_path.read_text(encoding="utf-8"))))
    schemes.sort(key=lambda item: item.created_at)
    return schemes


def _next_scheme_id(project_id: int) -> str:
    existing = {scheme.id for scheme in list_schemes(project_id)}
    for letter in "abcdefghijklmnopqrstuvwxyz":
        candidate = letter
        if candidate not in existing:
            return candidate
    return uuid4().hex[:8]


def _next_scheme_name(project_id: int) -> str:
    count = len(list_schemes(project_id))
    return f"方案 {chr(ord('A') + count)}"


def create_scheme(project_id: int, name: str | None = None, scheme_id: str | None = None) -> SchemeMeta:
    """
    创建新方案

    @param project_id 项目 ID
    @param name 方案名称
    @param scheme_id 指定 ID（仅默认方案使用）
    @return 新方案元数据
    @raises ValueError 超过软上限
    """
    schemes = list_schemes(project_id)
    if len(schemes) >= SCHEME_MAX_COUNT:
        raise ValueError(f"方案数量已达上限 {SCHEME_MAX_COUNT}，请先删除旧方案")

    sid = scheme_id or _next_scheme_id(project_id)
    if any(item.id == sid for item in schemes):
        raise ValueError(f"方案 ID 已存在: {sid}")

    display_name = name or _next_scheme_name(project_id)
    meta = SchemeMeta(id=sid, name=display_name, status="empty")
    ensure_project_dir(project_id)
    _write_scheme_meta(project_id, meta)
    return meta


def ensure_default_scheme(project_id: int) -> SchemeMeta:
    """
    首次进设计时自动创建方案 A

    @param project_id 项目 ID
    @return 默认或首个方案
    """
    schemes = list_schemes(project_id)
    if schemes:
        return schemes[0]
    return create_scheme(project_id, name=DEFAULT_SCHEME_NAME, scheme_id=DEFAULT_SCHEME_ID)


def delete_scheme(project_id: int, scheme_id: str) -> None:
    """
    删除方案及其全部产物

    @param project_id 项目 ID
    @param scheme_id 方案 ID
    @raises ValueError 方案不存在
    """
    scheme_dir = get_scheme_dir(project_id, scheme_id)
    if not scheme_dir.is_dir():
        raise ValueError(f"方案不存在: {scheme_id}")
    shutil.rmtree(scheme_dir)


def mark_all_schemes_stale(project_id: int) -> None:
    """
    重新解析后标记全部方案 stale

    @param project_id 项目 ID
    """
    for scheme in list_schemes(project_id):
        if not scheme.stale:
            scheme.stale = True
            save_scheme_meta(project_id, scheme)


def clear_scheme_stale(project_id: int, scheme_id: str) -> None:
    """
    清除单个方案 stale 标记

    @param project_id 项目 ID
    @param scheme_id 方案 ID
    """
    meta_dict = load_scheme_meta(project_id, scheme_id)
    if meta_dict is None:
        return
    meta = SchemeMeta.model_validate(meta_dict)
    meta.stale = False
    save_scheme_meta(project_id, meta)


def get_design_spec_path(project_id: int, scheme_id: str) -> Path:
    """
    方案 design_spec.json 路径

    @param project_id 项目 ID
    @param scheme_id 方案 ID
    @return design_spec.json 路径
    """
    return get_scheme_dir(project_id, scheme_id) / DESIGN_SPEC_FILENAME


def get_renders_dir(project_id: int, scheme_id: str) -> Path:
    """
    方案 renders 目录

    @param project_id 项目 ID
    @param scheme_id 方案 ID
    @return renders 目录路径
    """
    return get_scheme_dir(project_id, scheme_id) / "renders"


def get_scene_dir(project_id: int, scheme_id: str) -> Path:
    """
    方案 scene 目录

    @param project_id 项目 ID
    @param scheme_id 方案 ID
    @return scene 目录路径
    """
    return get_scheme_dir(project_id, scheme_id) / "scene"
