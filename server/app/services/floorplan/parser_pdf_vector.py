"""
PDF 矢量 path 提取与 structure 图渲染
"""

import json
import logging
import math
import re
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.services.floorplan.pdf_vector_types import (
    DIMENSION_BAND_RATIO,
    MAX_PATH_SEGMENTS,
    MAX_WALL_WIDTH_PT,
    MIN_WALL_LENGTH_PT,
    PDF_VECTOR_META_FILENAME,
    VECTOR_LINE_WIDTH_PX,
    VECTOR_STRUCTURAL_FILENAME,
    PdfTextBlock,
    PdfVectorExtract,
    PdfWallSegment,
)

logger = logging.getLogger(__name__)

AREA_LABEL_PATTERN = re.compile(r"^\d+(\.\d+)?$")
ROOM_NAME_PATTERN = re.compile(r"[\u4e00-\u9fff]{1,8}")


def _segment_length(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def _point_in_dimension_band(
    x: float,
    y: float,
    page_width: float,
    page_height: float,
    *,
    band_ratio: float = DIMENSION_BAND_RATIO,
) -> bool:
    margin_x = page_width * band_ratio
    margin_y = page_height * band_ratio
    return (
        x <= margin_x
        or x >= page_width - margin_x
        or y <= margin_y
        or y >= page_height - margin_y
    )


def _segment_in_dimension_band(
    segment: PdfWallSegment,
    page_width: float,
    page_height: float,
) -> bool:
    for x, y in ((segment.x1, segment.y1), (segment.x2, segment.y2)):
        if _point_in_dimension_band(x, y, page_width, page_height):
            return True
    length = _segment_length(segment.x1, segment.y1, segment.x2, segment.y2)
    if length >= MIN_WALL_LENGTH_PT * 2:
        return False
    upper_bound = page_height * max(DIMENSION_BAND_RATIO * 2, 0.28)
    if max(segment.y1, segment.y2) <= upper_bound:
        return True
    lower_bound = page_height * (1 - max(DIMENSION_BAND_RATIO * 2, 0.28))
    if min(segment.y1, segment.y2) >= lower_bound:
        return True
    return False


def _rect_to_segments(rect: Any, width: float) -> list[PdfWallSegment]:
    x0, y0, x1, y1 = float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    segments: list[PdfWallSegment] = []
    for index in range(4):
        cx, cy = corners[index]
        nx, ny = corners[(index + 1) % 4]
        segments.append(PdfWallSegment(x1=cx, y1=cy, x2=nx, y2=ny, width=width))
    return segments


def _drawing_items_to_segments(drawing: dict[str, Any]) -> list[PdfWallSegment]:
    line_width = float(drawing.get("width") or 1.0)
    if line_width > MAX_WALL_WIDTH_PT:
        return []

    segments: list[PdfWallSegment] = []
    for item in drawing.get("items") or []:
        if not item:
            continue
        kind = item[0]
        if kind == "l" and len(item) >= 3:
            p1, p2 = item[1], item[2]
            segments.append(
                PdfWallSegment(
                    x1=float(p1.x),
                    y1=float(p1.y),
                    x2=float(p2.x),
                    y2=float(p2.y),
                    width=line_width,
                )
            )
        elif kind == "re" and len(item) >= 2:
            segments.extend(_rect_to_segments(item[1], line_width))
    return segments


def _filter_wall_segments(
    segments: list[PdfWallSegment],
    page_width: float,
    page_height: float,
) -> list[PdfWallSegment]:
    filtered: list[PdfWallSegment] = []
    for segment in segments:
        length = _segment_length(segment.x1, segment.y1, segment.x2, segment.y2)
        if length < MIN_WALL_LENGTH_PT:
            continue
        if _segment_in_dimension_band(segment, page_width, page_height) and length < MIN_WALL_LENGTH_PT * 2:
            continue
        filtered.append(segment)
    if len(filtered) > MAX_PATH_SEGMENTS:
        step = max(1, len(filtered) // MAX_PATH_SEGMENTS)
        filtered = filtered[::step][:MAX_PATH_SEGMENTS]
    return filtered


def extract_pdf_text_blocks(page: Any) -> list[PdfTextBlock]:
    """
    从 PDF 页提取文字块

    @param page PyMuPDF Page
    @return 文字块列表
    """
    blocks: list[PdfTextBlock] = []
    page_dict = page.get_text("dict")
    for block in page_dict.get("blocks") or []:
        if block.get("type") != 0:
            continue
        for line in block.get("lines") or []:
            for span in line.get("spans") or []:
                text = str(span.get("text") or "").strip()
                if not text:
                    continue
                bbox_raw = span.get("bbox")
                if not bbox_raw or len(bbox_raw) < 4:
                    continue
                bbox = (float(bbox_raw[0]), float(bbox_raw[1]), float(bbox_raw[2]), float(bbox_raw[3]))
                blocks.append(PdfTextBlock(text=text, bbox=bbox))
    return blocks


def extract_pdf_vector(page: Any, scale: float) -> PdfVectorExtract:
    """
    从 PDF 首页 get_drawings() 提取墙线段

    @param page PyMuPDF Page
    @param scale PDF pt → pixel 缩放比
    @return 矢量提取结果
    """
    page_rect = page.rect
    page_width = float(page_rect.width)
    page_height = float(page_rect.height)
    drawings = page.get_drawings()
    raw_segments: list[PdfWallSegment] = []
    for drawing in drawings:
        raw_segments.extend(_drawing_items_to_segments(drawing))

    wall_segments = _filter_wall_segments(raw_segments, page_width, page_height)
    text_blocks = extract_pdf_text_blocks(page)
    return PdfVectorExtract(
        wall_segments=wall_segments,
        text_blocks=text_blocks,
        page_width=page_width,
        page_height=page_height,
        render_scale=scale,
        path_count=len(drawings),
    )


def render_vector_structure(
    extract: PdfVectorExtract,
    output_path: Path,
    *,
    width_px: int,
    height_px: int,
) -> None:
    """
    渲染白底黑线矢量 structure 图

    @param extract 矢量提取结果
    @param output_path 输出 PNG 路径
    @param width_px 目标宽（像素）
    @param height_px 目标高（像素）
    """
    canvas = np.full((height_px, width_px, 3), 255, dtype=np.uint8)
    scale_x = width_px / extract.page_width if extract.page_width > 0 else extract.render_scale
    scale_y = height_px / extract.page_height if extract.page_height > 0 else extract.render_scale

    for segment in extract.wall_segments:
        x1 = int(round(segment.x1 * scale_x))
        y1 = int(round(segment.y1 * scale_y))
        x2 = int(round(segment.x2 * scale_x))
        y2 = int(round(segment.y2 * scale_y))
        cv2.line(canvas, (x1, y1), (x2, y2), (0, 0, 0), VECTOR_LINE_WIDTH_PX)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), canvas)


