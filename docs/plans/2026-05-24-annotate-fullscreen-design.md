# 标注页全屏手动标注模式 — 设计文档

> 日期：2026-05-24  
> 状态：已确认  
> 关联：`docs/11-流程重构需求.md` §4.3 标注、`FloorPlanEditor`

## 背景

标注页为三栏布局（左工具 / 中画布 / 右手动标注），中间画布可视区域偏小，拖拽顶点、右键新增房间等操作不便。现有「点击查看大图」弹窗为只读预览，无法编辑。

## 目标

- 在画布工具栏增加 **「全屏标注」** 入口，进入全屏可编辑模式
- 全屏以 **画布优先（方案 C）**：铺满视口 + 精简浮动工具，不展示比例尺、左栏工具、确认进设计等
- 全屏内 **保存 / 取消** 仅退出全屏；**保存不调用 API**（方案 B），改动保留在内存并标记 dirty，回到三栏页后仍用主工具栏「保存」落盘

## 非目标

- 不新增路由或独立标注页
- 全屏内不提供「确认并进入设计」（仍在三栏右栏）
- 全屏内不提供比例尺标定（需退出全屏使用左栏）
- 不改变后端 annotation / confirm API 语义

## 已确认决策

| 项 | 决策 |
|----|------|
| 布局 | **C** — 全屏画布 + 右下/右侧精简浮动工具 |
| 全屏保存 | **B** — 保留内存改动 + `markDirty()`，不调 `PUT /annotation` |
| 全屏取消 | 丢弃**本次全屏会话**内改动；有变更时二次确认 |
| 实现方式 | **方案 1** — 同组件 `fixed` overlay，复用 `useCanvas` 与 `FloorPlanSvg` |
| 入口 | 画布工具栏「保存 \| 状态」同一行，按钮文案 **「全屏标注」** |
| 浮动工具位置 | 右侧浮层（与现网右栏手动标注能力对齐，不占底部横条） |

## 交互流程

```
三栏标注页
  → 点击「全屏标注」
      → 深拷贝 floorplan 为 fullscreenSnapshot
      → 强制 editorMode = select，退出放置/比例尺
      → 打开 fixed 全屏 overlay（z-index 高于 AppHeader）
  → 全屏内编辑（顶点/边线/右键新增/浮动面板增删改）
  → 「保存」：markDirty()，关闭 overlay（内存保留）
  → 「取消」：若相对 snapshot 有改动 → confirm → 恢复快照 → 关闭
  → Esc：同取消
回到三栏页
  → 用户点击主工具栏「保存」→ PUT /floorplan/annotation
  → 「确认并进入设计」逻辑不变
```

## 全屏 UI 结构

```
┌──────────────────────────────────────────────────┐
│ 手动标注     [☑ 原图底图]          保存    取消   │
├──────────────────────────────────────────────────┤
│                                                  │
│              FloorPlanSvg（editable）             │
│                                                  │
│                               ┌─────────────┐    │
│                               │ 房间类型 ▼  │    │
│                               │ + 新增房间  │    │
│                               │ 名称 [    ] │    │
│                               │ 删除房间    │    │
│                               └─────────────┘    │
└──────────────────────────────────────────────────┘
```

### 全屏顶栏

| 元素 | 说明 |
|------|------|
| 标题 | 「手动标注」 |
| 原图底图 | 复用 `showUnderlay` checkbox |
| 保存 | 退出全屏，保留改动，markDirty |
| 取消 | 恢复快照并退出（有改动时 confirm） |

### 浮动工具（精简）

- 房间类型选择
- 「+ 新增房间」（进入放置模式，顶栏可显示放置提示条）
- 选中房间：名称编辑、删除（至少保留 1 室）
- 不展示：房间完整列表、比例尺、确认进设计、左栏墙线/门洞工具

### 画布能力（与三栏一致）

- 顶点拖拽、边线拖动
- 右键菜单新增房间
- 放置模式 banner + Esc 取消

## 状态与快照

| 状态 | 说明 |
|------|------|
| `fullscreenOpen` | 是否显示 overlay |
| `fullscreenSnapshot` | 进入时 `structuredClone(floorplan)`，取消时恢复 |
| `fullscreenDirty` | 可选：进入后是否有编辑（或通过 deepEqual 与 snapshot 比较） |

**取消确认文案：**「放弃全屏内的修改？」

**进入限制：**

- `floorplan` 已加载
- 非 `loading` / 非 `saving`
- 若 `editorMode === 'scale'`：提示先完成或退出比例尺，或自动切回 select（推荐：自动切 select 并取消 scale 选点）

## 与 dirty / 路由拦截

- 全屏「保存」退出 → 调用现有 `markDirty()`，父级 `v-model:dirty` 为 true
- 全屏「取消」且恢复快照 → 若进入前未 dirty 且恢复后与进入前一致，不应误标 dirty
- overlay 打开期间不触发 `useUnsavedGuard` 路由拦截（仍在同一路由）；Esc/取消仅在 overlay 内处理

## 样式要点

- `position: fixed; inset: 0; z-index: 2000`（高于 header / step bar）
- 背景 `#1a1917`，画布区 flex 撑满
- 浮动面板：右下或右侧，`max-width: 240px`，与现有 `editor-inspector` 视觉一致
- 打开全屏时 `document.body overflow: hidden`

## 测试要点

- 进入全屏后画布可视高度 > 三栏模式下 `.floor-canvas` 高度（可测 CSS 或 snapshot）
- 全屏内改顶点 → 保存退出 → 三栏页数据一致 → 主保存 API 被调用
- 全屏内改动 → 取消确认 → 数据与进入前 snapshot 一致
- 全屏内右键新增、边线拖动可用
- Esc 与取消行为一致
- 全屏打开时步骤条/header 被遮挡不可误点（pointer-events 在 overlay 内）

## 文件影响（预估）

| 文件 | 变更 |
|------|------|
| `web/src/components/FloorPlanEditor/index.vue` | overlay UI、快照、进入/退出逻辑 |
| `web/src/components/FloorPlanEditor/useCanvas.ts` | 可选：`restoreFloorplan()` / 快照辅助 |
| `web/src/components/FloorPlanEditor/__tests__/...` | 全屏开关与 cancel 恢复快照 |

无需后端改动。
