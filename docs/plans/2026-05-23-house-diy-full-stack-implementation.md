# House-DIY 全栈 MVP 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 `docs/原型` 13 屏交互流程落地为 Vue 3 + FastAPI 本地离线应用：上传户型 → 2D 校对 → RAG + DesignSpec → ComfyUI 2D + 程序化 3D → Obsidian 沉淀，并支持方案微调。

**Architecture:** 浏览器 Vue SPA 通过 REST/WebSocket 调用 FastAPI 编排层；编排层串行调度 oMLX（LLM/VLM/Embed）与 ComfyUI；FloorPlan/SceneBuilder/Knowledge 为独立 service；SQLite 存元数据，Vault + Chroma 存知识与向量。GPU 重任务经 `scheduler.py` 全局单槽队列。

**Tech Stack:** Vue 3 + TypeScript + Vite + Pinia + Vue Router + Element Plus + Fabric.js + Three.js · Python 3.12 + FastAPI + SQLAlchemy + SQLite + httpx + openai SDK + ChromaDB + OpenCV + Shapely + trimesh · oMLX（alias: house-llm/vlm/embed）· ComfyUI（`workflows/flux_interior_t2i_api.json`）

---

## 0. 现状与原型映射

### 0.1 本机已就绪（无需重复实现）

| 组件 | 状态 | 参考 |
|------|------|------|
| oMLX + alias + 内存 | ✅ | `docs/04`、`docs/05` §8 |
| ComfyUI + FLUX workflow | ✅ | `workflows/flux_interior_t2i_api.json` |
| Obsidian Vault 目录 | ✅ | `~/House-DIY-Vault` |
| 交互原型（UX 验收基准） | ✅ | `docs/原型/` |

### 0.2 待创建目录（对齐 `docs/02` §10）

```
House-DIY/
├── server/          # FastAPI
├── web/             # Vue 3
├── vault-templates/
├── assets/furniture/
├── scripts/
└── workflows/       # 已有
```

### 0.3 原型 13 屏 → Vue 路由 → API

| 原型 ID | 页面 | Vue 路由 | 主要 API |
|---------|------|----------|----------|
| 01 | 项目列表 | `/` | `GET/POST/DELETE /projects` |
| 02 | 上传户型 | `/projects/:id/upload` | `POST /projects/{id}/floorplan` |
| 03 | AI 解析中 | `/projects/:id/parse` | `GET /tasks/{taskId}` + WS |
| 04 | 2D 校对 | `/projects/:id/editor` | `GET/PUT /floorplan` |
| 05 | 设计描述 + RAG | `/projects/:id/studio` | `GET /knowledge/search` |
| 06 | 生成进度 | `/projects/:id/generate` | WS + `GET /tasks/{id}` |
| 07 | 方案微调 | `/projects/:id/refine` | `POST /design/refine` + `/apply` |
| 08 | 交付总览 | `/projects/:id/delivery` | `GET /renders` + `/scene` |
| 09 | 2D 画廊 | `/projects/:id/gallery` | `GET /renders` |
| 10 | 3D 漫游 | `/projects/:id/scene` | `GET /scene` |
| 11 | 知识库 | `/knowledge` | `GET /knowledge/search` |
| 12 | 导入参考 | `/knowledge/import` | `POST /knowledge/import` |
| 13 | 系统设置 | `/settings` | `GET /health` + 配置读写 |

### 0.4 里程碑与阶段对照

| 阶段 | 周期（估） | 原型覆盖 | V1 完成定义项 |
|------|------------|----------|---------------|
| **P0** | 1–2 周 | 01、13 | 健康检查、项目 CRUD |
| **P1** | 2–3 周 | 02–04 | 上传、解析、校对 confirmed |
| **P2** | 2–3 周 | 05–06、09 | DesignSpec、单/多房间 2D、写 Cases |
| **P3** | 2–3 周 | 10（单房间） | Scene Builder + Three.js |
| **P4** | 3–4 周 | 07–08、10（全屋） | 微调、Portal、端到端 |
| **P5** | 1–2 周 | 11–12 | RAG、导入、reindex |
| **P6** | 持续 | — | 资产、脚本、文档 |

