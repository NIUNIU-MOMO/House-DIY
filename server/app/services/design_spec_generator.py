from __future__ import annotations

import json
from pathlib import Path

from app.schemas.design_spec import DesignSpec
from app.schemas.floorplan import FloorPlanModel
from app.services.floorplan.parser_vlm import extract_json_payload
from app.services.knowledge.indexer import rag_search
from app.services.omlx_client import OmlxClient, get_omlx_client


def load_prompt() -> str:
    prompt_path = Path(__file__).resolve().parents[2] / "prompts" / "design_spec.txt"
    return prompt_path.read_text(encoding="utf-8")


def build_rag_query(brief: str, floorplan: FloorPlanModel) -> str:
    room_names = "、".join(room.name for room in floorplan.rooms)
    return f"{brief} · 户型房间：{room_names}"


def build_design_messages(
    brief: str,
    floorplan: FloorPlanModel,
    global_style: str | None,
    rag_cases: list[dict],
) -> list[dict[str, str]]:
    rooms_summary = [
        {"id": room.id, "name": room.name, "area": room.area}
        for room in floorplan.rooms
    ]
    user_content = {
        "brief": brief,
        "globalStyleHint": global_style or "",
        "floorplanRooms": rooms_summary,
        "ragReferences": rag_cases,
    }
    return [
        {"role": "system", "content": load_prompt()},
        {"role": "user", "content": json.dumps(user_content, ensure_ascii=False)},
    ]


def parse_design_spec_response(text: str) -> DesignSpec:
    payload = extract_json_payload(text)
    return DesignSpec.model_validate(payload)


def generate_design_spec(
    brief: str,
    floorplan: FloorPlanModel,
    global_style: str | None = None,
    use_rag: bool = True,
    omlx_client: OmlxClient | None = None,
) -> DesignSpec:
    """
    调用 LLM 生成 DesignSpec

    @param brief 用户设计描述
    @param floorplan 已确认户型
    @param global_style 全局风格提示
    @param use_rag 是否注入 RAG 参考
    @param omlx_client oMLX 客户端
    @return DesignSpec
    """
    client = omlx_client or get_omlx_client()
    rag_cases = rag_search(build_rag_query(brief, floorplan), top_k=3) if use_rag else []
    messages = build_design_messages(brief, floorplan, global_style, rag_cases)
    response = client.chat_text(messages)
    spec = parse_design_spec_response(response)
    if use_rag:
        spec.ragContextIds = [case["id"] for case in rag_cases]
    return spec
