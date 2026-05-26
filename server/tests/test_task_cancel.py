import threading
import time

import pytest
from sqlalchemy.orm import sessionmaker

from app.models.project import Project, ProjectStatus
from app.models.task import TaskStatus
from app.services.floorplan import storage
from app.services.floorplan.task_parse import (
    create_floorplan_parse_task,
    run_floorplan_parse_sync,
)

MINI_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)

STEP1_RESPONSE = """
{
  "scale_hint": 100,
  "rooms": [
    {"id": "r1", "name": "客厅", "area_label": "12.0"}
  ]
}
"""

STEP2_RESPONSE = """
{
  "rooms": [
    {
      "id": "r1",
      "polygon": [
        {"x": 0, "y": 0},
        {"x": 1, "y": 0},
        {"x": 1, "y": 1},
        {"x": 0, "y": 1}
      ]
    }
  ]
}
"""


class SlowOmlxClient:
    def __init__(self):
        self.responses = [STEP1_RESPONSE, STEP2_RESPONSE]
        self.index = 0
        self.step1_entered = threading.Event()

    def chat_vision(self, prompt, image_base64, mime_type="image/png", **kwargs):
        if self.index == 0:
            self.step1_entered.set()
            time.sleep(0.3)
        response = self.responses[self.index]
        self.index += 1
        return response


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.floorplan.storage.settings.house_diy_projects_dir",
        str(tmp_path),
    )
    return tmp_path


@pytest.fixture
def patched_task_session(db_session, monkeypatch):
    factory = sessionmaker(bind=db_session.get_bind())
    monkeypatch.setattr("app.services.floorplan.task_parse.SessionLocal", factory)


@pytest.mark.asyncio
async def test_cancel_parse_task(client, data_dir, patched_task_session, monkeypatch, db_session):
    create = await client.post("/api/v1/projects", json={"name": "取消测试"})
    project_id = create.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/floorplan",
        files={"file": ("plan.png", MINI_PNG, "image/png")},
    )

    slow_client = SlowOmlxClient()

    def run_in_background(task_id: int) -> None:
        run_floorplan_parse_sync(task_id, omlx_client=slow_client)

    start = await client.post(f"/api/v1/projects/{project_id}/floorplan/parse")
    assert start.status_code == 202
    task_id = start.json()["id"]

    worker = threading.Thread(target=run_in_background, args=(task_id,), daemon=True)
    worker.start()

    assert slow_client.step1_entered.wait(timeout=5)

    cancel = await client.post(f"/api/v1/projects/{project_id}/tasks/{task_id}/cancel")
    assert cancel.status_code == 200
    body = cancel.json()
    assert body["status"] == "cancelled"
    assert body["logs"]
    assert "取消" in body["logs"][-1]

    worker.join(timeout=5)

    project = db_session.get(Project, project_id)
    assert project is not None
    assert project.status == ProjectStatus.DRAFT


def test_cancelled_task_has_logs(data_dir, db_session, patched_task_session):
    project = Project(name="log-test", status=ProjectStatus.DRAFT)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    storage.save_upload(project.id, MINI_PNG, "plan.png")
    task = create_floorplan_parse_task(db_session, project.id)
    run_floorplan_parse_sync(task.id, omlx_client=SlowOmlxClient())

    db_session.refresh(task)
    assert task.status == TaskStatus.DONE
    payload = task.payload or ""
    assert "开始解析任务" in payload
    assert "VLM" in payload
