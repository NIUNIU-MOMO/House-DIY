"""PDF 栅格化与 raster 路径解析"""

from pathlib import Path

import cv2
import numpy as np
import pytest

from app.services.floorplan.parser_pdf import (
    analyze_pdf_vector_content,
    ensure_raster_source,
    extract_pdf_for_floorplan,
    is_pdf_path,
    rasterize_pdf_first_page,
)

fitz = pytest.importorskip("fitz")


def _create_minimal_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=400, height=300)
    page.draw_rect(fitz.Rect(40, 40, 360, 260), color=(0, 0, 0), width=2)
    page.draw_line(fitz.Point(200, 40), fitz.Point(200, 260), color=(0, 0, 0), width=2)
    for index in range(15):
        page.draw_line(
            fitz.Point(50 + index * 10, 50),
            fitz.Point(50 + index * 10, 80),
            color=(0, 0, 0),
            width=1,
        )
    doc.save(str(path))
    doc.close()


def test_is_pdf_path():
    assert is_pdf_path("plan.pdf") is True
    assert is_pdf_path("plan.png") is False


def test_rasterize_pdf_first_page(tmp_path: Path):
    pdf_path = tmp_path / "plan.pdf"
    png_path = tmp_path / "source.png"
    _create_minimal_pdf(pdf_path)
    width, height = rasterize_pdf_first_page(pdf_path, png_path)
    assert png_path.is_file()
    assert width > 0 and height > 0


def test_ensure_raster_source_for_pdf(tmp_path: Path):
    pdf_path = tmp_path / "source.pdf"
    _create_minimal_pdf(pdf_path)
    raster_path, meta = ensure_raster_source(pdf_path)
    assert raster_path.suffix.lower() == ".png"
    assert meta["pdf_mode"] in {"vector_rasterized", "scan_rasterized"}
    assert meta["original_pdf"] == "source.pdf"


def test_ensure_raster_source_for_png(tmp_path: Path):
    png_path = tmp_path / "source.png"
    image = np.full((900, 1200, 3), 255, dtype=np.uint8)
    cv2.imwrite(str(png_path), image)
    raster_path, meta = ensure_raster_source(png_path)
    assert raster_path == png_path
    assert meta["low_resolution"] is False


def test_extract_pdf_for_floorplan(tmp_path: Path):
    pdf_path = tmp_path / "input.pdf"
    _create_minimal_pdf(pdf_path)
    result = extract_pdf_for_floorplan(pdf_path, tmp_path)
    assert result.raster_path.is_file()
    assert result.width > 0


def test_ensure_raster_source_vector_pdf_writes_structure(tmp_path: Path):
    pdf_path = tmp_path / "source.pdf"
    _create_minimal_pdf(pdf_path)
    raster_path, meta = ensure_raster_source(pdf_path)
    assert raster_path.is_file()
    if meta.get("pdf_mode") == "vector_rasterized":
        assert meta.get("structure_source") == "vector"
        assert (tmp_path / "source_vector_structure.png").is_file()
        assert meta.get("pdf_wall_segments", 0) >= 4
