import json

import pytest

from app.services.floorplan.parser_vlm import merge_vlm_result, parse_vlm_response
from app.schemas.floorplan import FloorPlanStatus


VLM_SAMPLE = """
{
  "scale_hint": 100,
  "rooms": [
    {"id": "r1", "name": "客厅", "x": 0, "y": 0, "width": 400, "height": 300},
    {"id": "r2", "name": "卧室", "x": 400, "y": 0, "width": 200, "height": 300}
  ],
  "openings": [
    {"id": "o1", "type": "door", "x": 380, "y": 120, "width": 40, "connects": ["r1", "r2"]}
  ]
}
"""


def test_parse_vlm_response_from_json():
    result = parse_vlm_response(VLM_SAMPLE)
    assert len(result.rooms) == 2
    assert result.rooms[0].name == "客厅"


def test_parse_vlm_response_from_markdown_fence():
    wrapped = f"```json\n{VLM_SAMPLE}\n```"
    result = parse_vlm_response(wrapped)
    assert len(result.openings) == 1


def test_merge_vlm_result_into_floorplan_draft():
    result = parse_vlm_response(VLM_SAMPLE)
    model = merge_vlm_result(result)

    assert model.status == FloorPlanStatus.DRAFT
    assert len(model.rooms) == 2
    assert len(model.walls) >= 4
    assert model.rooms[0].polygon[0].x == 0
