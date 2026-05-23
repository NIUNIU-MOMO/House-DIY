import json

import pytest

from app.schemas.design_spec import DesignSpec
from app.services.design_spec_generator import parse_design_spec_response

SAMPLE_SPEC = {
    "version": 1,
    "globalStyle": "现代简约、暖白、原木",
    "ragContextIds": ["case-001"],
    "rooms": [
        {
            "id": "r1",
            "name": "客厅",
            "style": "现代简约",
            "palette": ["#F5F0E8", "#8B7355"],
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


def test_design_spec_validates_sample():
    spec = DesignSpec.model_validate(SAMPLE_SPEC)
    assert spec.globalStyle.startswith("现代")
    assert spec.rooms[0].render2d.prompt


def test_parse_design_spec_from_json_string():
    spec = parse_design_spec_response(json.dumps(SAMPLE_SPEC, ensure_ascii=False))
    assert len(spec.rooms) == 1


def test_design_spec_requires_rooms():
    invalid = {**SAMPLE_SPEC, "rooms": []}
    with pytest.raises(Exception):
        DesignSpec.model_validate(invalid)