---

## P0：基础设施（Week 1–2）

### Task P0-1：初始化 server 包与 health 端点

**Files:**
- Create: `server/app/__init__.py`
- Create: `server/app/main.py`
- Create: `server/app/core/config.py`
- Create: `server/app/api/health.py`
- Create: `server/requirements.txt`
- Create: `server/.env.example`
- Create: `server/tests/test_health.py`
- Test: `server/tests/test_health.py`

**Step 1: Write the failing test**

```python
# server/tests/test_health.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_health_returns_ok_and_services():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "omlx" in body["services"]
    assert "comfyui" in body["services"]
```

**Step 2: Run test to verify it fails**

Run: `cd server && source ~/House-DIY-env/bin/activate && pip install -e ".[dev]" 2>/dev/null || pip install pytest pytest-asyncio httpx fastapi uvicorn && pytest tests/test_health.py -v`

Expected: FAIL — `app.main` or route not found

**Step 3: Write minimal implementation**

```python
# server/app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    house_diy_vault_path: str = "~/House-DIY-Vault"
    house_diy_omlx_base_url: str = "http://127.0.0.1:8000/v1"
    house_diy_omlx_api_key: str = ""
    house_diy_omlx_llm_model: str = "house-llm"
    house_diy_omlx_vlm_model: str = "house-vlm"
    house_diy_omlx_embed_model: str = "house-embed"
    house_diy_comfy_url: str = "http://127.0.0.1:8188"
    house_diy_data_dir: str = "data"

    class Config:
        env_file = ".env"
```

```python
# server/app/api/health.py — 探测 oMLX / ComfyUI / Vault 路径
@router.get("/health")
async def health():
    return {"status": "ok", "services": {"omlx": ..., "comfyui": ..., "vault": ...}}
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_health.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add server/
git commit -m "feat(server): add FastAPI shell and health endpoint"
```

---

### Task P0-2：SQLite 模型与 Project CRUD

**Files:**
- Create: `server/app/models/base.py`
- Create: `server/app/models/project.py`
- Create: `server/app/schemas/project.py`
- Create: `server/app/api/projects.py`
- Create: `server/tests/test_projects.py`
- Modify: `server/app/main.py`

**Step 1: Write the failing test**

```python
async def test_create_and_list_projects():
    async with AsyncClient(...) as client:
        create = await client.post("/api/v1/projects", json={"name": "望京三期 89㎡"})
        assert create.status_code == 201
        pid = create.json()["id"]
        listing = await client.get("/api/v1/projects")
        assert any(p["id"] == pid for p in listing.json())
```

**Step 2: Run test — Expected FAIL**

**Step 3: Implement SQLAlchemy models**

表字段最小集：`projects(id, name, status, created_at, updated_at)`；`status` 枚举：`draft|parsing|review|designing|delivered`

**Step 4: Run test — Expected PASS**

**Step 5: Commit**

```bash
git commit -m "feat(server): add project CRUD with SQLite"
```

---

### Task P0-3：初始化 Vue 3 前端壳

**Files:**
- Create: `web/` via `npm create vue@latest`（TypeScript, Router, Pinia, ESLint）
- Create: `web/src/views/HomeView.vue`（对应原型 01）
- Create: `web/src/views/SettingsView.vue`（对应原型 13）
- Create: `web/src/api/client.ts`
- Create: `web/src/stores/app.ts`（服务健康灯）
- Modify: `web/vite.config.ts`（proxy `/api` → `:8080`）

**Step 1: Write failing component test（Vitest）**

```typescript
// web/src/views/__tests__/HomeView.spec.ts
it('shows service status from health API', async () => {
  // mock GET /api/v1/health
  // mount HomeView
  // expect oMLX dot green
})
```

**Step 2: Run — Expected FAIL**

