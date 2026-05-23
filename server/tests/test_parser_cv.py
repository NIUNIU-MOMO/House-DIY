from pathlib import Path

import cv2
import numpy as np
import pytest

from app.services.floorplan.parser_cv import (
    _score_walls,
    _vlm_room_bounds,
    extract_walls_from_image,
)
from app.services.floorplan.parser_vlm import VlmParseResult, VlmPoint, VlmRoom, walls_from_room_polygons as vlm_walls_from_rooms
from app.schemas.floorplan import Point, Wall


@pytest.fixture
def sample_floor_image(tmp_path: Path) -> Path:
    image = np.ones((300, 400, 3), dtype=np.uint8) * 255
    cv2.rectangle(image, (40, 40), (360, 260), (0, 0, 0), 4)
    cv2.line(image, (200, 40), (200, 180), (0, 0, 0), 3)
    cv2.line(image, (40, 180), (360, 180), (0, 0, 0), 3)
    path = tmp_path / "sample_floor.png"
    cv2.imwrite(str(path), image)
    return path


def test_extract_walls_returns_at_least_four(sample_floor_image: Path):
    vlm_result = VlmParseResult(
        rooms=[
            VlmRoom(id="r1", name="客厅", x=40, y=40, width=160, height=140),
            VlmRoom(id="r2", name="卧室", x=200, y=40, width=160, height=140),
        ]
    )
    walls = extract_walls_from_image(sample_floor_image, vlm_result)
    assert len(walls) >= 4


def test_extract_walls_falls_back_when_dimension_lines_outside_rooms(tmp_path: Path):
    """彩色图外侧尺寸标注线不应覆盖 VLM 房间墙。"""
    image = np.ones((540, 720, 3), dtype=np.uint8) * 255
    cv2.rectangle(image, (80, 60), (420, 420), (0, 0, 0), 5)
    cv2.line(image, (300, 60), (300, 260), (0, 0, 0), 4)
    for y in range(80, 500, 40):
        cv2.line(image, (520, y), (700, y), (80, 80, 80), 1)
    for x in range(520, 700, 30):
        cv2.line(image, (x, 80), (x, 500), (80, 80, 80), 1)
    path = tmp_path / "plan.png"
    cv2.imwrite(str(path), image)

    vlm_result = VlmParseResult(
        rooms=[
            VlmRoom(id="r1", name="客厅", x=80, y=60, width=220, height=360),
            VlmRoom(id="r2", name="卧室", x=300, y=60, width=120, height=200),
        ]
    )
    walls = extract_walls_from_image(path, vlm_result)
    for wall in walls:
        mid_x = (wall.points[0].x + wall.points[1].x) / 2
        assert mid_x < 500, "不应保留右侧尺寸标注区域的墙线"
    assert len(walls) >= 4


def test_score_walls_penalizes_noise():
    vlm_result = VlmParseResult(
        rooms=[VlmRoom(id="r1", name="客厅", x=40, y=40, width=200, height=200)]
    )
    good = vlm_walls_from_rooms([room.polygon_points() for room in vlm_result.rooms])
    noisy = good + [
        Wall(id=f"n{i}", points=[Point(x=600.0, y=float(i)), Point(x=650.0, y=float(i))])
        for i in range(20)
    ]
    assert _score_walls(good, vlm_result, 400, 300) > _score_walls(noisy, vlm_result, 400, 300)


def test_vlm_room_bounds_from_polygon_only_rooms():
    vlm_result = VlmParseResult(
        rooms=[
            VlmRoom(
                id="r1",
                name="客厅",
                polygon=[
                    VlmPoint(x=80.0, y=60.0),
                    VlmPoint(x=420.0, y=60.0),
                    VlmPoint(x=420.0, y=420.0),
                    VlmPoint(x=80.0, y=420.0),
                ],
            )
        ]
    )
    bounds = _vlm_room_bounds(vlm_result, 720, 540)
    assert bounds is not None
    left, top, right, bottom = bounds
    assert left < 80
    assert top < 60
    assert right > 420
    assert bottom > 420


def test_extract_walls_polygon_only_rooms(sample_floor_image: Path):
    vlm_result = VlmParseResult(
        rooms=[
            VlmRoom(
                id="r1",
                name="客厅",
                polygon=[
                    VlmPoint(x=40.0, y=40.0),
                    VlmPoint(x=200.0, y=40.0),
                    VlmPoint(x=200.0, y=180.0),
                    VlmPoint(x=40.0, y=180.0),
                ],
            ),
            VlmRoom(
                id="r2",
                name="卧室",
                polygon=[
                    VlmPoint(x=200.0, y=40.0),
                    VlmPoint(x=360.0, y=40.0),
                    VlmPoint(x=360.0, y=180.0),
                    VlmPoint(x=200.0, y=180.0),
                ],
            ),
        ]
    )
    walls = extract_walls_from_image(sample_floor_image, vlm_result)
    assert len(walls) >= 4
