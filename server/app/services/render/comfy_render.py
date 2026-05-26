from __future__ import annotations

from collections.abc import Callable

import hashlib

from app.core.config import settings
from app.schemas.design_spec import RoomDesignSpec
from app.schemas.floorplan import FloorPlanModel
from app.services.comfy_client import (
    ComfyClient,
    WORKFLOW_DEPTH,
    build_room_render_workflow,
    resolve_render_workflow_name,
)
from app.services.render.room_depth_map import save_room_depth_map
from app.services.render.storage import (
    RenderRecord,
    get_render_path,
    get_renders_dir,
    load_manifest,
    upsert_render,
)


def extract_output_image(history_entry: dict) -> tuple[str, str]:
    """
    从 ComfyUI history 提取输出图片信息

    @param history_entry history 单条记录
    @return (filename, subfolder)
    """
    outputs = history_entry.get("outputs", {})
    for node_output in outputs.values():
        images = node_output.get("images", [])
        if images:
            image = images[0]
            return image["filename"], image.get("subfolder", "")
    raise ValueError("no output image in ComfyUI history")


def _should_skip_existing(
    project_id: int,
    room: RoomDesignSpec,
    skip_existing: bool,
    scheme_id: str | None = None,
) -> bool:
    if not skip_existing:
        return False
    workflow_name = resolve_render_workflow_name(room.render2d.controlnet)
    manifest = load_manifest(project_id, scheme_id)
    existing = next((item for item in manifest.rooms if item.room_id == room.id), None)
    if existing is None or get_render_path(project_id, room.id, scheme_id) is None:
        return False
    return existing.workflow == workflow_name


def render_room(
    project_id: int,
    room: RoomDesignSpec,
    floorplan: FloorPlanModel | None = None,
    comfy_client: ComfyClient | None = None,
    placeholder_png: bytes | None = None,
    on_poll: Callable[[float, float], None] | None = None,
    skip_existing: bool = True,
    scheme_id: str | None = None,
) -> RenderRecord:
    """
    渲染单个房间效果图

    @param project_id 项目 ID
    @param room 房间 DesignSpec
    @param floorplan 户型模型（layout_depth 控制图需要）
    @param comfy_client ComfyUI 客户端
    @param placeholder_png 测试占位图（跳过 ComfyUI）
    @param on_poll ComfyUI 轮询回调 (elapsed_sec, timeout_sec)
    @param skip_existing 已有同 workflow 渲染时跳过
    @return 渲染记录
    """
    workflow_name = resolve_render_workflow_name(room.render2d.controlnet)
    if _should_skip_existing(project_id, room, skip_existing, scheme_id) and placeholder_png is None:
        manifest = load_manifest(project_id, scheme_id)
        existing = next((item for item in manifest.rooms if item.room_id == room.id), None)
        if existing is not None:
            return existing

    filename = f"{room.id}.png"
    if placeholder_png is not None:
        record = RenderRecord(
            room_id=room.id,
            room_name=room.name,
            filename=filename,
            prompt=room.render2d.prompt,
            negative=room.render2d.negative,
            workflow=workflow_name,
        )
        upsert_render(project_id, record, placeholder_png, scheme_id=scheme_id)
        return record

    client = comfy_client or ComfyClient()
    seed = int(hashlib.md5(room.id.encode()).hexdigest()[:8], 16) % 999999
    prefix = f"house-diy/p{project_id}/{room.id}"

    controlnet_image_name: str | None = None
    if workflow_name == WORKFLOW_DEPTH:
        if floorplan is None:
            raise ValueError(f"floorplan required for layout_depth render of room {room.id}")
        depth_path = get_renders_dir(project_id, scheme_id) / "depth" / f"{room.id}.png"
        depth_bytes = save_room_depth_map(floorplan, room.id, depth_path, room_spec=room)
        upload_name = f"house-diy-p{project_id}-{room.id}-depth.png"
        controlnet_image_name = client.upload_image(depth_bytes, upload_name)

    workflow = build_room_render_workflow(
        room.render2d.prompt,
        seed,
        prefix,
        workflow_name=workflow_name,
        controlnet_image_name=controlnet_image_name,
        controlnet_strength=settings.house_diy_comfyui_depth_strength,
    )
    prompt_id = client.submit_prompt(workflow)
    history_entry = client.wait_for_completion(
        prompt_id,
        poll_interval=2.0,
        timeout=settings.house_diy_comfyui_render_timeout,
        on_poll=on_poll,
    )
    image_name, subfolder = extract_output_image(history_entry)
    image_bytes = client.download_image(image_name, subfolder=subfolder)

    record = RenderRecord(
        room_id=room.id,
        room_name=room.name,
        filename=filename,
        prompt=room.render2d.prompt,
        negative=room.render2d.negative,
        workflow=workflow_name,
    )
    upsert_render(project_id, record, image_bytes, scheme_id=scheme_id)
    return record
