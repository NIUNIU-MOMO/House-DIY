from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.project import Project
from app.schemas.design_spec import DesignGenerateRequest, DesignSpec
from app.schemas.task import TaskRead
from app.services.design import scheme_storage
from app.services.design.scheme_storage import (
    SchemeCreateRequest,
    SchemeMeta,
    SchemeUpdateRequest,
)
from app.services.design.storage import load_design_spec, save_design_spec
from app.services.orchestrator import create_pipeline_task, start_pipeline
from app.services.project_progress import bump_max_step_db
from app.models.project import ProjectMaxStep
from app.services.stale_guard import StaleDesignBlocked, check_design_operation_allowed
from app.services.gpu_scheduler import gpu_scheduler

router = APIRouter(prefix="/projects/{project_id}/schemes", tags=["schemes"])


def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _get_scheme_or_404(project_id: int, scheme_id: str) -> SchemeMeta:
    meta_dict = scheme_storage.load_scheme_meta(project_id, scheme_id)
    if meta_dict is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheme not found")
    return SchemeMeta.model_validate(meta_dict)


def _stale_http_error(exc: StaleDesignBlocked) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"message": exc.message, "code": exc.code},
    )


@router.get("", response_model=list[SchemeMeta])
def list_project_schemes(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(project_id, db)
    schemes = scheme_storage.list_schemes(project_id)
    if not schemes:
        default = scheme_storage.ensure_default_scheme(project_id)
        project = _get_project_or_404(project_id, db)
        if project.active_scheme_id is None:
            project.active_scheme_id = default.id
            db.add(project)
            db.commit()
        return [default]
    return schemes


@router.post("", response_model=SchemeMeta, status_code=status.HTTP_201_CREATED)
def create_project_scheme(
    project_id: int,
    payload: SchemeCreateRequest,
    db: Session = Depends(get_db),
):
    _get_project_or_404(project_id, db)
    try:
        scheme = scheme_storage.create_scheme(project_id, name=payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return scheme


@router.delete("/{scheme_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_scheme(project_id: int, scheme_id: str, db: Session = Depends(get_db)):
    project = _get_project_or_404(project_id, db)
    try:
        scheme_storage.delete_scheme(project_id, scheme_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if project.active_scheme_id == scheme_id:
        remaining = scheme_storage.list_schemes(project_id)
        project.active_scheme_id = remaining[0].id if remaining else None
        db.add(project)
        db.commit()


@router.put("/{scheme_id}", response_model=SchemeMeta)
def update_project_scheme(
    project_id: int,
    scheme_id: str,
    payload: SchemeUpdateRequest,
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(project_id, db)
    scheme = _get_scheme_or_404(project_id, scheme_id)

    if payload.name is not None:
        scheme.name = payload.name
    if payload.status is not None:
        scheme.status = payload.status
    scheme_storage.save_scheme_meta(project_id, scheme)

    bump_max_step_db(db, project, ProjectMaxStep.DESIGN)
    return scheme


@router.put("/{scheme_id}/spec", response_model=DesignSpec)
def save_scheme_spec(
    project_id: int,
    scheme_id: str,
    spec: DesignSpec,
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(project_id, db)
    _get_scheme_or_404(project_id, scheme_id)

    try:
        check_design_operation_allowed(project_id, scheme_id)
    except StaleDesignBlocked as exc:
        raise _stale_http_error(exc) from exc

    save_design_spec(project_id, spec, scheme_id=scheme_id)
    scheme = _get_scheme_or_404(project_id, scheme_id)
    scheme.status = "saved"
    scheme.stale = False
    scheme_storage.save_scheme_meta(project_id, scheme)

    bump_max_step_db(db, project, ProjectMaxStep.DESIGN)
    if project.active_scheme_id != scheme_id:
        project.active_scheme_id = scheme_id
        db.add(project)
        db.commit()
    return spec


@router.get("/{scheme_id}/spec", response_model=DesignSpec)
def get_scheme_spec(project_id: int, scheme_id: str, db: Session = Depends(get_db)):
    _get_project_or_404(project_id, db)
    _get_scheme_or_404(project_id, scheme_id)
    spec = load_design_spec(project_id, scheme_id=scheme_id)
    if spec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DesignSpec not found")
    return spec


@router.post("/{scheme_id}/generate-2d", response_model=TaskRead, status_code=status.HTTP_202_ACCEPTED)
async def generate_scheme_2d(
    project_id: int,
    scheme_id: str,
    payload: DesignGenerateRequest,
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(project_id, db)
    scheme = _get_scheme_or_404(project_id, scheme_id)

    try:
        check_design_operation_allowed(project_id, scheme_id)
    except StaleDesignBlocked as exc:
        raise _stale_http_error(exc) from exc

    scheme.status = "rendering_2d"
    scheme_storage.save_scheme_meta(project_id, scheme)

    task = create_pipeline_task(
        db,
        project_id,
        {
            "brief": payload.brief,
            "global_style": payload.global_style,
            "use_rag": payload.use_rag,
            "scheme_id": scheme_id,
            "pipeline_mode": "2d_only",
        },
    )

    if project.active_scheme_id != scheme_id:
        project.active_scheme_id = scheme_id
        db.add(project)
        db.commit()

    async def job() -> None:
        await start_pipeline(task.id)

    await gpu_scheduler.enqueue(job)
    return task


@router.post("/{scheme_id}/generate-3d", response_model=TaskRead, status_code=status.HTTP_202_ACCEPTED)
async def generate_scheme_3d(
    project_id: int,
    scheme_id: str,
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(project_id, db)
    scheme = _get_scheme_or_404(project_id, scheme_id)

    try:
        check_design_operation_allowed(project_id, scheme_id)
    except StaleDesignBlocked as exc:
        raise _stale_http_error(exc) from exc

    spec = load_design_spec(project_id, scheme_id=scheme_id)
    if spec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DesignSpec not found")

    scheme.status = "rendering_3d"
    scheme_storage.save_scheme_meta(project_id, scheme)

    task = create_pipeline_task(
        db,
        project_id,
        {
            "scheme_id": scheme_id,
            "pipeline_mode": "3d_only",
        },
    )

    async def job() -> None:
        await start_pipeline(task.id)

    await gpu_scheduler.enqueue(job)
    return task
