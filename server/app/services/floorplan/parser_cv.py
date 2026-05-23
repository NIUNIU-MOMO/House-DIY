import math
from pathlib import Path

import cv2
import numpy as np

from app.schemas.floorplan import FloorPlanModel, Point, Wall
from app.services.floorplan.parser_vlm import VlmParseResult, walls_from_rooms

MIN_WALL_COUNT = 4
MIN_LINE_LENGTH = 40
HOUGH_THRESHOLD = 80
MAX_LINE_GAP = 10


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


def _merge_similar_lines(lines: np.ndarray, angle_tol: float = 5.0, dist_tol: float = 12.0) -> list[tuple[float, float, float, float]]:
    merged: list[tuple[float, float, float, float]] = []
    for raw in lines:
        x1, y1, x2, y2 = map(float, raw[0])
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
        length = math.hypot(x2 - x1, y2 - y1)
        if length < MIN_LINE_LENGTH:
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


def extract_walls_from_image(source_path: Path, vlm_result: VlmParseResult) -> list[Wall]:
    """
    OpenCV 轮廓 + Hough 提取墙线；不足时回退 VLM 房间矩形

    @param source_path 源图片路径
    @param vlm_result VLM 解析结果
    @return 墙线段列表
    """
    fallback = walls_from_rooms(vlm_result.rooms)
    if source_path.suffix.lower() == ".pdf":
        return fallback

    image = cv2.imread(str(source_path))
    if image is None:
        return fallback

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=HOUGH_THRESHOLD,
        minLineLength=MIN_LINE_LENGTH,
        maxLineGap=MAX_LINE_GAP,
    )

    if lines is None:
        return fallback

    merged = _merge_similar_lines(lines)
    walls = _lines_to_walls(merged)
    return walls if len(walls) >= MIN_WALL_COUNT else fallback


def apply_cv_walls(model: FloorPlanModel, walls: list[Wall]) -> FloorPlanModel:
    return model.model_copy(update={"walls": walls})
