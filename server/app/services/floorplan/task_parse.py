import asyncio
import base64
import json
import mimetypes
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import cv2
from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskStatus, TaskType
from app.core.config import settings
from app.schemas.floorplan import ParseMeta, ValidationIssue
from app.services.floorplan import storage
from app.services.floorplan.floorplan_service import prepare_floorplan_for_save
from app.services.floorplan.parser_cv import extract_walls_with_meta
from app.services.floorplan.parser_vlm import (
    apply_coord_offset,
    build_validation_retry_hint,
    merge_vlm_result,
    run_multistep_vlm_parse,
)
from app.services.floorplan.plan_classifier import PlanType, classify_floorplan_image
from app.services.floorplan.parser_preprocess import preprocess_floorplan_image
from app.services.floorplan.parser_seg import extract_room_regions, seg_backend_label
from app.services.floorplan.seg_hint import build_seg_hint_payload, format_seg_hint_for_prompt
from app.services.floorplan.pdf_text_hint import build_pdf_text_hint
from app.services.floorplan.pdf_vector_types import PdfTextBlock, VECTOR_STRUCTURAL_FILENAME
from app.services.omlx_client import OmlxClient, get_omlx_client
from app.services.task_control import ParseTaskCancelled, parse_task_control

PARSE_STEPS = [
    "图像预处理与结构增强",
    "VLM 识别房间列表",
    "VLM 分批提取轮廓",
    "OpenCV 评估墙线质量",
    "生成草稿并质检",
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


def _load_task_payload(task: Task) -> dict[str, Any]:
    if not task.payload:
        return {"logs": []}
    try:
        data = json.loads(task.payload)
    except json.JSONDecodeError:
        return {"logs": []}
    if not isinstance(data, dict):
        return {"logs": []}
    logs = data.get("logs")
    if not isinstance(logs, list):
        data["logs"] = []
    return data


def _parse_task_logs(task: Task) -> list[str]:
    logs = _load_task_payload(task).get("logs", [])
    return [str(item) for item in logs]


def _append_task_log(db: Session, task: Task, message: str, *, notify: bool = True) -> Task:
    data = _load_task_payload(task)
    logs = data.setdefault("logs", [])
    timestamp = datetime.now().strftime("%H:%M:%S")
    logs.append(f"[{timestamp}] {message}")
    if len(logs) > 200:
        data["logs"] = logs[-200:]
    task.payload = json.dumps(data, ensure_ascii=False)
    db.add(task)
    db.commit()
    db.refresh(task)
    if notify:
        _notify_task(task)
    return task


def _ensure_parse_running(task_id: int) -> None:
    parse_task_control.ensure_running(task_id)


def _finalize_parse_cancel(db: Session, task: Task, *, message: str = "用户已取消解析") -> Task:
    project = db.get(Project, task.project_id)
    if project is not None and project.status == ProjectStatus.PARSING:
        project.status = ProjectStatus.DRAFT
        db.add(project)
    _append_task_log(db, task, message, notify=False)
    task = _update_task(
        db,
        task,
        status=TaskStatus.CANCELLED,
        error=message,
    )
    _notify_task(task)
    return task


def cancel_floorplan_parse_task(db: Session, task: Task) -> Task:
    if task.type != TaskType.FLOORPLAN_PARSE:
        raise ValueError("Not a floorplan parse task")
    if task.status not in {TaskStatus.PENDING, TaskStatus.RUNNING}:
        raise ValueError("Task is not running")
    parse_task_control.request_cancel(task.id)
    return _finalize_parse_cancel(db, task)


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
        "logs": _parse_task_logs(task),
    }


def task_to_read(task: Task) -> "TaskRead":
    from app.schemas.task import TaskRead

    data = TaskRead.model_validate(task).model_dump()
    data["logs"] = _parse_task_logs(task)
    return TaskRead(**data)


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
        payload=json.dumps({"logs": []}, ensure_ascii=False),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def preprocess_image(
    source_path: str,
    *,
    plan_type: PlanType = "unknown",
    has_watermark: bool = False,
) -> tuple[str, dict]:
    return preprocess_floorplan_image(
        source_path,
        plan_type=plan_type,
        has_watermark=has_watermark,
    )


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


def _offset_wall_extract(wall_extract, offset_x: float, offset_y: float):
    if offset_x == 0 and offset_y == 0:
        return wall_extract
    from app.services.floorplan.parser_cv import WallExtractResult

    return WallExtractResult(
        walls=_offset_walls(wall_extract.walls, offset_x, offset_y),
        quality=wall_extract.quality,
        wall_source=wall_extract.wall_source,
    )


