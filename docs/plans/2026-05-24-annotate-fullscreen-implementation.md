# 标注页全屏手动标注 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在标注页画布工具栏增加「全屏标注」，以 fixed overlay 提供全屏可编辑画布 + 精简浮动工具；全屏保存仅保留内存并 markDirty，取消恢复快照。

**Architecture:** 在 `FloorPlanEditor/index.vue` 增加 `fullscreenOpen` 与 `fullscreenSnapshot`；进入时 clone floorplan，overlay 内复用同一 `useCanvas` 实例与 `FloorPlanSvg`；不新增路由与 API。全屏顶栏提供保存/取消与原图开关；浮动面板抽取右栏「手动标注」核心表单项。

**Tech Stack:** Vue 3 + TypeScript、Vitest、现有 FloorPlanEditor / useCanvas / FloorPlanSvg

**Design doc:** `docs/plans/2026-05-24-annotate-fullscreen-design.md`

---

### Task 1: 快照与恢复辅助

**Files:**
- Modify: `web/src/components/FloorPlanEditor/useCanvas.ts`
- Create: `web/src/components/FloorPlanEditor/__tests__/fullscreenSnapshot.spec.ts`

**Step 1:** 写测试 `cloneFloorplanSnapshot` / `restoreFloorplanSnapshot` 往返一致

**Step 2:** 在 `useCanvas` 导出：

```typescript
function snapshotFloorplan(): FloorPlanData | null {
  return floorplan.value ? structuredClone(floorplan.value) : null
}

function restoreFloorplanSnapshot(data: FloorPlanData) {
  floorplan.value = structuredClone(data)
  selectedRoomId.value = data.rooms[0]?.id ?? null
  cancelPlacement()
  resetScalePoints()
  editorMode.value = 'select'
}
```

**Step 3:** 测试 PASS

**Step 4:** Commit `feat(editor): add floorplan snapshot restore helpers`

---

### Task 2: 全屏状态与进入/退出逻辑

**Files:**
- Modify: `web/src/components/FloorPlanEditor/index.vue`

**Step 1:** 增加 refs：

```typescript
const fullscreenOpen = ref(false)
const fullscreenSnapshot = ref<FloorPlanData | null>(null)

function hasFullscreenChanges() {
  if (!fullscreenSnapshot.value || !floorplan.value) return false
  return JSON.stringify(fullscreenSnapshot.value) !== JSON.stringify(floorplan.value)
}

function enterFullscreen() {
  if (!floorplan.value || loading.value) return
  setEditorMode('select')
  cancelPlacement()
  fullscreenSnapshot.value = snapshotFloorplan()
  fullscreenOpen.value = true
  document.body.style.overflow = 'hidden'
}

function exitFullscreenSave() {
  markDirty() // 或 isDirty 已由编辑触发
  closeFullscreen()
}

function exitFullscreenCancel() {
  if (hasFullscreenChanges() && !window.confirm('放弃全屏内的修改？')) return
  if (fullscreenSnapshot.value) restoreFloorplanSnapshot(fullscreenSnapshot.value)
  closeFullscreen()
}

function closeFullscreen() {
  fullscreenOpen.value = false
  fullscreenSnapshot.value = null
  document.body.style.overflow = ''
}
```

**Step 2:** `onUnmounted` 清理 body overflow

**Step 3:** 画布工具栏增加按钮：

```html
<button type="button" class="btn sm ghost" :disabled="loading || !floorplan" @click="enterFullscreen">
  全屏标注
</button>
```

**Step 4:** Commit `feat(editor): add fullscreen annotate mode state`

---

### Task 3: 全屏 overlay UI（方案 C）

**Files:**
- Modify: `web/src/components/FloorPlanEditor/index.vue`（template + scoped styles）

**Step 1:** 在根 template 末尾增加 `Teleport to="body"` 或同级 fixed 层：

```html
<div v-if="fullscreenOpen && floorplan" class="annotate-fullscreen" role="dialog" aria-modal="true">
  <header class="annotate-fullscreen-head">...</header>
  <div class="annotate-fullscreen-body">
    <FloorPlanSvg editable ... /> <!-- 与主画布相同 props/events -->
    <aside class="annotate-fullscreen-tools">...</aside>
  </div>
</div>
```

**Step 2:** 顶栏：标题、原图 checkbox、保存（`exitFullscreenSave`）、取消（`exitFullscreenCancel`）

**Step 3:** 浮动工具：复用 `pendingRoomType`、`startPlacement`、`deleteSelectedRoom`、`updateRoomName` 等；不渲染 confirm 按钮

**Step 4:** 样式：`inset:0; z-index:2000`；body 内 canvas flex:1；tools 宽 220px 贴右

**Step 5:** 手动验证：1080p 下画布明显变大

**Step 6:** Commit `feat(editor): fullscreen annotate overlay UI`

---

### Task 4: 键盘与互斥

**Files:**
- Modify: `web/src/components/FloorPlanEditor/index.vue`

**Step 1:** 全屏打开时监听 `keydown`：Esc → `exitFullscreenCancel`；放置模式 Esc 仍优先 cancelPlacement

**Step 2:** 全屏内禁用 openPreview 背景点击（或保留只读大图，二选一 — 推荐全屏内禁用大图弹窗避免 z-index 冲突）

**Step 3:** Commit `feat(editor): fullscreen esc and interaction guards`

---

### Task 5: 单元测试

**Files:**
- Create/Modify: `web/src/components/FloorPlanEditor/__tests__/fullscreenSnapshot.spec.ts`
- Optional: 组件测试 mount `FloorPlanEditor` mock api

**Cases:**

1. `restoreFloorplanSnapshot` 恢复 rooms 数量与 polygon
2. `hasFullscreenChanges` 改顶点后为 true
3. （可选）enter → 改 → cancel restore 后 JSON 与 snapshot 一致

Run: `cd web && npm test -- --run src/components/FloorPlanEditor/__tests__/fullscreenSnapshot.spec.ts`

**Commit:** `test(editor): fullscreen snapshot and restore`

---

### Task 6: E2E smoke（可选）

**Files:**
- Modify: `web/e2e/full-flow.spec.ts`

**Step 1:** 在标注页断言「全屏标注」按钮可见

**Step 2:** 点击后断言 overlay 标题「手动标注」可见

**Commit:** `test(e2e): annotate fullscreen entry smoke`

---

### Task 7: 文档同步

**Files:**
- Modify: `docs/11-流程重构需求.md` §4.3 增加 FR-A13 全屏标注模式一句

**Commit:** `docs: annotate fullscreen mode`

---

## 验证清单

```bash
cd web && npm test -- --run
cd web && npm run test:e2e   # 若 Task 6 完成
```

- [ ] 三栏页「全屏标注」可进入
- [ ] 全屏保存退出后主「保存」可 PUT annotation
- [ ] 全屏取消确认后数据回滚
- [ ] 全屏内右键新增、边线拖动正常
- [ ] 确认进设计仍在三栏右栏，全屏内不可见
