import json

from app.schemas.floorplan import Point
from app.services.floorplan.parser_seg import SegRoomRegion
from app.services.floorplan.seg_hint import (
    MAX_SEG_REGIONS,
    MAX_VERTICES,
    build_seg_hint_payload,
    format_seg_hint_for_prompt,
    simplify_seg_polygon,
)


def _rect_polygon(x: float, y: float, w: float, h: float) -> list[Point]:
    return [
        Point(x=x, y=y),
        Point(x=x + w, y=y),
        Point(x=x + w, y=y + h),
        Point(x=x, y=y + h),
    ]


def test_simplify_seg_polygon_limits_vertices():
    points = [Point(x=float(i * 10), y=float(i * 5)) for i in range(12)]
    simplified = simplify_seg_polygon(points)
    assert len(simplified) <= MAX_VERTICES
    assert all("x" in point and "y" in point for point in simplified)


def test_build_seg_hint_payload_top_n_and_sort():
    regions = [
        SegRoomRegion(
            region_id=f"s{i}",
            polygon=_rect_polygon(0, 0, 100 + i * 10, 100),
            confidence=0.1 * (i + 1),
            source="morph",
        )
        for i in range(10)
    ]
    payload = build_seg_hint_payload(regions)
    assert len(payload) <= MAX_SEG_REGIONS
    for item in payload:
        assert len(item["polygon"]) <= MAX_VERTICES
        assert "region_id" in item
        assert "confidence" in item


def test_format_seg_hint_for_prompt_contains_json():
    payload = [{"region_id": "seg1", "polygon": [{"x": 0, "y": 0}], "confidence": 0.9}]
    text = format_seg_hint_for_prompt(payload)
    assert "预检测" in text
    assert "seg1" in text
    assert json.loads(text.split("\n", 1)[1]) == payload


def test_format_seg_hint_for_prompt_empty_payload():
    assert format_seg_hint_for_prompt([]) == ""
