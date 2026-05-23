import pytest

from app.models.project import Project, ProjectStatus
from app.services.render.storage import RenderRecord, upsert_render

MINI_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.floorplan.storage.settings.house_diy_projects_dir",
        str(tmp_path),
    )
    return tmp_path


@pytest.mark.asyncio
async def test_create_and_list_projects(client):
    create = await client.post("/api/v1/projects", json={"name": "望京三期 89㎡"})
    assert create.status_code == 201
    pid = create.json()["id"]
    listing = await client.get("/api/v1/projects")
    assert listing.status_code == 200
    assert any(p["id"] == pid for p in listing.json())


@pytest.mark.asyncio
async def test_get_and_delete_project(client):
    create = await client.post("/api/v1/projects", json={"name": "测试项目"})
    pid = create.json()["id"]

    detail = await client.get(f"/api/v1/projects/{pid}")
    assert detail.status_code == 200
    assert detail.json()["name"] == "测试项目"

    deleted = await client.delete(f"/api/v1/projects/{pid}")
    assert deleted.status_code == 204

    missing = await client.get(f"/api/v1/projects/{pid}")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_list_projects_includes_cover_for_delivered(client, data_dir, db_session):
    create = await client.post("/api/v1/projects", json={"name": "封面测试"})
    pid = create.json()["id"]

    upsert_render(
        pid,
        RenderRecord(
            room_id="r1",
            room_name="客厅",
            filename="r1.png",
            prompt="interior design",
        ),
        MINI_PNG,
    )

    project = db_session.get(Project, pid)
    project.status = ProjectStatus.DELIVERED
    db_session.commit()

    listing = await client.get("/api/v1/projects")
    match = next(item for item in listing.json() if item["id"] == pid)
    assert match["cover_image_url"] == f"/api/v1/projects/{pid}/renders/r1/image"
