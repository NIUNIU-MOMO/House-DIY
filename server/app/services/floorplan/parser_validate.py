from __future__ import annotations

"""
户型 FloorPlanModel 解析结果质检
"""

from datetime import datetime, timezone

from shapely.geometry import Polygon

from app.schemas.floorplan import FloorPlanModel, FloorPlanValidation, Point, Room, ValidationIssue
from app.services.floorplan.parser_seg import SegRoomRegion
from app.services.floorplan.plan_classifier import PlanType

IOU_WARN_CAD = 0.15
IOU_ERROR_CAD = 0.30
IOU_WARN_MARKETING = 0.10
IOU_ERROR_MARKETING = 0.25
IOU_SEG_WARN_CAD = 0.12
IOU_SEG_WARN_MARKETING = 0.08
AREA_MISMATCH_RATIO = 0.30
COORD_ROUND = 1


def _polygon_from_points(points: list[Point]) -> Polygon | None:
    if len(points) < 3:
        return None
    try:
        shape = Polygon([(p.x, p.y) for p in points])
        if not shape.is_valid:
            shape = shape.buffer(0)
        if shape.is_empty or shape.area <= 0:
            return None
        return shape
    except Exception:
        return None


def polygon_iou(polygon_a: list[Point], polygon_b: list[Point]) -> float:
    """
    计算两多边形 IoU

    @param polygon_a 多边形 A 顶点
    @param polygon_b 多边形 B 顶点
    @return IoU，无法计算时返回 0
    """
    shape_a = _polygon_from_points(polygon_a)
    shape_b = _polygon_from_points(polygon_b)
    if shape_a is None or shape_b is None:
        return 0.0
    union_area = shape_a.union(shape_b).area
    if union_area <= 0:
        return 0.0
    return float(shape_a.intersection(shape_b).area / union_area)


def polygon_key(polygon: list[Point]) -> tuple[tuple[float, float], ...]:
    """归一化顶点序列，用于重复 polygon 检测。"""
    points = sorted((round(p.x, COORD_ROUND), round(p.y, COORD_ROUND)) for p in polygon)
    return tuple(points)


def _bbox_area(polygon: list[Point]) -> float:
    xs = [p.x for p in polygon]
    ys = [p.y for p in polygon]
    return max(0.0, max(xs) - min(xs)) * max(0.0, max(ys) - min(ys))


def _is_axis_aligned_rectangle(polygon: list[Point]) -> bool:
    if len(polygon) != 4:
        return False
    xs = sorted({round(p.x, COORD_ROUND) for p in polygon})
    ys = sorted({round(p.y, COORD_ROUND) for p in polygon})
    return len(xs) == 2 and len(ys) == 2


def _geometric_area_sqm(room: Room, scale: float | None) -> float | None:
    if None == scale or scale <= 0:
        return None
    pixel_area = _bbox_area(room.polygon)
    if pixel_area <= 0:
        return None
    meters_per_pixel = 1.0 / scale
    return round(pixel_area * meters_per_pixel * meters_per_pixel, 2)


def _iou_thresholds(plan_type: PlanType | None) -> tuple[float, float]:
    if plan_type == "marketing_color":
        return IOU_WARN_MARKETING, IOU_ERROR_MARKETING
    return IOU_WARN_CAD, IOU_ERROR_CAD


def _seg_iou_warn_threshold(plan_type: PlanType | None) -> float:
    if plan_type == "marketing_color":
        return IOU_SEG_WARN_MARKETING
    return IOU_SEG_WARN_CAD


