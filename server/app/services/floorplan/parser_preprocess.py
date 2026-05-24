"""
户型图预处理：CAD 裁边、营销图水印修复、结构图生成
"""

from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.services.floorplan.parser_pdf import ensure_raster_source, is_pdf_path
from app.services.floorplan.plan_classifier import (
    PlanType,
    WATERMARK_BLUE_HUE_HIGH,
    WATERMARK_BLUE_HUE_LOW,
    WATERMARK_CENTER_RATIO,
)

STRUCTURAL_FILENAME = "source_structural.png"
DIMENSION_BAND_MAX_RATIO = 0.15
DIMENSION_BAND_STRIP_HEIGHT = 6
DIMENSION_SMALL_COMPONENT_AREA = 180
DIMENSION_SMALL_RATIO_THRESHOLD = 0.55
MIN_CROP_RETAIN_RATIO = 0.50
INPAINT_RADIUS = 5


def crop_to_plan_region(bgr: np.ndarray) -> tuple[np.ndarray, tuple[int, int]]:
    """
    裁剪掉外侧空白与标注，保留主体户型区域

    @param bgr BGR 图像
    @return (裁剪图, (offset_x, offset_y))
    """
    height, width = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    _, dark = cv2.threshold(gray, 90, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, kernel, iterations=1)
    dark = cv2.morphologyEx(
        dark,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (8, 8)),
        iterations=1,
    )

    min_contour_area = max(200, int(height * width * 0.002))
    contours, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [
        cv2.boundingRect(contour)
        for contour in contours
        if cv2.contourArea(contour) >= min_contour_area
    ]

    if boxes:
        x0 = min(box[0] for box in boxes)
        y0 = min(box[1] for box in boxes)
        x1 = max(box[0] + box[2] for box in boxes)
        y1 = max(box[1] + box[3] for box in boxes)
        x, y, crop_w, crop_h = x0, y0, x1 - x0, y1 - y0
    else:
        coords = cv2.findNonZero(dark)
        if coords is None:
            return bgr, (0, 0)
        x, y, crop_w, crop_h = cv2.boundingRect(coords)
    margin = max(8, int(min(width, height) * 0.01))
    x0 = max(0, x - margin)
    y0 = max(0, y - margin)
    x1 = min(width, x + crop_w + margin)
    y1 = min(height, y + crop_h + margin)

    cropped = bgr[y0:y1, x0:x1]
    if cropped.size == 0:
        return bgr, (0, 0)
    return cropped, (x0, y0)


def _is_dimension_annotation_strip(strip: np.ndarray) -> bool:
    if strip.size == 0:
        return False
    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(strip, connectivity=8)
    if num_labels <= 1:
        return False
    areas = stats[1:, cv2.CC_STAT_AREA]
    small_count = sum(1 for area in areas if area < DIMENSION_SMALL_COMPONENT_AREA)
    return (small_count / len(areas)) >= DIMENSION_SMALL_RATIO_THRESHOLD


