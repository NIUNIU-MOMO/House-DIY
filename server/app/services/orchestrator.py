import asyncio
import json
import time
from collections.abc import Callable
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskStatus, TaskType
from app.services.design.storage import save_design_spec
from app.services.design_spec_generator import generate_design_spec
from app.services.floorplan import storage
from app.services.floorplan.task_parse import _notify_task, _update_task, ws_manager
from app.services.knowledge.case_writer import write_design_case
from app.services.comfy_client import ComfyClient
from app.services.omlx_client import OmlxClient, get_omlx_client
from app.services.render.comfy_render import render_room
from app.services.render.storage import load_manifest
from app.services.scene_builder import build_scene
from app.services.scheduler import TaskEvent, next_task_status

PIPELINE_STEPS = [
    ("designSpec", "DesignSpec 生成"),
    ("render2d", "2D 效果图 ComfyUI"),
    ("scene3d", "3D 场景构建"),
    ("obsidian", "Obsidian 案例写入"),
]


def _notify_pipeline(project_id: int, task: Task, pipeline_step: str, event: str, extra: dict | None = None) -> None:
    payload = {
        "type": "pipeline_update",
        "event": event,
        "pipeline_step": pipeline_step,
        "task": {
            "id": task.id,
            "project_id": task.project_id,
            "type": task.type.value,
            "status": task.status.value,
            "progress": task.progress,
            "step": task.step,
            "step_label": task.step_label,
            "error": task.error,
        },
    }
    if extra:
        payload.update(extra)
    ws_manager.notify_sync(project_id, payload)
    if event != "room_poll":
        _notify_task(task)


def _render_progress(total_rooms: int, room_index: int, room_ratio: float = 0.0) -> float:
    """
    计算 2D 渲染阶段总进度

    @param total_rooms 房间总数
    @param room_index 当前房间索引（0-based）
    @param room_ratio 当前房间内部进度 0~1
    @return 总进度 30~72
    """
    span = 40.0 / max(total_rooms, 1)
    return 30.0 + room_index * span + span * min(max(room_ratio, 0.0), 1.0)