def _detect_seg_vlm_mismatch(
    rooms: list[Room],
    seg_regions: list[SegRoomRegion],
    plan_type: PlanType | None,
) -> list[ValidationIssue]:
    """
    检测 VLM room polygon 与最近 seg 区域 IoU 过低

    @param rooms VLM 识别的房间
    @param seg_regions segmentation 区域
    @param plan_type 图源类型，影响 IoU 阈值
    @return SEG_VLM_MISMATCH warning 列表
    """
    if not rooms or not seg_regions:
        return []

    threshold = _seg_iou_warn_threshold(plan_type)
    issues: list[ValidationIssue] = []
    for room in rooms:
        best_iou = 0.0
        best_region_id = ""
        for region in seg_regions:
            iou = polygon_iou(room.polygon, region.polygon)
            if iou > best_iou:
                best_iou = iou
                best_region_id = region.region_id
        if best_iou >= threshold:
            continue
        issues.append(
            ValidationIssue(
                code="SEG_VLM_MISMATCH",
                severity="warning",
                message=(
                    f"{room.name}({room.id}) 与 seg 区域 {best_region_id} "
                    f"最大 IoU={best_iou:.2f} 低于阈值 {threshold:.2f}"
                ),
                room_ids=[room.id],
            )
        )
    return issues


def _detect_overlaps(rooms: list[Room], plan_type: PlanType | None) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    warn_threshold, error_threshold = _iou_thresholds(plan_type)
    for index, room_a in enumerate(rooms):
        for room_b in rooms[index + 1 :]:
            iou = polygon_iou(room_a.polygon, room_b.polygon)
            if iou <= warn_threshold:
                continue
            severity = "error" if iou >= error_threshold else "warning"
            issues.append(
                ValidationIssue(
                    code="ROOM_OVERLAP",
                    severity=severity,
                    message=f"{room_a.name}({room_a.id}) 与 {room_b.name}({room_b.id}) 重叠 IoU={iou:.2f}",
                    room_ids=[room_a.id, room_b.id],
                )
            )
    return issues


