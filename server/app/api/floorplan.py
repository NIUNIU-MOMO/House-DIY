from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.project import Project, ProjectStatus
from app.schemas.floorplan import FloorPlanModel, FloorPlanRead, FloorPlanStatus, ScaleRequest
from app.schemas.task import TaskRead
from app.services.floorplan import storage
from app.services.floorplan.parser_cv import compute_scale_pixels_per_meter
from app.services.floorplan.task_parse import create_floorplan_parse_task, start_floorplan_parse

router = APIRouter(prefix="/projects/{project_id}/floorplan", tags=["floorplan"])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _to_read_model(project_id: int) -> FloorPlanRead:
    model = storage.load_floorplan(project_id)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floorplan not found")

    meta = storage.load_meta(project_id) or {}
    source_image = meta.get("source_image")
    source_url = None
    if source_image:
        source_url = f"/api/v1/projects/{project_id}/floorplan/source"

    return FloorPlanRead(
        **model.model_dump(),
        source_image=source_image,
        original_filename=meta.get("original_filename"),
        estimated_area=meta.get("estimated_area"),
        source_url=source_url,
    )


@router.get("", response_model=FloorPlanRead)
def get_floorplan(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(project_id, db)
    if not storage.has_floorplan(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floorplan not found")
    return _to_read_model(project_id)


@router.post("", response_model=FloorPlanRead, status_code=status.HTTP_201_CREATED)
async def upload_floorplan(
    project_id: int,
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    estimated_area: float | None = Form(default=None),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(project_id, db)

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")

    filename = file.filename or "source.png"
    try:
        storage.save_upload(project_id, content, filename, estimated_area=estimated_area)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if name and name.strip():
        project.name = name.strip()
        db.add(project)
        db.commit()
        db.refresh(project)

    return _to_read_model(project_id)


@router.put("", response_model=FloorPlanRead)
def update_floorplan(
    project_id: int,
    payload: FloorPlanModel,
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(project_id, db)
    if not storage.has_floorplan(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floorplan not found")

    storage.save_floorplan(project_id, payload)
    if payload.status == FloorPlanStatus.CONFIRMED:
        project.status = ProjectStatus.DESIGNING
        db.add(project)
        db.commit()

    return _to_read_model(project_id)


@router.post("/scale", response_model=FloorPlanRead)
def set_floorplan_scale(
    project_id: int,
    payload: ScaleRequest,
    db: Session = Depends(get_db),
):
    _get_project_or_404(project_id, db)
    model = storage.load_floorplan(project_id)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floorplan not found")

    try:
        scale = compute_scale_pixels_per_meter(payload.point_a, payload.point_b, payload.distance_m)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    updated = model.model_copy(update={"scale": scale})
    storage.save_floorplan(project_id, updated)
    return _to_read_model(project_id)


@router.get("/source")
def get_floorplan_source(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(project_id, db)
    source_path = storage.get_source_path(project_id)
    if source_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source image not found")

    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".pdf": "application/pdf",
    }
    media_type = media_types.get(source_path.suffix.lower(), "application/octet-stream")
    return FileResponse(path=Path(source_path), media_type=media_type, filename=source_path.name)


@router.post("/parse", response_model=TaskRead, status_code=status.HTTP_202_ACCEPTED)
async def start_parse_floorplan(
    project_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    _get_project_or_404(project_id, db)
    if not storage.has_floorplan(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floorplan not found")

    task = create_floorplan_parse_task(db, project_id)
    background_tasks.add_task(start_floorplan_parse, task.id)
    return task
