from pathlib import Path

import cv2
import numpy as np

from app.services.floorplan.parser_preprocess import (
    STRUCTURAL_FILENAME,
    build_watermark_mask,
    crop_to_plan_region,
    inpaint_watermark,
    preprocess_floorplan_image,
    trim_cad_dimension_bands,
    watermark_brand_pixel_ratio,
)


def _write(path: Path, image: np.ndarray) -> None:
    cv2.imwrite(str(path), image)


def _cad_with_dimension_band(width: int = 420, height: int = 360) -> np.ndarray:
    image = np.full((height, width, 3), 255, dtype=np.uint8)
    plan_left = 50
    plan_right = width - 50
    plan_top = 70
    band_height = 34
    wall_top = plan_top + band_height

    for row in range(plan_top, wall_top):
        for col in range(plan_left + 10, plan_right - 10, 32):
            cv2.putText(
                image,
                str((col - plan_left) // 8),
                (col, row - plan_top + 14),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                (0, 0, 0),
                1,
                cv2.LINE_AA,
            )

    cv2.rectangle(image, (plan_left, wall_top), (plan_right, height - 40), (0, 0, 0), 2)
    cv2.line(image, (plan_left, wall_top + 90), (plan_right, wall_top + 90), (0, 0, 0), 2)
    cv2.line(image, (width // 2, wall_top), (width // 2, height - 40), (0, 0, 0), 2)
    return image


def test_crop_to_plan_region_trims_whitespace(tmp_path: Path):
    image = np.full((300, 400, 3), 255, dtype=np.uint8)
    cv2.rectangle(image, (80, 60), (320, 240), (0, 0, 0), 2)
    source = tmp_path / "cad.png"
    _write(source, image)

    cropped, offset = crop_to_plan_region(image)
    assert offset[0] >= 70
    assert offset[1] >= 50
    assert cropped.shape[0] < image.shape[0]
    assert cropped.shape[1] < image.shape[1]


def test_trim_cad_dimension_bands_removes_top_annotation(tmp_path: Path):
    image = _cad_with_dimension_band()
    cropped, _ = crop_to_plan_region(image)
    trimmed, (trim_x, trim_y) = trim_cad_dimension_bands(cropped)
    assert trim_y > 0
    assert trimmed.shape[0] < cropped.shape[0]
    assert trim_x >= 0


def test_watermark_inpaint_reduces_center_brand_color(tmp_path: Path):
    image = np.full((240, 320, 3), 245, dtype=np.uint8)
    cv2.rectangle(image, (10, 10), (310, 230), (20, 20, 20), 2)
    cv2.circle(image, (160, 120), 40, (220, 120, 40), -1)
    before_ratio = watermark_brand_pixel_ratio(image)

    mask = build_watermark_mask(image)
    repaired = inpaint_watermark(image, mask)
    after_ratio = watermark_brand_pixel_ratio(repaired)

    assert mask.max() > 0
    assert after_ratio < before_ratio * 0.5


def test_preprocess_marketing_writes_structural_and_inpaints(tmp_path: Path):
    image = np.full((240, 320, 3), 245, dtype=np.uint8)
    cv2.rectangle(image, (10, 10), (310, 230), (20, 20, 20), 2)
    cv2.circle(image, (160, 120), 36, (220, 120, 40), -1)
    source = tmp_path / "source.png"
    _write(source, image)

    structural_path, meta = preprocess_floorplan_image(
        str(source),
        plan_type="marketing_color",
        has_watermark=True,
    )

    assert Path(structural_path).name == STRUCTURAL_FILENAME
    assert Path(structural_path).is_file()
    assert meta["structural_image"] == STRUCTURAL_FILENAME
    assert meta["watermark_inpainted"] is True
    assert meta["source_width"] == 320
    assert meta["source_height"] == 240

    structural = cv2.imread(structural_path)
    assert structural is not None
    assert structural.shape[0] <= 240
    assert watermark_brand_pixel_ratio(structural) < watermark_brand_pixel_ratio(image) * 0.6


def test_preprocess_cad_trims_and_writes_structural(tmp_path: Path):
    image = _cad_with_dimension_band()
    source = tmp_path / "source.png"
    _write(source, image)

    structural_path, meta = preprocess_floorplan_image(
        str(source),
        plan_type="cad_lineart",
        has_watermark=False,
    )

    assert Path(structural_path).is_file()
    assert meta["source_width"] == image.shape[1]
    assert meta["source_height"] == image.shape[0]
    assert meta["crop_offset"][1] >= 0
    assert meta.get("dimension_trimmed") is True or meta["crop_offset"][1] > 0

    structural = cv2.imread(structural_path)
    assert structural is not None
    assert structural.shape[0] < image.shape[0]
