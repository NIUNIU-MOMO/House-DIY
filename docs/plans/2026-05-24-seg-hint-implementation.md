# Seg Hint Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Inject segmentation region geometry hints into VLM Step2 prompts and report Seg/VLM mismatches during validation.

**Architecture:** After preprocessing produces `source_structural.png`, run `extract_room_regions()` when seg hint is active, serialize top regions to JSON, append to Step2 prompts via `parser_vlm`, then pass the same regions to `parser_validate` for `SEG_VLM_MISMATCH` warnings. Record `seg_hint_used` and `seg_match_warnings` in `parse_meta`.

**Tech Stack:** Python 3.12, FastAPI, OpenCV, Shapely IoU, existing oMLX VLM client

---

### Task 1: Config extension

**Files:**
- Modify: `server/app/core/config.py`
- Modify: `server/.env.example`
- Create: `server/tests/test_config_seg_hint.py`

**Step 1: Write the failing test**

```python
def test_seg_hint_active_requires_seg_enabled():
    cfg = Settings(house_diy_seg_enabled=False, house_diy_seg_hint_enabled=True)
    assert cfg.seg_hint_active() is False

def test_seg_hint_active_when_both_enabled():
    cfg = Settings(house_diy_seg_enabled=True, house_diy_seg_hint_enabled=True)
    assert cfg.seg_hint_active() is True

def test_seg_hint_disabled_when_hint_flag_off():
    cfg = Settings(house_diy_seg_enabled=True, house_diy_seg_hint_enabled=False)
    assert cfg.seg_hint_active() is False
```

**Step 2: Run test to verify it fails**

Run: `cd server && pytest tests/test_config_seg_hint.py -v`
Expected: FAIL with `AttributeError: seg_hint_active`

**Step 3: Write minimal implementation**

Add to `Settings`:
```python
house_diy_seg_hint_enabled: bool = True

def seg_hint_active(self) -> bool:
    return self.house_diy_seg_enabled and self.house_diy_seg_hint_enabled
```

Add to `.env.example`:
```env
HOUSE_DIY_SEG_HINT_ENABLED=true
```

**Step 4: Run test to verify it passes**

Run: `cd server && pytest tests/test_config_seg_hint.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add server/app/core/config.py server/.env.example server/tests/test_config_seg_hint.py
git commit -m "feat(config): add HOUSE_DIY_SEG_HINT_ENABLED and seg_hint_active()"
```

---

### Task 2: Seg hint serialization module

**Files:**
- Create: `server/app/services/floorplan/seg_hint.py`
- Test: `server/tests/test_seg_hint.py`

**Step 1: Write the failing test**

```python
from app.schemas.floorplan import Point
from app.services.floorplan.parser_seg import SegRoomRegion
from app.services.floorplan.seg_hint import (
    MAX_SEG_REGIONS,
    MAX_VERTICES,
    build_seg_hint_payload,
    format_seg_hint_for_prompt,
    simplify_seg_polygon,
)

def test_simplify_seg_polygon_limits_vertices():
    points = [Point(x=float(i * 10), y=float(i * 5)) for i in range(12)]
    simplified = simplify_seg_polygon(points)
    assert len(simplified) <= MAX_VERTICES
    assert all("x" in p and "y" in p for p in simplified)

def test_build_seg_hint_payload_top_n_and_sort():
    regions = [
        SegRoomRegion(region_id=f"s{i}", polygon=[Point(x=0,y=0),Point(x=100,y=0),Point(x=100,y=100),Point(x=0,y=100)], confidence=0.5, source="morph")
        for i in range(10)
    ]
    payload = build_seg_hint_payload(regions)
    assert len(payload) <= MAX_SEG_REGIONS
    for item in payload:
        assert len(item["polygon"]) <= MAX_VERTICES

def test_format_seg_hint_for_prompt_contains_json():
    payload = [{"region_id": "seg1", "polygon": [{"x": 0, "y": 0}], "confidence": 0.9}]
    text = format_seg_hint_for_prompt(payload)
    assert "segmentation" in text.lower() or "预检测" in text
    assert "seg1" in text
```

**Step 2: Run test to verify it fails**

Run: `cd server && pytest tests/test_seg_hint.py -v`
Expected: FAIL with import error

**Step 3: Write minimal implementation**

```python
MAX_SEG_REGIONS = 8
MAX_VERTICES = 8

def _polygon_area(points: list[Point]) -> float:
    # shoelace formula
    ...

def simplify_seg_polygon(points: list[Point]) -> list[dict]:
    # cv2.approxPolyDP iteratively reduce epsilon until <= MAX_VERTICES
    ...

def build_seg_hint_payload(regions: list[SegRoomRegion]) -> list[dict]:
    # sort by confidence * area desc, take top MAX_SEG_REGIONS
    ...

def format_seg_hint_for_prompt(payload: list[dict]) -> str:
    return (
        "以下 segmentation 预检测区域仅供参考，polygon 必须贴墙体内侧，勿沿色块/家具：\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )
```

**Step 4: Run test to verify it passes**

Run: `cd server && pytest tests/test_seg_hint.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add server/app/services/floorplan/seg_hint.py server/tests/test_seg_hint.py
git commit -m "feat(floorplan): add seg hint serialization for VLM Step2"
```

