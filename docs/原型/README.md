# House-DIY 页面原型

可交互 HTML 线框原型，与 `D:\IdeaProjects\House-DIY\prototype` 同源，用于对齐产品与 Vue 前端实现。

## 打开方式

**交互原型（推荐）**

```bash
cd docs/原型
python -m http.server 5500
# 访问 http://127.0.0.1:5500/index.html
```

- 左侧切换 **13** 个界面；键盘 `←` `→` 切换上一屏/下一屏。
- 也可直接用浏览器打开 `index.html`（部分环境需本地服务以加载脚本）。

**一览缩略图**

- 打开 [overview.html](./overview.html) 一次查看全部页面；点击「打开」跳回交互原型对应屏。

**流程与架构图（Mermaid）**

- [diagrams/user-flow.md](./diagrams/user-flow.md) — 用户主流程、状态机
- [diagrams/information-architecture.md](./diagrams/information-architecture.md) — 路由与 Pinia
- [diagrams/system-overview.md](./diagrams/system-overview.md) — 系统上下文

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
| `screens.js` | 各屏 HTML 内容 |
| `app.js` | 切换逻辑 |
| `styles.css` | 暖色家居风样式（CSS 变量可复用到 Vue） |
| `overview.html` | 全页缩略一览 |
| `diagrams/` | Mermaid 流程与信息架构 |

## 说明

- 按钮与链接为示意，无真实 API。
- 视觉：Fraunces + IBM Plex Sans，色板见 `styles.css` 内 `:root`。
