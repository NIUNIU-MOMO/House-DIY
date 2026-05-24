"""
户型图源分类：CAD 线稿 / 开发商彩色 / 未知
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import cv2
import numpy as np

PlanType = Literal["cad_lineart", "marketing_color", "unknown"]

PLAN_TYPE_LABELS: dict[PlanType, str] = {
    "cad_lineart": "CAD 黑白线稿",
    "marketing_color": "开发商彩色户型图",
    "unknown": "未识别类型（按线稿模式解析）",
}

SATURATION_MARKETING_THRESHOLD = 20.0
SATURATION_CAD_THRESHOLD = 12.0
WATERMARK_CENTER_RATIO = 0.40
WATERMARK_BLUE_RATIO_THRESHOLD = 0.015
WATERMARK_BLUE_HUE_LOW = 90
WATERMARK_BLUE_HUE_HIGH = 140


@dataclass
class PlanClassification:
    plan_type: PlanType
    has_watermark: bool
    saturation_std: float
    message: str


def _read_image_bgr(source_path: Path) -> np.ndarray | None:
    if source_path.suffix.lower() == ".pdf":
        return None
    return cv2.imread(str(source_path))


def _saturation_std(image_bgr: np.ndarray) -> float:
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    return float(hsv[:, :, 1].std())


def _detect_center_watermark(image_bgr: np.ndarray) -> bool:
    height, width = image_bgr.shape[:2]
    if height < 40 or width < 40:
        return False

    margin_x = int(width * (1 - WATERMARK_CENTER_RATIO) / 2)
    margin_y = int(height * (1 - WATERMARK_CENTER_RATIO) / 2)
    center = image_bgr[margin_y : height - margin_y, margin_x : width - margin_x]
    if center.size == 0:
        return False

    hsv = cv2.cvtColor(center, cv2.COLOR_BGR2HSV)
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    blue_mask = (
        (hue >= WATERMARK_BLUE_HUE_LOW)
        & (hue <= WATERMARK_BLUE_HUE_HIGH)
        & (sat >= 30)
        & (val >= 40)
    )
    ratio = float(np.count_nonzero(blue_mask)) / blue_mask.size
    return ratio >= WATERMARK_BLUE_RATIO_THRESHOLD


def classify_floorplan_image(source_path: Path) -> PlanClassification:
    """
    根据颜色、水印等启发式规则判断户型图类型

    @param source_path 源文件路径
    @return 分类结果
    """
    image = _read_image_bgr(source_path)
    if image is None:
        return PlanClassification(
            plan_type="unknown",
            has_watermark=False,
            saturation_std=0.0,
            message="无法读取 raster 图像，按默认线稿模式处理",
        )

    saturation = _saturation_std(image)
    has_watermark = _detect_center_watermark(image)

    if has_watermark or saturation >= SATURATION_MARKETING_THRESHOLD:
        message = "检测到彩色填充或中央水印，将使用开发商彩色解析模式"
        if has_watermark:
            message = "检测到中央水印/品牌标识，将使用开发商彩色解析模式"
        return PlanClassification(
            plan_type="marketing_color",
            has_watermark=has_watermark,
            saturation_std=saturation,
            message=message,
        )

    if saturation <= SATURATION_CAD_THRESHOLD:
        return PlanClassification(
            plan_type="cad_lineart",
            has_watermark=False,
            saturation_std=saturation,
            message="检测为 CAD 黑白线稿，将使用线稿解析模式",
        )

    return PlanClassification(
        plan_type="unknown",
        has_watermark=has_watermark,
        saturation_std=saturation,
        message="图型介于线稿与彩色之间，将按线稿模式解析",
    )


def plan_type_label(plan_type: PlanType) -> str:
    """
    图源类型中文标签

    @param plan_type 图源类型
    @return 中文说明
    """
    return PLAN_TYPE_LABELS.get(plan_type, PLAN_TYPE_LABELS["unknown"])
