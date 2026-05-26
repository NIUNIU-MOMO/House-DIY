from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.project import Project
from app.models.task import Task, TaskStatus, TaskType
from app.schemas.task import TaskRead
from app.services.floorplan.task_parse import (
    cancel_floorplan_parse_task,
    task_to_read,
    ws_manager,
)

router = APIRouter(prefix="/projects/{project_id}", tags=["tasks"])


def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.get("/tasks/{task_id}", response_model=TaskRead)
def get_task(project_id: int, task_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(project_id, db)
    task = db.get(Task, task_id)
    if task is None or task.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task_to_read(task)


@router.post("/tasks/{task_id}/cancel", response_model=TaskRead)
def cancel_task(project_id: int, task_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(project_id, db)
    task = db.get(Task, task_id)
    if task is None or task.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.type != TaskType.FLOORPLAN_PARSE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only floorplan parse tasks can be cancelled",
        )
    if task.status not in {TaskStatus.PENDING, TaskStatus.RUNNING}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task is not running",
        )
    try:
        task = cancel_floorplan_parse_task(db, task)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return task_to_read(task)


@router.websocket("/ws")
async def project_ws(project_id: int, websocket: WebSocket):
    await ws_manager.connect(project_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(project_id, websocket)
