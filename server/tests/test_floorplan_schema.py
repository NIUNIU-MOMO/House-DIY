import json
from pathlib import Path

import pytest

from app.schemas.floorplan import FloorPlanModel, FloorPlanStatus, OpeningType


@pytest.fixture
def sample_data() -> dict:
    fixture = Path(__file__).parent / "fixtures" / "floorplan_sample.json"
    return json.loads(fixture.read_text(encoding="utf-8"))


def test_floorplan_sample_validates(sample_data: dict):
    model = FloorPlanModel.model_validate(sample_data)

    assert model.status == FloorPlanStatus.DRAFT
    assert model.scale == 100.0
    assert len(model.walls) == 2
    assert len(model.rooms) == 1
    assert model.rooms[0].name == "客厅"
    assert model.openings[0].type == OpeningType.DOOR


def test_floorplan_confirmed_status(sample_data: dict):
    sample_data["status"] = "confirmed"
    model = FloorPlanModel.model_validate(sample_data)
    assert model.status == FloorPlanStatus.CONFIRMED


def test_floorplan_rejects_empty_walls_when_confirmed(sample_data: dict):
    sample_data["status"] = "confirmed"
    sample_data["walls"] = []
    with pytest.raises(ValueError):
        FloorPlanModel.model_validate(sample_data)


def test_floorplan_allows_empty_walls_in_draft():
    model = FloorPlanModel.model_validate({"status": "draft", "walls": []})
    assert model.status.value == "draft"
    assert model.walls == []
