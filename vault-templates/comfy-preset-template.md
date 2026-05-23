---
type: comfy_preset
name: flux_interior_t2i_api
workflow_file: flux_interior_t2i_api.json
api_workflow: room_render_api.json
tags: []
rating: 0
source: internal
created: {{created}}
---

# ComfyUI 预设 · {{name}}

## 用途

全屋室内效果图 text-to-image，配合 DesignSpec `render2d.prompt` 逐房间渲染。

## Workflow 文件

- 本机 ComfyUI：`workflows/{{api_workflow}}`
- 参数化：`prompt`、`seed`、`filename_prefix`

## 关联案例

在 Cases frontmatter 中通过 `comfy_workflows` 引用此预设名。

## 备注

由 House-DIY 流水线自动关联；可在 Obsidian 中补充采样步数、LoRA 等参数说明。
