from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.project import Project
from app.models.task import Task
from app.schemas.task import TaskRead
from app.services.floorplan.task_parse import ws_manager

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
    return task


@router.websocket("/ws")
async def project_ws(project_id: int, websocket: WebSocket):
    await ws_manager.connect(project_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(project_id, websocket)
