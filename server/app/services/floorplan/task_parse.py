import asyncio
import base64
import mimetypes
from collections import defaultdict
from pathlib import Path
from typing import Any

import cv2
from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskStatus, TaskType
from app.services.floorplan import storage
from app.services.floorplan.parser_cv import apply_cv_walls, extract_walls_from_image
from app.services.floorplan.parser_vlm import (
    apply_coord_offset,
    load_prompt_for_image,
    merge_vlm_result,
    parse_vlm_response,
)
from app.services.floorplan.parser_preprocess import preprocess_floorplan_image
from app.services.omlx_client import OmlxClient, get_omlx_client

PARSE_STEPS = [
    "图像预处理与矫正",
    "oMLX VLM 识别房间与门窗",
    "OpenCV 提取墙线矢量",
    "生成 FloorPlanModel 草稿",
]


class ProjectWSManager:
    def __init__(self) -> None:
        self._connections: dict[int, list[WebSocket]] = defaultdict(list)
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, project_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[project_id].append(websocket)

    def disconnect(self, project_id: int, websocket: WebSocket) -> None:
        if project_id not in self._connections:
            return
        self._connections[project_id] = [
            conn for conn in self._connections[project_id] if conn is not websocket
        ]

    async def broadcast(self, project_id: int, message: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for websocket in self._connections.get(project_id, []):
            try:
                await websocket.send_json(message)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            self.disconnect(project_id, websocket)

    def notify_sync(self, project_id: int, message: dict[str, Any]) -> None:
        if self._loop is None or not self._loop.is_running():
            return
        asyncio.run_coroutine_threadsafe(self.broadcast(project_id, message), self._loop)


ws_manager = ProjectWSManager()


def _update_task(db: Session, task: Task, **fields: Any) -> Task:
    for key, value in fields.items():
        setattr(task, key, value)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def task_payload(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "project_id": task.project_id,
        "type": task.type.value,
        "status": task.status.value,
        "progress": task.progress,
        "step": task.step,
        "step_label": task.step_label,
        "error": task.error,
    }


def _notify_task(task: Task) -> None:
    ws_manager.notify_sync(task.project_id, {"type": "task_update", "task": task_payload(task)})


def create_floorplan_parse_task(db: Session, project_id: int) -> Task:
    task = Task(
        project_id=project_id,
        type=TaskType.FLOORPLAN_PARSE,
        status=TaskStatus.PENDING,
        progress=0,
        step=0,
        step_label=PARSE_STEPS[0],
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def preprocess_image(source_path: str) -> tuple[str, dict]:
    return preprocess_floorplan_image(source_path)


def _offset_walls(walls, offset_x: float, offset_y: float):
    from app.schemas.floorplan import Wall

    if offset_x == 0 and offset_y == 0:
        return walls
    shifted: list[Wall] = []
    for wall in walls:
        shifted.append(
            Wall(
                id=wall.id,
                points=apply_coord_offset(wall.points, offset_x, offset_y),
                thickness=wall.thickness,
            )
        )
    return shifted


def run_floorplan_parse_sync(task_id: int, omlx_client: OmlxClient | None = None) -> None:
    client = omlx_client or get_omlx_client()
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        if task is None:
            return

        project = db.get(Project, task.project_id)
        if project is None:
            _update_task(db, task, status=TaskStatus.FAILED, error="Project not found")
            _notify_task(task)
            return

        source_path = storage.get_source_path(task.project_id)
        if source_path is None:
            _update_task(db, task, status=TaskStatus.FAILED, error="Source image not found")
            _notify_task(task)
            return

        project.status = ProjectStatus.PARSING
        db.add(project)
        db.commit()

        _update_task(
            db,
            task,
            status=TaskStatus.RUNNING,
            progress=5,
            step=0,
            step_label=PARSE_STEPS[0],
        )
        _notify_task(task)

        processed_path, preprocess_meta = preprocess_image(str(source_path))
        storage.patch_meta(task.project_id, preprocess_meta)
        crop_offset = preprocess_meta.get("crop_offset", (0, 0))
        if isinstance(crop_offset, list):
            crop_offset = tuple(crop_offset)
        source_w = int(preprocess_meta.get("source_width") or 0)
        source_h = int(preprocess_meta.get("source_height") or 0)
        _update_task(db, task, progress=20, step=0, step_label=PARSE_STEPS[0])
        _notify_task(task)

        _update_task(db, task, progress=30, step=1, step_label=PARSE_STEPS[1])
        _notify_task(task)

        image = cv2.imread(processed_path)
        img_h, img_w = (image.shape[:2] if image is not None else (540, 720))
        if not source_w or not source_h:
            source_w, source_h = img_w, img_h
        mime_type = mimetypes.guess_type(processed_path)[0] or "image/png"
        image_base64 = base64.b64encode(Path(processed_path).read_bytes()).decode("ascii")
        vlm_text = client.chat_vision(
            load_prompt_for_image(img_w, img_h),
            image_base64,
            mime_type=mime_type,
        )
        vlm_result = parse_vlm_response(vlm_text)
        offset_x, offset_y = crop_offset if isinstance(crop_offset, tuple) else (0.0, 0.0)
        draft = merge_vlm_result(
            vlm_result,
            coord_offset=(float(offset_x), float(offset_y)),
            image_size=(source_w, source_h),
        )

        _update_task(db, task, progress=60, step=2, step_label=PARSE_STEPS[2])
        _notify_task(task)

        cv_walls = extract_walls_from_image(Path(processed_path), vlm_result)
        cv_walls = _offset_walls(cv_walls, float(offset_x), float(offset_y))
        draft = apply_cv_walls(draft, cv_walls)

        _update_task(db, task, progress=85, step=3, step_label=PARSE_STEPS[3])
        _notify_task(task)

        storage.save_floorplan(task.project_id, draft)
        project.status = ProjectStatus.REVIEW
        db.add(project)
        db.commit()

        _update_task(
            db,
            task,
            status=TaskStatus.DONE,
            progress=100,
            step=3,
            step_label=PARSE_STEPS[3],
            error=None,
        )
        _notify_task(task)
    except Exception as exc:
        task = db.get(Task, task_id)
        if task is not None:
            _update_task(db, task, status=TaskStatus.FAILED, error=str(exc))
            _notify_task(task)
    finally:
        db.close()


async def start_floorplan_parse(task_id: int) -> None:
    await asyncio.to_thread(run_floorplan_parse_sync, task_id)