def _detect_duplicate_polygons(rooms: list[Room]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    groups: dict[tuple[tuple[float, float], ...], list[Room]] = {}
    for room in rooms:
        key = polygon_key(room.polygon)
        groups.setdefault(key, []).append(room)

    for grouped in groups.values():
        if len(grouped) < 2:
            continue
        names = "、".join(f"{room.name}({room.id})" for room in grouped)
        issues.append(
            ValidationIssue(
                code="ROOM_DUPLICATE_POLYGON",
                severity="error",
                message=f"以下房间使用了相同边界：{names}",
                room_ids=[room.id for room in grouped],
            )
        )
    return issues


def _detect_area_mismatch(rooms: list[Room], scale: float | None) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for room in rooms:
        if None == room.area or None == scale:
            continue
        geometric = _geometric_area_sqm(room, scale)
        if None == geometric or geometric <= 0:
            continue
        diff_ratio = abs(room.area - geometric) / max(room.area, geometric)
        if diff_ratio <= AREA_MISMATCH_RATIO:
            continue
        issues.append(
            ValidationIssue(
                code="AREA_MISMATCH",
                severity="warning",
                message=(
                    f"{room.name}({room.id}) 标注面积 {room.area}㎡ 与几何估算 "
                    f"{geometric}㎡ 偏差 {diff_ratio * 100:.0f}%"
                ),
                room_ids=[room.id],
            )
        )
    return issues


def _detect_all_rectangles(rooms: list[Room]) -> list[ValidationIssue]:
    if len(rooms) <= 6:
        return []
    if not rooms:
        return []
    if all(_is_axis_aligned_rectangle(room.polygon) for room in rooms):
        return [
            ValidationIssue(
                code="ALL_RECTANGLES",
                severity="warning",
                message="全部房间均为简单矩形，可能未贴墙体内侧轮廓",
                room_ids=[room.id for room in rooms],
            )
        ]
    return []


def _detect_low_room_count(rooms: list[Room]) -> list[ValidationIssue]:
    if len(rooms) >= 2:
        return []
    return [
        ValidationIssue(
            code="LOW_ROOM_COUNT",
            severity="warning",
            message="识别到的房间数少于 2，请核对是否漏房间",
            room_ids=[room.id for room in rooms],
        )
    ]


def _detect_duplicate_labels(rooms: list[Room]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    groups: dict[str, list[Room]] = {}
    for room in rooms:
        label = room.name.strip()
        if not label:
            continue
        groups.setdefault(label, []).append(room)

    for label, grouped in groups.items():
        if len(grouped) < 2:
            continue
        ids = "、".join(f"{room.name}({room.id})" for room in grouped)
        issues.append(
            ValidationIssue(
                code="ROOM_DUPLICATE_LABEL",
                severity="warning",
                message=f"存在同名房间「{label}」：{ids}",
                room_ids=[room.id for room in grouped],
            )
        )
    return issues


def _raw_polygon_from_points(points: list[Point]) -> Polygon | None:
    if len(points) < 3:
        return None
    try:
        return Polygon([(p.x, p.y) for p in points])
    except Exception:
        return None


def _detect_invalid_polygons(rooms: list[Room]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for room in rooms:
        shape = _raw_polygon_from_points(room.polygon)
        if shape is None or shape.is_empty or shape.area <= 0:
            issues.append(
                ValidationIssue(
                    code="POLYGON_INVALID",
                    severity="error",
                    message=f"{room.name}({room.id}) 多边形无效或面积为 0",
                    room_ids=[room.id],
                )
            )
            continue
        if not shape.is_valid or not shape.is_simple:
            issues.append(
                ValidationIssue(
                    code="POLYGON_INVALID",
                    severity="error",
                    message=f"{room.name}({room.id}) 多边形自交叉或拓扑无效",
                    room_ids=[room.id],
                )
            )
    return issues


def _detect_low_resolution(meta_low_resolution: bool | None) -> list[ValidationIssue]:
    if not meta_low_resolution:
        return []
    return [
        ValidationIssue(
            code="LOW_RESOLUTION",
            severity="warning",
            message="源图短边低于 800px，解析精度可能不足，建议更换更高分辨率原图",
            room_ids=[],
        )
    ]


def _resolve_level(issues: list[ValidationIssue]) -> str:
    if any(issue.severity == "error" for issue in issues):
        return "error"
    if any(issue.severity == "warning" for issue in issues):
        return "warning"
    return "pass"


def validate_floorplan(
    model: FloorPlanModel,
    plan_type: PlanType | None = None,
    *,
    low_resolution: bool = False,
    seg_regions: list[SegRoomRegion] | None = None,
) -> FloorPlanValidation:
    """
    对 FloorPlanModel 执行质检

    @param model 户型模型
    @param plan_type 图源类型，影响重叠阈值
    @param low_resolution 源图是否低分辨率
    @param seg_regions segmentation 区域（可选，用于 Seg/VLM 交叉校验）
    @return 质检结果
    """
    effective_plan_type = plan_type or model.plan_type
    issues: list[ValidationIssue] = []
    issues.extend(_detect_invalid_polygons(model.rooms))
    issues.extend(_detect_duplicate_polygons(model.rooms))
    issues.extend(_detect_duplicate_labels(model.rooms))
    issues.extend(_detect_overlaps(model.rooms, effective_plan_type))
    issues.extend(_detect_area_mismatch(model.rooms, model.scale))
    issues.extend(_detect_all_rectangles(model.rooms))
    issues.extend(_detect_low_room_count(model.rooms))
    issues.extend(_detect_low_resolution(low_resolution))
    if seg_regions is not None:
        issues.extend(_detect_seg_vlm_mismatch(model.rooms, seg_regions, effective_plan_type))

    return FloorPlanValidation(
        level=_resolve_level(issues),
        checked_at=datetime.now(timezone.utc).isoformat(),
        issues=issues,
    )


def validation_blocks_confirm(validation: FloorPlanValidation | None) -> bool:
    """
    是否应阻止 confirmed

    @param validation 质检结果
    @return True 表示不可确认
    """
    if validation is None:
        return False
    return validation.level == "error"
