# House-DIY 页面原型

可交互 HTML 线框原型，与 `D:\IdeaProjects\House-DIY\prototype` 同源，用于对齐产品与 Vue 前端实现。

**v1.1 更新：** 内置模拟数据与状态管理（`store.js`），支持完整主流程点击体验：新建项目 → 解析 → 校对 → 设计 → 生成 → 交付 → 微调；数据持久化至 `localStorage`。

## 打开方式

**交互原型（推荐）**

```bash
cd docs/原型
python3 -m http.server 5500
# 访问 http://127.0.0.1:5500/index.html
```

- 左侧切换 **13** 个界面；键盘 `←` `→` 切换上一屏/下一屏。
- **应用内**按钮可点击：新建项目、上传解析、确认户型、生成方案、3D 漫游（WASD）、知识库导入等。
- 设置页可 **重置演示数据**。

**一览缩略图**

- 打开 [overview.html](./overview.html) 一次查看全部页面；点击「打开」跳回交互原型对应屏。

**流程与架构图（Mermaid）**

- [diagrams/user-flow.md](./diagrams/user-flow.md) — 用户主流程、状态机
- [diagrams/information-architecture.md](./diagrams/information-architecture.md) — 路由与 Pinia
- [diagrams/system-overview.md](./diagrams/system-overview.md) — 系统上下文

## 可交互流程

| 操作 | 效果 |
|------|------|
| 新建项目 → 选文件 → 开始解析 | 模拟 VLM 解析进度，自动进入校对 |
| 确认户型 → 描述需求 → 生成方案 | 模拟 DesignSpec + ComfyUI 流水线 |
| 交付总览 → 微调 / 3D / 2D 画廊 | 页面内导航 + WASD 漫游 |
| 知识库 → 导入参考 | 写入模拟索引列表 |
| 顶栏 项目/设计/知识库/设置 | 跳转对应模块 |

## 页面清单（13 屏）

| ID | 页面 | 流程 |
|----|------|------|
| 01 | 项目列表 | 入口 |
| 02 | 新建 · 上传户型 | 上传 |
| 03 | 户型 AI 解析中 | 上传 |
| 04 | 户型 2D 校对编辑器 | 校对 |
| 05 | 设计描述 · RAG 参考 | 设计 |
| 06 | 方案生成进度 | 生成 |
| 07 | **方案微调** | **微调** |
| 08 | 方案交付总览 | 交付 |
| 09 | 2D 效果图画廊 | 交付 |
| 10 | 3D 全屋漫游 | 交付 |
| 11 | 设计知识库（Obsidian） | 知识库 |
| 12 | 导入外部参考 | 知识库 |
| 13 | 系统状态与设置 | 设置 |

### 07 方案微调（新增）

- 用户用自然语言描述调整意图，LLM 对已有 **DesignSpec** 生成 patch（不改户型几何）。
- 右侧展示变更 diff 与受影响房间的 2D/3D 增量重渲染范围，确认后入队。
- 建议 API：`POST /api/v1/projects/{id}/design/refine`（预览）→ `POST .../design/refine/apply`。

## 文件说明

| 文件 | 说明 |
|------|------|
| `index.html` | 原型壳 + 侧栏导航 |
| `store.js` | 模拟数据、状态、localStorage |
| `screens.js` | 各屏动态渲染模板 |
| `app.js` | 事件绑定、模拟异步流程 |
| `styles.css` | 暖色家居风样式（CSS 变量可复用到 Vue） |
| `overview.html` | 全页缩略一览 |
| `diagrams/` | Mermaid 流程与信息架构 |

## 说明

- 无真实 API；oMLX / ComfyUI 状态为模拟，可与 §13 设置页对照本机实际服务。
- 视觉：Fraunces + IBM Plex Sans，色板见 `styles.css` 内 `:root`。
