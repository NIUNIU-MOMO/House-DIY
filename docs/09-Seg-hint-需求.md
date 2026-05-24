# Seg Hint 深化 — 需求文档

> **文档版本：** v0.1  
> **日期：** 2026-05-20  
> **状态：** 待实施  
> **上级文档：** [07-户型解析优化方案与需求](./07-户型解析优化方案与需求.md) §4.3.1 M3、Q4  
> **关联文档：** [07-appendix-seg-models](./07-appendix-seg-models.md)、[09-Seg-hint-实现计划](./09-Seg-hint-实现计划.md)

---

## 1. 背景

Phase 5～6 已交付 `parser_seg.py`、配置项 `HOUSE_DIY_SEG_*`、解析后 `parse_meta.seg_regions/seg_backend` 统计，以及 benchmark `--seg` 对比。

**缺口：** Seg 结果**未参与** VLM 推理与质检决策，无法改善「彩色图跟色块走、polygon 不贴墙」等 M3 目标场景。

---

## 2. 目标与非目标

### 2.1 目标

1. 在 **VLM Step2**（分批 polygon）向模型提供 **Seg 区域几何 hint**，提高初稿贴墙率、降低重叠。
2. 在 **质检阶段** 增加 Seg 与 VLM 不一致告警，引导用户在校对页修正。
3. 保持 **100% 本地离线**；Seg 关闭时行为与现网完全一致（零回归）。
4. `parse_meta` 扩展记录 hint 是否启用、匹配统计。

### 2.2 非目标

- 不用 Seg **完全替代** VLM polygon 输出（仍保留 FR-D 质检 + FR-E 编辑）。
- 本期不训练/微调专用 Seg 模型（可接第三方 ONNX；默认形态学回退仅作链路验证）。
- 不把 Seg 结果直接写入 `floorplan.json` 的 room polygon（仅 hint + validation）。

---

## 3. 用户场景

| ID | 场景 | 验收要点 |
|----|------|----------|
| US-S1 | 上传贝壳类彩色 JPG，开启 Seg | Step2 prompt 含 seg 区域；房间 polygon 更贴墙体围合 |
| US-S2 | Seg 与 VLM 房间区域偏差大 | 校对页出现 `SEG_VLM_MISMATCH` warning，不阻止 confirmed |
| US-S3 | `HOUSE_DIY_SEG_ENABLED=false` | 解析流程、prompt、validation 与现网一致 |
| US-S4 | 仅形态学 Seg（无 ONNX） | hint 链路可跑通；质量低于 ONNX 时可配置关闭 hint |

---

## 4. 功能需求（FR-S）

| ID | 需求 | 优先级 |
|----|------|--------|
| FR-S1 | 预处理完成后、VLM Step1 之前，对 `source_structural.png` 执行 `extract_room_regions()` | P0 |
| FR-S2 | 将 Seg 区域简化为 ≤N 个顶点 polygon，序列化注入 Step2 prompt（按 room 批次或全局） | P0 |
| FR-S3 | Step2 prompt 明确：hint **仅供参考**，必须以墙体线为准，忽略家具/色块 | P0 |
| FR-S4 | 新增质检 `SEG_VLM_MISMATCH`：room 与最近 seg 区域 IoU &lt; 阈值 → warning | P1 |
| FR-S5 | `parse_meta` 增加 `seg_hint_used: bool`、`seg_match_warnings: int` | P1 |
| FR-S6 | 配置 `HOUSE_DIY_SEG_HINT_ENABLED`（默认 true，且依赖 `SEG_ENABLED`） | P1 |
| FR-S7 | marketing 图源 IoU 阈值严于 cad（与 FR-D 一致） | P1 |

---

## 5. 接口与数据模型

### 5.1 配置（`server/.env`）

```env
HOUSE_DIY_SEG_ENABLED=true
HOUSE_DIY_SEG_HINT_ENABLED=true
HOUSE_DIY_SEG_MODEL_PATH=   # 可选 ONNX
```

### 5.2 `parse_meta` 扩展

```json
{
  "seg_regions": 3,
  "seg_backend": "morph",
  "seg_hint_used": true,
  "seg_match_warnings": 1
}
```

### 5.3 质检 Issue（附录扩展）

| Code | Severity | 说明 |
|------|----------|------|
| `SEG_VLM_MISMATCH` | warning | VLM room polygon 与 Seg 区域 IoU 低于阈值 |

---

## 6. 验收标准

| 指标 | 目标 |
|------|------|
| Seg 关闭 | 与 Phase 6 行为 bit-equal（mock e2e 通过） |
| Seg + hint 开启 | Step2 prompt 含 seg JSON；`parse_meta.seg_hint_used=true` |
| 彩色样本 | `SEG_VLM_MISMATCH` 可触发（单测 + 合成图） |
| 性能 | Seg + hint 增加解析耗时 &lt; 15s（形态学后端） |
| 测试 | 新增 ≥6 个单元/集成测试 |

---

## 7. 风险与依赖

| 风险 | 缓解 |
|------|------|
| hint 过长超 context | 限制 seg 区域数 ≤8；polygon 顶点 ≤8 |
| 形态学 seg 噪声误导 VLM | 配置可关 hint；marketing 仅 hint 不强制 |
| Seg/VLM 坐标系不一致 | 统一使用 structural 图像素坐标 |

**依赖：** Phase 6 `parser_seg.py`、`parser_vlm.load_step2_prompt_for_image`、`parser_validate.polygon_iou`。

---

## 8. 确认清单

- [ ] 范围：FR-S1～S7  
- [ ] 不替代 VLM、不替代人工校对  
- [ ] 实现细节见 [09-Seg-hint-实现计划](./09-Seg-hint-实现计划.md)
