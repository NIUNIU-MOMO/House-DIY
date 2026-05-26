from __future__ import annotations

import json

import pytest

from app.services.floorplan.parser_vlm import (
    batch_room_stubs,
    build_validation_retry_hint,
    merge_multistep_vlm,
    parse_vlm_polygon_batch,
    parse_vlm_room_list,
    run_multistep_vlm_parse,
)
from app.schemas.floorplan import FloorPlanValidation, ValidationIssue
from app.services.floorplan.parser_vlm import VlmRoomListResult, VlmRoomStub


STEP1_JSON = """
{
  "scale_hint": 100,
  "rooms": [
    {"id": "r1", "name": "客厅", "area_label": "32.9"},
    {"id": "r2", "name": "卧室", "area_label": "15.5"},
    {"id": "r3", "name": "厨房", "area_label": "8.2"}
  ]
}
"""

STEP2_BATCH1_JSON = """
{
  "rooms": [
    {
      "id": "r1",
      "polygon": [{"x": 0, "y": 0}, {"x": 200, "y": 0}, {"x": 200, "y": 150}, {"x": 0, "y": 150}]
    },
    {
      "id": "r2",
      "polygon": [{"x": 200, "y": 0}, {"x": 400, "y": 0}, {"x": 400, "y": 150}, {"x": 200, "y": 150}]
    }
  ]
}
"""

STEP2_BATCH2_JSON = """
{
  "rooms": [
    {
      "id": "r3",
      "polygon": [{"x": 0, "y": 150}, {"x": 120, "y": 150}, {"x": 120, "y": 250}, {"x": 0, "y": 250}]
    }
  ]
}
"""


class QueueOmlxClient:
    def __init__(self, responses: list[str]):
        self.responses = responses
        self.index = 0
        self.models_used: list[str | None] = []

    def chat_vision(self, prompt, image_base64, mime_type="image/png", model=None, **kwargs):
        self.models_used.append(model)
        response = self.responses[self.index]
        self.index += 1
        return response


def test_batch_room_stubs_splits_by_two():
    rooms = [VlmRoomStub(id=f"r{i}", name=f"房间{i}") for i in range(1, 8)]
    batches = batch_room_stubs(rooms, batch_size=2)
    assert len(batches) == 4
    assert len(batches[0]) == 2
    assert len(batches[-1]) == 1


def test_merge_multistep_vlm_combines_step1_and_step2():
    room_list = parse_vlm_room_list(STEP1_JSON)
    polygons = parse_vlm_polygon_batch(STEP2_BATCH1_JSON)
    polygons.extend(parse_vlm_polygon_batch(STEP2_BATCH2_JSON))
    merged = merge_multistep_vlm(room_list, polygons)
    assert len(merged.rooms) == 3
    assert merged.rooms[0].name == "客厅"
    assert merged.rooms[0].polygon is not None
    assert len(merged.rooms[0].polygon) == 4


def test_run_multistep_vlm_parse_calls_step1_and_batches():
    client = QueueOmlxClient([STEP1_JSON, STEP2_BATCH1_JSON, STEP2_BATCH2_JSON])
    result, calls = run_multistep_vlm_parse(
        client,
        image_base64="abc",
        mime_type="image/png",
        img_w=400,
        img_h=300,
        plan_type="cad_lineart",
        vlm_model="house-vlm-cad",
    )
    assert calls == 3
    assert len(result.rooms) == 3
    assert client.index == 3


def test_run_multistep_vlm_parse_passes_vlm_model_to_client():
    client = QueueOmlxClient([STEP1_JSON, STEP2_BATCH1_JSON, STEP2_BATCH2_JSON])
    run_multistep_vlm_parse(
        client,
        image_base64="abc",
        mime_type="image/png",
        img_w=400,
        img_h=300,
        plan_type="marketing_color",
        vlm_model="house-vlm-mkt",
    )
    assert client.models_used == ["house-vlm-mkt", "house-vlm-mkt", "house-vlm-mkt"]


