from app.schemas.floorplan import FloorPlanModel, Point, Room, Wall
from app.services.floorplan.parser_validate import (
    validate_floorplan,
    validation_blocks_confirm,
)


def _room(room_id: str, name: str, x: float, y: float, w: float, h: float, area: float | None = None) -> Room:
    return Room(
        id=room_id,
        name=name,
        polygon=[
            Point(x=x, y=y),
            Point(x=x + w, y=y),
            Point(x=x + w, y=y + h),
            Point(x=x, y=y + h),
        ],
        area=area,
    )


def test_validate_passes_non_overlapping_rooms():
    model = FloorPlanModel(
        rooms=[
            _room("r1", "客厅", 0, 0, 400, 300, 12.0),
            _room("r2", "卧室", 400, 0, 200, 300, 8.0),
        ],
        walls=[Wall(id="w1", points=[Point(x=0, y=0), Point(x=400, y=0)])],
    )
    result = validate_floorplan(model)
    assert result.level == "pass"
    assert not validation_blocks_confirm(result)


def test_validate_detects_duplicate_polygon_as_error():
    duplicate = _room("r1", "儿童房", 10, 10, 100, 100, 16.8)
    model = FloorPlanModel(
        rooms=[
            duplicate,
            _room("r2", "长辈房", 10, 10, 100, 100, 24.7),
        ]
    )
    result = validate_floorplan(model)
    assert result.level == "error"
    assert any(issue.code == "ROOM_DUPLICATE_POLYGON" for issue in result.issues)
    assert validation_blocks_confirm(result)


def test_validate_detects_overlap_as_error():
    model = FloorPlanModel(
        rooms=[
            _room("r1", "客厅", 0, 0, 400, 300, 32.9),
            _room("r2", "餐厅", 50, 50, 200, 150, 8.4),
        ]
    )
    result = validate_floorplan(model)
    assert result.level in {"error", "warning"}
    assert any(issue.code == "ROOM_OVERLAP" for issue in result.issues)


def test_validate_area_mismatch_warning_when_scale_set():
    model = FloorPlanModel(
        scale=100.0,
        rooms=[_room("r1", "客厅", 0, 0, 100, 100, 50.0)],
    )
    result = validate_floorplan(model)
    assert result.level == "warning"
    assert any(issue.code == "AREA_MISMATCH" for issue in result.issues)
    assert not validation_blocks_confirm(result)
