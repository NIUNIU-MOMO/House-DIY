import pytest
from httpx import ASGITransport, AsyncClient

MINI_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.floorplan.storage.settings.house_diy_projects_dir",
        str(tmp_path),
    )
    monkeypatch.setattr(
        "app.services.settings_storage.resolve_output_root",
        lambda env_fallback=None: tmp_path,
    )
    return tmp_path


@pytest.mark.asyncio
async def test_upload_and_get_floorplan(client, data_dir):
    create = await client.post("/api/v1/projects", json={"name": "望京三期"})
    project_id = create.json()["id"]

    upload = await client.post(
        f"/api/v1/projects/{project_id}/floorplan",
        files={"file": ("plan.png", MINI_PNG, "image/png")},
        data={"name": "望京三期 89㎡", "estimated_area": "89"},
    )
    assert upload.status_code == 201
    body = upload.json()
    assert body["status"] == "draft"
    assert body["source_image"] == "source.png"
    assert body["estimated_area"] == 89.0
    assert body["plan_type"] in {"cad_lineart", "marketing_color", "unknown"}
    assert "plan_type_label" in body

    detail = await client.get(f"/api/v1/projects/{project_id}/floorplan")
    assert detail.status_code == 200
    assert detail.json()["status"] == "draft"

    source_path = data_dir / str(project_id) / "source.png"
    assert source_path.is_file()


@pytest.mark.asyncio
async def test_get_floorplan_not_found(client):
    resp = await client.get("/api/v1/projects/9999/floorplan")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_upload_invalid_project(client, data_dir):
    resp = await client.post(
        "/api/v1/projects/9999/floorplan",
        files={"file": ("plan.png", MINI_PNG, "image/png")},
    )
    assert resp.status_code == 404


FLOORPLAN_DRAFT = {
    "scale": 100.0,
    "status": "draft",
    "walls": [
        {"id": "w1", "points": [{"x": 0, "y": 0}, {"x": 400, "y": 0}], "thickness": 0.2},
        {"id": "w2", "points": [{"x": 400, "y": 0}, {"x": 400, "y": 300}], "thickness": 0.2},
    ],
    "rooms": [
        {
            "id": "r1",
            "name": "客厅",
            "polygon": [
                {"x": 0, "y": 0},
                {"x": 400, "y": 0},
                {"x": 400, "y": 300},
                {"x": 0, "y": 300},
            ],
            "area": 12.0,
        }
    ],
    "openings": [],
}


def _room_for_api(room_id: str, name: str, x: float, y: float, w: float, h: float, area: float):
    return {
        "id": room_id,
        "name": name,
        "polygon": [
            {"x": x, "y": y},
            {"x": x + w, "y": y},
            {"x": x + w, "y": y + h},
            {"x": x, "y": y + h},
        ],
        "area": area,
    }


@pytest.mark.asyncio
async def test_upload_bumps_max_step_to_parse(client, data_dir):
    create = await client.post("/api/v1/projects", json={"name": "上传进度"})
    project_id = create.json()["id"]
    assert create.json()["max_step"] == "upload"

    upload = await client.post(
        f"/api/v1/projects/{project_id}/floorplan",
        files={"file": ("plan.png", MINI_PNG, "image/png")},
    )
    assert upload.status_code == 201

    project = await client.get(f"/api/v1/projects/{project_id}")
    assert project.json()["max_step"] == "parse"


@pytest.mark.asyncio
async def test_save_annotation_bumps_max_step(client, data_dir):
    create = await client.post("/api/v1/projects", json={"name": "标注进度"})
    project_id = create.json()["id"]
    await client.post(
        f"/api/v1/projects/{project_id}/floorplan",
        files={"file": ("plan.png", MINI_PNG, "image/png")},
    )

    saved = await client.put(
        f"/api/v1/projects/{project_id}/floorplan/annotation",
        json=FLOORPLAN_DRAFT,
    )
    assert saved.status_code == 200
    assert saved.json()["status"] == "draft"

    project = await client.get(f"/api/v1/projects/{project_id}")
    assert project.json()["max_step"] == "annotate"


