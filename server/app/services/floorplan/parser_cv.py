import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import cv2
import numpy as np

from app.schemas.floorplan import FloorPlanModel, Point, Wall
from app.services.floorplan.parser_vlm import VlmParseResult, walls_from_room_polygons

MIN_WALL_COUNT = 4
MIN_LINE_LENGTH = 40
HOUGH_THRESHOLD = 80
MAX_LINE_GAP = 10
AXIS_ALIGN_TOL_DEG = 12.0
BOUNDS_MARGIN_RATIO = 0.06
MAX_WALLS_PER_ROOM = 12
MIN_WALL_QUALITY = 0.45


def compute_scale_pixels_per_meter(point_a: Point, point_b: Point, distance_m: float) -> float:
    """
    根据两点像素距离与实际米数计算比例尺（像素/米）

    @param point_a 起点
    @param point_b 终点
    @param distance_m 实际距离（米）
    @return 像素/米
    """
    pixel_length = math.hypot(point_b.x - point_a.x, point_b.y - point_a.y)
    if pixel_length <= 0 or distance_m <= 0:
        raise ValueError("invalid scale input")
    return pixel_length / distance_m


def _merge_similar_lines(
    lines: np.ndarray,
    angle_tol: float = 5.0,
    dist_tol: float = 12.0,
    min_line_length: float = MIN_LINE_LENGTH,
) -> list[tuple[float, float, float, float]]:
    merged: list[tuple[float, float, float, float]] = []
    for raw in lines:
        x1, y1, x2, y2 = map(float, raw[0])
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
        length = math.hypot(x2 - x1, y2 - y1)
        if length < min_line_length:
            continue

        duplicate = False
        for index, (mx1, my1, mx2, my2) in enumerate(merged):
            mangle = math.degrees(math.atan2(my2 - my1, mx2 - mx1))
            if abs(angle - mangle) <= angle_tol or abs(abs(angle - mangle) - 180) <= angle_tol:
                mid_x = (x1 + x2) / 2
                mid_y = (y1 + y2) / 2
                mmid_x = (mx1 + mx2) / 2
                mmid_y = (my1 + my2) / 2
                if math.hypot(mid_x - mmid_x, mid_y - mmid_y) <= dist_tol:
                    merged[index] = (
                        min(mx1, x1),
                        min(my1, y1),
                        max(mx2, x2),
                        max(my2, y2),
                    )
                    duplicate = True
                    break
        if not duplicate:
            merged.append((x1, y1, x2, y2))
    return merged


def _lines_to_walls(lines: list[tuple[float, float, float, float]]) -> list[Wall]:
    walls: list[Wall] = []
    for index, (x1, y1, x2, y2) in enumerate(lines, start=1):
        walls.append(
            Wall(
                id=f"cv{index}",
                points=[Point(x=x1, y=y1), Point(x=x2, y=y2)],
            )
        )
    return walls


def _is_axis_aligned(x1: float, y1: float, x2: float, y2: float) -> bool:
    angle = abs(math.degrees(math.atan2(y2 - y1, x2 - x1)))
    return (
        angle <= AXIS_ALIGN_TOL_DEG
        or abs(angle - 90) <= AXIS_ALIGN_TOL_DEG
        or abs(angle - 180) <= AXIS_ALIGN_TOL_DEG
    )


def _vlm_room_bounds(vlm_result: VlmParseResult, img_w: int, img_h: int) -> tuple[float, float, float, float] | None:
    if not vlm_result.rooms:
        return None
    margin = max(img_w, img_h) * BOUNDS_MARGIN_RATIO
    xs: list[float] = []
    ys: list[float] = []
    for room in vlm_result.rooms:
        if None not in (room.x, room.y, room.width, room.height):
            xs.extend([room.x, room.x + room.width])  # type: ignore[operator]
            ys.extend([room.y, room.y + room.height])  # type: ignore[operator]
            continue
        try:
            for point in room.polygon_points():
                xs.append(point.x)
                ys.append(point.y)
        except ValueError:
            continue
    if not xs or not ys:
        return None
    return (
        max(0.0, min(xs) - margin),
        max(0.0, min(ys) - margin),
        min(float(img_w), max(xs) + margin),
        min(float(img_h), max(ys) + margin),
    )


def _line_in_bounds(x1: float, y1: float, x2: float, y2: float, bounds: tuple[float, float, float, float]) -> bool:
    left, top, right, bottom = bounds
    mid_x = (x1 + x2) / 2
    mid_y = (y1 + y2) / 2
    return left <= mid_x <= right and top <= mid_y <= bottom


