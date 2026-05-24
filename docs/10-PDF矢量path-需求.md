# PDF 矢量 Path 深化 — 需求文档

> **文档版本：** v0.1  
> **日期：** 2026-05-20  
> **状态：** 待实施  
> **上级文档：** [07-户型解析优化方案与需求](./07-户型解析优化方案与需求.md) FR-B6、Q2  
> **关联文档：** [10-PDF矢量path-实现计划](./10-PDF矢量path-实现计划.md)

---

## 1. 背景

Phase 6 已实现 PDF **栅格化全链路**（`parser_pdf.py` → `source.png` → 分类/预处理/VLM），解决「PDF 无法解析」问题。

**缺口：** 对 **矢量 PDF**（CAD 导出），文档要求提取 **墙/文字矢量路径**，而非仅截图。矢量 path 可提供更准确墙线与 OCR 面积，减少尺寸标注带对 VLM 的干扰。

---

## 2. 目标与非目标

### 2.1 目标

1. **矢量 PDF**：从 PyMuPDF 提取 line/path/rect 与 text block，生成：
   - `source_vector_structure.png`（仅墙线结构图，供 VLM/CV）
   - `pdf_vector_meta.json`（path 统计、文字块列表）
2. **扫描 PDF**：保持 Phase 6 rasterize 行为不变。
3. 矢量提取的 **文字块**（房间名、面积）可作为 VLM Step1 **弱 hint**（可选）。
4. 矢量 path 可辅助 **OpenCV 墙线** 或后续 Seg（P2 扩展点）。

### 2.2 非目标

- 完整 DXF/DWG 导入（文档 §2.3 非目标）。
- 100% 自动从 path 生成 room polygon（仍由 VLM 主导，path 为辅助）。
- 多页 PDF（本期仅 **首页**；多页记 warning）。

---

## 3. 用户场景

| ID | 场景 | 验收要点 |
|----|------|----------|
| US-P1 | 上传 CAD 矢量 PDF | `meta.pdf_mode=vector_rasterized`；生成 structure 矢量图 |
| US-P2 | 上传扫描 PDF | 仅 rasterize；不跑 path 提取 |
| US-P3 | 矢量 PDF 含房间名/面积文字 | Step1 可选 hint；面积 OCR 率提升 |
| US-P4 | 上传 PNG/JPG | 零影响，无 pdf 字段 |

---

## 4. 功能需求（FR-P）

| ID | 需求 | 优先级 |
|----|------|--------|
| FR-P1 | `extract_pdf_vector_paths()`：解析 `page.get_drawings()` 线段/矩形 | P0 |
| FR-P2 | 过滤尺寸标注带、图框外线（启发式：外围 band + 短线段） | P0 |
| FR-P3 | 渲染 `source_vector_structure.png`（白底黑线，与原图同尺寸） | P0 |
| FR-P4 | 矢量 PDF 解析时 **VLM 使用 vector structure 图** 替代普通 structural | P0 |
| FR-P5 | `extract_pdf_text_blocks()`：房间名/面积候选 → Step1 hint | P1 |
| FR-P6 | `meta.json` 扩展：`pdf_vector_paths`、`pdf_text_blocks`、`structure_source` | P1 |
| FR-P7 | 单测：合成矢量 PDF fixture 可提取 ≥4 条墙线 | P0 |
| FR-P8 | 集成：矢量 PDF 项目走完整 parse → validation | P1 |

---

## 5. 数据模型

### 5.1 `meta.json` 扩展

```json
{
  "pdf_mode": "vector_rasterized",
  "original_pdf": "source.pdf",
  "structure_source": "vector",
  "pdf_path_count": 128,
  "pdf_wall_segments": 42,
  "pdf_text_blocks": [
    {"text": "客厅", "bbox": [120, 80, 180, 100]},
    {"text": "28.8", "bbox": [200, 90, 240, 110]}
  ]
}
```

### 5.2 文件输出

| 文件 | 说明 |
|------|------|
| `source.pdf` | 原始上传 |
| `source.png` | 栅格预览（展示用） |
| `source_structural.png` | 现网结构图（非矢量 PDF） |
| `source_vector_structure.png` | **新增** 矢量渲染结构图 |
| `pdf_vector_meta.json` | **新增** 矢量提取详情（可选） |

---

## 6. 双路径策略

| PDF 类型 | 判定 | 解析用图 |
|----------|------|----------|
| 矢量 | `path_count ≥ 12` 且 `image_count ≤ 2` | `source_vector_structure.png` |
| 扫描 | 否则 | raster → 现有 preprocess structural |

---

## 7. 验收标准

| 指标 | 目标 |
|------|------|
| 矢量 PDF | 生成 vector structure；VLM 读 vector 图 |
| 扫描 PDF | 与 Phase 6 行为一致 |
| PNG 上传 | 无回归 |
| 测试 | `test_parser_pdf_vector.py` ≥8 cases |
| 性能 | 矢量提取 &lt; 3s / 页 |

---

## 8. 风险与依赖

| 风险 | 缓解 |
|------|------|
| CAD PDF path 过于复杂 | 简化渲染；fallback 到 raster structural |
| 文字块乱序 | Step1 hint 标注「仅供参考」 |
| 坐标系 Y 轴翻转 | PyMuPDF → OpenCV 统一变换 |

**依赖：** `pymupdf`（已安装）、`parser_pdf.py`、`parser_preprocess.py`、`task_parse.py`。

---

## 9. 确认清单

- [ ] 范围：FR-P1～P8  
- [ ] 首页 PDF only  
- [ ] 实现细节见 [10-PDF矢量path-实现计划](./10-PDF矢量path-实现计划.md)
