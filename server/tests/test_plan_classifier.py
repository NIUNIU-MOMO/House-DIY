from pathlib import Path

import cv2
import numpy as np
import pytest

from app.services.floorplan.plan_classifier import classify_floorplan_image


def _write_image(path: Path, image: np.ndarray) -> None:
    cv2.imwrite(str(path), image)


def test_classify_cad_lineart(tmp_path: Path):
    image = np.full((200, 300, 3), 245, dtype=np.uint8)
    cv2.rectangle(image, (20, 20), (280, 180), (30, 30, 30), 2)
    source = tmp_path / "cad.png"
    _write_image(source, image)

    result = classify_floorplan_image(source)
    assert result.plan_type == "cad_lineart"
    assert result.has_watermark is False


def test_classify_marketing_color_by_saturation(tmp_path: Path):
    height, width = 200, 300
    image = np.zeros((height, width, 3), dtype=np.uint8)
    for row in range(height):
        for col in range(width):
            hue = int((col / width) * 179)
            sat = int(80 + (row / height) * 120)
            val = 200
            hsv_pixel = np.uint8([[[hue, sat, val]]])
            image[row, col] = cv2.cvtColor(hsv_pixel, cv2.COLOR_HSV2BGR)[0, 0]
    source = tmp_path / "marketing.png"
    _write_image(source, image)

    result = classify_floorplan_image(source)
    assert result.plan_type == "marketing_color"
    assert "彩色" in result.message


def test_classify_marketing_color_by_center_watermark(tmp_path: Path):
    image = np.full((240, 320, 3), 240, dtype=np.uint8)
    cv2.rectangle(image, (10, 10), (310, 230), (20, 20, 20), 2)
    center_x, center_y = 160, 120
    cv2.circle(image, (center_x, center_y), 36, (220, 120, 40), -1)
    source = tmp_path / "watermark.png"
    _write_image(source, image)

    result = classify_floorplan_image(source)
    assert result.plan_type == "marketing_color"
    assert result.has_watermark is True


def test_classify_pdf_returns_unknown(tmp_path: Path):
    source = tmp_path / "plan.pdf"
    source.write_bytes(b"%PDF-1.4")
    result = classify_floorplan_image(source)
    assert result.plan_type == "unknown"
