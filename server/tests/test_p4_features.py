import pytest

from app.schemas.design_spec import DesignSpec
from app.schemas.floorplan import FloorPlanModel
from app.services.design_refine_generator import apply_patch, preview_refine
from app.services.scene_builder import build_portals, build_scene

MULTI_ROOM_FLOORPLAN = {
    "scale": 100.0,
    "status": "confirmed",
    "walls": [
        {"id": "w1", "points": [{"x": 0, "y": 0}, {"x": 400, "y": 0}], "thickness": 0.2},
        {"id": "w2", "points": [{"x": 400, "y": 0}, {"x": 400, "y": 300}], "thickness": 0.2},
        {"id": "w3", "points": [{"x": 400, "y": 300}, {"x": 0, "y": 300}], "thickness": 0.2},
        {"id": "w4", "points": [{"x": 0, "y": 300}, {"x": 0, "y": 0}], "thickness": 0.2},
        {"id": "w5", "points": [{"x": 400, "y": 0}, {"x": 700, "y": 0}], "thickness": 0.2},
        {"id": "w6", "points": [{"x": 700, "y": 0}, {"x": 700, "y": 300}], "thickness": 0.2},
        {"id": "w7", "points": [{"x": 700, "y": 300}, {"x": 400, "y": 300}], "thickness": 0.2},
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
        },
        {
            "id": "r2",
            "name": "主卧",
            "polygon": [
                {"x": 400, "y": 0},
                {"x": 700, "y": 0},
                {"x": 700, "y": 300},
                {"x": 400, "y": 300},
            ],
            "area": 9.0,
        },
    ],
    "openings": [
        {
            "id": "d1",
            "type": "door",
            "wall_id": "w2",
            "position": 0.5,
            "width": 90,
            "connects": ["r1", "r2"],
        }
    ],
}

DESIGN_SPEC = {
    "version": 1,
    "globalStyle": "现代简约",
    "ragContextIds": [],
    "rooms": [
        {
            "id": "r1",
            "name": "客厅",
            "style": "现代简约",
            "palette": [],
            "furniture": [],
            "render2d": {"prompt": "living room", "negative": "blurry", "workflow": "flux_interior_t2i_api"},
        },
        {
            "id": "r2",
            "name": "主卧",
            "style": "现代简约",
            "palette": [],
            "furniture": [],
            "render2d": {"prompt": "bedroom", "negative": "blurry", "workflow": "flux_interior_t2i_api"},
        },
    ],
}


def test_build_portals_for_connected_rooms():
    floorplan = FloorPlanModel.model_validate(MULTI_ROOM_FLOORPLAN)
    portals = build_portals(floorplan, 100.0)
    assert len(portals) >= 2
    assert any(portal.source_room_id == "r1" and portal.target_room_id == "r2" for portal in portals)
    assert any(portal.source_room_id == "r2" and portal.target_room_id == "r1" for portal in portals)


def test_build_scene_includes_portals(tmp_path):
    floorplan = FloorPlanModel.model_validate(MULTI_ROOM_FLOORPLAN)
    spec = DesignSpec.model_validate(DESIGN_SPEC)
    package = build_scene(floorplan, spec, tmp_path)
    assert len(package.portals) >= 2
    assert package.rooms[0].portals


class FakeRefineClient:
    def chat_text(self, messages, **kwargs):
        return """
        {
          "affectedRoomIds": ["r1"],
          "changes": [{"roomId": "r1", "field": "style", "value": "轻奢"}],
          "diff": [{"tag": "mod", "text": "客厅风格改为轻奢", "roomId": "r1"}]
        }
        """


def test_preview_and_apply_refine():
    spec = DesignSpec.model_validate(DESIGN_SPEC)
    preview = preview_refine("客厅改轻奢", spec, omlx_client=FakeRefineClient())
    assert preview.affected_room_ids == ["r1"]
    assert preview.diff[0].text

    updated = apply_patch(spec, preview.patch)
    assert updated.rooms[0].style == "轻奢"