def test_build_validation_retry_hint_from_errors():
    validation = FloorPlanValidation(
        level="error",
        issues=[
            ValidationIssue(
                code="ROOM_OVERLAP",
                severity="error",
                message="客厅(r1) 与 餐厅(r2) IoU=0.42",
                room_ids=["r1", "r2"],
            )
        ],
    )
    hint = build_validation_retry_hint(validation)
    assert hint is not None
    assert "ROOM_OVERLAP" not in hint
    assert "IoU=0.42" in hint


def test_build_validation_retry_hint_returns_none_for_pass():
    validation = FloorPlanValidation(level="pass", issues=[])
    assert build_validation_retry_hint(validation) is None


def test_load_step2_prompt_includes_seg_hint():
    from app.services.floorplan.parser_vlm import load_step2_prompt_for_image
    from app.services.floorplan.seg_hint import format_seg_hint_for_prompt

    payload = [{"region_id": "seg1", "polygon": [{"x": 0, "y": 0}], "confidence": 0.9}]
    hint = format_seg_hint_for_prompt(payload)
    prompt = load_step2_prompt_for_image(
        400,
        300,
        "cad_lineart",
        [VlmRoomStub(id="r1", name="客厅")],
        seg_hint=hint,
    )
    assert "seg1" in prompt
    assert "预检测" in prompt


def test_load_step2_prompt_without_seg_hint_unchanged():
    from app.services.floorplan.parser_vlm import load_step2_prompt_for_image

    base = load_step2_prompt_for_image(
        400, 300, "cad_lineart", [VlmRoomStub(id="r1", name="客厅")]
    )
    with_hint_none = load_step2_prompt_for_image(
        400, 300, "cad_lineart", [VlmRoomStub(id="r1", name="客厅")], seg_hint=None
    )
    assert base == with_hint_none


def test_run_multistep_vlm_parse_passes_seg_hint_to_step2():
    captured_prompts: list[str] = []

    class CaptureClient:
        def chat_vision(self, prompt, image_base64, mime_type="image/png", model=None, **kwargs):
            captured_prompts.append(prompt)
            if len(captured_prompts) == 1:
                return STEP1_JSON
            if len(captured_prompts) == 2:
                return STEP2_BATCH1_JSON
            return STEP2_BATCH2_JSON

    run_multistep_vlm_parse(
        CaptureClient(),
        image_base64="abc",
        mime_type="image/png",
        img_w=400,
        img_h=300,
        plan_type="cad_lineart",
        seg_hint='[{"region_id":"seg1"}]',
    )
    assert "预检测" not in captured_prompts[0]
    assert any("seg1" in prompt for prompt in captured_prompts[1:])


def test_load_step1_prompt_includes_pdf_text_hint():
    from app.services.floorplan.parser_vlm import load_step1_prompt_for_image

    hint = '以下文字来自 PDF 矢量层（仅供参考）：\n[{"name":"客厅"}]'
    prompt = load_step1_prompt_for_image(400, 300, "cad_lineart", pdf_text_hint=hint)
    assert "客厅" in prompt


def test_run_multistep_vlm_parse_passes_pdf_text_hint_to_step1():
    captured_prompts: list[str] = []

    class CaptureClient:
        def chat_vision(self, prompt, image_base64, mime_type="image/png", model=None, **kwargs):
            captured_prompts.append(prompt)
            if len(captured_prompts) == 1:
                return STEP1_JSON
            if len(captured_prompts) == 2:
                return STEP2_BATCH1_JSON
            return STEP2_BATCH2_JSON

    pdf_hint = '[{"name":"客厅","area_label":"28.8"}]'
    run_multistep_vlm_parse(
        CaptureClient(),
        image_base64="abc",
        mime_type="image/png",
        img_w=400,
        img_h=300,
        plan_type="cad_lineart",
        pdf_text_hint=pdf_hint,
    )
    assert pdf_hint in captured_prompts[0]
    assert pdf_hint not in captured_prompts[1]
