# Seg Hint 深化 — 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans + TDD to implement task-by-task.  
> **Goal:** 将 Seg 区域注入 VLM Step2 prompt，并在质检中报告 Seg/VLM 不一致。  
> **Architecture:** 预处理 structural 图 → `parser_seg` 提取区域 → `parser_vlm` 拼接 hint → 解析后 `parser_validate` 交叉校验 → `parse_meta` 落盘。  
> **Tech Stack:** Python 3.12、OpenCV、现有 oMLX VLM、Shapely IoU  
> **需求文档：** [09-Seg-hint-需求.md](./09-Seg-hint-需求.md)  
> **预估周期：** 3～4 天

---

## 里程碑

| 阶段 | 交付 | 工期 |
|------|------|------|
| **S-H0** | 配置 + Seg hint 序列化模块 | 0.5d |
| **S-H1** | Step2 prompt 注入 + task_parse 串联 | 1d |
| **S-H2** | SEG_VLM_MISMATCH 质检 + parse_meta | 1d |
| **S-H3** | 测试 + 文档 | 0.5～1d |

---

## Task 1：配置项扩展

**Files:**
- Modify: `server/app/core/config.py`
- Modify: `server/.env.example`
- Create: `server/tests/test_config_seg_hint.py`

**Step 1:** 新增 `house_diy_seg_hint_enabled: bool = True`

**Step 2:** 新增 helper `def seg_hint_active(self) -> bool` → `seg_enabled and seg_hint_enabled`

**Step 3:** 单测：hint 在 seg 关闭时为 False

---

## Task 2：Seg hint 序列化

**Files:**
- Create: `server/app/services/floorplan/seg_hint.py`
- Test: `server/tests/test_seg_hint.py`

**职责：**

```python
MAX_SEG_REGIONS = 8
MAX_VERTICES = 8

def simplify_seg_polygon(points: list[Point]) -> list[dict]
def build_seg_hint_payload(regions: list[SegRoomRegion]) -> list[dict]
def format_seg_hint_for_prompt(payload: list[dict]) -> str
```

**规则：**
- 按 `confidence * area` 降序，取 top-N 区域
- `cv2.approxPolyDP` 或 Shapely simplify 限制顶点数
- 输出 JSON 数组：`[{ "region_id", "polygon": [{x,y},...], "confidence" }]`

**Step 1:** 写失败单测：8 区域输入 → 输出 ≤8、顶点 ≤8

**Step 2:** 实现并通过测试

---

## Task 3：Step2 prompt 注入

**Files:**
- Modify: `server/app/services/floorplan/parser_vlm.py`
  - `load_step2_prompt_for_image(..., seg_hint: str | None = None)`
  - `run_multistep_vlm_parse(..., seg_hint: str | None = None)`
- Modify: `server/prompts/floorplan_vlm_polygons.txt`（末尾加 hint 说明段，可选独立 `floorplan_vlm_seg_hint.txt`）
- Test: `server/tests/test_parser_vlm_multistep.py`

**Prompt 追加模板：**

```
以下 segmentation 预检测区域仅供参考，polygon 必须贴墙体内侧，勿沿色块/家具：
{seg_hint_json}
```

**Step 1:** 单测 mock client 收到的 prompt 含 seg JSON

**Step 2:** `seg_hint=None` 时 prompt 与现网一致

---

## Task 4：task_parse 串联

**Files:**
- Modify: `server/app/services/floorplan/task_parse.py`

**流程调整：**

```
preprocess → structural_path
  → if seg_hint_active:
       regions = extract_room_regions(structural_path)
       seg_hint = format_seg_hint_for_prompt(...)
     else:
       seg_hint = None
  → run_multistep_vlm_parse(..., seg_hint=seg_hint)
  → validate (+ seg mismatch)
```

**注意：** Seg 提取移到 VLM **之前**（现网在之后，需调整顺序）。

**Step 1:** 集成测试 mock：seg enabled → `parse_meta.seg_hint_used=true`

---

## Task 5：SEG_VLM_MISMATCH 质检

**Files:**
- Modify: `server/app/services/floorplan/parser_validate.py`
- Modify: `server/app/schemas/floorplan.py`（ParseMeta 字段，可选）
- Test: `server/tests/test_parser_validate.py`

**算法：**

```python
def _detect_seg_vlm_mismatch(
    rooms: list[Room],
    seg_regions: list[SegRoomRegion],
    plan_type: PlanType | None,
) -> list[ValidationIssue]:
    # 每个 room 找 IoU 最大的 seg 区域
    # IoU < IOU_SEG_WARN (cad 0.12 / mkt 0.08) → SEG_VLM_MISMATCH warning
```

**Step 1:** 单测：room 与 seg 区域重叠低 → 产生 warning

**Step 2:** `validate_floorplan(..., seg_regions=None)` 跳过此项

---

## Task 6：parse_meta 与 floorplan_service

**Files:**
- Modify: `server/app/schemas/floorplan.py` — `seg_hint_used`, `seg_match_warnings`
- Modify: `server/app/services/floorplan/floorplan_service.py` — 传递 seg_regions 给 validate（或 task_parse 内先 validate 再 save）

**推荐：** `prepare_floorplan_for_save(..., seg_regions=...)` 扩展参数，避免重复跑 seg。

---

## Task 7：benchmark 与文档

**Files:**
- Modify: `scripts/benchmark_floorplan_vlm.py` — `--seg-hint` 标志
- Modify: `docs/07-appendix-seg-models.md`

---

## Task 8：回归测试清单

```bash
cd server && pytest tests/test_seg_hint.py tests/test_parser_vlm_multistep.py \
  tests/test_parser_validate.py tests/test_floorplan_parse_e2e.py -q
./scripts/benchmark-floorplan-vlm.sh --mock --seg
```

**期望：** 全通过；Seg 关闭时 e2e 与 Phase 6 等价。

---

## 提交建议

```
feat(floorplan): inject seg hints into VLM Step2 and validation (Phase 7-SH)
```

分 2～3 PR：Task 1-4（hint 链路）→ Task 5-6（质检）→ Task 7-8（文档测试）。

---

## 开放问题（实施前默认）

| # | 问题 | 默认 |
|---|------|------|
| Q1 | hint 注入 Step1 还是仅 Step2？ | **仅 Step2** |
| Q2 | 形态学 seg 默认开 hint？ | **开**，可 `.env` 关 |
| Q3 | mismatch 是否 error？ | **warning** |
