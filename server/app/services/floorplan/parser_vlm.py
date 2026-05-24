import json
import re
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.services.floorplan.plan_classifier import PlanType

from app.schemas.floorplan import FloorPlanModel, FloorPlanStatus, FloorPlanValidation, Opening, OpeningType, Point, Room, Wall

POLYGON_BATCH_SIZE = 2
PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"


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


class VlmRoomStub(BaseModel):
    id: str
    name: str
    area_label: str | None = None


class VlmRoomListResult(BaseModel):
    scale_hint: float | None = None
    rooms: list[VlmRoomStub] = Field(default_factory=list)


class VlmRoomPolygon(BaseModel):
    id: str
    polygon: Annotated[list[VlmPoint], Field(min_length=3)]


def load_prompt(plan_type: PlanType = "cad_lineart") -> str:
    if plan_type == "marketing_color":
        prompt_path = PROMPTS_DIR / "floorplan_vlm_marketing.txt"
    else:
        prompt_path = PROMPTS_DIR / "floorplan_vlm.txt"
    return prompt_path.read_text(encoding="utf-8")


def load_step1_prompt(plan_type: PlanType = "cad_lineart") -> str:
    base = (PROMPTS_DIR / "floorplan_vlm_rooms.txt").read_text(encoding="utf-8")
    if plan_type == "marketing_color":
        base += (
            "\n\n补充（彩色营销图）：跟墙体线走，不要跟地板颜色块走；"
            "完全忽略中央水印/Logo/品牌字。"
        )
    return base


def load_step2_prompt(plan_type: PlanType = "cad_lineart") -> str:
    base = (PROMPTS_DIR / "floorplan_vlm_polygons.txt").read_text(encoding="utf-8")
    if plan_type == "marketing_color":
        base += (
            "\n\n补充（彩色营销图）：polygon 必须贴墙体围合内侧，"
            "不要跟色块填充或家具外轮廓走。"
        )
    return base


def _append_image_size(prompt: str, width: int, height: int) -> str:
    return (
        f"{prompt}\n\n"
        f"当前图片尺寸：宽 {width}px，高 {height}px。"
        f"polygon 顶点 x∈[0,{width}]，y∈[0,{height}]。"
    )


def load_prompt_for_image(
    width: int,
    height: int,
    plan_type: PlanType = "cad_lineart",
) -> str:
    """
    加载 VLM 提示词并附加当前图片尺寸约束

    @param width 图片宽度（像素）
    @param height 图片高度（像素）
    @param plan_type 户型图源类型
    @return 完整提示词
    """
    return _append_image_size(load_prompt(plan_type), width, height)


def load_step1_prompt_for_image(
    width: int,
    height: int,
    plan_type: PlanType = "cad_lineart",
    pdf_text_hint: str | None = None,
) -> str:
    """
    分步解析 Step1：房间名单提示词

    @param width 图片宽度（像素）
    @param height 图片高度（像素）
    @param plan_type 户型图源类型
    @param pdf_text_hint PDF 矢量文字弱 hint（可选）
    @return 完整提示词
    """
    prompt = _append_image_size(load_step1_prompt(plan_type), width, height)
    if pdf_text_hint:
        prompt += f"\n{pdf_text_hint}\n"
    return prompt


def load_step2_prompt_for_image(
    width: int,
    height: int,
    plan_type: PlanType,
    room_batch: list[VlmRoomStub],
    retry_hint: str | None = None,
    seg_hint: str | None = None,
) -> str:
    """
    分步解析 Step2：批次 polygon 提示词

    @param width 图片宽度（像素）
    @param height 图片高度（像素）
    @param plan_type 户型图源类型
    @param room_batch 本批待提取轮廓的房间
    @param retry_hint 质检失败后的修正提示
    @param seg_hint segmentation 区域 hint 文本（可选）
    @return 完整提示词
    """
    room_spec = json.dumps(
        [{"id": room.id, "name": room.name, "area_label": room.area_label} for room in room_batch],
        ensure_ascii=False,
        indent=2,
    )
    prompt = (
        f"{load_step2_prompt(plan_type)}\n\n"
        f"本次需要输出 polygon 的房间：\n{room_spec}\n"
    )
    if retry_hint:
        prompt += f"\n修正要求：\n{retry_hint}\n"
    if seg_hint:
        prompt += f"\n{seg_hint}\n"
    return _append_image_size(prompt, width, height)


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


def parse_vlm_room_list(text: str) -> VlmRoomListResult:
    """
    解析 Step1 房间名单 JSON

    @param text VLM 原始输出
    @return 房间名单
    """
    payload = extract_json_payload(text)
    return VlmRoomListResult.model_validate(payload)


