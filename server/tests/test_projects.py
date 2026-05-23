import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


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
