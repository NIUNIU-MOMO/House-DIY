# 流程重构 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 House-DIY 主流程重构为「上传 → 解析 → 标注 → 设计 → 预览」，落实 max_step、多方案、标注保存/确认分离、output_root 配置与 stale 标记。

**Architecture:** 后端 Project 表扩展 `max_step`/`active_scheme_id`；floorplan 保存/confirm 拆 API；设计产物迁入 `{output_root}/{id}/schemes/{sid}/`；前端 `projectNavigation` 与 `ProjectStepBar` 统一五步与黄/绿/灰；标注 dirty 双层 Modal；`server/settings.local.json` 运行时覆盖 config。

**Tech Stack:** FastAPI, SQLAlchemy, Vue 3, Pinia, Vitest, pytest

**设计文档：** [2026-05-26-workflow-refactor-design.md](./2026-05-26-workflow-refactor-design.md)

---

## Task 1: Project max_step 字段与迁移

**Files:**
- Modify: `server/app/models/project.py`
- Create: `server/alembic/versions/xxxx_add_max_step.py`（若项目用 alembic；否则 SQLite 启动迁移脚本）
- Modify: `server/app/schemas/project.py`
- Test: `server/tests/test_projects.py`

**Step 1:** 写失败测试 `test_project_has_max_step_default_upload`

**Step 2:** 运行 `pytest server/tests/test_projects.py -v` → FAIL

**Step 3:** 添加 `max_step` Enum 列，默认 `upload`；API 返回字段

**Step 4:** 测试 PASS

**Step 5:** Commit `feat(project): add max_step field`

---

## Task 2: max_step 推进服务

**Files:**
- Create: `server/app/services/project_progress.py`
- Modify: `server/app/api/floorplan.py`（上传、保存标注、confirm）
- Modify: `server/app/services/floorplan/task_parse.py`（解析完成不自动抬 design）
- Test: `server/tests/test_project_progress.py`

**规则实现：**
- 上传成功 → `max(parse, upload)`
- PUT annotation 首次/每次 → `max(annotate, annotate)`
- POST confirm → 仅 confirmed，不改 design
- PUT scheme save → `max(design, design)`
- 3D task done → `max(preview, preview)`

**Step 1–5:** TDD 各规则单测 + 实现 + commit

---

## Task 3: floorplan 保存/确认 API 拆分

**Files:**
- Modify: `server/app/api/floorplan.py`
- Modify: `server/app/services/floorplan/floorplan_service.py`
- Test: `server/tests/test_floorplan_api.py`

**Endpoints:**
- `PUT .../floorplan/annotation` — 保存 draft/快照，触发 max_step annotate
- `POST .../floorplan/confirm` — validation_blocks_confirm + confirmed

**Step 1–5:** 测试 confirm 需无 error；annotation 可带 warning + commit

---

## Task 4: stale 标记

**Files:**
- Modify: `server/app/services/floorplan/storage.py`（meta.json 字段）
- Modify: `server/app/services/floorplan/task_parse.py`（解析完成设 annotation_stale）
- Create: `server/app/services/stale_guard.py`
- Test: `server/tests/test_stale_guard.py`

**行为：** 重新解析 → `annotation_stale=true`；confirm 后清 stale；scheme 标 stale；设计 generate 前检查

---

## Task 5: settings.local.json + output_root

**Files:**
- Create: `server/app/services/settings_storage.py`
- Modify: `server/app/core/config.py`（运行时 reload output_root）
- Modify: `server/app/services/floorplan/storage.py`（get_projects_root 读 config）
- Modify: `server/.env.example`
- Modify: `.gitignore`（`server/settings.local.json`）
- Create: `server/app/api/settings.py`
- Test: `server/tests/test_settings_storage.py`

**Step 1–5:** GET/PUT `/api/v1/settings/storage` + 可写检测 + commit

---

## Task 6: schemes 存储与 CRUD

**Files:**
- Create: `server/app/services/design/scheme_storage.py`
- Create: `server/app/api/schemes.py`
- Modify: `server/app/services/design/storage.py`（委托到 scheme 路径）
- Test: `server/tests/test_scheme_storage.py`

