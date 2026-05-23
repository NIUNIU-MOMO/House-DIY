import asyncio
import json

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.task import Task, TaskStatus, TaskType
from app.services.design.storage import load_design_spec
from app.services.floorplan.task_parse import _notify_task, _update_task
from app.services.render.comfy_render import render_room
from app.services.scheduler import TaskEvent, next_task_status


def create_room_render_task(db: Session, project_id: int, room_id: str) -> Task:
    task = Task(
        project_id=project_id,
        type=TaskType.ROOM_RENDER,
        status=TaskStatus.PENDING,
        progress=0,
        step=0,
        step_label=f"渲染 {room_id}",
        payload=json.dumps({"room_id": room_id}, ensure_ascii=False),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def run_room_render_sync(task_id: int, placeholder_png: bytes | None = None) -> None:
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        if task is None:
            return

        payload = json.loads(task.payload or "{}")
        room_id = payload.get("room_id")
        spec = load_design_spec(task.project_id)
        if spec is None or not room_id:
            _update_task(db, task, status=TaskStatus.FAILED, error="DesignSpec or room_id not found")
            _notify_task(task)
            return

        room = next((item for item in spec.rooms if item.id == room_id), None)
        if room is None:
            _update_task(db, task, status=TaskStatus.FAILED, error=f"Room {room_id} not found")
            _notify_task(task)
            return

        task = _update_task(
            db,
            task,
            status=TaskStatus.RUNNING,
            progress=10,
            step=0,
            step_label=f"渲染 {room.name}",
            error=None,
        )
        _notify_task(task)

        try:
            render_room(task.project_id, room, placeholder_png=placeholder_png)
            task = _update_task(
                db,
                task,
                status=TaskStatus.DONE,
                progress=100,
                step=0,
                step_label=f"{room.name} 渲染完成",
            )
            _notify_task(task)
        except Exception as exc:
            fail_status, retry_count = next_task_status(TaskStatus.RUNNING, TaskEvent.FAIL, task.retry_count)
            task = _update_task(
                db,
                task,
                status=fail_status,
                retry_count=retry_count,
                error=str(exc),
            )
            _notify_task(task)
    finally:
        db.close()


async def start_room_render(task_id: int) -> None:
    await asyncio.to_thread(run_room_render_sync, task_id)
