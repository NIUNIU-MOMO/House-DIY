from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.project import Project, ProjectMaxStep
from app.schemas.design_refine import RefineApplyRequest, RefinePreviewResponse, RefineRequest
from app.schemas.task import TaskRead
from app.services.design.storage import load_design_spec, save_design_spec
from app.services.design_refine_generator import apply_patch, preview_refine
from app.services.design.task_refine import create_refine_apply_task, start_refine_apply
from app.services.floorplan import storage
from app.services.gpu_scheduler import gpu_scheduler
from app.services.project_progress import bump_max_step_db
from app.services.stale_guard import StaleDesignBlocked, check_design_operation_allowed

router = APIRouter(prefix="/projects/{project_id}/design", tags=["design-refine"])


def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post("/refine", response_model=RefinePreviewResponse)
def refine_design_preview(
    project_id: int,
    payload: RefineRequest,
    scheme_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    _get_project_or_404(project_id, db)
    spec = load_design_spec(project_id, scheme_id=scheme_id)
    if spec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DesignSpec not found")
    return preview_refine(payload.instruction, spec)


@router.post("/refine/apply", response_model=TaskRead, status_code=status.HTTP_202_ACCEPTED)
async def refine_design_apply(
    project_id: int,
    payload: RefineApplyRequest,
    scheme_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(project_id, db)

    try:
        check_design_operation_allowed(project_id, scheme_id)
    except StaleDesignBlocked as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": exc.message, "code": exc.code},
        ) from exc

    spec = load_design_spec(project_id, scheme_id=scheme_id)
    floorplan = storage.load_floorplan(project_id)
    if spec is None or floorplan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DesignSpec or floorplan not found")

    updated = apply_patch(spec, payload.patch)
    save_design_spec(project_id, updated, scheme_id=scheme_id)
    bump_max_step_db(db, project, ProjectMaxStep.DESIGN)

    task = create_refine_apply_task(
        db,
        project_id,
        {
            "affected_room_ids": payload.affected_room_ids,
            "update_obsidian": payload.update_obsidian,
        },
    )

    async def job() -> None:
        await start_refine_apply(task.id)

    await gpu_scheduler.enqueue(job)
    return task
