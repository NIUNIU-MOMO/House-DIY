from __future__ import annotations

import json
from pathlib import Path

from app.schemas.design_spec import DesignSpec
from app.services.design import scheme_storage
from app.services.floorplan.storage import get_project_dir

LEGACY_DESIGNSPEC_FILENAME = "designspec.json"


def _resolve_scheme_id(project_id: int, scheme_id: str | None) -> str:
    if scheme_id is not None:
        return scheme_id
    from app.core.database import SessionLocal
    from app.models.project import Project

    db = SessionLocal()
    try:
        project = db.get(Project, project_id)
        if project is not None and project.active_scheme_id:
            return project.active_scheme_id
    finally:
        db.close()
    return scheme_storage.DEFAULT_SCHEME_ID


def get_design_spec_path(project_id: int, scheme_id: str | None = None) -> Path:
    """
    方案 design_spec.json 路径

    @param project_id 项目 ID
    @param scheme_id 方案 ID，缺省时用 active_scheme_id
    @return design_spec.json 路径
    """
    sid = _resolve_scheme_id(project_id, scheme_id)
    return scheme_storage.get_design_spec_path(project_id, sid)


def save_design_spec(project_id: int, spec: DesignSpec, scheme_id: str | None = None) -> Path:
    """
    保存方案 DesignSpec

    @param project_id 项目 ID
    @param spec 设计规格
    @param scheme_id 方案 ID
    @return 写入路径
    """
    sid = _resolve_scheme_id(project_id, scheme_id)
    path = scheme_storage.get_design_spec_path(project_id, sid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_design_spec(project_id: int, scheme_id: str | None = None) -> DesignSpec | None:
    """
    读取方案 DesignSpec

    @param project_id 项目 ID
    @param scheme_id 方案 ID
    @return DesignSpec 或 None
    """
    sid = _resolve_scheme_id(project_id, scheme_id)
    path = scheme_storage.get_design_spec_path(project_id, sid)
    if path.is_file():
        return DesignSpec.model_validate(json.loads(path.read_text(encoding="utf-8")))

    legacy_path = get_project_dir(project_id) / LEGACY_DESIGNSPEC_FILENAME
    if legacy_path.is_file():
        return DesignSpec.model_validate(json.loads(legacy_path.read_text(encoding="utf-8")))
    return None
