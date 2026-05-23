import asyncio
import json

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.task import Task, TaskStatus, TaskType
from app.services.design.storage import load_design_spec
from app.services.floorplan import storage
from app.services.floorplan.task_parse import _notify_task, _update_task
from app.services.knowledge.case_writer import write_design_case
from app.services.render.comfy_render import render_room
from app.services.render.storage import load_manifest
from app.services.scene_builder import build_scene
from app.services.scheduler import TaskEvent, next_task_status


def create_refine_apply_task(db: Session, project_id: int, payload: dict) -> Task:
    task = Task(
        project_id=project_id,
        type=TaskType.ROOM_RENDER,
        status=TaskStatus.PENDING,
        progress=0,
        step=0,
        step_label="应用微调",
        payload=json.dumps(payload, ensure_ascii=False),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def run_refine_apply_sync(task_id: int, placeholder_png: bytes | None = None) -> None:
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        if task is None:
            return

        payload = json.loads(task.payload or "{}")
        affected_ids = payload.get("affected_room_ids", [])
        spec = load_design_spec(task.project_id)
        floorplan = storage.load_floorplan(task.project_id)
        if spec is None or floorplan is None:
            _update_task(db, task, status=TaskStatus.FAILED, error="DesignSpec or floorplan not found")
            _notify_task(task)
            return

        task = _update_task(db, task, status=TaskStatus.RUNNING, progress=10, step_label="增量 2D 渲染")
        _notify_task(task)

        try:
            total = max(len(affected_ids), 1)
            for index, room_id in enumerate(affected_ids):
                room = next((item for item in spec.rooms if item.id == room_id), None)
                if room is None:
                    continue
                render_room(task.project_id, room, placeholder_png=placeholder_png)
                progress = 10 + ((index + 1) / total) * 60
                task = _update_task(db, task, progress=progress, step_label=f"渲染 {room.name}")
                _notify_task(task)

            task = _update_task(db, task, progress=75, step_label="重建 3D 场景")
            _notify_task(task)
            build_scene(floorplan, spec, storage.get_project_dir(task.project_id))

            if payload.get("update_obsidian"):
                project_dir = storage.get_project_dir(task.project_id)
                from app.models.project import Project

                project = db.get(Project, task.project_id)
                if project is not None:
                    manifest = load_manifest(task.project_id)
                    write_design_case(task.project_id, project.name, spec, floorplan, manifest)

            task = _update_task(
                db,
                task,
                status=TaskStatus.DONE,
                progress=100,
                step_label="微调应用完成",
            )
            _notify_task(task)
        except Exception as exc:
            fail_status, retry_count = next_task_status(TaskStatus.RUNNING, TaskEvent.FAIL, task.retry_count)
            task = _update_task(db, task, status=fail_status, retry_count=retry_count, error=str(exc))
            _notify_task(task)
    finally:
        db.close()


async def start_refine_apply(task_id: int) -> None:
    await asyncio.to_thread(run_refine_apply_sync, task_id)
