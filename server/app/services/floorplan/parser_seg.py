from __future__ import annotations

"""
房间/墙体 segmentation 辅助模块（M3）

优先加载 ONNX 模型；未配置或加载失败时回退 OpenCV 形态学区域提取。
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from app.core.config import settings
from app.schemas.floorplan import Point

logger = logging.getLogger(__name__)

MIN_REGION_AREA_RATIO = 0.02
MAX_REGION_AREA_RATIO = 0.85
MIN_POLYGON_VERTICES = 4
POLYGON_EPSILON_RATIO = 0.01


@dataclass
class SegRoomRegion:
    """segmentation 提取的房间区域"""

    region_id: str
    polygon: list[Point]
    confidence: float
    source: str


def is_onnx_seg_configured() -> bool:
    """
    是否已配置 ONNX segmentation 模型路径

    @return True 表示路径非空且文件存在
    """
    if not settings.house_diy_seg_enabled:
        return False
    if not settings.house_diy_seg_model_path:
        return False
    return Path(settings.house_diy_seg_model_path).expanduser().is_file()


def seg_backend_label() -> str:
    """
    当前 segmentation 后端标签

    @return onnx / morph / disabled
    """
    if is_onnx_seg_configured():
        return "onnx"
    if settings.house_diy_seg_enabled:
        return "morph"
    return "disabled"


def extract_room_regions(source_path: Path | str) -> list[SegRoomRegion]:
    """
    从户型图提取房间区域 polygon

    @param source_path 结构图或原图路径
    @return 房间区域列表；seg 未启用时返回空列表
    """
    if not settings.house_diy_seg_enabled:
        return []

    path = Path(source_path)
    if not path.is_file():
        return []

    if is_onnx_seg_configured():
        regions = _extract_with_onnx(path)
        if regions:
            return regions
        logger.info("ONNX seg 无结果，回退形态学提取: %s", path)

    return _extract_with_morphology(path)


def benchmark_seg_region_count(source_path: Path | str) -> tuple[int, str]:
    """
    benchmark 用：返回区域数与后端标签

    @param source_path 图片路径
    @return (区域数, 后端标签)
    """
    regions = extract_room_regions(source_path)
    return len(regions), seg_backend_label()


# =================================================================================================================


def _extract_with_onnx(path: Path) -> list[SegRoomRegion]:
    """
    使用 ONNX 模型推理房间 mask

    @param path 图片路径
    @return 房间区域列表
    """
    try:
        import onnxruntime as ort
    except ImportError:
        logger.warning("未安装 onnxruntime，跳过 ONNX seg")
        return []

    model_path = Path(settings.house_diy_seg_model_path).expanduser()
    image = cv2.imread(str(path))
    if image is None:
        return []

    try:
        session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    except Exception as exc:
        logger.warning("加载 ONNX seg 模型失败: %s", exc)
        return []

    input_meta = session.get_inputs()[0]
    input_name = input_meta.name
    shape = input_meta.shape
    target_h = int(shape[2]) if isinstance(shape[2], int) else image.shape[0]
    target_w = int(shape[3]) if isinstance(shape[3], int) else image.shape[1]

    resized = cv2.resize(image, (target_w, target_h))
    blob = resized.astype(np.float32) / 255.0
    blob = np.transpose(blob, (2, 0, 1))
    blob = np.expand_dims(blob, axis=0)

    try:
        outputs = session.run(None, {input_name: blob})
    except Exception as exc:
        logger.warning("ONNX seg 推理失败: %s", exc)
        return []

    if not outputs:
        return []

    mask = outputs[0]
    if mask.ndim == 4:
        mask = mask[0]
    if mask.ndim == 3:
        mask = np.argmax(mask, axis=0)
    mask = cv2.resize(mask.astype(np.uint8), (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)

    return _mask_to_regions(mask, source="onnx")


def _extract_with_morphology(path: Path) -> list[SegRoomRegion]:
    """
    形态学回退：从墙线围合区域提取候选房间 polygon

    @param path 图片路径
    @return 房间区域列表
    """
    image = cv2.imread(str(path))
    if image is None:
        return []

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)

    return _mask_to_regions(closed, source="morph")


def _mask_to_regions(mask: np.ndarray, *, source: str) -> list[SegRoomRegion]:
    """
    将二值/标签 mask 转为房间 polygon 列表

    @param mask 单通道 mask
    @param source 来源标签 onnx / morph
    @return 房间区域列表
    """
    height, width = mask.shape[:2]
    image_area = float(height * width)
    min_area = image_area * MIN_REGION_AREA_RATIO
    max_area = image_area * MAX_REGION_AREA_RATIO

    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions: list[SegRoomRegion] = []
    index = 0
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area or area > max_area:
            continue
        epsilon = POLYGON_EPSILON_RATIO * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        if len(approx) < MIN_POLYGON_VERTICES:
            continue
        polygon = [Point(x=float(point[0][0]), y=float(point[0][1])) for point in approx]
        index += 1
        confidence = min(1.0, area / max(min_area * 4, 1.0))
        regions.append(
            SegRoomRegion(
                region_id=f"seg{index}",
                polygon=polygon,
                confidence=round(confidence, 3),
                source=source,
            )
        )
    return regions
