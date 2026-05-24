"""parser_seg 形态学回退"""

from pathlib import Path

import cv2
import numpy as np
import pytest

from app.core.config import settings
from app.services.floorplan.parser_seg import (
    benchmark_seg_region_count,
    extract_room_regions,
    is_onnx_seg_configured,
    seg_backend_label,
)


@pytest.fixture
def cad_like_image(tmp_path: Path) -> Path:
    image = np.full((360, 480, 3), 255, dtype=np.uint8)
    cv2.rectangle(image, (40, 40), (440, 320), (0, 0, 0), 2)
    cv2.line(image, (240, 40), (240, 320), (0, 0, 0), 2)
    path = tmp_path / "cad.png"
    cv2.imwrite(str(path), image)
    return path


def test_seg_disabled_returns_empty(monkeypatch, cad_like_image: Path):
    monkeypatch.setattr(settings, "house_diy_seg_enabled", False)
    assert extract_room_regions(cad_like_image) == []
    count, backend = benchmark_seg_region_count(cad_like_image)
    assert count == 0
    assert backend == "disabled"


def test_morph_fallback_extracts_regions(monkeypatch, cad_like_image: Path):
    monkeypatch.setattr(settings, "house_diy_seg_enabled", True)
    monkeypatch.setattr(settings, "house_diy_seg_model_path", "")
    assert is_onnx_seg_configured() is False
    assert seg_backend_label() == "morph"
    regions = extract_room_regions(cad_like_image)
    assert len(regions) >= 1
    assert all(len(region.polygon) >= 4 for region in regions)
    count, backend = benchmark_seg_region_count(cad_like_image)
    assert count >= 1
    assert backend == "morph"