def _append_cv_quality_info(prepared, wall_extract):
    if prepared.validation is None:
        return prepared
    if wall_extract.wall_source != "polygon" or wall_extract.quality is None:
        return prepared
    issues = list(prepared.validation.issues)
    issues.append(
        ValidationIssue(
            code="WALL_CV_LOW_QUALITY",
            severity="info",
            message=(
                f"OpenCV 墙线质量 {wall_extract.quality:.2f} 不足或未适用，"
                "已统一使用房间轮廓墙线"
            ),
            room_ids=[],
        )
    )
    return prepared.model_copy(
        update={
            "validation": prepared.validation.model_copy(update={"issues": issues}),
        }
    )


def _pdf_text_hint_from_meta(meta: dict | None) -> str | None:
    if not meta:
        return None
    raw_blocks = meta.get("pdf_text_blocks") or []
    if not raw_blocks:
        return None
    blocks: list[PdfTextBlock] = []
    for item in raw_blocks:
        bbox_raw = item.get("bbox") or []
        if len(bbox_raw) < 4:
            continue
        blocks.append(
            PdfTextBlock(
                text=str(item.get("text") or ""),
                bbox=(float(bbox_raw[0]), float(bbox_raw[1]), float(bbox_raw[2]), float(bbox_raw[3])),
            )
        )
    return build_pdf_text_hint(blocks)


def _vector_preprocess_meta(
    vector_path: Path,
    *,
    raster_meta: dict | None = None,
) -> dict[str, Any]:
    image = cv2.imread(str(vector_path))
    source_h, source_w = (image.shape[:2] if image is not None else (0, 0))
    meta: dict[str, Any] = {
        "source_width": source_w,
        "source_height": source_h,
        "crop_offset": [0, 0],
        "structural_image": VECTOR_STRUCTURAL_FILENAME,
        "structure_source": "vector",
        "watermark_inpainted": False,
        "dimension_trimmed": False,
        "low_resolution": False,
    }
    if raster_meta:
        meta["low_resolution"] = bool(raster_meta.get("low_resolution"))
        for key in ("pdf_mode", "pdf_path_count", "pdf_wall_segments", "pdf_text_blocks", "pdf_multi_page_warning"):
            if key in raster_meta:
                meta[key] = raster_meta[key]
    return meta


def _run_vlm_pipeline(
    client: OmlxClient,
    *,
    structural_path: str,
    plan_type: PlanType,
    crop_offset: tuple[float, float],
    source_w: int,
    source_h: int,
    retry_hint: str | None = None,
    seg_hint: str | None = None,
    pdf_text_hint: str | None = None,
    vlm_model: str | None = None,
    on_progress: Callable[[str], None] | None = None,
    cancel_check: Callable[[], None] | None = None,
) -> tuple[Any, Any, int]:
    image = cv2.imread(structural_path)
    img_h, img_w = (image.shape[:2] if image is not None else (540, 720))
    mime_type = mimetypes.guess_type(structural_path)[0] or "image/png"
    image_base64 = base64.b64encode(Path(structural_path).read_bytes()).decode("ascii")

    vlm_result, vlm_calls = run_multistep_vlm_parse(
        client,
        image_base64=image_base64,
        mime_type=mime_type,
        img_w=img_w,
        img_h=img_h,
        plan_type=plan_type,
        retry_hint=retry_hint,
        seg_hint=seg_hint,
        pdf_text_hint=pdf_text_hint,
        vlm_model=vlm_model,
        on_progress=on_progress,
        cancel_check=cancel_check,
        on_model_used=(
            (lambda step, actual, configured=vlm_model: on_progress(
                f"实际调用模型 {actual}（{step}）"
                if actual == configured
                else f"模型 {configured} 不可用，已回退至 {actual}（{step}）"
            ))
            if on_progress and vlm_model
            else None
        ),
    )
    offset_x, offset_y = crop_offset
    draft = merge_vlm_result(
        vlm_result,
        coord_offset=(offset_x, offset_y),
        image_size=(source_w, source_h),
    )
    draft = draft.model_copy(update={"plan_type": plan_type})
    return vlm_result, draft, vlm_calls


