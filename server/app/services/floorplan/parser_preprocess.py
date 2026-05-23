import cv2
import numpy as np
from pathlib import Path


def crop_to_plan_region(bgr: np.ndarray) -> tuple[np.ndarray, tuple[int, int]]:
    """
    裁剪掉外侧尺寸标注，保留主体户型区域

    @param bgr BGR 图像
    @return (裁剪图, (offset_x, offset_y))
    """
    height, width = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    _, dark = cv2.threshold(gray, 90, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (4, 4))
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, kernel, iterations=1)
    dark = cv2.morphologyEx(
        dark,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (12, 12)),
        iterations=1,
    )
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


def preprocess_floorplan_image(source_path: str) -> tuple[str, dict[str, int | tuple[int, int]]]:
    """
    预处理上传图：裁剪主体并写 processed 文件

    @param source_path 原始图片路径
    @return (处理后路径, 元信息 source_width/height/crop_offset)
    """
    path = Path(source_path)
    meta: dict[str, int | tuple[int, int]] = {
        "source_width": 0,
        "source_height": 0,
        "crop_offset": (0, 0),
    }
    if path.suffix.lower() == ".pdf":
        return source_path, meta

    image = cv2.imread(str(path))
    if image is None:
        return source_path, meta

    full_h, full_w = image.shape[:2]
    meta["source_width"] = full_w
    meta["source_height"] = full_h

    cropped, offset = crop_to_plan_region(image)
    processed_path = path.parent / "source_processed.png"
    cv2.imwrite(str(processed_path), cropped)
    meta["crop_offset"] = [offset[0], offset[1]]
    return str(processed_path), meta