@pytest.mark.asyncio
async def test_confirm_floorplan(client, data_dir):
    create = await client.post("/api/v1/projects", json={"name": "确认测试"})
    project_id = create.json()["id"]
    await client.post(
        f"/api/v1/projects/{project_id}/floorplan",
        files={"file": ("plan.png", MINI_PNG, "image/png")},
    )
    await client.put(
        f"/api/v1/projects/{project_id}/floorplan/annotation",
        json={
            **FLOORPLAN_DRAFT,
            "rooms": [
                {**FLOORPLAN_DRAFT["rooms"][0], "name": "客餐厅"},
                _room_for_api("r2", "卧室", 400, 0, 200, 300, 8.0),
            ],
        },
    )

    confirmed = await client.post(f"/api/v1/projects/{project_id}/floorplan/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    assert confirmed.json()["annotation_stale"] is False

    project = await client.get(f"/api/v1/projects/{project_id}")
    assert project.json()["status"] == "designing"
    assert project.json()["max_step"] == "annotate"


@pytest.mark.asyncio
async def test_confirm_rejected_on_validation_error(client, data_dir):
    create = await client.post("/api/v1/projects", json={"name": "质检拦截"})
    project_id = create.json()["id"]
    await client.post(
        f"/api/v1/projects/{project_id}/floorplan",
        files={"file": ("plan.png", MINI_PNG, "image/png")},
    )

    duplicate_room = {
        "id": "r2",
        "name": "卧室",
        "polygon": FLOORPLAN_DRAFT["rooms"][0]["polygon"],
        "area": 10.0,
    }
    payload = {
        **FLOORPLAN_DRAFT,
        "rooms": [FLOORPLAN_DRAFT["rooms"][0], duplicate_room],
    }
    await client.put(f"/api/v1/projects/{project_id}/floorplan/annotation", json=payload)
    confirmed = await client.post(f"/api/v1/projects/{project_id}/floorplan/confirm")
    assert confirmed.status_code == 422


@pytest.mark.asyncio
async def test_update_floorplan_confirmed(client, data_dir):
    create = await client.post("/api/v1/projects", json={"name": "校对测试"})
    project_id = create.json()["id"]
    await client.post(
        f"/api/v1/projects/{project_id}/floorplan",
        files={"file": ("plan.png", MINI_PNG, "image/png")},
    )

    confirmed = {
        **FLOORPLAN_DRAFT,
        "status": "confirmed",
        "rooms": [
            {**FLOORPLAN_DRAFT["rooms"][0], "name": "客餐厅"},
            _room_for_api("r2", "卧室", 400, 0, 200, 300, 8.0),
        ],
    }
    updated = await client.put(f"/api/v1/projects/{project_id}/floorplan", json=confirmed)
    assert updated.status_code == 400


@pytest.mark.asyncio
async def test_update_floorplan_confirmed_rejected_on_validation_error(client, data_dir):
    create = await client.post("/api/v1/projects", json={"name": "质检拦截旧接口"})
    project_id = create.json()["id"]
    await client.post(
        f"/api/v1/projects/{project_id}/floorplan",
        files={"file": ("plan.png", MINI_PNG, "image/png")},
    )

    duplicate_room = {
        "id": "r2",
        "name": "卧室",
        "polygon": FLOORPLAN_DRAFT["rooms"][0]["polygon"],
        "area": 10.0,
    }
    payload = {
        **FLOORPLAN_DRAFT,
        "status": "confirmed",
        "rooms": [FLOORPLAN_DRAFT["rooms"][0], duplicate_room],
    }
    updated = await client.put(f"/api/v1/projects/{project_id}/floorplan", json=payload)
    assert updated.status_code == 400


@pytest.mark.asyncio
async def test_set_floorplan_scale(client, data_dir):
    create = await client.post("/api/v1/projects", json={"name": "比例尺测试"})
    project_id = create.json()["id"]
    await client.post(
        f"/api/v1/projects/{project_id}/floorplan",
        files={"file": ("plan.png", MINI_PNG, "image/png")},
    )
    await client.put(f"/api/v1/projects/{project_id}/floorplan", json=FLOORPLAN_DRAFT)

    scale = await client.post(
        f"/api/v1/projects/{project_id}/floorplan/scale",
        json={
            "point_a": {"x": 0, "y": 0},
            "point_b": {"x": 100, "y": 0},
            "distance_m": 1.2,
        },
    )
    assert scale.status_code == 200
    assert scale.json()["scale"] == pytest.approx(100 / 1.2, rel=0.01)
