# House-DIY

本地离线全屋设计助手：上传标准平面图 → AI 解析与 2D 校对 → RAG + DesignSpec → ComfyUI 效果图 + 程序化 3D → Obsidian 案例沉淀。

**技术栈：** Vue 3 + FastAPI · oMLX（LLM/VLM/Embed）· ComfyUI · SQLite · Chroma · Three.js

## 前置条件

本机需已按 [docs/04-本地环境检查与安装步骤.md](docs/04-本地环境检查与安装步骤.md) 完成：

- Python 3.12 虚拟环境 `~/House-DIY-env`
- Node.js 20+
- oMLX（`:8000`，alias: `house-llm` / `house-vlm-pro` / `house-embed`）
- ComfyUI（`:8188`）
- Redis Docker 容器 `house-diy-redis`
- Obsidian Vault `~/House-DIY-Vault`

复制并填写 API 密钥：

```bash
cp server/.env.example server/.env
# 编辑 HOUSE_DIY_OMLX_API_KEY
```

## 快速启动

```bash
# 环境验收（oMLX / ComfyUI / Redis / Vault 等）
./scripts/check-deps.sh

# 一键启动 ComfyUI + FastAPI + Vue（Ctrl+C 停止）
./scripts/start-all.sh
```

或分别启动：

```bash
# 终端 1 — API（8080，避免与 oMLX :8000 冲突）
cd server && source ~/House-DIY-env/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload

# 终端 2 — 前端
cd web && npm install && npm run dev
```

访问 **http://127.0.0.1:5173**

## 用户流程

```
首页 → 新建 → 上传 → 解析(VLM) → 2D 校对 → 设计描述(RAG)
  → 全屋生成 → 交付总览 → [2D 画廊 | 3D 漫游 | 方案微调]
知识库：/knowledge · 系统设置：/settings
```

原型 UX 基准见 [docs/原型/](docs/原型/)。

## 测试

```bash
# 后端单元测试（默认跳过 integration）
cd server && source ~/House-DIY-env/bin/activate && pytest -v

# 本机 oMLX 集成测试
pytest -m integration -v

# 前端类型检查 + 单元测试
cd web && npm run type-check && npm test

# E2E（Playwright，需 dev server 或由配置自动拉起）
cd web && npm run test:e2e
```

## 目录结构

```
House-DIY/
├── server/           # FastAPI 编排层、服务、测试
├── web/              # Vue 3 SPA
├── assets/furniture/ # 家具 catalog + GLB
├── vault-templates/  # Obsidian 笔记模板
├── workflows/        # ComfyUI FLUX workflow
├── scripts/          # check-deps、start-all、资产生成
└── docs/             # 架构、里程碑、环境、原型
```

## 文档

| 文档 | 说明 |
|------|------|
| [02-产品架构与技术方案](docs/02-产品架构与技术方案.md) | 系统架构 |
| [03-实现计划与里程碑](docs/03-实现计划与里程碑.md) | 阶段划分 |
| [04-本地环境检查与安装步骤](docs/04-本地环境检查与安装步骤.md) | 环境搭建 |
| [06-V1-验收清单](docs/06-V1-验收清单.md) | V1 人工验收步骤 |
| [plans/全栈实现计划](docs/plans/2026-05-23-house-diy-full-stack-implementation.md) | 详细 Task 清单 |

## V1 完成定义

- 100% 离线完成：上传 → 校对 → 描述 → 全屋 3D 漫游
- 客厅、主卧、厨房各有 ≥1 张 ComfyUI 效果图
- 每次设计自动写入 Obsidian `Cases/`
- 新设计可 RAG 检索历史 Cases / References

详见 [docs/06-V1-验收清单.md](docs/06-V1-验收清单.md)。
