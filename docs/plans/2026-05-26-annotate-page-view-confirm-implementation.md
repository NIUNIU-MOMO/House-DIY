# 标注页查看确认 + 全屏编辑 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 主标注页只读查看与右侧质检确认；全屏承担全部编辑与比例尺标定。

**Architecture:** `index.vue` 拆分主/全屏模板；`FloorPlanSvg` 只读下保留选房与背景点击；E2E 迁至全屏。

**Tech Stack:** Vue 3, `FloorPlanEditor`, Playwright, Vitest

---

### Task 1: FloorPlanSvg 只读选房

**Files:** `FloorPlanSvg.vue`

- `onRoomClick`：`!editable` 时仍 `emit('roomSelect')`
- `onSvgClick`：`!editable` 时 `emit('backgroundClick')`
- `room-hit` 类在只读选房时启用

### Task 2: 主页面布局

**Files:** `index.vue`

- 移除顶栏 `validation-banner`
- 左侧去掉比例尺与占位工具
- 主画布 `editable=false`；`contextMenu` 仅全屏
- 右侧 `inspector-validation` + 底部确认

### Task 3: 全屏右侧三块

**Files:** `index.vue`

- 上：房间标注（testid 保留）
- 中：比例尺 + `beginScaleMode`
- 下：选中房间（名称/面积/重画/删除）
- 全屏 SVG `:editor-mode="editorMode"`

### Task 4: E2E

**Files:** `full-flow.spec.ts`

- 04d/04e 先打开全屏
- 04 断言主页面无 add-room-btn
- 04c 断言全屏含 scale-distance-input 或 tool-scale

### Task 5: 自测

- `npm run test:unit`（web）
- `npx playwright test full-flow -g "04"`
