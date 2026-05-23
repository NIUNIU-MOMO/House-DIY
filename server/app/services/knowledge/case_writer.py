import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.schemas.design_spec import DesignSpec
from app.schemas.floorplan import FloorPlanModel
from app.services.design.storage import get_design_spec_path
from app.services.knowledge.vault_io import ensure_vault_dirs
from app.services.render.storage import RenderManifest


def _slugify(name: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", name.strip().lower())
    return slug.strip("-") or "project"


def write_design_case(
    project_id: int,
    project_name: str,
    spec: DesignSpec,
    floorplan: FloorPlanModel,
    renders: RenderManifest,
    vault_root: Path | None = None,
) -> Path:
    """
    写入 Obsidian 案例笔记并复制 Spec / 效果图到 Vault

    @param project_id 项目 ID
    @param project_name 项目名称
    @param spec DesignSpec
    @param floorplan 户型模型
    @param renders 渲染清单
    @param vault_root Vault 根路径
    @return 案例笔记路径
    """
    vault = vault_root or settings.vault_path()
    ensure_vault_dirs(vault)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = _slugify(project_name)
    case_path = vault / "Cases" / f"{date_str}-{slug}.md"

    spec_dest = vault / "Specs" / f"project-{project_id}-designspec.json"
    spec_dest.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
    project_spec = get_design_spec_path(project_id)
    if project_spec.is_file():
        shutil.copy2(project_spec, spec_dest)

    render_links: list[str] = []
    from app.services.render.storage import get_renders_dir

    renders_dir = get_renders_dir(project_id)
    for item in renders.rooms:
        source = renders_dir / item.filename
        if source.is_file():
            asset_name = f"project-{project_id}-{item.filename}"
            shutil.copy2(source, vault / "Assets" / asset_name)
            render_links.append(f"![[{asset_name}]]")

    room_names = ", ".join(room.name for room in floorplan.rooms)
    created = datetime.now(timezone.utc).isoformat()
    workflows = sorted({room.render2d.workflow for room in spec.rooms if room.render2d.workflow})
    comfy_preset = workflows[0] if workflows else "flux_interior_t2i_api"
    workflow_lines = "\n".join(f"- `{name}`" for name in workflows) if workflows else "- `flux_interior_t2i_api`"
    body = f"""---
type: design_case
project_id: "{project_id}"
project_name: "{project_name}"
rooms: {json.dumps([room.id for room in spec.rooms], ensure_ascii=False)}
style: "{spec.globalStyle}"
tags: []
rating: 0
source: internal
comfy_preset: {comfy_preset}
comfy_workflows: {json.dumps(workflows or [comfy_preset], ensure_ascii=False)}
created: {created}
---

# {project_name}

## 户型摘要

{len(floorplan.rooms)} 个房间：{room_names}

## 设计策略

{spec.globalStyle}

## 家具与软装

待 Scene Builder 补充

## ComfyUI 预设

{workflow_lines}

## 效果图

{chr(10).join(render_links) if render_links else "暂无"}

## 备注

自动生成于 House-DIY 流水线
"""
    case_path.write_text(body, encoding="utf-8")

    from app.services.knowledge.indexer import get_knowledge_indexer

    try:
        get_knowledge_indexer().index_markdown_file(case_path, source="internal")
    except Exception:
        pass

    return case_path