**Step 3: Implement HomeView** — 复用 `docs/原型/styles.css` 中 `:root` 色板到 `web/src/assets/theme.css`

**Step 4: Run — Expected PASS**

**Step 5: Commit**

```bash
git commit -m "feat(web): scaffold Vue app with home and settings views"
```

---

### Task P0-4：Vault 模板与 vault_io 基础

**Files:**
- Create: `vault-templates/case-template.md`
- Create: `vault-templates/reference-template.md`
- Create: `server/app/services/knowledge/vault_io.py`
- Create: `server/tests/test_vault_io.py`

**Step 1: Test `ensure_vault_dirs()` 创建 Cases/References/Templates/Assets/Specs/.house-diy/chroma**

**Step 2–4: 实现 + 通过**

**Step 5: Commit**

```bash
git commit -m "feat(knowledge): vault templates and vault_io bootstrap"
```

---

### Task P0-5：启动脚本

**Files:**
- Create: `scripts/check-deps.sh`（调用 `docs/04` 验收命令）
- Create: `scripts/start-all.sh`（oMLX 提示 / ComfyUI / uvicorn / vite）

**验收:** `./scripts/check-deps.sh` 全绿；`start-all.sh` 后访问 `http://127.0.0.1:5173` 见首页状态灯

---

## P1：户型解析与 2D 校对（Week 3–5）

### Task P1-1：oMLX 客户端封装

**Files:**
- Create: `server/app/services/omlx_client.py`
- Create: `server/tests/test_omlx_client.py`（mock httpx）
- Create: `server/tests/integration/test_omlx_live.py`（标记 `@pytest.mark.integration`）

**Step 1: 失败测试 — `embed(["测试"])` 返回 1024 维向量（mock）**

**Step 3: 实现 `chat_text`, `chat_vision`, `embed` — openai SDK + `Authorization: Bearer`**

**Step 4: 集成测试（可选 CI skip）**

Run: `pytest tests/integration/test_omlx_live.py -v -m integration`

Expected: PASS（需本机 oMLX 运行）

**Step 5: Commit**

---

### Task P1-2：FloorPlanModel schema

**Files:**
- Create: `server/app/schemas/floorplan.py`
- Create: `server/tests/test_floorplan_schema.py`

**Step 1: 测试 JSON 样例通过 Pydantic 校验（walls, rooms, openings, scale, status）**

**Step 3: 定义 `FloorPlanModel`, `Wall`, `Room`, `Opening`**

---

### Task P1-3：平面图上传 API + 前端上传页（原型 02）

**Files:**
- Create: `server/app/api/floorplan.py`
- Create: `web/src/views/FloorPlanUploadView.vue`
- Modify: `web/src/router/index.ts`

**API:** `POST /api/v1/projects/{id}/floorplan` multipart → 存 `data/projects/{id}/source.png`

**前端:** 拖拽上传、项目名称、预览条 — 对齐原型 02 布局

**E2E 验收:** 上传后 `GET /floorplan` 返回 `status=draft`

---

### Task P1-4：VLM 解析任务（原型 03）

**Files:**
- Create: `server/app/services/floorplan/parser_vlm.py`
- Create: `server/prompts/floorplan_vlm.txt`
- Create: `server/app/services/floorplan/task_parse.py`
- Create: `web/src/views/FloorPlanParseView.vue`

**Flow:**
1. 上传后创建 `task`（type=`floorplan_parse`）
2. 后台：调 `house-vlm` → 房间/门窗 JSON
3. WS 推送步骤（预处理 → VLM → CV → 草稿）
4. 完成跳转 `/projects/:id/editor`

**Step 1: 测试 parser_vlm 输出合并进 FloorPlanModel 草稿**

---

### Task P1-5：CV 墙线矢量化

**Files:**
- Create: `server/app/services/floorplan/parser_cv.py`

**Step 1: 测试标准样本图返回 ≥4 条墙线段**

**实现:** OpenCV 轮廓 + Hough；比例尺 API `POST /floorplan/scale`（两点 + 实际米数）