def vector_extract_to_meta(extract: PdfVectorExtract) -> dict[str, Any]:
    """
    将矢量提取结果序列化为 meta / json 字段

    @param extract 矢量提取结果
    @return 可写入 meta.json 的字段
    """
    return {
        "structure_source": "vector",
        "pdf_path_count": extract.path_count,
        "pdf_wall_segments": len(extract.wall_segments),
        "pdf_text_blocks": [
            {"text": block.text, "bbox": list(block.bbox)} for block in extract.text_blocks
        ],
        "vector_structure_image": VECTOR_STRUCTURAL_FILENAME,
        "structural_image": VECTOR_STRUCTURAL_FILENAME,
    }


def write_pdf_vector_meta(output_dir: Path, extract: PdfVectorExtract) -> Path:
    """
    写入 pdf_vector_meta.json 调试文件

    @param output_dir 项目目录
    @param extract 矢量提取结果
    @return 写入路径
    """
    payload = {
        "page_width": extract.page_width,
        "page_height": extract.page_height,
        "render_scale": extract.render_scale,
        "path_count": extract.path_count,
        "wall_segments": [
            {
                "x1": segment.x1,
                "y1": segment.y1,
                "x2": segment.x2,
                "y2": segment.y2,
                "width": segment.width,
            }
            for segment in extract.wall_segments
        ],
        "text_blocks": [{"text": block.text, "bbox": list(block.bbox)} for block in extract.text_blocks],
    }
    meta_path = output_dir / PDF_VECTOR_META_FILENAME
    meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta_path


def process_pdf_vector_page(
    page: Any,
    output_dir: Path,
    *,
    width_px: int,
    height_px: int,
    scale: float,
) -> PdfVectorExtract | None:
    """
    提取矢量 path 并渲染 structure 图

    @param page PyMuPDF 首页
    @param output_dir 输出目录
    @param width_px raster 宽（像素）
    @param height_px raster 高（像素）
    @param scale PDF pt → pixel
    @return 提取结果；无墙线时返回 None
    """
    extract = extract_pdf_vector(page, scale)
    if not extract.wall_segments:
        logger.info("PDF 矢量提取无有效墙线段，回退 raster structural")
        return None

    vector_path = output_dir / VECTOR_STRUCTURAL_FILENAME
    render_vector_structure(extract, vector_path, width_px=width_px, height_px=height_px)
    write_pdf_vector_meta(output_dir, extract)
    return extract


def is_room_name_candidate(text: str) -> bool:
    """
    是否为房间名候选

    @param text 文字
    @return True 表示可能是房间名
    """
    return bool(ROOM_NAME_PATTERN.search(text))


def is_area_label_candidate(text: str) -> bool:
    """
    是否为面积标注候选

    @param text 文字
    @return True 表示可能是面积数字
    """
    return bool(AREA_LABEL_PATTERN.match(text.strip()))