def trim_cad_dimension_bands(bgr: np.ndarray) -> tuple[np.ndarray, tuple[int, int]]:
    """
    CAD 线稿：进一步裁掉外围尺寸标注带

    @param bgr BGR 图像
    @return (裁剪图, 相对输入图的 (offset_x, offset_y))
    """
    height, width = bgr.shape[:2]
    max_margin = int(min(width, height) * DIMENSION_BAND_MAX_RATIO)
    if max_margin < DIMENSION_BAND_STRIP_HEIGHT:
        return bgr, (0, 0)

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    top = 0
    for row in range(0, max_margin, DIMENSION_BAND_STRIP_HEIGHT):
        strip = binary[row : row + DIMENSION_BAND_STRIP_HEIGHT, :]
        if np.count_nonzero(strip) == 0:
            top = row + DIMENSION_BAND_STRIP_HEIGHT
            continue
        if _is_dimension_annotation_strip(strip):
            top = row + DIMENSION_BAND_STRIP_HEIGHT
        else:
            break

    bottom = height
    for row in range(height, max(height - max_margin, 0), -DIMENSION_BAND_STRIP_HEIGHT):
        strip = binary[row - DIMENSION_BAND_STRIP_HEIGHT : row, :]
        if np.count_nonzero(strip) == 0:
            bottom = row - DIMENSION_BAND_STRIP_HEIGHT
            continue
        if _is_dimension_annotation_strip(strip):
            bottom = row - DIMENSION_BAND_STRIP_HEIGHT
        else:
            break

    left = 0
    for col in range(0, max_margin, DIMENSION_BAND_STRIP_HEIGHT):
        strip = binary[:, col : col + DIMENSION_BAND_STRIP_HEIGHT]
        if np.count_nonzero(strip) == 0:
            left = col + DIMENSION_BAND_STRIP_HEIGHT
            continue
        if _is_dimension_annotation_strip(strip):
            left = col + DIMENSION_BAND_STRIP_HEIGHT
        else:
            break

    right = width
    for col in range(width, max(width - max_margin, 0), -DIMENSION_BAND_STRIP_HEIGHT):
        strip = binary[:, col - DIMENSION_BAND_STRIP_HEIGHT : col]
        if np.count_nonzero(strip) == 0:
            right = col - DIMENSION_BAND_STRIP_HEIGHT
            continue
        if _is_dimension_annotation_strip(strip):
            right = col - DIMENSION_BAND_STRIP_HEIGHT
        else:
            break

    if right - left < width * MIN_CROP_RETAIN_RATIO or bottom - top < height * MIN_CROP_RETAIN_RATIO:
        return bgr, (0, 0)

    trimmed = bgr[top:bottom, left:right]
    if trimmed.size == 0:
        return bgr, (0, 0)
    return trimmed, (left, top)


def build_watermark_mask(image_bgr: np.ndarray) -> np.ndarray:
    """
    营销图中央水印区域 mask（颜色 + 位置启发式）

    @param image_bgr BGR 图像
    @return 单通道 mask，255 表示待修复区域
    """
    height, width = image_bgr.shape[:2]
    mask = np.zeros((height, width), dtype=np.uint8)

    margin_x = int(width * (1 - WATERMARK_CENTER_RATIO) / 2)
    margin_y = int(height * (1 - WATERMARK_CENTER_RATIO) / 2)
    center_region = np.zeros((height, width), dtype=np.uint8)
    center_region[margin_y : height - margin_y, margin_x : width - margin_x] = 255

    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    hue = hsv[:, :, 0]
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]

    blue_mask = (
        (hue >= WATERMARK_BLUE_HUE_LOW)
        & (hue <= WATERMARK_BLUE_HUE_HIGH)
        & (saturation >= 30)
        & (value >= 40)
    ).astype(np.uint8) * 255

    high_sat_center = (
        (saturation >= 40)
        & (value >= 120)
        & (center_region > 0)
    ).astype(np.uint8) * 255

    mask = cv2.bitwise_or(blue_mask, high_sat_center)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))
    mask = cv2.dilate(mask, kernel, iterations=2)
    return mask