---

### Task P1-6：2D 校对编辑器（原型 04）

**Files:**
- Create: `web/src/components/FloorPlanEditor/index.vue`
- Create: `web/src/components/FloorPlanEditor/useCanvas.ts`
- Modify: `server/app/api/floorplan.py` — `PUT` 保存 + `status=confirmed`

**交互（对齐原型）:**
- 左侧工具栏、房间列表切换
- 中间 SVG/Canvas 墙线编辑
- 右侧 inspector 面积/连通
- 「确认户型」→ `confirmed` → 路由 `/studio`

**验收:** Playwright — 上传 → 等待解析 → 改房间名 → 确认 → DB status=confirmed

---

## P2：DesignSpec 与 2D 渲染（Week 6–8）

### Task P2-1：Scheduler 与 Task 状态机（原型 06 基础）

**Files:**
- Create: `server/app/services/scheduler.py`
- Create: `server/app/models/task.py`
- Create: `server/app/api/ws.py`
- Create: `web/src/composables/useTaskWebSocket.ts`

**规则（`docs/02` §9）:** 全局 GPU 单槽；ComfyUI 按房间串行

**Step 1: 测试状态机 `pending→running→done|failed`，失败最多重试 2 次**

---

### Task P2-2：DesignSpec schema + LLM 生成（原型 05）

**Files:**
- Create: `server/app/schemas/design_spec.py`
- Create: `server/prompts/design_spec.txt`
- Create: `server/app/services/design_spec_generator.py`
- Create: `web/src/views/DesignStudioView.vue`

**Step 1: 测试 DesignSpec JSON Schema 校验（globalStyle + rooms[] + render2d）**

**Step 3: `POST /design/generate` 创建 pipeline task**

**前端 05:** textarea、风格 chips、RAG 侧栏（先 mock Top-K，P5 接真检索）

---

### Task P2-3：ComfyUI 客户端（复用已有 workflow）

**Files:**
- Create: `server/app/services/comfy_client.py`
- Copy/Adapt: `workflows/flux_interior_t2i_api.json` → `workflows/room_render_api.json`（参数化 prompt、seed、filename_prefix）
- Create: `server/tests/test_comfy_client.py`（mock httpx）

**Step 1: 测试 `submit_prompt` 返回 prompt_id**

**Step 3: 实现 poll history + download `/view` → `data/projects/{id}/renders/{room_id}/`**

**集成:** 本机 ComfyUI 8188 跑通单张客厅图

---

### Task P2-4：Orchestrator 流水线（原型 06）

**Files:**
- Create: `server/app/services/orchestrator.py`
- Create: `web/src/views/DesignGenerateView.vue`

**Pipeline 步骤（对齐原型 06）:**
1. DesignSpec（LLM）
2. 2D 效果图（ComfyUI × N 房间）
3. 3D 场景构建（P3 接入，P2 可 stub）
4. Obsidian 案例写入

**WS 事件:** `step_start`, `step_progress`, `step_done`, `pipeline_done`

---

### Task P2-5：Obsidian 案例写入

**Files:**
- Create: `server/app/services/knowledge/case_writer.py`
- Modify: `server/app/services/knowledge/vault_io.py`

**输出:** `Cases/{date}-{slug}.md` + 复制 renders 到 `Assets/` + DesignSpec 到 `Specs/`

**验收:** 生成完成后 Vault 内可见笔记，Obsidian 可打开

---

### Task P2-6：2D 画廊（原型 09）

**Files:**
- Create: `web/src/views/RenderGalleryView.vue`
- Create: `server/app/api/renders.py`

**交互:** 左侧房间 nav、大图、缩略图切换、Prompt details、重生成按钮 → 入队单房间 Comfy 任务

---

## P3：3D 单房间（Week 9–11）

### Task P3-1：家具 catalog MVP（≥20 SKU）

**Files:**
- Create: `assets/furniture/catalog.json`
- Add: `assets/furniture/*.glb`（≥20，CC0 或自有授权）

