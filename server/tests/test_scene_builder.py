import pytest

from app.schemas.design_spec import DesignSpec
from app.schemas.floorplan import FloorPlanModel
from app.services.scene_builder import build_scene, load_furniture_catalog, load_scene_package

FLOORPLAN_SAMPLE = {
    "scale": 100.0,
    "status": "confirmed",
    "walls": [
        {"id": "w1", "points": [{"x": 0, "y": 0}, {"x": 400, "y": 0}], "thickness": 0.2},
        {"id": "w2", "points": [{"x": 400, "y": 0}, {"x": 400, "y": 500}], "thickness": 0.2},
        {"id": "w3", "points": [{"x": 400, "y": 500}, {"x": 0, "y": 500}], "thickness": 0.2},
        {"id": "w4", "points": [{"x": 0, "y": 500}, {"x": 0, "y": 0}], "thickness": 0.2},
    ],
    "rooms": [
        {
            "id": "r1",
            "name": "客厅",
            "polygon": [
                {"x": 0, "y": 0},
                {"x": 400, "y": 0},
                {"x": 400, "y": 500},
                {"x": 0, "y": 500},
            ],
            "area": 20.0,
        }
    ],
    "openings": [],
}

DESIGN_SPEC_SAMPLE = {
    "version": 1,
    "globalStyle": "现代简约",
    "ragContextIds": [],
    "rooms": [
        {
            "id": "r1",
            "name": "客厅",
            "style": "现代简约",
            "palette": ["#F5F0E8"],
            "furniture": [
                {"sku": "sofa_3seat_modern_01", "wall": "south", "offset": [0.5, 0.3], "rotation": 0}
            ],
            "render2d": {
                "prompt": "modern living room",
                "negative": "blurry",
                "workflow": "flux_interior_t2i_api",
            },
            "render3d": {
                "floorMaterial": "oak_light",
                "wallMaterial": "paint_warm_white",
                "ceilingHeight": 2.8,
                "lighting": "day_soft",
            },
        }
    ],
}


def test_furniture_catalog_has_at_least_80_skus():
    catalog = load_furniture_catalog()
    assert len(catalog) >= 80
    item = catalog["sofa_3seat_modern_01"]
    assert item["width"] > 0
    assert item["glb_path"].endswith(".glb")


def test_build_scene_exports_gltf_and_json(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.floorplan.storage.settings.house_diy_projects_dir",
        str(tmp_path),
    )
    project_id = 42
    output_dir = tmp_path / str(project_id)
    floorplan = FloorPlanModel.model_validate(FLOORPLAN_SAMPLE)
    spec = DesignSpec.model_validate(DESIGN_SPEC_SAMPLE)

    package = build_scene(floorplan, spec, output_dir)

    assert (output_dir / "scene.gltf").is_file()
    assert (output_dir / "scene.json").is_file()
    assert package.status == "ready"
    assert len(package.rooms) == 1
    assert len(package.rooms[0].collision_boxes) >= 4
    assert len(package.rooms[0].furniture) == 1

    loaded = load_scene_package(project_id)
    assert loaded is not None
    assert loaded.active_room == "r1"


@pytest.mark.asyncio
async def test_scene_api(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.floorplan.storage.settings.house_diy_projects_dir",
        str(tmp_path),
    )
    create = await client.post("/api/v1/projects", json={"name": "3D 测试"})
    project_id = create.json()["id"]
    output_dir = tmp_path / str(project_id)
    build_scene(
        FloorPlanModel.model_validate(FLOORPLAN_SAMPLE),
        DesignSpec.model_validate(DESIGN_SPEC_SAMPLE),
        output_dir,
    )

    scene = await client.get(f"/api/v1/projects/{project_id}/scene")
    assert scene.status_code == 200
    body = scene.json()
    assert body["status"] == "ready"
    assert body["gltf_url"].endswith("/scene/gltf")

    gltf = await client.get(f"/api/v1/projects/{project_id}/scene/gltf")
    assert gltf.status_code == 200
    assert b"asset" in gltf.content or b"meshes" in gltf.content