def create_pipeline_task(db: Session, project_id: int, payload: dict) -> Task:
    task = Task(
        project_id=project_id,
        type=TaskType.DESIGN_GENERATE,
        status=TaskStatus.PENDING,
        progress=0,
        step=0,
        step_label=PIPELINE_STEPS[0][1],
        payload=json.dumps(payload, ensure_ascii=False),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def _build_scene_package(project_id: int, floorplan, spec) -> Path:
    project_dir = storage.get_project_dir(project_id)
    build_scene(floorplan, spec, project_dir)
    return project_dir / "scene.json"


def run_pipeline_sync(
    task_id: int,
    omlx_client: OmlxClient | None = None,
    comfy_client: ComfyClient | None = None,
    placeholder_png: bytes | None = None,
) -> None:
    llm = omlx_client or get_omlx_client()
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        if task is None:
            return

        project = db.get(Project, task.project_id)
        floorplan = storage.load_floorplan(task.project_id)
        if project is None or floorplan is None:
            _update_task(db, task, status=TaskStatus.FAILED, error="Project or floorplan not found")
            _notify_pipeline(task.project_id, task, "designSpec", "step_done")
            return

        payload = json.loads(task.payload or "{}")

        task = _update_task(
            db,
            task,
            status=TaskStatus.RUNNING,
            progress=5,
            step=0,
            step_label=PIPELINE_STEPS[0][1],
        )
        _notify_pipeline(task.project_id, task, "designSpec", "step_start")

        try:
            spec = generate_design_spec(
                brief=payload.get("brief", ""),
                floorplan=floorplan,
                global_style=payload.get("global_style"),
                use_rag=payload.get("use_rag", True),
                omlx_client=llm,
            )
            save_design_spec(task.project_id, spec)
            task = _update_task(db, task, progress=25, step=0, step_label=PIPELINE_STEPS[0][1])
            _notify_pipeline(task.project_id, task, "designSpec", "step_done")

            task = _update_task(db, task, progress=30, step=1, step_label=PIPELINE_STEPS[1][1])
            _notify_pipeline(task.project_id, task, "render2d", "step_start")

            total_rooms = max(len(spec.rooms), 1)
            last_poll_notify = 0.0
            for index, room in enumerate(spec.rooms):
                start_progress = _render_progress(total_rooms, index, 0.0)
                task = _update_task(
                    db,
                    task,
                    progress=start_progress,
                    step=1,
                    step_label=f"渲染 {room.name}",
                )
                _notify_pipeline(
                    task.project_id,
                    task,
                    "render2d",
                    "room_start",
                    {
                        "room_id": room.id,
                        "room_index": index,
                        "room_total": total_rooms,
                        "room_name": room.name,
                    },
                )

                def make_poll_handler(
                    room_index: int,
                    room_name: str,
                    room_id: str,
                ) -> Callable[[float, float], None]:
                    def on_poll(elapsed: float, timeout: float) -> None:
                        nonlocal last_poll_notify, task
                        now = time.time()
                        if now - last_poll_notify < 3.0:
                            return
                        last_poll_notify = now
                        ratio = min(0.95, elapsed / timeout) if timeout > 0 else 0.0
                        task.progress = _render_progress(total_rooms, room_index, ratio)
                        task.step_label = f"渲染 {room_name}"
                        _notify_pipeline(
                            task.project_id,
                            task,
                            "render2d",
                            "room_poll",
                            {
                                "room_id": room_id,
                                "room_index": room_index,
                                "room_total": total_rooms,
                                "room_name": room_name,
                                "room_ratio": ratio,
                            },
                        )

                    return on_poll

                render_room(
                    task.project_id,
                    room,
                    floorplan=floorplan,
                    comfy_client=comfy_client,
                    placeholder_png=placeholder_png,
                    on_poll=make_poll_handler(index, room.name, room.id),
                )
                progress = _render_progress(total_rooms, index + 1, 0.0)
                task = _update_task(db, task, progress=progress, step=1, step_label=f"渲染 {room.name}")
                _notify_pipeline(
                    task.project_id,
                    task,
                    "render2d",
                    "step_progress",
                    {"room_id": room.id, "room_index": index, "room_total": total_rooms},
                )

            task = _update_task(db, task, progress=72, step=1, step_label=PIPELINE_STEPS[1][1])
            _notify_pipeline(task.project_id, task, "render2d", "step_done")

            task = _update_task(db, task, progress=75, step=2, step_label=PIPELINE_STEPS[2][1])
            _notify_pipeline(task.project_id, task, "scene3d", "step_start")
            _build_scene_package(task.project_id, floorplan, spec)
            task = _update_task(db, task, progress=85, step=2, step_label=PIPELINE_STEPS[2][1])
            _notify_pipeline(task.project_id, task, "scene3d", "step_done")

            task = _update_task(db, task, progress=88, step=3, step_label=PIPELINE_STEPS[3][1])
            _notify_pipeline(task.project_id, task, "obsidian", "step_start")
            manifest = load_manifest(task.project_id)
            write_design_case(task.project_id, project.name, spec, floorplan, manifest)
            task = _update_task(db, task, progress=95, step=3, step_label=PIPELINE_STEPS[3][1])
            _notify_pipeline(task.project_id, task, "obsidian", "step_done")

            project.status = ProjectStatus.DELIVERED
            db.add(project)
            db.commit()

            task = _update_task(
                db,
                task,
                status=TaskStatus.DONE,
                progress=100,
                step=3,
                step_label="流水线完成",
            )
            _notify_pipeline(task.project_id, task, "obsidian", "pipeline_done")
        except Exception as exc:
            fail_status, retry_count = next_task_status(TaskStatus.RUNNING, TaskEvent.FAIL, task.retry_count)
            task = _update_task(
                db,
                task,
                status=fail_status,
                retry_count=retry_count,
                error=str(exc),
            )
            _notify_pipeline(task.project_id, task, "pipeline", "failed", {"error": str(exc)})
    finally:
        db.close()


async def start_pipeline(task_id: int) -> None:
    await asyncio.to_thread(run_pipeline_sync, task_id)
