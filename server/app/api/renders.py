from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.project import Project
from app.schemas.render import RenderManifestRead, RenderRecordRead
from app.schemas.task import TaskRead
from app.services.design.storage import load_design_spec
from app.services.gpu_scheduler import gpu_scheduler
from app.services.render.storage import get_render_path, load_manifest
from app.services.render.task_room_render import create_room_render_task, start_room_render

router = APIRouter(prefix="/projects/{project_id}/renders", tags=["renders"])


def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _manifest_response(project_id: int) -> RenderManifestRead:
    manifest = load_manifest(project_id)
    rooms = [
        RenderRecordRead(
            **item.model_dump(),
            image_url=f"/api/v1/projects/{project_id}/renders/{item.room_id}/image",
        )
        for item in manifest.rooms
    ]
    return RenderManifestRead(rooms=rooms)


@router.get("", response_model=RenderManifestRead)
def list_renders(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(project_id, db)
    return _manifest_response(project_id)


@router.get("/{room_id}/image")
def get_render_image(project_id: int, room_id: str, db: Session = Depends(get_db)):
    _get_project_or_404(project_id, db)
    path = get_render_path(project_id, room_id)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Render not found")
    return FileResponse(path, media_type="image/png")


@router.post("/{room_id}/regenerate", response_model=TaskRead, status_code=status.HTTP_202_ACCEPTED)
async def regenerate_room_render(project_id: int, room_id: str, db: Session = Depends(get_db)):
    _get_project_or_404(project_id, db)
    spec = load_design_spec(project_id)
    if spec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DesignSpec not found")

    room = next((item for item in spec.rooms if item.id == room_id), None)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    task = create_room_render_task(db, project_id, room_id)

    async def job() -> None:
        await start_room_render(task.id)

    await gpu_scheduler.enqueue(job)
    return task
