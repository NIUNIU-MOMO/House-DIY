import json
from copy import deepcopy
from pathlib import Path

from app.schemas.design_refine import RefineDiffItem, RefinePreviewResponse
from app.schemas.design_spec import DesignSpec
from app.services.floorplan.parser_vlm import extract_json_payload
from app.services.omlx_client import OmlxClient, get_omlx_client


def load_refine_prompt() -> str:
    prompt_path = Path(__file__).resolve().parents[2] / "prompts" / "design_refine.txt"
    return prompt_path.read_text(encoding="utf-8")


def parse_refine_response(text: str) -> dict:
    return extract_json_payload(text)


def preview_refine(
    instruction: str,
    spec: DesignSpec,
    omlx_client: OmlxClient | None = None,
) -> RefinePreviewResponse:
    """
    生成 DesignSpec 微调预览

    @param instruction 用户微调描述
    @param spec 当前 DesignSpec
    @param omlx_client oMLX 客户端
    @return 预览结果
    """
    client = omlx_client or get_omlx_client()
    messages = [
        {"role": "system", "content": load_refine_prompt()},
        {
            "role": "user",
            "content": json.dumps(
                {"instruction": instruction, "currentDesignSpec": spec.model_dump()},
                ensure_ascii=False,
            ),
        },
    ]
    payload = parse_refine_response(client.chat_text(messages))
    diff = [RefineDiffItem.model_validate(item) for item in payload.get("diff", [])]
    affected = payload.get("affectedRoomIds", [])
    return RefinePreviewResponse(
        instruction=instruction,
        diff=diff,
        patch=payload,
        affected_room_ids=affected,
    )


def apply_patch(spec: DesignSpec, patch: dict) -> DesignSpec:
    """
    将 LLM patch 合并到 DesignSpec

    @param spec 原 DesignSpec
    @param patch LLM 返回 patch
    @return 更新后的 DesignSpec
    """
    updated = deepcopy(spec)
    for change in patch.get("changes", []):
        field = change.get("field")
        value = change.get("value")
        room_id = change.get("roomId")
        if field == "globalStyle":
            updated.globalStyle = value
            continue
        if not room_id:
            continue
        room = next((item for item in updated.rooms if item.id == room_id), None)
        if room is None:
            continue
        if field == "style":
            room.style = value
        elif field == "palette":
            room.palette = value
        elif field == "furniture":
            room.furniture = value
        elif field == "render2d.prompt":
            room.render2d.prompt = value
    return updated