def inpaint_watermark(image_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    OpenCV inpaint 去除水印区域

    @param image_bgr BGR 图像
    @param mask 水印 mask
    @return 修复后的 BGR 图像
    """
    if mask.max() == 0:
        return image_bgr
    return cv2.inpaint(image_bgr, mask, INPAINT_RADIUS, cv2.INPAINT_TELEA)


def _prepare_structural_edges(gray: np.ndarray) -> np.ndarray:
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    thin_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    thick_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (4, 4))
    opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, thin_kernel, iterations=1)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, thick_kernel, iterations=1)
    return cv2.Canny(closed, 40, 120, apertureSize=3)


def build_structural_image(bgr: np.ndarray, plan_type: PlanType) -> np.ndarray:
    """
    生成供 VLM/CV 使用的结构增强图

    @param bgr BGR 图像
    @param plan_type 图源类型
    @return 结构增强 BGR 图像
    """
    if plan_type == "marketing_color":
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        hsv[:, :, 1] = (hsv[:, :, 1].astype(np.float32) * 0.25).astype(np.uint8)
        working = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        gray = cv2.cvtColor(working, cv2.COLOR_BGR2GRAY)
    else:
        working = bgr
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    edges = _prepare_structural_edges(gray)
    structural = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    structural[edges > 0] = (0, 0, 0)
    if plan_type == "marketing_color":
        structural = cv2.addWeighted(working, 0.55, structural, 0.45, 0)
    return structural


def watermark_brand_pixel_ratio(image_bgr: np.ndarray) -> float:
    """
    中央区域品牌色（蓝）像素占比，用于测试水印修复效果

    @param image_bgr BGR 图像
    @return 占比 0~1
    """
    height, width = image_bgr.shape[:2]
    margin_x = int(width * (1 - WATERMARK_CENTER_RATIO) / 2)
    margin_y = int(height * (1 - WATERMARK_CENTER_RATIO) / 2)
    center = image_bgr[margin_y : height - margin_y, margin_x : width - margin_x]
    if center.size == 0:
        return 0.0
    hsv = cv2.cvtColor(center, cv2.COLOR_BGR2HSV)
    hue = hsv[:, :, 0]
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    blue_mask = (
        (hue >= WATERMARK_BLUE_HUE_LOW)
        & (hue <= WATERMARK_BLUE_HUE_HIGH)
        & (saturation >= 30)
        & (value >= 40)
    )
    return float(np.count_nonzero(blue_mask)) / blue_mask.size


def _preprocess_cad(bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray, tuple[int, int], dict[str, Any]]:
    cropped, (crop_x, crop_y) = crop_to_plan_region(bgr)
    trimmed, (trim_x, trim_y) = trim_cad_dimension_bands(cropped)
    offset = (crop_x + trim_x, crop_y + trim_y)
    structural = build_structural_image(trimmed, "cad_lineart")
    extra = {
        "dimension_trimmed": trim_x > 0 or trim_y > 0,
    }
    return trimmed, structural, offset, extra


def _preprocess_marketing(
    bgr: np.ndarray,
    has_watermark: bool,
) -> tuple[np.ndarray, np.ndarray, tuple[int, int], dict[str, Any]]:
    cropped, offset = crop_to_plan_region(bgr)
    working = cropped
    watermark_inpainted = False
    if has_watermark:
        mask = build_watermark_mask(working)
        if mask.max() > 0:
            working = inpaint_watermark(working, mask)
            watermark_inpainted = True
    structural = build_structural_image(working, "marketing_color")
    extra = {
        "watermark_inpainted": watermark_inpainted,
    }
    return working, structural, offset, extra


def _preprocess_unknown(bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray, tuple[int, int], dict[str, Any]]:
    cropped, offset = crop_to_plan_region(bgr)
    structural = build_structural_image(cropped, "unknown")
    return cropped, structural, offset, {}


def preprocess_floorplan_image(
    source_path: str,
    *,
    plan_type: PlanType = "unknown",
    has_watermark: bool = False,
) -> tuple[str, dict[str, Any]]:
    """
    预处理上传图：按图源类型分支，生成 structural 图供 VLM 使用

    @param source_path 原始图片路径
    @param plan_type 图源类型
    @param has_watermark 是否检测到中央水印
    @return (structural 图路径, 元信息)
    """
    path = Path(source_path)
    meta: dict[str, Any] = {
        "source_width": 0,
        "source_height": 0,
        "crop_offset": [0, 0],
        "structural_image": STRUCTURAL_FILENAME,
        "watermark_inpainted": False,
        "dimension_trimmed": False,
        "low_resolution": False,
    }

    if is_pdf_path(path):
        path, pdf_meta = ensure_raster_source(path)
        meta.update(pdf_meta)

    image = cv2.imread(str(path))
    if image is None:
        return source_path, meta

    full_h, full_w = image.shape[:2]
    meta["source_width"] = full_w
    meta["source_height"] = full_h
    if not meta.get("low_resolution"):
        meta["low_resolution"] = min(full_w, full_h) < 800

    if plan_type == "cad_lineart":
        _, structural, offset, extra = _preprocess_cad(image)
    elif plan_type == "marketing_color":
        _, structural, offset, extra = _preprocess_marketing(image, has_watermark)
    else:
        _, structural, offset, extra = _preprocess_unknown(image)

    meta["crop_offset"] = [offset[0], offset[1]]
    meta.update(extra)

    structural_path = path.parent / STRUCTURAL_FILENAME
    cv2.imwrite(str(structural_path), structural)
    return str(structural_path), meta
