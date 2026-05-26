from __future__ import annotations

"""
从户型与家具布局生成房间深度控制图，供 FLUX Depth ControlNet 使用。
"""

from pathlib import Path

import cv2
import numpy as np

from app.schemas.design_spec import FurniturePlacement, RoomDesignSpec
from app.schemas.floorplan import FloorPlanModel, Room
from app.services.scene_builder import (
    DEFAULT_SCALE,
    _furniture_position,
    _room_bounds,
    _room_polygon_meters,
    default_furniture_for_room,
    load_furniture_catalog,
)

DEFAULT_SIZE = 1024
FAR_DEPTH = 35
FLOOR_DEPTH = 110
WALL_DEPTH = 55
FURNITURE_BASE = 150
FURNITURE_HEIGHT_SCALE = 18


def _resolve_scale(floorplan: FloorPlanModel) -> float:
    return floorplan.scale or DEFAULT_SCALE


def _find_room(floorplan: FloorPlanModel, room_id: str) -> Room | None:
    return next((item for item in floorplan.rooms if item.id == room_id), None)


def _polygon_to_canvas(
    polygon_m: list[tuple[float, float]],
    size: int,
    margin: float = 0.12,
) -> np.ndarray:
    min_x, min_y, max_x, max_y = _room_bounds(polygon_m)
    span_x = max(max_x - min_x, 1e-3)
    span_y = max(max_y - min_y, 1e-3)
    usable = size * (1.0 - 2.0 * margin)
    scale = usable / max(span_x, span_y)
    offset_x = (size - span_x * scale) / 2.0
    offset_y = (size - span_y * scale) / 2.0
    points = []
    for x, y in polygon_m:
        px = int(round(offset_x + (x - min_x) * scale))
        py = int(round(size - (offset_y + (y - min_y) * scale)))
        points.append([px, py])
    return np.array(points, dtype=np.int32)


def _perspective_warp(image: np.ndarray) -> np.ndarray:
    height, width = image.shape[:2]
    margin = int(width * 0.08)
    src = np.float32([
        [margin, height - margin],
        [width - margin, height - margin],
        [width - margin * 2, margin * 2],
        [margin * 2, margin * 2],
    ])
    dst = np.float32([
        [0, height - 1],
        [width - 1, height - 1],
        [width - 1, 0],
        [0, 0],
    ])
    matrix = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(image, matrix, (width, height), borderValue=FAR_DEPTH)


def _furniture_rect(
    bounds: tuple[float, float, float, float],
    placement: FurniturePlacement,
    catalog_item: dict,
    polygon_pts: np.ndarray,
    size: int,
    margin: float,
) -> tuple[int, int, int, int, int] | None:
    min_x, min_y, max_x, max_y = bounds
    center_x, center_y, _ = _furniture_position(bounds, placement, catalog_item)
    width = catalog_item["width"]
    depth = catalog_item["depth"]
    height = catalog_item.get("height", 0.8)

    half_w = width / 2.0
    half_d = depth / 2.0
    corners_m = [
        (center_x - half_w, center_y - half_d),
        (center_x + half_w, center_y - half_d),
        (center_x + half_w, center_y + half_d),
        (center_x - half_w, center_y + half_d),
    ]

    span_x = max(max_x - min_x, 1e-3)
    span_y = max(max_y - min_y, 1e-3)
    usable = size * (1.0 - 2.0 * margin)
    scale = usable / max(span_x, span_y)
    offset_x = (size - span_x * scale) / 2.0
    offset_y = (size - span_y * scale) / 2.0

    canvas_corners = []
    for x, y in corners_m:
        px = int(round(offset_x + (x - min_x) * scale))
        py = int(round(size - (offset_y + (y - min_y) * scale)))
        canvas_corners.append([px, py])

    mask = np.zeros((size, size), dtype=np.uint8)
    cv2.fillPoly(mask, [polygon_pts], 255)
    center_px = int(round(offset_x + (center_x - min_x) * scale))
    center_py = int(round(size - (offset_y + (center_y - min_y) * scale)))
    if mask[min(max(center_py, 0), size - 1), min(max(center_px, 0), size - 1)] == 0:
        return None

    xs = [point[0] for point in canvas_corners]
    ys = [point[1] for point in canvas_corners]
    depth_value = int(min(235, FURNITURE_BASE + height * FURNITURE_HEIGHT_SCALE))
    return min(xs), min(ys), max(xs), max(ys), depth_value


def _resolve_furniture(room_spec: RoomDesignSpec | None, room_name: str) -> list[FurniturePlacement]:
    if room_spec is not None and room_spec.furniture:
        return room_spec.furniture
    return default_furniture_for_room(room_name)


def render_room_layout_depth(
    floorplan: FloorPlanModel,
    room_id: str,
    room_spec: RoomDesignSpec | None = None,
    size: int = DEFAULT_SIZE,
) -> bytes:
    """
    根据户型多边形与家具布局生成深度控制图 PNG

    @param floorplan 户型模型
    @param room_id 房间 ID
    @param room_spec 房间 DesignSpec（可选，用于家具）
    @param size 输出边长像素
    @return PNG 二进制
    """
    room = _find_room(floorplan, room_id)
    if room is None:
        raise ValueError(f"room {room_id} not found in floorplan")

    scale = _resolve_scale(floorplan)
    polygon_m = _room_polygon_meters(room, scale)
    bounds = _room_bounds(polygon_m)
    polygon_pts = _polygon_to_canvas(polygon_m, size)

    canvas = np.full((size, size), FAR_DEPTH, dtype=np.uint8)
    cv2.fillPoly(canvas, [polygon_pts], FLOOR_DEPTH)
    cv2.polylines(canvas, [polygon_pts], True, WALL_DEPTH, thickness=max(8, size // 128))

    min_y_px = int(polygon_pts[:, 1].min())
    max_y_px = int(polygon_pts[:, 1].max())
    if max_y_px > min_y_px:
        for y in range(min_y_px, max_y_px + 1):
            ratio = (y - min_y_px) / (max_y_px - min_y_px)
            depth = int(FLOOR_DEPTH + ratio * 25)
            row_mask = canvas[y, :] == FLOOR_DEPTH
            canvas[y, row_mask] = depth

    catalog = load_furniture_catalog()
    furniture_list = _resolve_furniture(room_spec, room.name)
    margin = 0.12
    for placement in furniture_list:
        catalog_item = catalog.get(placement.sku)
        if catalog_item is None:
            continue
        rect = _furniture_rect(bounds, placement, catalog_item, polygon_pts, size, margin)
        if rect is None:
            continue
        x1, y1, x2, y2, depth_value = rect
        cv2.rectangle(canvas, (x1, y1), (x2, y2), depth_value, thickness=-1)

    canvas = _perspective_warp(canvas)
    blur = max(11, size // 64) | 1
    canvas = cv2.GaussianBlur(canvas, (blur, blur), 0)

    success, encoded = cv2.imencode(".png", canvas)
    if not success:
        raise RuntimeError("failed to encode depth map png")
    return encoded.tobytes()


def save_room_depth_map(
    floorplan: FloorPlanModel,
    room_id: str,
    target_path,
    room_spec: RoomDesignSpec | None = None,
    size: int = DEFAULT_SIZE,
) -> bytes:
    """
    生成并保存房间深度控制图

    @param floorplan 户型模型
    @param room_id 房间 ID
    @param target_path 保存路径
    @param room_spec 房间 DesignSpec
    @param size 输出边长像素
    @return PNG 二进制
    """
    png_bytes = render_room_layout_depth(floorplan, room_id, room_spec=room_spec, size=size)
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png_bytes)
    return png_bytes
