#!/usr/bin/env python3
"""生成黄金样本 fixture PNG 到 server/tests/fixtures/floorplans/"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server"
sys.path.insert(0, str(SERVER))

from tests.test_floorplan_parse_e2e import (  # noqa: E402
    GOLDEN_SAMPLES,
    _write_cad_image,
    _write_marketing_image,
)

OUT_DIR = SERVER / "tests" / "fixtures" / "floorplans"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for sample in GOLDEN_SAMPLES:
        path = OUT_DIR / f"{sample.sample_id}.png"
        if sample.plan_type == "cad_lineart":
            _write_cad_image(path, sample.width, sample.height, sample.expected_rooms)
        else:
            _write_marketing_image(path, sample.width, sample.height, sample.has_watermark)
        print(f"written {path}")
    readme = OUT_DIR / "README.md"
    readme.write_text(
        "# 黄金样本 fixture\n\n"
        "由 `scripts/generate-golden-fixtures.py` 生成，对应 docs/07 §7.1。\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
