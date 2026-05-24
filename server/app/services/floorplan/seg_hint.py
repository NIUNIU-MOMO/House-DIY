"""
Seg 区域序列化：简化 polygon、构建 VLM Step2 hint payload
"""

import json

import cv2
import numpy as np

from app.schemas.floorplan import Point
from app.services.floorplan.parser_seg import SegRoomRegion

MAX_SEG_REGIONS = 8
MAX_VERTICES = 8


def _polygon_area(points: list[Point]) -> float:
    if len(points) < 3:
        return 0.0
    coords = [(p.x, p.y) for p in points]
    area = 0.0
    for index, (x1, y1) in enumerate(coords):
        x2, y2 = coords[(index + 1) % len(coords)]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def simplify_seg_polygon(points: list[Point]) -> list[dict]:
    """
    将 seg polygon 简化为不超过 MAX_VERTICES 个顶点

    @param points 原始顶点
    @return [{x, y}, ...] 简化后的顶点
    """
    if len(points) <= MAX_VERTICES:
        return [{"x": round(p.x, 1), "y": round(p.y, 1)} for p in points]

    contour = np.array([[p.x, p.y] for p in points], dtype=np.float32).reshape(-1, 1, 2)
    epsilon_ratio = 0.005
    simplified = contour
    for _ in range(20):
        epsilon = epsilon_ratio * cv2.arcLength(contour, True)
        simplified = cv2.approxPolyDP(contour, epsilon, True)
        if len(simplified) <= MAX_VERTICES:
            break
        epsilon_ratio *= 1.5

    if len(simplified) > MAX_VERTICES:
        step = max(1, len(simplified) // MAX_VERTICES)
        indices = list(range(0, len(simplified), step))[:MAX_VERTICES]
        simplified = simplified[indices]

    return [
        {"x": round(float(point[0][0]), 1), "y": round(float(point[0][1]), 1)}
        for point in simplified
    ]


def build_seg_hint_payload(regions: list[SegRoomRegion]) -> list[dict]:
    """
    按 confidence * area 降序选取 top-N seg 区域并简化 polygon

    @param regions segmentation 提取的区域列表
    @return VLM hint JSON 数组元素
    """
    if not regions:
        return []

    scored = sorted(
        regions,
        key=lambda region: region.confidence * _polygon_area(region.polygon),
        reverse=True,
    )
    payload: list[dict] = []
    for region in scored[:MAX_SEG_REGIONS]:
        payload.append(
            {
                "region_id": region.region_id,
                "polygon": simplify_seg_polygon(region.polygon),
                "confidence": region.confidence,
            }
        )
    return payload


def format_seg_hint_for_prompt(payload: list[dict]) -> str:
    """
    将 seg hint payload 格式化为 Step2 prompt 追加段

    @param payload build_seg_hint_payload 输出
    @return 可拼接到 Step2 prompt 的文本
    """
    if not payload:
        return ""
    seg_json = json.dumps(payload, ensure_ascii=False, indent=2)
    return (
        "以下 segmentation 预检测区域仅供参考，polygon 必须贴墙体内侧，勿沿色块/家具：\n"
        f"{seg_json}"
    )
