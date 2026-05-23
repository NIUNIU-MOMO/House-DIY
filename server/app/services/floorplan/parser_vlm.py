import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.schemas.floorplan import FloorPlanModel, FloorPlanStatus, Opening, OpeningType, Point, Room, Wall


class VlmPoint(BaseModel):
    x: float
    y: float


class VlmRoom(BaseModel):
    id: str
    name: str
    x: float | None = None
    y: float | None = None
    width: float | None = Field(default=None, gt=0)
    height: float | None = Field(default=None, gt=0)
    polygon: list[VlmPoint] | None = None
    area_label: str | None = None

    @model_validator(mode="after")
    def validate_geometry(self) -> "VlmRoom":
        has_bbox = None not in (self.x, self.y, self.width, self.height)
        has_polygon = self.polygon is not None and len(self.polygon) >= 3
        if not has_bbox and not has_polygon:
            raise ValueError("room requires polygon or x/y/width/height")
        return self

    def polygon_points(self) -> list[Point]:
        if self.polygon and len(self.polygon) >= 3:
            return [Point(x=p.x, y=p.y) for p in self.polygon]
        if None not in (self.x, self.y, self.width, self.height):
            x2 = self.x + self.width  # type: ignore[operator]
            y2 = self.y + self.height  # type: ignore[operator]
            return [
                Point(x=self.x, y=self.y),  # type: ignore[arg-type]
                Point(x=x2, y=self.y),  # type: ignore[arg-type]
                Point(x=x2, y=y2),
                Point(x=self.x, y=y2),  # type: ignore[arg-type]
            ]
        raise ValueError(f"room {self.id} has no geometry")


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


def load_prompt_for_image(width: int, height: int) -> str:
    """
    加载 VLM 提示词并附加当前图片尺寸约束

    @param width 图片宽度（像素）
    @param height 图片高度（像素）
    @return 完整提示词
    """
    return (
        f"{load_prompt()}\n\n"
        f"当前图片尺寸：宽 {width}px，高 {height}px。"
        f"polygon 顶点 x∈[0,{width}]，y∈[0,{height}]。"
    )


def extract_json_payload(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    return json.loads(cleaned)


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _normalize_polygon(raw: Any) -> list[dict[str, float]] | None:
    """
    将 VLM 多种 polygon 写法统一为 [{"x":..,"y":..}, ...]

    @param raw 原始 polygon 字段
    @return 归一化后的顶点列表，无法识别时返回 None
    """
    if raw is None:
        return None
    if not isinstance(raw, list) or len(raw) < 3:
        return None

    if all(isinstance(item, dict) and "x" in item and "y" in item for item in raw):
        points: list[dict[str, float]] = []
        for item in raw:
            x = _coerce_float(item.get("x"))
            y = _coerce_float(item.get("y"))
            if None in (x, y):
                return None
            points.append({"x": x, "y": y})
        return points

    if all(isinstance(item, (list, tuple)) and len(item) >= 2 for item in raw):
        points = []
        for item in raw:
            x = _coerce_float(item[0])
            y = _coerce_float(item[1])
            if None in (x, y):
                return None
            points.append({"x": x, "y": y})
        return points if len(points) >= 3 else None

    if all(isinstance(item, (int, float, str)) for item in raw):
        coords = [_coerce_float(item) for item in raw]
        if any(c is None for c in coords) or len(coords) % 2 != 0:
            return None
        points = [{"x": coords[i], "y": coords[i + 1]} for i in range(0, len(coords), 2)]
        return points if len(points) >= 3 else None

    return None


def _normalize_vlm_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    归一化 VLM JSON，兼容扁平坐标等非常规格式

    @param payload 原始 JSON 对象
    @return 归一化后的 JSON 对象
    """
    rooms = payload.get("rooms")
    if not isinstance(rooms, list):
        return payload

    normalized_rooms: list[Any] = []
    for room in rooms:
        if not isinstance(room, dict):
            normalized_rooms.append(room)
            continue
        room_copy = dict(room)
        if "polygon" in room_copy:
            normalized = _normalize_polygon(room_copy["polygon"])
            if normalized is not None:
                room_copy["polygon"] = normalized
        normalized_rooms.append(room_copy)

    return {**payload, "rooms": normalized_rooms}


def parse_vlm_response(text: str) -> VlmParseResult:
    """
    解析 VLM 返回的 JSON 文本

    @param text VLM 原始输出
    @return 结构化 VLM 解析结果
    """
    payload = _normalize_vlm_payload(extract_json_payload(text))
    return VlmParseResult.model_validate(payload)


def apply_coord_offset(points: list[Point], offset_x: float, offset_y: float) -> list[Point]:
    return [Point(x=p.x + offset_x, y=p.y + offset_y) for p in points]


def _clamp_points(points: list[Point], img_w: int | None, img_h: int | None) -> list[Point]:
    if img_w is None or img_h is None:
        return points
    return [
        Point(x=max(0.0, min(float(img_w), p.x)), y=max(0.0, min(float(img_h), p.y)))
        for p in points
    ]


def _parse_area_label(label: str | None) -> float | None:
    if not label:
        return None
    match = re.search(r"[\d.]+", label)
    if not match:
        return None
    try:
        return round(float(match.group()), 2)
    except ValueError:
        return None


def walls_from_room_polygons(room_polygons: list[list[Point]]) -> list[Wall]:
    """
    由房间多边形生成外墙线段

    @param room_polygons 房间多边形顶点列表
    @return 墙线段列表
    """
    walls: list[Wall] = []
    for index, polygon in enumerate(room_polygons):
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


def merge_vlm_result(
    result: VlmParseResult,
    *,
    coord_offset: tuple[float, float] = (0.0, 0.0),
    image_size: tuple[int, int] | None = None,
) -> FloorPlanModel:
    """
    将 VLM 结果合并为 FloorPlanModel 草稿

    @param result VLM 结构化结果
    @param coord_offset 裁剪图 → 原图的坐标偏移 (dx, dy)
    @param image_size 原图 (宽, 高)，用于坐标裁剪
    @return FloorPlanModel 草稿
    """
    offset_x, offset_y = coord_offset
    img_w, img_h = image_size if image_size else (None, None)

    room_polygons: list[list[Point]] = []
    rooms: list[Room] = []
    for room in result.rooms:
        polygon = _clamp_points(
            apply_coord_offset(room.polygon_points(), offset_x, offset_y),
            img_w,
            img_h,
        )
        room_polygons.append(polygon)
        area = _parse_area_label(room.area_label)
        if area is None and result.scale_hint:
            xs = [p.x for p in polygon]
            ys = [p.y for p in polygon]
            area = round((max(xs) - min(xs)) * (max(ys) - min(ys)) / 10000, 2)
        rooms.append(Room(id=room.id, name=room.name, polygon=polygon, area=area))

    walls = walls_from_room_polygons(room_polygons)
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
