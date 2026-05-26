import json
from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

from app.services.knowledge.case_writer import write_design_case
from app.services.knowledge.vault_io import ensure_vault_dirs
from app.services.orchestrator import run_pipeline_sync
from app.services.render.storage import RenderManifest, RenderRecord, upsert_render
from app.schemas.design_spec import DesignSpec
from app.schemas.floorplan import FloorPlanModel

SAMPLE_SPEC = {
    "version": 1,
    "globalStyle": "现代简约、暖白、原木",
    "ragContextIds": ["case-001"],
    "rooms": [
        {
            "id": "r1",
            "name": "客厅",
            "style": "现代简约",
            "palette": ["#F5F0E8"],
            "furniture": [],
            "render2d": {
                "prompt": "interior design, modern living room",
                "negative": "blurry",
                "workflow": "flux_interior_t2i_api",
                "controlnet": "layout_depth",
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

MINI_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)

FLOORPLAN_DRAFT = {
    "scale": 100.0,
    "status": "confirmed",
    "walls": [
        {"id": "w1", "points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}], "thickness": 0.2},
    ],
    "rooms": [
        {
            "id": "r1",
            "name": "客厅",
            "polygon": [
                {"x": 0, "y": 0},
                {"x": 100, "y": 0},
                {"x": 100, "y": 100},
                {"x": 0, "y": 100},
            ],
            "area": 12.0,
        }
    ],
    "openings": [],
}


class FakeOmlxClient:
    def chat_text(self, messages, **kwargs):
        return json.dumps(SAMPLE_SPEC, ensure_ascii=False)


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


@pytest.fixture
def vault_dir(tmp_path, monkeypatch):
    path = tmp_path / "vault"
    monkeypatch.setattr(
        "app.services.knowledge.case_writer.settings.house_diy_vault_path",
        str(path),
    )
    return path


@pytest.mark.asyncio
async def test_design_generate_pipeline(client, db_session, data_dir, vault_dir, monkeypatch):
    factory = sessionmaker(bind=db_session.get_bind())
    monkeypatch.setattr("app.services.orchestrator.SessionLocal", factory)
    monkeypatch.setattr("app.services.knowledge.case_writer.settings.house_diy_vault_path", str(vault_dir))

    async def noop_enqueue(job):
        return None

    monkeypatch.setattr("app.api.design.gpu_scheduler.enqueue", noop_enqueue)

    create = await client.post("/api/v1/projects", json={"name": "流水线测试"})
    project_id = create.json()["id"]
    await client.post(
        f"/api/v1/projects/{project_id}/floorplan",
        files={"file": ("plan.png", MINI_PNG, "image/png")},
    )
    await client.put(f"/api/v1/projects/{project_id}/floorplan/annotation", json=FLOORPLAN_DRAFT)
    await client.post(f"/api/v1/projects/{project_id}/floorplan/confirm")

    start = await client.post(
        f"/api/v1/projects/{project_id}/design/generate",
        json={"brief": "现代简约暖白", "global_style": "现代简约", "use_rag": True},
    )
    assert start.status_code == 202
    task_id = start.json()["id"]

    run_pipeline_sync(task_id, omlx_client=FakeOmlxClient(), placeholder_png=MINI_PNG)

    task = await client.get(f"/api/v1/projects/{project_id}/tasks/{task_id}")
    assert task.json()["status"] == "done"

    spec = await client.get(f"/api/v1/projects/{project_id}/design/spec")
    assert spec.status_code == 200

    renders = await client.get(f"/api/v1/projects/{project_id}/renders")
    assert renders.status_code == 200
    assert len(renders.json()["rooms"]) == 1

    image = await client.get(f"/api/v1/projects/{project_id}/renders/r1/image")
    assert image.status_code == 200
    assert image.content[:8] == MINI_PNG[:8]

    scene_path = data_dir / str(project_id) / "scene.json"
    assert scene_path.is_file()
    scene_data = json.loads(scene_path.read_text(encoding="utf-8"))
    assert scene_data["status"] == "ready"
    assert len(scene_data["rooms"]) >= 1

    ensure_vault_dirs(vault_dir)
    case_files = list((vault_dir / "Cases").glob("*.md"))
    assert case_files


def test_case_writer_writes_vault_files(data_dir, vault_dir, monkeypatch):
    monkeypatch.setattr(
        "app.services.knowledge.case_writer.settings.house_diy_vault_path",
        str(vault_dir),
    )
    ensure_vault_dirs(vault_dir)

    project_id = 1
    spec = DesignSpec.model_validate(SAMPLE_SPEC)
    floorplan = FloorPlanModel.model_validate(FLOORPLAN_DRAFT)

    upsert_render(
        project_id,
        RenderRecord(
            room_id="r1",
            room_name="客厅",
            filename="r1.png",
            prompt="interior design",
        ),
        MINI_PNG,
    )
    manifest = RenderManifest(rooms=[
        RenderRecord(
            room_id="r1",
            room_name="客厅",
            filename="r1.png",
            prompt="interior design",
        )
    ])

    case_path = write_design_case(project_id, "测试项目", spec, floorplan, manifest, vault_root=vault_dir)

    assert case_path.is_file()
    assert "现代简约" in case_path.read_text(encoding="utf-8")
    assert (vault_dir / "Assets" / "project-1-r1.png").is_file()
    assert (vault_dir / "Specs" / "project-1-designspec.json").is_file()
