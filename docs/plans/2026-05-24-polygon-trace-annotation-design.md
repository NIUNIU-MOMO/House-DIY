# 异形房间多边形标注 — 设计文档

> 日期：2026-05-24  
> 状态：已确认（方案 2 + 方案 3 融合）  
> 关联：`FloorPlanEditor`、`docs/11-流程重构需求.md` FR-A7～A13、`docs/07-户型解析优化方案与需求.md` FR-E4

## 背景

现网手动标注以 **4 顶点矩形** 为初值，编辑仅支持 **拖顶点** 与 **拖边平移**。L 型、斜墙、凹角等非矩形房间无法贴准墙体轮廓。

数据层 `Room.polygon: FloorPoint[]` 已支持任意顶点数，后端有自交叉校验；瓶颈在 **交互层**。

## 目标

覆盖两类场景（用户确认 **C**）：

| 场景 | 说明 |
|------|------|
| **A — 修正 AI 结果** | VLM 给出近似轮廓，用户增删顶点、拖边微调 |
| **B — 漏识别补画** | 沿墙线逐点描边，闭合为多边形房间 |

融合 **方案 2（双模式）** 与 **方案 3（智能沿墙辅助）**，在 CAD 黑白图、彩色营销图、墙线缺失等情况下尽量可用。

## 非目标（YAGNI）

- 不引入独立「标注工具」路由或新 API
- 不持久化 `room_type` 字段（仍用 `name` 推断）
- 不做自动 Magic Wand / 全图 Seg 一键填色（Seg 仍仅服务 VLM hint）
- 不做多边形布尔运算（合并/分割房间）
- 不在本期实现 Bezier 曲线墙线

## 已确认决策

| 项 | 决策 |
|----|------|
| 模式 | **调整**（默认）+ **描边** |
| 智能辅助 | 墙线线段吸附 + **墙端点/交点角点吸附**（方案 3） |
| 调整模式增删点 | 双击边中点插入；选中顶点 Delete / 右键删除 |
| 描边闭合 | ≥3 点；双击首点或 Enter 闭合；Esc 取消 |
| 快速新增 | 保留「放置默认矩形」作为快捷路径 |
| 顶点上限 | 手动标注 **32** 点（VLM Seg hint 仍 ≤8，互不冲突） |
| 顶点下限 | **3** 点（删除时不足则禁止） |
| Schema | **不变** |

---

## 1. 模式与入口

### 1.1 标注子模式（`annotationSubMode`）

在现有 `editorMode: select | scale` 之下，当 `editorMode === 'select'` 时增加：

```
annotationSubMode: 'adjust' | 'trace' | 'place-rect'
```

| 子模式 | 用途 | 进入方式 |
|--------|------|----------|
| **adjust** | 修正已有房间 | 默认；选中房间后 |
| **trace** | 沿墙描边新增/重画 | 见入口表 |
| **place-rect** | 快速矩形（现网） | 面板「+ 新增房间」或右键「矩形放置」 |

互斥：进入 `trace` / `place-rect` / `scale` 时退出其它子模式；全屏标注 overlay 内同步可用。

### 1.2 入口

| 入口 | 行为 |
|------|------|
| 右侧面板「+ 新增房间」 | 保持现网：选类型 → `place-rect` |
| 右侧面板「+ 沿墙描边」 | 选类型 → `trace` |
| 右键菜单 | 分组：**矩形放置** / **沿墙描边**（各带子类型列表） |
| 选中房间 · 面板「重画轮廓」 | 清空该 room polygon，进入 `trace` 预填类型/名称 |
| 工具栏（可选） | 「调整 / 描边」分段切换，仅在有选中房间或 trace 进行中时高亮 |

---

## 2. 调整模式（Adjust）

在现有顶点/边拖拽基础上扩展。

### 2.1 顶点拖拽（已有）

- 拖顶点 → `snapPointToWalls`（增强版，见 §4）
- 实时重算 `area`（有比例尺时）

### 2.2 边拖拽（已有）

- 拖边中点 → 该边两端点同步平移
- **单击边中点**（无拖动）→ 不插点（避免误触）
- **双击边中点** → 在边中点位置 **插入顶点**（插入点同样走 snap）

### 2.3 删点

- 选中顶点后按 **Delete / Backspace**
- 或顶点 handle **右键 → 删除顶点**
- 若删除后 `< 3` 点 → toast「至少保留 3 个顶点」，不执行
- 删除后重算 area + 本地自交叉预检（见 §6）

### 2.4 视觉

- 顶点 handle：白底圆（现网）
- 边中点 handle：小方点；hover 显示 `+` 提示
- 选中顶点：描边加粗 / 变色

---

## 3. 描边模式（Trace）

### 3.1 交互流程

```
选类型（+ 可选名称）
  → 进入 trace（顶部 banner + crosshair）
  → 单击画布落点（智能吸附，见 §4）
  → 显示橡皮筋折线 + 已落点序号
  → 继续点击追加顶点
  → 双击首点 或 Enter 闭合
      → 写入 Room（新增或重画）
      → 退出 trace，选中该 room，回到 adjust
  → Esc / banner「取消」→ 丢弃未闭合点，退出 trace
```

### 3.2 约束

- 未闭合时 **≥3 点** 才允许闭合；否则提示
- 闭合前本地校验：**简单多边形**（无自交叉）
- 闭合后写入 `rooms[]`，`id` 规则沿用 `nextRoomId`；重画模式保留原 `id/name`

