import pytest

from app.schemas.design_spec import DesignSpec, Render2DSpec, RoomDesignSpec
from app.services.design import scheme_storage


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


MINI_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)

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


def _sample_spec() -> DesignSpec:
    return DesignSpec(
        globalStyle="modern",
        rooms=[
            RoomDesignSpec(
                id="r1",
                name="客厅",
                style="modern",
                render2d=Render2DSpec(prompt="living room"),
            )
        ],
    )


@pytest.mark.asyncio
async def test_list_schemes_auto_creates_scheme_a(client, data_dir):
    create = await client.post("/api/v1/projects", json={"name": "方案列表"})
    project_id = create.json()["id"]

    resp = await client.get(f"/api/v1/projects/{project_id}/schemes")
    assert resp.status_code == 200
    schemes = resp.json()
    assert len(schemes) == 1
    assert schemes[0]["id"] == "a"
    assert schemes[0]["name"] == "方案 A"

    project = await client.get(f"/api/v1/projects/{project_id}")
    assert project.json()["active_scheme_id"] == "a"


@pytest.mark.asyncio
async def test_save_scheme_spec_bumps_max_step(client, data_dir):
    create = await client.post("/api/v1/projects", json={"name": "保存方案"})
    project_id = create.json()["id"]
    await client.post(
        f"/api/v1/projects/{project_id}/floorplan",
        files={"file": ("plan.png", MINI_PNG, "image/png")},
    )
    await client.put(f"/api/v1/projects/{project_id}/floorplan/annotation", json=FLOORPLAN_DRAFT)
    await client.post(f"/api/v1/projects/{project_id}/floorplan/confirm")

    schemes = await client.get(f"/api/v1/projects/{project_id}/schemes")
    scheme_id = schemes.json()[0]["id"]

    saved = await client.put(
        f"/api/v1/projects/{project_id}/schemes/{scheme_id}/spec",
        json=_sample_spec().model_dump(),
    )
    assert saved.status_code == 200

    project = await client.get(f"/api/v1/projects/{project_id}")
    assert project.json()["max_step"] == "design"
