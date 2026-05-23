import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.floorplan import FloorPlanModel, FloorPlanStatus, Opening, OpeningType, Point, Room, Wall


class VlmRoom(BaseModel):
    id: str
    name: str
    x: float
    y: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class VlmOpening(BaseModel):
    id: str
    type: OpeningType
    x: float
    y: float
    width: float = Field(gt=0)
    connects: list[str] = Field(default_factory=list)


class VlmParseResult(BaseModel):
    scale_hint: float | None = None
    rooms: list[VlmRoom] = Field(default_factory=list)
    openings: list[VlmOpening] = Field(default_factory=list)


def load_prompt() -> str:
    prompt_path = Path(__file__).resolve().parents[3] / "prompts" / "floorplan_vlm.txt"
    return prompt_path.read_text(encoding="utf-8")


def extract_json_payload(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    return json.loads(cleaned)


def parse_vlm_response(text: str) -> VlmParseResult:
    """
    解析 VLM 返回的 JSON 文本

    @param text VLM 原始输出
    @return 结构化 VLM 解析结果
    """
    payload = extract_json_payload(text)
    return VlmParseResult.model_validate(payload)


def room_to_polygon(room: VlmRoom) -> list[Point]:
    x2 = room.x + room.width
    y2 = room.y + room.height
    return [
        Point(x=room.x, y=room.y),
        Point(x=x2, y=room.y),
        Point(x=x2, y=y2),
        Point(x=room.x, y=y2),
    ]


def walls_from_rooms(rooms: list[VlmRoom]) -> list[Wall]:
    """
    由房间矩形生成墙线段（CV 占位，P1-5 将替换为 OpenCV 提取）

    @param rooms VLM 房间列表
    @return 墙线段列表
    """
    walls: list[Wall] = []
    for index, room in enumerate(rooms):
        polygon = room_to_polygon(room)
        for point_index in range(len(polygon)):
            start = polygon[point_index]
            end = polygon[(point_index + 1) % len(polygon)]
            walls.append(
                Wall(
                    id=f"w{index + 1}_{point_index + 1}",
                    points=[start, end],
                )
            )
    return walls


def merge_vlm_result(result: VlmParseResult) -> FloorPlanModel:
    """
    将 VLM 结果合并为 FloorPlanModel 草稿

    @param result VLM 结构化结果
    @return FloorPlanModel 草稿
    """
    rooms = [
        Room(
            id=room.id,
            name=room.name,
            polygon=room_to_polygon(room),
            area=round((room.width * room.height) / 10000, 2) if result.scale_hint else None,
        )
        for room in result.rooms
    ]
    walls = walls_from_rooms(result.rooms)
    openings: list[Opening] = []
    for opening in result.openings:
        wall_id = walls[0].id if walls else "w1_1"
        openings.append(
            Opening(
                id=opening.id,
                type=opening.type,
                wall_id=wall_id,
                position=0.5,
                width=max(opening.width / 100, 0.6),
                connects=opening.connects,
            )
        )

    return FloorPlanModel(
        scale=result.scale_hint,
        walls=walls,
        rooms=rooms,
        openings=openings,
        status=FloorPlanStatus.DRAFT,
    )
