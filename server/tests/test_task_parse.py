import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import sessionmaker

from app.services.floorplan.task_parse import run_floorplan_parse_sync

MINI_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)

VLM_RESPONSE = """
{
  "scale_hint": 100,
  "rooms": [
    {"id": "r1", "name": "客厅", "x": 0, "y": 0, "width": 100, "height": 100}
  ],
  "openings": []
}
"""


class FakeOmlxClient:
    def chat_vision(self, prompt, image_base64, mime_type="image/png", **kwargs):
        return VLM_RESPONSE


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
async def test_start_parse_task(client, data_dir, patched_task_session, monkeypatch):
    create = await client.post("/api/v1/projects", json={"name": "解析测试"})
    project_id = create.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/floorplan",
        files={"file": ("plan.png", MINI_PNG, "image/png")},
    )

    monkeypatch.setattr(
        "app.services.floorplan.task_parse.get_omlx_client",
        lambda: FakeOmlxClient(),
    )

    start = await client.post(f"/api/v1/projects/{project_id}/floorplan/parse")
    assert start.status_code == 202
    task_id = start.json()["id"]

    run_floorplan_parse_sync(task_id, omlx_client=FakeOmlxClient())

    task = await client.get(f"/api/v1/projects/{project_id}/tasks/{task_id}")
    assert task.status_code == 200
    assert task.json()["status"] == "done"
    assert task.json()["progress"] == 100

    floorplan = await client.get(f"/api/v1/projects/{project_id}/floorplan")
    body = floorplan.json()
    assert body["status"] == "draft"
    assert len(body["rooms"]) == 1
    assert body["rooms"][0]["name"] == "客厅"
