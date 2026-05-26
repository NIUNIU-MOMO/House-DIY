# 流程重构 — 设计文档

> **日期：** 2026-05-26  
> **状态：** 已评审通过  
> **需求文档：** [11-流程重构需求.md](../11-流程重构需求.md)  
> **原型：** [docs/原型/v2/](../原型/v2/)

---

## 1. 评审结论摘要

经 brainstorming 逐项确认，在 v1.0 需求基础上补充以下**已决规则**（取代原 §10 开放问题）。

| # | 议题 | 决策 |
|---|------|------|
| 1 | 保存 vs 进入设计 | **两步分离**：「保存标注」随时可点；「确认并进入设计」单独解锁设计页 |
| 2 | 重新解析与 max_step | **不回退**；标注/方案标 stale，进设计前提醒 |
| 3 | 放弃未保存变更 | **二次确认** Modal |
| 4 | 上传页 | **保留**项目名、预估面积；收简布局与按钮文案 |
| 5 | 多方案 | 软上限 **10**；首次进设计自动 **方案 A**；**禁止自动删除** |
| 6 | 旧数据 | **不迁移**；优化完成后用户**手动清空**旧项目数据 |
| 7 | 输出目录 | `server/settings.local.json`；UI 优先；保存即生效 |
| 8 | max_step 推进 | 见 §2.2 |
| 9 | 确认与 max_step | **确认不抬 design**；design 由保存方案/微调保存触发 |

---

## 2. 标注与进度模型

### 2.1 两步操作

| 按钮 | 作用 | 推进 max_step |
|------|------|---------------|
| **保存标注** | 覆盖唯一标注快照；可多次、慢慢改 | 解析后**首次保存** → `≥ annotate`；之后每次保存更新快照 |
| **确认并进入设计** | `floorplan.status = confirmed`；解锁设计页 | **否** |

**质检：**
- `error`：阻断「确认并进入设计」；允许「保存标注」
- `warning`：不阻断

### 2.2 max_step 推进表

| 值 | 触发条件 | 可回退 |
|----|----------|--------|
| `upload` | 新建默认 | — |
| `parse` | 源图上传成功 | 否 |
| `annotate` | 解析完成后首次「保存标注」 | 否 |
| `design` | 首次「保存方案」或微调完成并保存 | 否 |
| `preview` | **任一方案** 3D 生成成功 | 否 |

**列表入口：** 始终进入 `max_step` 对应页面。

**设计页可达：** 标注已 `confirmed`；若 `annotation_stale` 或 `scheme_stale`，生成/微调前拦截。

### 2.3 重新解析 / 换图

- `max_step` **不变**
- 新解析覆盖 draft → `annotation_stale = true`
- `confirmed` 快照与 draft 不一致 → 设计相关操作前弹窗：「户型已变更，请先保存并确认标注」
- 已有方案 → `scheme_stale = true`；**不自动删除**

### 2.4 未保存拦截（双层 Modal）

1. 切换步骤：保存 / 放弃并离开 / 取消  
2. 选「放弃并离开」→「未保存的修改将丢失，确定放弃？」→ 返回 / 确定放弃  

适用：标注页、设计页（含未应用的描述/微调）。

---

## 3. 设计方案与多方案

### 3.1 方案状态机

```
empty → draft → rendering_2d → draft_2d → saved → rendering_3d → ready
                                                              ↓
                                                         refining → saved
```

| 状态 | 含义 |
|------|------|
| `draft` | 仅有描述 |
| `draft_2d` | 2D 已生成未保存 |
| `saved` | 2D 已确认落盘 |
| `ready` | 3D 可漫游 |
| `stale` | 标注基底变更（叠加标记） |

### 3.2 多方案规则

- 首次进设计且无方案 → 自动创建「方案 A」
- 软上限 10 套；满额禁止新建，提示手动删除
- 删除：仅用户主动 + 二次确认；删除该方案全部产物
- 记住 `active_scheme_id`

### 3.3 设计页操作与 max_step

| 操作 | max_step |
|------|----------|
| 生成 2D | 否 |
| 保存方案 | 首次 → `≥ design` |
| 生成 3D 成功 | 项目 `≥ preview` |
| 微调完成并保存 | 保持 `≥ design` |

### 3.4 预览页

- 只读：方案选择 + 2D 平铺 + 进入 3D
- 编辑回设计页；删除方案仅在设计页

---

## 4. 上传、流程条、存储

### 4.1 上传页

保留：项目名、预估面积、上传区、已有图替换。  
按钮：「上传并开始解析 →」。上传成功 → `max_step ≥ parse`。

### 4.2 流程条

- 步骤：上传 → 解析 → **标注** → 设计 → 预览
- 颜色：已完成绿 / 当前黄 / 未到达灰
- 前端 key：`review` → `annotate`

### 4.3 输出根目录

| 项 | 值 |
|----|-----|
| 配置文件 | `server/settings.local.json`（gitignore） |
| 优先级 | UI > `HOUSE_DIY_OUTPUT_ROOT` > 默认 |
| 生效 | 保存后立即 |
| 迁移 | 无；旧数据用户手动清空 |

```
{output_root}/{project_id}/
  source.*
  floorplan.json
  meta.json
  schemes/{scheme_id}/
    design_spec.json
    meta.json
    renders/
    scene/
```

### 4.4 标注交互

- 放大：原图/标注 checkbox，默认双开
- 新增：**右键**类型菜单 + 自适应框（右侧面板保留 P1）
- 调整：顶点 + 边线拖动
- 删除：左侧列表 + 删除按钮

---

## 5. 数据模型与 API

### 5.1 Project 扩展

```python
max_step: Literal["upload", "parse", "annotate", "design", "preview"]
active_scheme_id: str | None
annotation_confirmed_at: datetime | None  # 可选
```

项目 `meta.json` 或 DB 可存：`annotation_stale`, 各 scheme 的 `stale`。

### 5.2 API 增量

| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | `/projects/{id}/floorplan/annotation` | 保存标注；更新 max_step≥annotate |
| POST | `/projects/{id}/floorplan/confirm` | confirmed；不抬 max_step 到 design |
| GET/PUT | `/api/v1/settings/storage` | output_root |
| GET/POST | `/projects/{id}/schemes` | 列表 / 新建 |
| DELETE | `/projects/{id}/schemes/{sid}` | 用户删除方案 |
| PUT | `/projects/{id}/schemes/{sid}` | 保存方案 |
| POST | `.../generate-2d` `.../generate-3d` `.../refine` | 生成与微调 |

---

## 6. 里程碑

| 阶段 | 范围 |
|------|------|
| M1 | 流程条 + annotate 重命名 + 上传/解析 UI |
| M2 | 标注保存/确认分离 + dirty 双层 Modal + 右键新增 |
| M3 | max_step + stale + 列表入口 |
| M4 | 多 scheme + 2D/3D 分步 + 预览 |
| M5 | settings.local.json + output_root |

---

## 7. 非目标（重申）

- 标注/方案历史版本栈
- 旧 `design_spec.json` 自动迁移
- 系统自动删除方案或项目文件