**规则：** 自动创建 scheme A；上限 10；DELETE 仅用户；禁止自动删

---

## Task 7: scheme 生成/保存/3D/refine 路由

**Files:**
- Modify: `server/app/api/design.py`
- Modify: `server/app/services/design/task_generate.py`
- Modify: `server/app/services/orchestrator.py`
- Test: `server/tests/test_design_api.py`

**行为：** generate-2d / save scheme / generate-3d / refine 按 design.md §3.3 更新 max_step 与 scheme meta.status

---

## Task 8: 前端 projectNavigation 重构

**Files:**
- Modify: `web/src/utils/projectNavigation.ts`
- Modify: `web/src/api/client.ts`（Project.max_step, schemes API）
- Test: `web/src/stores/__tests__/app.spec.ts` 或新建 `projectNavigation.spec.ts`

**变更：** `review`→`annotate`；`resolveProjectEntry` 用 API max_step；reachable 步骤计算含 confirmed 解锁 design

---

## Task 9: ProjectStepBar 黄/绿/灰 + locked

**Files:**
- Modify: `web/src/components/ProjectStepBar.vue`
- Test: 组件 snapshot 或 e2e 断言 class

**颜色：** active 黄；done 绿；pending 灰 disabled

---

## Task 10: 未保存拦截 composable

**Files:**
- Create: `web/src/composables/useUnsavedGuard.ts`
- Modify: `web/src/views/FloorPlanEditorView.vue`
- Modify: `web/src/views/DesignStudioView.vue`
- Test: `web/src/composables/__tests__/useUnsavedGuard.spec.ts`

**双层 Modal：** 放弃 → 二次确认

---

## Task 11: 标注页保存/确认拆分

**Files:**
- Modify: `web/src/components/FloorPlanEditor/index.vue`
- Modify: `web/src/components/FloorPlanEditor/useCanvas.ts`
- Test: `web/src/components/FloorPlanEditor/__tests__/...`

**UI：** 工具栏「保存」调 annotation API；底部「确认并进入设计」调 confirm API；error 时 confirm disabled

---

## Task 12: 右键新增房间 + 边线拖动

**Files:**
- Modify: `web/src/components/FloorPlanEditor/FloorPlanSvg.vue`
- Modify: `web/src/components/FloorPlanEditor/useManualRoom.ts`
- Create/Modify: 边线 hit-test 逻辑
- Test: `useManualRoom.spec.ts` 扩展

---

## Task 13: 上传页收简

**Files:**
- Modify: `web/src/views/FloorPlanUploadView.vue`

**保留字段，收简布局，按钮文案对齐设计 §4.1**

---

## Task 14: 设计页多方案 UI

**Files:**
- Modify: `web/src/views/DesignStudioView.vue`
- Create: `web/src/components/SchemeList.vue`
- Modify: `web/src/views/DesignGenerateView.vue`（2D 进度）
- Test: 方案切换 e2e

**流程：** 方案列表 + 生成2D + 保存方案 + 生成3D + 房间微调

---

## Task 15: 预览页只读平铺

**Files:**
- Modify: `web/src/views/DeliveryOverviewView.vue`

**方案下拉 + render-grid + 3D 按钮；移除编辑入口**

---

## Task 16: Settings 输出目录

**Files:**
- Modify: `web/src/views/SettingsView.vue`
- Modify: `web/src/stores/app.ts`

**展示路径、可写状态、保存调用 settings API**

---

## Task 17: E2E 回归

**Files:**
- Modify: `web/e2e/full-flow.spec.ts`

**覆盖：** 上传→解析→标注保存→确认→设计保存方案→预览

---

## Task 18: 文档同步

**Files:**
- Modify: `docs/11-流程重构需求.md`（v1.1 已决）
- Modify: `docs/原型/v2/`（标注按钮文案）

---

## 执行顺序建议

```
M1: Task 8, 9, 13
M2: Task 3, 10, 11, 12
M3: Task 1, 2, 4, 8
M4: Task 6, 7, 14, 15
M5: Task 5, 16
收尾: Task 17, 18
```

**旧数据：** 不实现迁移；README/文档注明优化后手动清空 `data/` 或旧 output 目录。
