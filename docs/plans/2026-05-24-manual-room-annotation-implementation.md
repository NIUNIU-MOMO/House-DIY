# 手动标注房间 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在校对页支持手动新增/删除房间：选类型 → 画布单击定中心 → 默认矩形 → 顶点微调 → 保存后重算质检。

**Architecture:** 前端纯功能，不改动后端 schema/API。新增 `roomTypes` 常量与 `useManualRoom`  composable，由右侧面板驱动 `placementMode`；`FloorPlanSvg` 在放置模式下 emit 点击坐标；保存仍走 `PUT /floorplan` 与 `prepare_floorplan_for_save`。

**Tech Stack:** Vue 3 + TypeScript、Vitest、现有 FloorPlanEditor / SVG 编辑栈

**Design doc:** `docs/plans/2026-05-24-manual-room-annotation-design.md`

---

### Task 1: 房间类型常量与纯函数

**Files:**
- Create: `web/src/constants/roomTypes.ts`
- Create: `web/src/constants/__tests__/roomTypes.spec.ts`

**Step 1: Write the failing tests**

```typescript
import { describe, expect, it } from 'vitest'
import {
  ROOM_TYPE_OPTIONS,
  buildRoomName,
  defaultPolygonAt,
  nextRoomId,
} from '@/constants/roomTypes'
import type { FloorRoom } from '@/types/floorplan'

describe('nextRoomId', () => {
  it('increments from existing r ids', () => {
    const rooms: FloorRoom[] = [
      { id: 'r1', name: '客厅', polygon: [] },
      { id: 'r4', name: '卧室A', polygon: [] },
    ]
    expect(nextRoomId(rooms)).toBe('r5')
  })
})

describe('buildRoomName', () => {
  it('assigns bedroom letter suffix', () => {
    const rooms: FloorRoom[] = [{ id: 'r1', name: '卧室A', polygon: [] }]
    expect(buildRoomName('bedroom', rooms)).toBe('卧室B')
  })

  it('assigns numeric suffix for kitchen', () => {
    const rooms: FloorRoom[] = [{ id: 'r1', name: '厨房', polygon: [] }]
    expect(buildRoomName('kitchen', rooms)).toBe('厨房2')
  })
})

describe('defaultPolygonAt', () => {
  it('creates axis-aligned rect clamped to source bounds', () => {
    const poly = defaultPolygonAt({ x: 10, y: 10 }, 800, 600)
    expect(poly).toHaveLength(4)
    expect(poly.every((p) => p.x >= 0 && p.y >= 0)).toBe(true)
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npm run test -- src/constants/__tests__/roomTypes.spec.ts`
Expected: FAIL — module not found

**Step 3: Implement `roomTypes.ts`**

- Export `RoomTypeKey` union + `ROOM_TYPE_GROUPS`（含 design 文档全部类型）
- `buildRoomName(key, existingRooms): string`
- `defaultPolygonAt(center, sourceW, sourceH): FloorPoint[]`
- `nextRoomId(rooms): string`
- `computeRoomArea(polygon, scale): number | null`（可选 helper）

**Step 4: Run tests**

Run: `cd web && npm run test -- src/constants/__tests__/roomTypes.spec.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/constants/roomTypes.ts web/src/constants/__tests__/roomTypes.spec.ts
git commit -m "feat(web): add room type catalog and naming helpers for manual annotation"
```

---

### Task 2: useManualRoom composable

**Files:**
- Create: `web/src/components/FloorPlanEditor/useManualRoom.ts`
- Create: `web/src/components/FloorPlanEditor/__tests__/useManualRoom.spec.ts`

**Step 1: Write failing tests**

```typescript
import { describe, expect, it } from 'vitest'
import { ref } from 'vue'
import { useManualRoom } from '../useManualRoom'
import type { FloorPlanData } from '@/types/floorplan'

const basePlan = (): FloorPlanData => ({
  scale: 100,
  status: 'draft',
  walls: [],
  rooms: [{ id: 'r1', name: '客厅', polygon: [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }] }],
  openings: [],
  source_width: 800,
  source_height: 600,
})

describe('useManualRoom', () => {
  it('addRoomAt appends room and returns id', () => {
    const floorplan = ref(basePlan())
    const { addRoomAt } = useManualRoom(floorplan)
    const id = addRoomAt('bedroom', { x: 200, y: 200 })
    expect(floorplan.value.rooms).toHaveLength(2)
    expect(floorplan.value.rooms[1]?.id).toBe(id)
    expect(floorplan.value.rooms[1]?.name).toMatch(/卧室/)
  })

  it('removeRoom blocks deleting last room', () => {
    const floorplan = ref(basePlan())
    const { removeRoom } = useManualRoom(floorplan)
    expect(removeRoom('r1')).toBe(false)
    expect(floorplan.value.rooms).toHaveLength(1)
  })
})
```

