from pathlib import Path

import cv2
import numpy as np
import pytest

from app.services.floorplan.parser_cv import extract_walls_from_image
from app.services.floorplan.parser_vlm import VlmParseResult, VlmRoom


@pytest.fixture
def sample_floor_image(tmp_path: Path) -> Path:
    image = np.ones((300, 400, 3), dtype=np.uint8) * 255
    cv2.rectangle(image, (40, 40), (360, 260), (0, 0, 0), 4)
    cv2.line(image, (200, 40), (200, 180), (0, 0, 0), 3)
    cv2.line(image, (40, 180), (360, 180), (0, 0, 0), 3)
    path = tmp_path / "sample_floor.png"
    cv2.imwrite(str(path), image)
    return path


def test_extract_walls_returns_at_least_four(sample_floor_image: Path):
    vlm_result = VlmParseResult(
        rooms=[
            VlmRoom(id="r1", name="客厅", x=40, y=40, width=160, height=140),
            VlmRoom(id="r2", name="卧室", x=200, y=40, width=160, height=140),
        ]
    )
    walls = extract_walls_from_image(sample_floor_image, vlm_result)
    assert len(walls) >= 4