### 3.3 辅助 UI

- Banner 文案：`沿墙点击拐点（至少 3 点）· Enter 闭合 · Esc 取消`
- 首点闭合区：首点 handle 放大，距离 `< 12px` 时高亮「点击闭合」
- 工具栏开关：**角点吸附**（默认开，有墙线时）；**Shift+单击** 强制不吸附单点

---

## 4. 智能沿墙辅助（方案 3）

扩展 `web/src/utils/geometry.ts`，统一为 **`snapAnnotationPoint`**，供 adjust / trace 共用。

### 4.1 吸附优先级（同一阈值内取最优）

```
1. 墙交点 / 墙端点（corner）  — 阈值 10px，优先级最高
2. 墙线段投影（segment）      — 阈值 12px（现网 FR-E4）
3. 原点击位置                  — 无吸附命中时
```

### 4.2 角点候选集

从 `floorplan.walls` 构建（墙段为 2 点线段，与现网一致）：

- **端点**：所有 `wall.points[0]`、`wall.points[1]`
- **交点**：任意两墙段 `[a0,a1]` × `[b0,b1]` 的线段相交点（排除平行/共线远端）
- 去重：距离 `< 2px` 合并

无墙线或 `walls.length === 0` 时：仅使用 segment 吸附（无命中则原坐标），trace 仍可用。

### 4.3 视觉反馈（trace / adjust 拖拽时）

- 命中 corner：画布上短暂显示绿色十字/方点预览
- 命中 segment：墙线上高亮最近投影点
- 可在 SVG 层增加 `snap-preview` 圆（不持久化）

### 4.4 降级策略

| 条件 | 行为 |
|------|------|
| CV 墙线质量低 / 墙线空 | 角点集为空，仅 segment 或无吸附 |
| 彩色图墙线不准 | 用户关「角点吸附」或 Shift+点 |
| 吸附误判 | 用户拖顶点远离即可；trace 可 Undo 最后一点（Backspace） |

### 4.5 Trace 附加能力

- **Backspace**：撤销上一个未闭合点
- **角点吸附关**：仅 segment 阈值吸附或纯自由点

---

## 5. 架构与文件

```
web/src/utils/geometry.ts
  + collectWallCorners(walls)
  + segmentIntersection(a,b,c,d)
  + snapAnnotationPoint(point, walls, options)
  + isSimplePolygon(points)          // 前端预检，镜像后端逻辑

web/src/components/FloorPlanEditor/
  usePolygonEdit.ts                  // insertVertex, removeVertex, moveEdge, ...
  useTraceMode.ts                    // trace state, addPoint, undo, close, cancel
  useCanvas.ts                       // 接入 subMode、trace、增删点
  FloorPlanSvg.vue                   // trace 折线、snap 预览、边双击插点、顶点删除
  index.vue                          // banner、面板入口、右键菜单扩展、全屏同步

docs/11-流程重构需求.md              // FR-A14～A17
```

数据流不变：`markDirty` → `PUT /floorplan` → `parser_validate` + `sync_walls_from_rooms`。

---

## 6. 校验与错误处理

### 6.1 本地预检（闭合/保存前）

- `isSimplePolygon`：自交叉 → 阻止闭合，banner 提示「轮廓自交叉，请调整顶点」
- 顶点数 `< 3` 或 `> 32` → 阻止

### 6.2 服务端（已有）

- `parser_validate.py`：`is_simple`、IoU、重复 polygon 等
- 保存后 validation banner 展示；error 级仍阻止「确认户型」

### 6.3 面积

- 增删点 / 拖顶点 / 闭合 trace 后调用 `computeRoomArea(polygon, scale)`
- 无比例尺时 area 可为 null，与现网一致

---

## 7. 与全屏标注的关系

- 全屏 overlay 复用同一 `useCanvas` 实例 → **adjust / trace / place-rect 在全屏内均可用**
- 全屏顶栏可增加「角点吸附」开关（与常规页同步状态）
- 全屏保存/取消语义不变（内存快照，不调 API）

---

## 8. 测试策略

| 层级 | 内容 |
|------|------|
| 单元 | `collectWallCorners`、`snapAnnotationPoint` 优先级、`isSimplePolygon`、insert/remove vertex |
| 组件 | `useTraceMode` 闭合/取消/undo |
| E2E | 双击边插点；trace 3 点闭合新房间；Shift+点不吸附（mock 墙线） |

---

## 9. 需求追溯（拟新增）

| ID | 描述 |
|----|------|
| FR-A14 | 调整模式：边上插入顶点、删除顶点，支持 ≥3 点异形轮廓 |
| FR-A15 | 描边模式：逐点落笔闭合多边形，用于漏识别或重画轮廓 |
| FR-A16 | 智能吸附：墙线段 + 墙端点/交点角点，可开关 |
| FR-A17 | 保留矩形快速放置；与 adjust/trace 入口并存 |

---

## 10. 分期建议

| 阶段 | 范围 |
|------|------|
| **MVP** | adjust 插删点 + trace 基础闭合 + segment/corner snap + 入口 |
| **P1** | snap 预览 UI、Backspace undo、重画轮廓、E2E |
| **P2** | 墙段 polyline 支持、吸附阈值设置（Settings 可选） |

本期实现 **MVP + P1**。
