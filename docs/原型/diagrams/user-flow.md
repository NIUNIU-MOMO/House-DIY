# House-DIY 用户主流程

> 对应产品文档 02 §3 端到端数据流、03 里程碑 P1–P5

## 主流程（Mermaid）

```mermaid
flowchart TD
  Start([用户打开应用]) --> Health{服务健康?}
  Health -->|否| Fix[检查 oMLX / ComfyUI / API]
  Fix --> Health
  Health -->|是| Home[首页 · 项目列表]
  Home --> New[新建项目]
  New --> Upload[上传平面图 PNG/PDF]
  Upload --> Parse[VLM 语义 + CV 矢量化]
  Parse --> Editor[2D 户型校对]
  Editor --> Confirm{确认户型?}
  Confirm -->|否| Editor
  Confirm -->|是| Studio[设计工作室 · 输入描述]
  Studio --> RAG[RAG 检索 Cases/References]
  RAG --> Spec[LLM 生成 DesignSpec]
  Spec --> Parallel{并行队列}
  Parallel --> Comfy[ComfyUI 各房间 2D]
  Parallel --> Scene[Scene Builder 3D]
  Comfy --> Vault[写入 Obsidian Cases]
  Scene --> Vault
  Vault --> Index[Chroma 向量索引]
  Index --> Deliver[方案交付总览]
  Deliver --> RefineQ{自然语言微调?}
  RefineQ -->|是| Refine[LLM patch DesignSpec]
  Refine --> Partial[增量 ComfyUI / 3D]
  Partial --> Deliver
  RefineQ -->|否| Done[画廊 + 3D 漫游]
  Done --> Gallery[2D 效果图画廊]
  Done --> Walk[3D 全屋漫游]
```

## 户型状态机

```mermaid
stateDiagram-v2
  [*] --> none: 未上传
  none --> draft: POST /floorplan
  draft --> draft: PUT 校对中
  draft --> confirmed: PUT status=confirmed
  confirmed --> [*]: 可进入设计生成
  note right of confirmed
    未 confirmed 时
    禁用 design/generate
  end note
```

## 设计生成任务状态

```mermaid
stateDiagram-v2
  [*] --> pending
  pending --> running: Scheduler 领取
  running --> done: 流水线完成
  running --> failed: 重试 2 次后
  failed --> pending: 手动重试
  done --> [*]
```

## API 触点一览

| 用户动作 | 前端页面 | API |
|----------|----------|-----|
| 查看服务状态 | 01-home | GET /health |
| 新建项目 | 01-home | POST /projects |
| 上传平面图 | 02-upload | POST /projects/{id}/floorplan |
| 保存校对 | 03-editor | PUT /projects/{id}/floorplan |
| 开始设计 | 05-studio | POST /projects/{id}/design/generate |
| 微调方案 | 07-refine | POST /projects/{id}/design/refine |
| 查看进度 | 04-studio | WS /projects/{id}/ws |
| 浏览效果图 | 05-gallery | GET /projects/{id}/renders |
| 3D 漫游 | 06-scene | GET /projects/{id}/scene |
| 导入参考 | 07-knowledge | POST /knowledge/import |
| 重建索引 | 07-knowledge | POST /knowledge/reindex |
