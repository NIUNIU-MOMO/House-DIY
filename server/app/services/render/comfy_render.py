import hashlib
from pathlib import Path

from app.schemas.design_spec import RoomDesignSpec
from app.services.comfy_client import ComfyClient, build_room_render_workflow
from app.services.render.storage import RenderRecord, upsert_render


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


def render_room(
    project_id: int,
    room: RoomDesignSpec,
    comfy_client: ComfyClient | None = None,
    placeholder_png: bytes | None = None,
) -> RenderRecord:
    """
    渲染单个房间效果图

    @param project_id 项目 ID
    @param room 房间 DesignSpec
    @param comfy_client ComfyUI 客户端
    @param placeholder_png 测试占位图（跳过 ComfyUI）
    @return 渲染记录
    """
    filename = f"{room.id}.png"
    if placeholder_png is not None:
        record = RenderRecord(
            room_id=room.id,
            room_name=room.name,
            filename=filename,
            prompt=room.render2d.prompt,
            negative=room.render2d.negative,
            workflow=room.render2d.workflow,
        )
        upsert_render(project_id, record, placeholder_png)
        return record

    client = comfy_client or ComfyClient()
    seed = int(hashlib.md5(room.id.encode()).hexdigest()[:8], 16) % 999999
    prefix = f"house-diy/p{project_id}/{room.id}"
    workflow = build_room_render_workflow(room.render2d.prompt, seed, prefix)
    prompt_id = client.submit_prompt(workflow)
    history_entry = client.wait_for_completion(prompt_id, poll_interval=1.0, timeout=120.0)
    image_name, subfolder = extract_output_image(history_entry)
    image_bytes = client.download_image(image_name, subfolder=subfolder)

    record = RenderRecord(
        room_id=room.id,
        room_name=room.name,
        filename=filename,
        prompt=room.render2d.prompt,
        negative=room.render2d.negative,
        workflow=room.render2d.workflow,
    )
    upsert_render(project_id, record, image_bytes)
    return record
