import pytest
from sqlalchemy.orm import sessionmaker

from app.models.project import Project, ProjectStatus
from app.services.floorplan import storage
from app.services.floorplan.task_parse import create_floorplan_parse_task, run_floorplan_parse_sync

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


class FakeOmlxClient:
    def __init__(self):
        base = [STEP1_RESPONSE, STEP2_RESPONSE]
        self.responses = base + base
        self.index = 0

    def chat_vision(self, prompt, image_base64, mime_type="image/png", **kwargs):
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
async def test_start_parse_task(client, data_dir, patched_task_session, monkeypatch, db_session):
    async def noop_parse(_task_id: int) -> None:
        return None

    monkeypatch.setattr("app.api.floorplan.start_floorplan_parse", noop_parse)

    create = await client.post("/api/v1/projects", json={"name": "解析测试"})
    project_id = create.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/floorplan",
        files={"file": ("plan.png", MINI_PNG, "image/png")},
    )

    fake_client = FakeOmlxClient()
    monkeypatch.setattr(
        "app.services.floorplan.task_parse.get_omlx_client",
        lambda: fake_client,
    )

    start = await client.post(f"/api/v1/projects/{project_id}/floorplan/parse")
    assert start.status_code == 202
    task_id = start.json()["id"]

    run_floorplan_parse_sync(task_id, omlx_client=fake_client)

    task = await client.get(f"/api/v1/projects/{project_id}/tasks/{task_id}")
    assert task.status_code == 200
    task_body = task.json()
    assert task_body["status"] == "done", task_body.get("error")
    assert task_body["progress"] == 100
    assert task_body["step"] == 4

    floorplan = await client.get(f"/api/v1/projects/{project_id}/floorplan")
    body = floorplan.json()
    assert body["status"] == "draft"
    assert len(body["rooms"]) == 1
    assert body["rooms"][0]["name"] == "客厅"


def test_run_parse_sync_directly(data_dir, db_session, patched_task_session):
    project = Project(name="direct-parse", status=ProjectStatus.DRAFT)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    storage.save_upload(project.id, MINI_PNG, "plan.png")
    task = create_floorplan_parse_task(db_session, project.id)
    run_floorplan_parse_sync(task.id, omlx_client=FakeOmlxClient())

    db_session.refresh(task)
    assert task.status.value == "done"

    model = storage.load_floorplan(project.id)
    assert model is not None
    assert len(model.rooms) == 1