def parse_vlm_polygon_batch(text: str) -> list[VlmRoomPolygon]:
    """
    解析 Step2 批次 polygon JSON

    @param text VLM 原始输出
    @return 本批房间 polygon 列表
    """
    payload = extract_json_payload(text)
    rooms = payload.get("rooms")
    if not isinstance(rooms, list):
        return []

    parsed: list[VlmRoomPolygon] = []
    for room in rooms:
        if not isinstance(room, dict):
            continue
        room_copy = dict(room)
        normalized = _normalize_polygon(room_copy.get("polygon"))
        if normalized is None:
            continue
        room_copy["polygon"] = normalized
        parsed.append(VlmRoomPolygon.model_validate(room_copy))
    return parsed


def batch_room_stubs(
    rooms: list[VlmRoomStub],
    batch_size: int = POLYGON_BATCH_SIZE,
) -> list[list[VlmRoomStub]]:
    """
    将房间名单按批切分

    @param rooms 房间名单
    @param batch_size 每批房间数
    @return 分批后的房间列表
    """
    return [rooms[index : index + batch_size] for index in range(0, len(rooms), batch_size)]


def merge_multistep_vlm(
    room_list: VlmRoomListResult,
    polygon_rooms: list[VlmRoomPolygon],
) -> VlmParseResult:
    """
    合并 Step1 名单与 Step2 polygon 批次

    @param room_list Step1 房间名单
    @param polygon_rooms Step2 全部 polygon
    @return 完整 VLM 解析结果
    """
    polygon_by_id = {room.id: room for room in polygon_rooms}
    merged_rooms: list[VlmRoom] = []
    for stub in room_list.rooms:
        polygon_room = polygon_by_id.get(stub.id)
        if polygon_room is None:
            raise ValueError(f"VLM Step2 缺少房间 {stub.id} 的 polygon")
        merged_rooms.append(
            VlmRoom(
                id=stub.id,
                name=stub.name,
                area_label=stub.area_label,
                polygon=[VlmPoint(x=point.x, y=point.y) for point in polygon_room.polygon],
            )
        )
    return VlmParseResult(scale_hint=room_list.scale_hint, rooms=merged_rooms, openings=[])


def build_validation_retry_hint(validation: FloorPlanValidation | None) -> str | None:
    """
    根据质检结果生成 VLM 重试提示

    @param validation 质检结果
    @return 重试提示文本
    """
    if validation is None or validation.level != "error":
        return None
    error_messages = [issue.message for issue in validation.issues if issue.severity == "error"]
    if not error_messages:
        return None
    lines = "\n".join(f"- {message}" for message in error_messages)
    return f"上次解析质检失败，请修正以下问题：\n{lines}"


def run_multistep_vlm_parse(
    client: Any,
    *,
    image_base64: str,
    mime_type: str,
    img_w: int,
    img_h: int,
    plan_type: PlanType,
    retry_hint: str | None = None,
    seg_hint: str | None = None,
    pdf_text_hint: str | None = None,
    vlm_model: str | None = None,
) -> tuple[VlmParseResult, int]:
    """
    分步 VLM 解析：Step1 房间名单 + Step2 分批 polygon

    @param client oMLX 客户端
    @param image_base64 图片 base64
    @param mime_type 图片 MIME
    @param img_w 图片宽
    @param img_h 图片高
    @param plan_type 图源类型
    @param retry_hint 质检失败后的修正提示
    @param seg_hint segmentation 区域 hint 文本（可选，仅 Step2）
    @param pdf_text_hint PDF 矢量文字 hint（可选，仅 Step1）
    @param vlm_model oMLX VLM alias，None 时使用客户端默认
    @return (合并后的 VLM 解析结果, VLM 调用次数)
    """
    vlm_calls = 0
    step1_text = client.chat_vision(
        load_step1_prompt_for_image(img_w, img_h, plan_type, pdf_text_hint=pdf_text_hint),
        image_base64,
        mime_type=mime_type,
        model=vlm_model,
    )
    vlm_calls += 1
    room_list = parse_vlm_room_list(step1_text)
    if not room_list.rooms:
        raise ValueError("VLM Step1 未识别到任何房间")

    polygon_rooms: list[VlmRoomPolygon] = []
    for batch in batch_room_stubs(room_list.rooms):
        step2_text = client.chat_vision(
            load_step2_prompt_for_image(
                img_w, img_h, plan_type, batch, retry_hint, seg_hint=seg_hint
            ),
            image_base64,
            mime_type=mime_type,
            model=vlm_model,
        )
        vlm_calls += 1
        polygon_rooms.extend(parse_vlm_polygon_batch(step2_text))

    return merge_multistep_vlm(room_list, polygon_rooms), vlm_calls


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