def _prepare_structural_edges(gray: np.ndarray) -> np.ndarray:
    """提取偏粗的结构墙线，弱化尺寸标注与家具细线。"""
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    thin_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    thick_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (4, 4))
    opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, thin_kernel, iterations=1)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, thick_kernel, iterations=1)
    return cv2.Canny(closed, 40, 120, apertureSize=3)


def _score_walls(
    walls: list[Wall],
    vlm_result: VlmParseResult,
    img_w: int,
    img_h: int,
) -> float:
    if len(walls) < MIN_WALL_COUNT:
        return 0.0
    room_count = max(len(vlm_result.rooms), 1)
    if len(walls) > room_count * MAX_WALLS_PER_ROOM:
        return 0.0

    bounds = _vlm_room_bounds(vlm_result, img_w, img_h)
    aligned = 0
    in_bounds = 0
    for wall in walls:
        x1, y1 = wall.points[0].x, wall.points[0].y
        x2, y2 = wall.points[1].x, wall.points[1].y
        if _is_axis_aligned(x1, y1, x2, y2):
            aligned += 1
        if bounds is None or _line_in_bounds(x1, y1, x2, y2, bounds):
            in_bounds += 1

    aligned_ratio = aligned / len(walls)
    bounds_ratio = in_bounds / len(walls)
    count_penalty = min(1.0, (room_count * 6) / len(walls))
    return aligned_ratio * 0.35 + bounds_ratio * 0.45 + count_penalty * 0.2


def _is_colored_floorplan(image: np.ndarray) -> bool:
    """彩色渲染户型（家具/地板纹理）不适合 Hough 墙线提取。"""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    return float(hsv[:, :, 1].std()) > 20.0


@dataclass
class WallExtractResult:
    walls: list[Wall]
    quality: float | None
    wall_source: Literal["cv", "polygon"]


def extract_walls_with_meta(source_path: Path, vlm_result: VlmParseResult) -> WallExtractResult:
    """
    OpenCV 提取结构墙线，并返回质量分与最终墙线来源

    @param source_path 源图片路径
    @param vlm_result VLM 解析结果
    @return 墙线提取结果
    """
    fallback = walls_from_room_polygons([room.polygon_points() for room in vlm_result.rooms])
    if source_path.suffix.lower() == ".pdf":
        return WallExtractResult(walls=fallback, quality=None, wall_source="polygon")

    image = cv2.imread(str(source_path))
    if image is None:
        return WallExtractResult(walls=fallback, quality=None, wall_source="polygon")

    if _is_colored_floorplan(image):
        return WallExtractResult(walls=fallback, quality=0.0, wall_source="polygon")

    img_h, img_w = image.shape[:2]
    min_line_length = max(MIN_LINE_LENGTH, int(min(img_w, img_h) * 0.05))

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = _prepare_structural_edges(gray)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=HOUGH_THRESHOLD,
        minLineLength=min_line_length,
        maxLineGap=MAX_LINE_GAP,
    )

    if lines is None:
        return WallExtractResult(walls=fallback, quality=0.0, wall_source="polygon")

    merged = _merge_similar_lines(lines, min_line_length=min_line_length)
    bounds = _vlm_room_bounds(vlm_result, img_w, img_h)
    filtered: list[tuple[float, float, float, float]] = []
    for x1, y1, x2, y2 in merged:
        if not _is_axis_aligned(x1, y1, x2, y2):
            continue
        if bounds is not None and not _line_in_bounds(x1, y1, x2, y2, bounds):
            continue
        filtered.append((x1, y1, x2, y2))

    cv_walls = _lines_to_walls(filtered)
    quality = _score_walls(cv_walls, vlm_result, img_w, img_h)
    if quality < MIN_WALL_QUALITY or len(cv_walls) < MIN_WALL_COUNT:
        return WallExtractResult(walls=fallback, quality=quality, wall_source="polygon")
    return WallExtractResult(walls=cv_walls, quality=quality, wall_source="cv")


def extract_walls_from_image(source_path: Path, vlm_result: VlmParseResult) -> list[Wall]:
    """
    OpenCV 提取结构墙线；质量不足时回退 VLM 房间矩形墙

    @param source_path 源图片路径
    @param vlm_result VLM 解析结果
    @return 墙线段列表
    """
    return extract_walls_with_meta(source_path, vlm_result).walls


def apply_cv_walls(model: FloorPlanModel, walls: list[Wall]) -> FloorPlanModel:
    return model.model_copy(update={"walls": walls})
