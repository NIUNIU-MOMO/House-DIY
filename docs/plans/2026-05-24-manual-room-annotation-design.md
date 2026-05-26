# 手动标注房间 — 设计文档

> 日期：2026-05-24  
> 状态：已确认  
> 关联：校对页 `FloorPlanEditor`、需求 `docs/07-户型解析优化方案与需求.md` FR 校对扩展

## 背景

VLM 解析可能漏识别房间，用户在校对页只能改已有房间名称与顶点，无法补房间或删误识别房间。需要在模型能力不足时用手动标注弥补。

## 目标

- 右侧面板提供「新增房间」：选预设类型 → 画布单击定中心 → 生成默认矩形 → 用户拖拽顶点微调
- 支持删除选中房间（至少保留 1 个）
- 保存时沿用现有 `PUT /floorplan` → `sync_walls_from_rooms` + 质检

## 非目标（YAGNI）

- 不新增 `room_type` 持久化字段（下游仍用 `name` 关键词推断）
- 不做独立标注页/路由
- 不做按类型区分默认矩形大小（统一规则，后续可扩展）
- 不做实时后端质检（保存时刷新即可）

## 已确认决策

| 项 | 决策 |
|----|------|
| 类型 | 预设枚举 + 自动命名 |
| 放置 | 选类型后画布单击中心，出现默认矩形 |
| 入口 | 右侧面板按钮，不占左侧工具栏 |
| 删除 | 支持，至少保留 1 个房间 |
| 默认矩形 | 120×120 px，或源图短边 8%（取较小），轴对齐，clamp 在源图范围内 |

## 交互流程

```
右侧面板「+ 新增房间」
  → 类型选择（分组下拉/列表）
  → 进入放置模式（crosshair 光标 + 提示条 +「取消」）
  → SVG 单击一点
      → 生成 Room（id/name/polygon/area）
      → 自动选中新房间，退出放置模式
  → 用户拖拽顶点微调（现有能力）
  → 「保存」→ 服务端重算 validation
```

删除：选中房间 → inspector「删除房间」→ 确认 → 本地移除；最后一个房间不可删。

放置模式与比例尺、大图预览、确认户型互斥；Esc / 取消退出放置。

## 房间类型枚举

分组展示，选择后仅影响默认 **name**（不写 type 字段）：

| 分组 | 类型 key | 显示名 |
|------|----------|--------|
| 起居 | living_room | 客厅 |
| | dining_room | 餐厅 |
| | family_room | 起居室 |
| 卧室 | master_bedroom | 主卧 |
| | bedroom | 卧室 |
| | secondary_bedroom | 次卧 |
| | kids_room | 儿童房 |
| | elder_room | 长辈房 |
| | guest_room | 客房 |
| | study | 书房 |
| 厨卫 | kitchen | 厨房 |
| | bathroom | 卫生间 |
| | master_bath | 主卫 |
| | secondary_bath | 次卫 |
| | laundry | 洗衣间 |
| 交通 | entry | 玄关 |
| | corridor | 走廊 |
| | staircase | 楼梯 |
| 附属 | balcony | 阳台 |
| | utility_balcony | 生活阳台 |
| | leisure_balcony | 休闲阳台 |
| | terrace | 露台 |
| | garden | 花园 |
| 功能 | storage | 储物间 |
| | cloakroom | 衣帽间 |
| | multipurpose | 多功能室 |
| | media_room | 影音室 |
| | equipment_platform | 设备平台 |

### 命名规则

- `bedroom` / `balcony` 等带字母序列：卧室A、卧室B…
- 无字母习惯的类型：厨房、厨房2…
- 与现有房间名去重（按前缀统计）

## 默认 polygon

- 中心：用户点击 SVG 坐标
- 半宽/半高：`min(60, sourceShortEdge * 0.04)`（即总边长 min(120, 8%)）
- 四顶点轴对齐矩形
- 顶点 clamp 至 `[0, source_width] × [0, source_height]`
- 若已有 `scale`，按像素面积换算 `area`（㎡）

## 数据与 API

- **Schema 不变**：`Room { id, name, polygon, area }`
- **无新 API**：`PUT /projects/{id}/floorplan` + 现有 `prepare_floorplan_for_save`
- **id**：`r{maxExisting+1}`（解析现有 `r1,r2,…`）

## 架构（方案 2）

```
constants/roomTypes.ts     — 枚举、buildRoomName、defaultPolygonAt、nextRoomId
useManualRoom.ts           — addRoomAt、removeRoom
useCanvas.ts               — placementMode 状态、挂接增删、保存
FloorPlanSvg.vue           — 放置模式下单击 emit
index.vue                  — 右侧 UI：类型选择、新增/删除、放置提示
```

### FloorPlanSvg 点击优先级

1. `placementMode.active` → emit 放置坐标  
2. `editorMode === 'scale'` → 标定点  
3. room polygon → 选中（stopPropagation）  
4. 空白 → 现有行为（大图等）

## 质检

- 增删改仅更新本地 `floorplan`
- 保存后服务端返回新 `validation`，更新 banner
- `validation.level === 'error'` 仍禁止确认户型

## 测试

| 层级 | 内容 |
|------|------|
| 单元 | `buildRoomName`、`defaultPolygonAt` clamp、`nextRoomId` |
| 单元 | `removeRoom` 保留至少 1 间 |
| 组件（可选） | 放置模式创建房间 |
| E2E（可选） | 新增 → 保存 → validation 更新 |

## 参考

- `web/src/components/FloorPlanEditor/useCanvas.ts` — 现有编辑状态
- `web/src/components/FloorPlanEditor/FloorPlanSvg.vue` — 顶点拖拽、scale 点击
- `server/app/services/scene_builder.py` — `_infer_room_category(name)` 命名约定
- `server/app/services/floorplan/floorplan_service.py` — 保存前 sync + validate