**catalog 字段:** `sku, name, category, width, depth, height, anchor, glb_path`

---

### Task P3-2：Scene Builder 单房间

**Files:**
- Create: `server/app/services/scene_builder.py`
- Create: `server/tests/test_scene_builder.py`

**Step 1: 测试 confirmed 户型单房间 → 输出 `scene.gltf` + `scene.json`**

**实现:** Shapely 多边形挤出墙；trimesh 导出；DesignSpec 家具规则摆放

---

### Task P3-3：Three.js 漫游组件（原型 10 单房间版）

**Files:**
- Create: `web/src/components/SceneViewer3D/index.vue`
- Create: `web/src/components/SceneViewer3D/useFirstPersonControls.ts`

**交互:** WASD、指针锁定、碰撞；HUD 显示房间名

**验收:** 单房间 glTF 浏览器内可走动不穿墙

---

## P4：全屋扩展与微调（Week 12–15）

### Task P4-1：多房间 Portal + 全屋 Scene

**Files:**
- Modify: `server/app/services/scene_builder.py`
- Modify: `web/src/components/SceneViewer3D/index.vue`

**实现:** `openings` → 门洞 + Portal 元数据；穿越切换 `activeRoom`

**验收:** ≥3 房间互通（对齐原型 10 房间 jump + portal）

---

### Task P4-2：方案微调 API（原型 07）

**Files:**
- Create: `server/app/api/design_refine.py`
- Create: `server/prompts/design_refine.txt`
- Create: `web/src/views/DesignRefineView.vue`

**API:**
- `POST /projects/{id}/design/refine` — LLM 生成 patch + diff 预览（不改 FloorPlanModel）
- `POST /projects/{id}/design/refine/apply` — 应用 patch + 增量 Comfy/3D 任务

**前端:** 三栏布局 — 摘要 / 输入 / diff 预览（对齐原型 07）

---

### Task P4-3：交付总览（原型 08）

**Files:**
- Create: `web/src/views/DeliveryOverviewView.vue`

**聚合:** 方案版本、房间覆盖 checklist、2D 速览、入口 3D/微调/画廊

---

### Task P4-4：全屋 2D 队列 + 端到端验收

**Modify:** `server/app/services/orchestrator.py`

**验收（V1 核心）:**
- 标准样本户型：上传 → 校对 → 描述 → 等待 → 交付总览
- 客厅/主卧/厨房各有 ≥1 张 Comfy 效果图
- Obsidian Cases 自动写入
- Playwright E2E：`web/e2e/full-flow.spec.ts`

---

## P5：Obsidian RAG（Week 16–17）

### Task P5-1：Chroma 索引服务

**Files:**
- Create: `server/app/services/knowledge/indexer.py`
- Create: `server/app/api/knowledge.py`

**Step 1: 测试 `index_document()` 写入 Chroma 后 `search()` Top-K**

**存储:** `~/House-DIY-Vault/.house-diy/chroma/`

---

### Task P5-2：生成前 RAG 注入

**Modify:** `server/app/services/design_spec_generator.py`
**Modify:** `server/prompts/design_spec.txt`

**查询:** 用户描述 + 户型摘要 → `house-embed` → Top-3 注入 prompt

**前端 05 侧栏:** 调用 `GET /knowledge/search?q=...` 展示 rag-card

---

### Task P5-3：知识库列表 + 导入（原型 11–12）

**Files:**
- Create: `web/src/views/KnowledgeListView.vue`
- Create: `web/src/views/KnowledgeImportView.vue`

**API:**
- `POST /knowledge/import` — PDF/图片 → VLM 摘要 → `References/`
- `POST /knowledge/reindex`

---

### Task P5-4：Vault watchdog

**Files:**
- Create: `server/app/services/knowledge/watcher.py`

**实现:** watchdog debounce → 增量 reindex

---

## P6：打磨（持续）

### Task P6-1：视觉对齐原型

