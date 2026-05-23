from pathlib import Path

import cv2
import numpy as np
import pytest

from app.schemas.design_spec import DesignSpec
from app.schemas.floorplan import FloorPlanModel
from app.services.render.room_depth_map import render_room_layout_depth, save_room_depth_map

FLOORPLAN = {
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

SAMPLE_SPEC = {
    "version": 1,
    "globalStyle": "现代简约",
    "rooms": [
        {
            "id": "r1",
            "name": "客厅",
            "style": "现代简约",
            "palette": [],
            "furniture": [],
            "render2d": {
                "prompt": "living room",
                "negative": "blurry",
                "workflow": "flux_interior_depth_api",
                "controlnet": "layout_depth",
            },
        }
    ],
}


def test_render_room_layout_depth_png_header():
    floorplan = FloorPlanModel.model_validate(FLOORPLAN)
    spec = DesignSpec.model_validate(SAMPLE_SPEC)
    png_bytes = render_room_layout_depth(floorplan, "r1", room_spec=spec.rooms[0])
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(png_bytes) > 1024


def test_render_room_layout_depth_has_furniture_signal():
    floorplan = FloorPlanModel.model_validate(FLOORPLAN)
    spec = DesignSpec.model_validate(SAMPLE_SPEC)
    png_bytes = render_room_layout_depth(floorplan, "r1", room_spec=spec.rooms[0], size=512)
    arr = cv2.imdecode(np.frombuffer(png_bytes, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    assert arr is not None
    assert int(arr.max()) - int(arr.min()) > 20


def test_save_room_depth_map(tmp_path: Path):
    floorplan = FloorPlanModel.model_validate(FLOORPLAN)
    target = tmp_path / "depth" / "r1.png"
    png_bytes = save_room_depth_map(floorplan, "r1", target)
    assert target.is_file()
    assert target.read_bytes() == png_bytes


def test_render_room_layout_depth_missing_room():
    floorplan = FloorPlanModel.model_validate(FLOORPLAN)
    with pytest.raises(ValueError, match="not found"):
        render_room_layout_depth(floorplan, "missing")
