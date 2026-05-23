import json
import shutil
from pathlib import Path

from app.core.config import settings
from app.schemas.floorplan import FloorPlanModel, FloorPlanStatus

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}
SOURCE_FILENAME = "source.png"
FLOORPLAN_FILENAME = "floorplan.json"
META_FILENAME = "meta.json"


def get_projects_root() -> Path:
    return Path(settings.house_diy_projects_dir).resolve()


def get_project_dir(project_id: int) -> Path:
    return get_projects_root() / str(project_id)


def ensure_project_dir(project_id: int) -> Path:
    project_dir = get_project_dir(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


def save_upload(
    project_id: int,
    content: bytes,
    original_filename: str,
    estimated_area: float | None = None,
) -> Path:
    """
    保存上传的平面图并初始化 draft FloorPlanModel

    @param project_id 项目 ID
    @param content 文件二进制内容
    @param original_filename 原始文件名
    @param estimated_area 预估总面积（㎡）
    @return 保存后的源文件路径
    """
    project_dir = ensure_project_dir(project_id)
    suffix = Path(original_filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(f"unsupported file type: {suffix}")

    if suffix == ".pdf":
        target_name = f"source{suffix}"
    else:
        target_name = SOURCE_FILENAME

    source_path = project_dir / target_name
    source_path.write_bytes(content)

    draft = FloorPlanModel(
        scale=None,
        walls=[],
        rooms=[],
        openings=[],
        status=FloorPlanStatus.DRAFT,
    )
    save_floorplan(project_id, draft)

    meta = {
        "source_image": target_name,
        "original_filename": original_filename,
        "estimated_area": estimated_area,
    }
    (project_dir / META_FILENAME).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return source_path


def load_meta(project_id: int) -> dict | None:
    meta_path = get_project_dir(project_id) / META_FILENAME
    if not meta_path.is_file():
        return None
    return json.loads(meta_path.read_text(encoding="utf-8"))


def load_floorplan(project_id: int) -> FloorPlanModel | None:
    floorplan_path = get_project_dir(project_id) / FLOORPLAN_FILENAME
    if not floorplan_path.is_file():
        return None
    data = json.loads(floorplan_path.read_text(encoding="utf-8"))
    return FloorPlanModel.model_validate(data)


def save_floorplan(project_id: int, model: FloorPlanModel) -> Path:
    project_dir = ensure_project_dir(project_id)
    floorplan_path = project_dir / FLOORPLAN_FILENAME
    floorplan_path.write_text(
        model.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return floorplan_path


def get_source_path(project_id: int) -> Path | None:
    meta = load_meta(project_id)
    if meta is None:
        return None
    source_path = get_project_dir(project_id) / meta["source_image"]
    return source_path if source_path.is_file() else None


def has_floorplan(project_id: int) -> bool:
    return (get_project_dir(project_id) / FLOORPLAN_FILENAME).is_file()