**Step 2: Run — expect FAIL**

**Step 3: Implement**

- `addRoomAt(typeKey, center): string | null`
- `removeRoom(roomId): boolean`（rooms.length <= 1 返回 false）
- 内部调用 `roomTypes` helpers

**Step 4: Run — expect PASS**

**Step 5: Commit**

```bash
git add web/src/components/FloorPlanEditor/useManualRoom.ts web/src/components/FloorPlanEditor/__tests__/useManualRoom.spec.ts
git commit -m "feat(web): add useManualRoom for add/delete room operations"
```

---

### Task 3: placementMode 接入 useCanvas

**Files:**
- Modify: `web/src/components/FloorPlanEditor/useCanvas.ts`
- Modify: `web/src/components/FloorPlanEditor/__tests__/useCanvas.spec.ts`（若不存在则创建最小测试）

**Step 1: Write failing test**

```typescript
it('startPlacement sets pending type and placeAt creates room', () => {
  const { placementMode, startPlacement, cancelPlacement, placeAt, floorplan } = useFloorPlanCanvas(ref(1))
  // mock load floorplan...
  startPlacement('bedroom')
  expect(placementMode.value.active).toBe(true)
  placeAt({ x: 100, y: 100 })
  expect(placementMode.value.active).toBe(false)
  expect(floorplan.value?.rooms.length).toBeGreaterThan(1)
})
```

**Step 2–4: Implement & verify**

- `placementMode: { active, typeKey } | null`
- `startPlacement(typeKey)` / `cancelPlacement()` / `placeAt(point)`
- 集成 `useManualRoom`
- `deleteSelectedRoom()` 包装 removeRoom + 重选 selectedRoomId
- Esc 由 index.vue 监听（或 composable 暴露 cancelPlacement）

**Step 5: Commit**

```bash
git commit -m "feat(web): wire manual room placement into floor plan canvas state"
```

---

### Task 4: FloorPlanSvg 放置点击

**Files:**
- Modify: `web/src/components/FloorPlanEditor/FloorPlanSvg.vue`

**Step 1: Add prop `placementActive?: boolean`**

**Step 2: Update `onSvgClick`**

```typescript
if (props.placementActive) {
  emit('canvasClick', svgPointFromEvent(event, svgRef.value))
  return
}
```

**Step 3: 放置模式 CSS** — `cursor: crosshair` on `.floor-svg.placement-active`

**Step 4: Manual smoke** — 校对页进入放置模式，单击应 emit（可用现有 HomeView/editor spec 扩展）

**Step 5: Commit**

```bash
git commit -m "feat(web): support placement click on floor plan SVG"
```

---

### Task 5: 右侧面板 UI

**Files:**
- Modify: `web/src/components/FloorPlanEditor/index.vue`

**Step 1: inspector 区域增加**

- `<select>` 或分组列表绑定 `pendingRoomType`
- 按钮「+ 新增房间」→ `startPlacement(pendingRoomType)`
- 放置模式提示条 + 「取消」
- 「删除房间」按钮（`:disabled="!selectedRoom || rooms.length <= 1"`）+ confirm

**Step 2: 绑定 FloorPlanSvg**

```vue
:placement-active="placementMode?.active"
@canvas-click="onCanvasClick"
```

`onCanvasClick`: placement 时 `placeAt`；scale 时 `addScalePoint`

**Step 3: 放置模式中**

- `:locked` 类禁用保存/确认/大图（或 disable 按钮）
- `ProjectStepBar` 无需改（校对页无 step bar）

**Step 4: 样式** — 与现有 editor-inspector 一致

**Step 5: Commit**

```bash
git commit -m "feat(web): add manual room add/delete UI on floor plan editor"
```

---

### Task 6: 回归测试

**Files:**
- Modify: `web/src/components/FloorPlanEditor/__tests__/useManualRoom.spec.ts`（补 edge cases）
- Optional: `web/e2e/full-flow.spec.ts` — 校对页新增房间 + 保存

**Step 1: Run full web unit tests**

Run: `cd web && npm run test`
Expected: PASS

**Step 2: Run server tests（无后端改动，应仍 PASS）**

Run: `cd server && pytest -q`
Expected: PASS

**Step 3: Commit if e2e added**

```bash
git commit -m "test(web): cover manual room annotation flows"
```

---

## 验收清单

- [ ] 右侧可选类型并进入放置模式
- [ ] 画布单击后出现矩形并选中新房间
- [ ] 可拖拽顶点、改名称、保存
- [ ] 保存后 validation banner 更新
- [ ] 可删除房间，最后一个不可删
- [ ] 放置模式可 Esc/取消退出
- [ ] 单元测试通过
