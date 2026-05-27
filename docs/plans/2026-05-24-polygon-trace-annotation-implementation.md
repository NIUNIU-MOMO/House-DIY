# 异形房间多边形标注 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在标注页实现「调整 + 描边」双模式与墙线/角点智能吸附，支持修正 AI 轮廓与沿墙手动画异形房间。

**Architecture:** 扩展 `geometry.ts` 提供统一 `snapAnnotationPoint` 与 `isSimplePolygon`；新增 `usePolygonEdit` / `useTraceMode` composable；`FloorPlanSvg` 渲染 trace 折线与边双击插点；`index.vue` 扩展入口与 banner。Schema 不变，保存仍走现有 `PUT /floorplan`。

**Tech Stack:** Vue 3, TypeScript, Vitest, Playwright, 现有 `parser_validate.py`

**Design doc:** `docs/plans/2026-05-24-polygon-trace-annotation-design.md`

---

### Task 1: 几何工具 — 角点集与增强吸附

**Files:**
- Modify: `web/src/utils/geometry.ts`
- Test: `web/src/utils/geometry.test.ts`

**Step 1:** 写失败单测

- `collectWallCorners` 返回端点 + 两墙段交点
- `snapAnnotationPoint` 在 corner 10px 内优先于 segment 12px
- 无 walls 时返回原点

**Step 2:** 运行 `cd web && npm test -- --run src/utils/geometry.test.ts` → FAIL

**Step 3:** 实现 `segmentIntersection`、`collectWallCorners`、`snapAnnotationPoint`

**Step 4:** 测试 PASS

**Step 5:** Commit `feat(web): add wall corner snap for annotation`

---

### Task 2: 简单多边形本地预检

**Files:**
- Modify: `web/src/utils/geometry.ts`
- Test: `web/src/utils/geometry.test.ts`

**Step 1:** 单测 `isSimplePolygon` — 矩形 true、8 字 false

**Step 2:** 实现（线段相交检测，不含相邻边共享顶点）

**Step 3:** PASS → Commit `feat(web): add isSimplePolygon helper`

---

### Task 3: usePolygonEdit — 插点 / 删点

**Files:**
- Create: `web/src/components/FloorPlanEditor/usePolygonEdit.ts`
- Test: `web/src/components/FloorPlanEditor/__tests__/usePolygonEdit.spec.ts`

**Step 1:** 单测

- `insertVertexOnEdge(room, edgeIndex, walls)` 在指定边插入 snap 后点
- `removeVertex(room, vertexIndex)` 少于 3 点返回 false
- 操作后 `computeRoomArea` 被调用（mock floorplan ref）

**Step 2:** 实现 composable，导出纯函数或 ref 包装

**Step 3:** PASS → Commit `feat(web): polygon insert/remove vertex helpers`

---

### Task 4: useTraceMode — 描边状态机

**Files:**
- Create: `web/src/components/FloorPlanEditor/useTraceMode.ts`
- Test: `web/src/components/FloorPlanEditor/__tests__/useTraceMode.spec.ts`

**Step 1:** 单测

- `startTrace(typeKey)` → points=[]
- `addPoint` ×3 → `canClose` true
- `closeTrace` 自交叉 → false
- `undoPoint` 移除最后一点
- `cancelTrace` 清空

**Step 2:** 实现；闭合时调用 `isSimplePolygon` + `snapAnnotationPoint`

**Step 3:** PASS → Commit `feat(web): trace mode state composable`

---

### Task 5: useCanvas 接入 subMode

**Files:**
- Modify: `web/src/components/FloorPlanEditor/useCanvas.ts`

**Step 1:** 增加 `annotationSubMode: ref<'adjust'|'trace'|'place-rect'>`

**Step 2:** 导出 `insertVertexOnEdge`, `removeVertex`, trace API；`updateRoomVertex` 改用 `snapAnnotationPoint`

**Step 3:** `markDirty` 在插删点 / trace 闭合时触发

**Step 4:** 运行 `npm test -- --run src/components/FloorPlanEditor` → PASS

**Step 5:** Commit `feat(web): wire polygon edit and trace into useCanvas`

---

### Task 6: FloorPlanSvg — 调整模式 UI

**Files:**
- Modify: `web/src/components/FloorPlanEditor/FloorPlanSvg.vue`

**Step 1:** 边 handle `@dblclick` → emit `edgeInsertVertex`

**Step 2:** 顶点 handle 支持选中态；emit `vertexDelete` on contextmenu 或父组件键盘 Delete

**Step 3:** 拖拽顶点/边 move 使用父级传入的 snapped point

**Step 4:** 手动验证：双击边出现第 5 个 handle

**Step 5:** Commit `feat(web): svg edge double-click insert vertex`

---

### Task 7: FloorPlanSvg — 描边渲染与 snap 预览

**Files:**
- Modify: `web/src/components/FloorPlanEditor/FloorPlanSvg.vue`

**Step 1:** props: `tracePoints`, `snapPreview`, `cornerSnapEnabled`

**Step 2:** 渲染 trace 折线 + 序号点 + 首点闭合高亮圈

**Step 3:** 渲染 snap-preview 圆（corner 绿 / segment 灰）

**Step 4:** trace 激活时 canvas click → emit `traceClick`（非 room select）

**Step 5:** Commit `feat(web): svg trace overlay and snap preview`

---

### Task 8: index.vue — 入口与 banner

**Files:**
- Modify: `web/src/components/FloorPlanEditor/index.vue`

**Step 1:** 右侧面板「+ 沿墙描边」按钮；右键菜单增加「沿墙描边」分组

**Step 2:** trace banner + 角点吸附 checkbox + Esc/Enter 键盘

**Step 3:** 选中房间「重画轮廓」按钮（可选 P1）

**Step 4:** 全屏 overlay 同步 props/events

**Step 5:** Commit `feat(web): trace mode UI entry and banner`

---

### Task 9: 文档与需求

**Files:**
- Modify: `docs/11-流程重构需求.md` — 增加 FR-A14～A17
- Modify: `docs/plans/2026-05-24-polygon-trace-annotation-design.md` — 状态改为「已实现」时更新

**Step 1:** 追加需求表 §4.3.4

**Step 2:** Commit `docs: add FR-A14-A17 polygon trace annotation`

---

### Task 10: E2E

**Files:**
- Modify: `web/e2e/full-flow.spec.ts`
- Modify: `web/e2e/fixtures.ts`（如需带 walls 的 mock）

**Step 1:** 测试 `04d 标注 — 沿墙描边新增房间`：mock 墙线 → 3 次 click → Enter → 断言 rooms.length+1

**Step 2:** 测试 `04e 标注 — 双击边插入顶点`：选中 room → dblclick edge handle → 断言 polygon 长度 +1

**Step 3:** `npm run test:e2e -g "04d|04e"` PASS

**Step 4:** Commit `test(e2e): polygon trace and insert vertex`

---

## 验收清单

- [ ] L 型 / 斜墙房间可通过插点贴墙
- [ ] 漏识别房间可 trace 闭合新增
- [ ] 角点吸附在 mock 墙线下生效，Shift+点击可跳过
- [ ] 自交叉 trace 无法闭合
- [ ] 全屏手动标注内 adjust/trace 均可用
- [ ] 保存后服务端 validation 正常
- [ ] Vitest + 新 E2E 通过
