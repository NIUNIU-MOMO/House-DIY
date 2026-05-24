# Phase 6 — 文档缺口补全实现计划

> **日期：** 2026-05-20  
> **分支：** `feat_AnalysisAndOptimization`  
> **依据：** [07-户型解析优化方案与需求](./07-户型解析优化方案与需求.md) 对照审计

## 未实现项清单

| 优先级 | ID | 内容 | 模块 |
|--------|-----|------|------|
| P0 | G1 | PDF 矢量/扫描双路径 → 栅格化 + 分类/预处理 | `parser_pdf.py`, `storage`, `preprocess` |
| P0 | G2 | 顶点拖拽吸附最近墙线 | `web/utils/geometry.ts`, `useCanvas.ts` |
| P1 | G3 | Seg 接入解析流水线 + parse_meta | `task_parse.py`, `ParseMeta` |
| P1 | G4 | `ROOM_DUPLICATE_LABEL` 质检 | `parser_validate.py` |
| P1 | G5 | 自交叉 polygon 校验 | `parser_validate.py` |
| P2 | G6 | 短边 &lt;800px 分辨率告警 | `parser_preprocess`, 上传页 |
| P2 | G7 | `parse_meta.vlm_duration_ms` | `task_parse.py` |
| P2 | G8 | 黄金样本 fixture 入库 | `tests/fixtures/floorplans/` |

## 实施顺序

1. **G1 PDF** — 阻塞 PDF 上传全链路  
2. **G4/G5 质检补全** — 低风险后端  
3. **G3/G7 parse_meta** — task_parse 扩展  
4. **G2 吸附墙线** — 前端几何工具  
5. **G6/G8** — 体验与测试资产  

## 验收

- [x] PDF 上传后可分类、预处理、解析  
- [x] 拖拽顶点 12px 内吸附墙线  
- [x] 解析后 `parse_meta` 含 `vlm_duration_ms`、`seg_regions`  
- [x] 同名房间 → `ROOM_DUPLICATE_LABEL` warning  
- [x] 自交叉 polygon → validation error  
- [x] 全量 pytest 通过  