---

### Task 3: Step2 prompt injection

**Files:**
- Modify: `server/app/services/floorplan/parser_vlm.py:153-181,378-425`
- Test: `server/tests/test_parser_vlm_multistep.py`

**Step 1: Write the failing test**

```python
def test_load_step2_prompt_includes_seg_hint():
    from app.services.floorplan.parser_vlm import load_step2_prompt_for_image, VlmRoomStub
    hint = '[{"region_id":"seg1","polygon":[{"x":0,"y":0}],"confidence":0.9}]'
    prompt = load_step2_prompt_for_image(400, 300, "cad_lineart", [VlmRoomStub(id="r1", name="客厅")], seg_hint=hint)
    assert "seg1" in prompt
    assert "预检测" in prompt or "segmentation" in prompt.lower()

def test_load_step2_prompt_without_seg_hint_unchanged():
    from app.services.floorplan.parser_vlm import load_step2_prompt_for_image, VlmRoomStub
    base = load_step2_prompt_for_image(400, 300, "cad_lineart", [VlmRoomStub(id="r1", name="客厅")])
    with_hint_none = load_step2_prompt_for_image(400, 300, "cad_lineart", [VlmRoomStub(id="r1", name="客厅")], seg_hint=None)
    assert base == with_hint_none

def test_run_multistep_vlm_parse_passes_seg_hint_to_step2():
    captured_prompts = []
    class CaptureClient:
        def chat_vision(self, prompt, *args, **kwargs):
            captured_prompts.append(prompt)
            ...
    run_multistep_vlm_parse(..., seg_hint='[{"region_id":"seg1"}]')
    assert any("seg1" in p for p in captured_prompts[1:])
```

**Step 2: Run test — expect FAIL**

**Step 3: Add `seg_hint: str | None = None` to `load_step2_prompt_for_image` and `run_multistep_vlm_parse`**

**Step 4: Run test — expect PASS**

**Step 5: Commit**

---

### Task 4: task_parse pipeline wiring

**Files:**
- Modify: `server/app/services/floorplan/task_parse.py:186-219,283-339`
- Test: `server/tests/test_floorplan_parse_e2e.py`

**Step 1: Write failing integration test**

```python
def test_parse_with_seg_hint_sets_parse_meta(data_dir, db_session, patched_task_session, monkeypatch):
    monkeypatch.setattr("app.services.floorplan.task_parse.settings.house_diy_seg_enabled", True)
    monkeypatch.setattr("app.services.floorplan.task_parse.settings.house_diy_seg_hint_enabled", True)
    # run parse, assert parse_meta.seg_hint_used is True
```

**Step 2-4: Implement — extract seg before VLM, pass seg_hint, store regions for validation**

**Step 5: Commit**

---

### Task 5: SEG_VLM_MISMATCH validation

**Files:**
- Modify: `server/app/services/floorplan/parser_validate.py`
- Test: `server/tests/test_parser_validate.py`

**Step 1: Write failing test**

```python
def test_validate_seg_vlm_mismatch_warning():
    from app.services.floorplan.parser_seg import SegRoomRegion
    room = _room("r1", "客厅", 0, 0, 50, 50)
    seg = SegRoomRegion(region_id="seg1", polygon=[Point(x=200,y=200),...], confidence=0.8, source="morph")
    result = validate_floorplan(FloorPlanModel(rooms=[room]), seg_regions=[seg])
    assert any(i.code == "SEG_VLM_MISMATCH" for i in result.issues)

def test_validate_skips_seg_mismatch_when_no_regions():
    result = validate_floorplan(FloorPlanModel(rooms=[_room("r1","客厅",0,0,100,100)]), seg_regions=None)
    assert not any(i.code == "SEG_VLM_MISMATCH" for i in result.issues)
```

Constants: `IOU_SEG_WARN_CAD = 0.12`, `IOU_SEG_WARN_MARKETING = 0.08`

**Step 2-5: Implement, test, commit**

---

### Task 6: parse_meta and floorplan_service

**Files:**
- Modify: `server/app/schemas/floorplan.py:32-39`
- Modify: `server/app/services/floorplan/floorplan_service.py:23-44`
- Modify: `server/app/services/floorplan/task_parse.py`

Add `seg_hint_used: bool | None`, `seg_match_warnings: int | None` to ParseMeta.
Extend `prepare_floorplan_for_save(..., seg_regions=None)` and count warnings.

**Commit after tests pass**

---

### Task 7: Benchmark and docs

**Files:**
- Modify: `scripts/benchmark_floorplan_vlm.py`
- Modify: `docs/07-appendix-seg-models.md`

Add `--seg-hint` flag; document hint config and validation codes.

---

### Task 8: Regression suite

Run:
```bash
cd server && pytest tests/test_config_seg_hint.py tests/test_seg_hint.py \
  tests/test_parser_vlm_multistep.py tests/test_parser_validate.py \
  tests/test_floorplan_parse_e2e.py -q
./scripts/benchmark-floorplan-vlm.sh --mock --seg
```

Expected: all pass; seg disabled e2e unchanged.