**Files:**
- Create: `web/src/assets/theme.css`（从 `docs/原型/styles.css` 提取 CSS 变量）
- Modify: 各 View 组件间距/字体对齐原型

**验收:** 设计走查 — 13 屏与原型布局偏差 < 10%

---

### Task P6-2：错误处理与日志

**Files:**
- Create: `server/app/core/logging.py`
- Create: `server/app/core/exceptions.py`

---

### Task P6-3：资产扩展至 80+ SKU

**Files:**
- Expand: `assets/furniture/catalog.json`

---

### Task P6-4：Comfy preset ↔ Obsidian 联动

**Files:**
- Create: `vault-templates/comfy-preset-template.md`
- Modify: `case_writer.py` — 记录 workflow 名到 Cases frontmatter

---

## 测试策略总表

| 层级 | 工具 | 覆盖 |
|------|------|------|
| 单元 | pytest | schema, vault_io, scheduler, scene_builder 几何 |
| 单元 | Vitest | Pinia stores, API client |
| 集成 | pytest + `@integration` | oMLX live, ComfyUI live |
| E2E | Playwright | 原型主流程 01→08 |
| 人工 | 3 套标准户型图 | VLM 解析 ±1 房间 |

**CI 建议:** 默认只跑 unit；nightly 跑 integration（需 self-hosted Mac runner 或 skip）

---

## 环境变量（`server/.env.example`）

```bash
HOUSE_DIY_VAULT_PATH=~/House-DIY-Vault
HOUSE_DIY_DATA_DIR=./data
HOUSE_DIY_OMLX_BASE_URL=http://127.0.0.1:8000/v1
HOUSE_DIY_OMLX_API_KEY=<API_KEY>
HOUSE_DIY_OMLX_LLM_MODEL=house-llm
HOUSE_DIY_OMLX_VLM_MODEL=house-vlm
HOUSE_DIY_OMLX_EMBED_MODEL=house-embed
HOUSE_DIY_COMFY_URL=http://127.0.0.1:8188
HOUSE_DIY_REDIS_URL=redis://127.0.0.1:6379/0
HOUSE_DIY_GPU_SERIAL=true
```

---

## 提交规范

- `feat(floorplan): ...` / `feat(web): ...` / `feat(knowledge): ...` / `feat(comfy): ...`
- 每个 Task 独立 commit；P0–P2 可按 PR 分批（见 `@split-to-prs`）

---

## V1 完成定义（摘自 `docs/03`）

- [ ] 100% 离线：上传标准平面图 → 校对 → 描述 → 全屋 3D 漫游
- [ ] 客厅、主卧、厨房各有 ≥1 张 ComfyUI 效果图
- [ ] 每次设计自动写入 Obsidian Cases
- [ ] 新设计可 RAG 检索历史 Cases/References
- [ ] `docs/01–05` + `scripts/` 可复现环境

---

## 推荐 PR 拆分顺序

| PR | 范围 | 依赖 |
|----|------|------|
| PR-1 | P0 server health + projects | — |
| PR-2 | P0 web 壳 + settings | PR-1 |
| PR-3 | P0 vault_io + templates | PR-1 |
| PR-4 | P1 upload + parse + editor | PR-1–3 |
| PR-5 | P2 omlx + design_spec + comfy | PR-4 |
| PR-6 | P2 orchestrator + gallery + case write | PR-5 |
| PR-7 | P3 scene builder + 3D viewer | PR-6 |
| PR-8 | P4 refine + delivery + full house | PR-7 |
| PR-9 | P5 RAG + knowledge UI | PR-6 |
| PR-10 | P6 polish + E2E | PR-8–9 |

---

## 相关文档

- 架构：`docs/02-产品架构与技术方案.md`
- 里程碑：`docs/03-实现计划与里程碑.md`
- 环境：`docs/04-本地环境检查与安装步骤.md`
- 原型 UX：`docs/原型/README.md`
- 信息架构：`docs/原型/diagrams/information-architecture.md`
- 用户流程：`docs/原型/diagrams/user-flow.md`
