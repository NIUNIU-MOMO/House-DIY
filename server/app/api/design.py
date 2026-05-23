from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.project import Project
from app.schemas.design_spec import DesignGenerateRequest, DesignSpec
from app.schemas.task import TaskRead
from app.services.design.storage import load_design_spec
from app.services.orchestrator import create_pipeline_task, start_pipeline
from app.services.floorplan import storage
from app.services.gpu_scheduler import gpu_scheduler

router = APIRouter(prefix="/projects/{project_id}/design", tags=["design"])


def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.get("/spec", response_model=DesignSpec)
def get_design_spec(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(project_id, db)
    spec = load_design_spec(project_id)
    if spec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DesignSpec not found")
    return spec


@router.post("/generate", response_model=TaskRead, status_code=status.HTTP_202_ACCEPTED)
async def generate_design(
    project_id: int,
    payload: DesignGenerateRequest,
    db: Session = Depends(get_db),
):
    _get_project_or_404(project_id, db)
    floorplan = storage.load_floorplan(project_id)
    if floorplan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floorplan not found")

    task = create_pipeline_task(
        db,
        project_id,
        {
            "brief": payload.brief,
            "global_style": payload.global_style,
            "use_rag": payload.use_rag,
        },
    )

    async def job() -> None:
        await start_pipeline(task.id)

    await gpu_scheduler.enqueue(job)
    return task