def run_floorplan_parse_sync(task_id: int, omlx_client: OmlxClient | None = None) -> None:
    client = omlx_client or get_omlx_client()
    db = SessionLocal()
    parse_task_control.register(task_id)
    try:
        task = db.get(Task, task_id)
        if task is None:
            return

        def log(message: str) -> None:
            nonlocal task
            task = _append_task_log(db, task, message)

        def ensure_running() -> None:
            _ensure_parse_running(task_id)

        def on_vlm_progress(message: str) -> None:
            log(message)

        project = db.get(Project, task.project_id)
        if project is None:
            _update_task(db, task, status=TaskStatus.FAILED, error="Project not found")
            _notify_task(task)
            return

        raster_path, raster_meta = storage.resolve_parse_image_path(task.project_id)
        if raster_path is None:
            _update_task(db, task, status=TaskStatus.FAILED, error="Source image not found")
            _notify_task(task)
            return
        if raster_meta:
            storage.patch_meta(task.project_id, raster_meta)

        project.status = ProjectStatus.PARSING
        db.add(project)
        db.commit()

        log("开始解析任务，加载源图…")
        _update_task(
            db,
            task,
            status=TaskStatus.RUNNING,
            progress=5,
            step=0,
            step_label=PARSE_STEPS[0],
        )
        _notify_task(task)
        ensure_running()

        classification = classify_floorplan_image(raster_path)
        log(f"图源分类：{classification.plan_type}（{classification.message}）")
        storage.patch_meta(
            task.project_id,
            {
                "plan_type": classification.plan_type,
                "has_watermark": classification.has_watermark,
                "plan_type_message": classification.message,
            },
        )
        plan_type = classification.plan_type

        project_meta = storage.load_meta(task.project_id) or {}
        vector_structural = storage.get_parse_structural_path(task.project_id)
        pdf_text_hint = _pdf_text_hint_from_meta(project_meta)

        if project_meta.get("structure_source") == "vector" and vector_structural is not None:
            structural_path = str(vector_structural)
            preprocess_meta = _vector_preprocess_meta(vector_structural, raster_meta=raster_meta)
            storage.patch_meta(task.project_id, preprocess_meta)
            log("使用 PDF 矢量结构图，跳过栅格预处理")
        else:
            log("执行图像预处理与结构增强…")
            structural_path, preprocess_meta = preprocess_image(
                str(raster_path),
                plan_type=plan_type,
                has_watermark=classification.has_watermark,
            )
            storage.patch_meta(task.project_id, preprocess_meta)
            log("图像预处理完成")
        ensure_running()
        crop_offset = preprocess_meta.get("crop_offset", (0, 0))
        if isinstance(crop_offset, list):
            crop_offset = tuple(crop_offset)
        source_w = int(preprocess_meta.get("source_width") or 0)
        source_h = int(preprocess_meta.get("source_height") or 0)
        _update_task(db, task, progress=18, step=0, step_label=PARSE_STEPS[0])
        _notify_task(task)

        _update_task(db, task, progress=25, step=1, step_label=PARSE_STEPS[1])
        _notify_task(task)

        float_offset = (
            float(crop_offset[0]) if isinstance(crop_offset, tuple) else 0.0,
            float(crop_offset[1]) if isinstance(crop_offset, tuple) else 0.0,
        )
        if not source_w or not source_h:
            image = cv2.imread(structural_path)
            if image is not None:
                source_h, source_w = image.shape[:2]

        vlm_model = settings.vlm_model_for_plan_type(plan_type)
        log(f"选用 VLM 模型：{vlm_model}")
        vlm_started = time.perf_counter()

        seg_hint_used = False
        seg_hint_text: str | None = None
        extracted_seg_regions: list = []
        if settings.seg_hint_active():
            log("提取 Seg 区域 hint…")
            extracted_seg_regions = extract_room_regions(Path(structural_path))
            payload = build_seg_hint_payload(extracted_seg_regions)
            seg_hint_text = format_seg_hint_for_prompt(payload) or None
            seg_hint_used = seg_hint_text is not None
            if seg_hint_used:
                log(f"Seg hint 已生成，共 {len(extracted_seg_regions)} 个区域")
            else:
                log("Seg hint 未生成有效区域")

        ensure_running()
        log("开始 VLM 多步解析（Step1 房间列表 + Step2 分批轮廓）…")
        vlm_result, draft, vlm_calls = _run_vlm_pipeline(
            client,
            structural_path=structural_path,
            plan_type=plan_type,
            crop_offset=float_offset,
            source_w=source_w,
            source_h=source_h,
            seg_hint=seg_hint_text,
            pdf_text_hint=pdf_text_hint,
            vlm_model=vlm_model,
            on_progress=on_vlm_progress,
            cancel_check=ensure_running,
        )

        vlm_duration_ms = int((time.perf_counter() - vlm_started) * 1000)
        log(f"VLM 解析完成，共 {vlm_calls} 次调用，耗时 {vlm_duration_ms}ms，识别 {len(vlm_result.rooms)} 个房间")
        ensure_running()

        _update_task(db, task, progress=62, step=2, step_label=PARSE_STEPS[2])
        _notify_task(task)

        _update_task(db, task, progress=72, step=3, step_label=PARSE_STEPS[3])
        _notify_task(task)
        log("OpenCV 评估墙线质量…")

        wall_extract = extract_walls_with_meta(Path(structural_path), vlm_result)
        wall_extract = _offset_wall_extract(wall_extract, float_offset[0], float_offset[1])
        quality_label = (
            f"{wall_extract.quality:.2f}" if wall_extract.quality is not None else "N/A"
        )
        log(f"墙线来源：{wall_extract.wall_source}，质量评分 {quality_label}")

        _update_task(db, task, progress=85, step=4, step_label=PARSE_STEPS[4])
        _notify_task(task)
        log("生成草稿并执行质检…")

        seg_regions = 0
        seg_backend = "disabled"
        if settings.house_diy_seg_enabled:
            if not extracted_seg_regions:
                extracted_seg_regions = extract_room_regions(Path(structural_path))
            seg_regions = len(extracted_seg_regions)
            seg_backend = seg_backend_label()

        parse_meta = ParseMeta(
            vlm_model=vlm_model,
            vlm_steps=vlm_calls,
            vlm_duration_ms=vlm_duration_ms,
            cv_wall_quality=wall_extract.quality,
            wall_source="polygon",
            seg_regions=seg_regions,
            seg_backend=seg_backend,
            seg_hint_used=seg_hint_used if settings.house_diy_seg_enabled else None,
        )
        low_res = bool(preprocess_meta.get("low_resolution"))
        seg_for_validate = extracted_seg_regions if settings.house_diy_seg_enabled else None
        prepared = prepare_floorplan_for_save(
            draft,
            parse_meta=parse_meta,
            low_resolution=low_res,
            seg_regions=seg_for_validate,
        )
        prepared = _append_cv_quality_info(prepared, wall_extract)

        retry_hint = build_validation_retry_hint(prepared.validation)
        if retry_hint is not None:
            log("质检未通过，发起 VLM 重试…")
            ensure_running()
            retry_started = time.perf_counter()
            retry_result, retry_draft, retry_calls = _run_vlm_pipeline(
                client,
                structural_path=structural_path,
                plan_type=plan_type,
                crop_offset=float_offset,
                source_w=source_w,
                source_h=source_h,
                retry_hint=retry_hint,
                seg_hint=seg_hint_text,
                pdf_text_hint=pdf_text_hint,
                vlm_model=vlm_model,
                on_progress=on_vlm_progress,
                cancel_check=ensure_running,
            )
            vlm_result = retry_result
            draft = retry_draft
            vlm_calls += retry_calls
            retry_ms = int((time.perf_counter() - retry_started) * 1000)
            log(f"VLM 重试完成，额外 {retry_calls} 次调用，耗时 {retry_ms}ms")
            vlm_duration_ms += retry_ms
            wall_extract = extract_walls_with_meta(Path(structural_path), vlm_result)
            wall_extract = _offset_wall_extract(wall_extract, float_offset[0], float_offset[1])
            parse_meta = parse_meta.model_copy(
                update={"vlm_steps": vlm_calls, "vlm_duration_ms": vlm_duration_ms},
            )
            prepared = prepare_floorplan_for_save(
                draft,
                parse_meta=parse_meta,
                low_resolution=low_res,
                seg_regions=seg_for_validate,
            )
            prepared = _append_cv_quality_info(prepared, wall_extract)

        ensure_running()
        storage.save_floorplan(task.project_id, prepared)
        project.status = ProjectStatus.REVIEW
        db.add(project)
        db.commit()
        log("解析完成，已保存草稿")

        _update_task(
            db,
            task,
            status=TaskStatus.DONE,
            progress=100,
            step=4,
            step_label=PARSE_STEPS[4],
            error=None,
        )
        _notify_task(task)
    except ParseTaskCancelled:
        task = db.get(Task, task_id)
        if task is not None and task.status != TaskStatus.CANCELLED:
            _finalize_parse_cancel(db, task)
    except Exception as exc:
        task = db.get(Task, task_id)
        if task is not None and task.status not in {TaskStatus.CANCELLED}:
            _append_task_log(db, task, f"解析失败：{exc}", notify=False)
            _update_task(db, task, status=TaskStatus.FAILED, error=str(exc))
            _notify_task(task)
            project = db.get(Project, task.project_id)
            if project is not None and project.status == ProjectStatus.PARSING:
                project.status = ProjectStatus.DRAFT
                db.add(project)
                db.commit()
    finally:
        parse_task_control.clear(task_id)
        db.close()


async def start_floorplan_parse(task_id: int) -> None:
    await asyncio.to_thread(run_floorplan_parse_sync, task_id)
