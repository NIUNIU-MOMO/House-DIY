import asyncio
import json

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.task import Task, TaskStatus, TaskType
from app.services.design.storage import save_design_spec
from app.services.design_spec_generator import generate_design_spec
from app.services.floorplan import storage
from app.services.floorplan.task_parse import _notify_task, _update_task
from app.services.omlx_client import OmlxClient, get_omlx_client
from app.services.scheduler import TaskEvent, next_task_status

DESIGN_STEPS = [
    "加载户型与 RAG 参考",
    "oMLX 生成 DesignSpec",
    "写入 Specs 目录",
]


def create_design_generate_task(db: Session, project_id: int, payload: dict) -> Task:
    task = Task(
        project_id=project_id,
        type=TaskType.DESIGN_GENERATE,
        status=TaskStatus.PENDING,
        progress=0,
        step=0,
        step_label=DESIGN_STEPS[0],
        payload=json.dumps(payload, ensure_ascii=False),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def run_design_generate_sync(task_id: int, omlx_client: OmlxClient | None = None) -> None:
    client = omlx_client or get_omlx_client()
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        if task is None:
            return

        floorplan = storage.load_floorplan(task.project_id)
        if floorplan is None:
            _update_task(db, task, status=TaskStatus.FAILED, error="Floorplan not found")
            _notify_task(task)
            return

        payload = json.loads(task.payload or "{}")

        task = _update_task(
            db,
            task,
            status=TaskStatus.RUNNING,
            progress=10,
            step=0,
            step_label=DESIGN_STEPS[0],
            error=None,
        )
        _notify_task(task)

        try:
            _update_task(db, task, progress=40, step=1, step_label=DESIGN_STEPS[1])
            _notify_task(task)

            spec = generate_design_spec(
                brief=payload.get("brief", ""),
                floorplan=floorplan,
                global_style=payload.get("global_style"),
                use_rag=payload.get("use_rag", True),
                omlx_client=client,
            )

            _update_task(db, task, progress=80, step=2, step_label=DESIGN_STEPS[2])
            _notify_task(task)

            save_design_spec(task.project_id, spec)

            task = _update_task(
                db,
                task,
                status=TaskStatus.DONE,
                progress=100,
                step=2,
                step_label=DESIGN_STEPS[2],
            )
            _notify_task(task)
        except Exception as exc:
            fail_status, retry_count = next_task_status(
                TaskStatus.RUNNING,
                TaskEvent.FAIL,
                task.retry_count,
            )
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


async def start_design_generate(task_id: int) -> None:
    await asyncio.to_thread(run_design_generate_sync, task_id)
